#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Multi-engine Test Daemon in Python

Original concept by Jeff Winkler in:
http://jeffwinkler.net/nosy-run-python-unit-tests-automatically/

The present code is published under the terms of the MIT License. See LICENSE
file for more details.
"""


import sys
import os
import optparse
import datetime
import subprocess

from time import sleep, time
from collections import defaultdict

IGNORE_EXTENSIONS = ('pyc', 'pyo', 'swp')
IGNORE_DIRS = ('.bzr', '.git', '.hg', '.darcs', '.svn')
IMPLEMENTED_TEST_PROGRAMS = ('nose', 'nosetests', 'django', 'py', 'symfony',
    'jelix',
)

# -------- Exceptions
class InvalidTestProgram(Exception):
    """Raised as soon as an unexpected test program is chosen"""
    pass

class InvalidFilePath(Exception):
    """Raised if the path to project/module is unknown/missing."""
    pass

class CancelDueToUserRequest(Exception):
    """Raised when user wants to cancel execution"""
    pass

# -------- Utils
def ask(message='Are you sure? [y/N]'):
    """Asks the user his opinion."""
    agree = False
    answer = raw_input(message).lower()
    if answer.startswith('y'):
        agree = True
    return agree

def escapearg(args):
    """Escapes characters you don't want in arguments (preventing shell
    injection)"""
    special_chars = '#&;`|*?~<>^()[]{}$\\'
    for char in special_chars:
        args = args.replace(char, '')
    return args

class Watcher(object):
    """
    Watcher class. This is the daemon that is watching every file in the
    directory and subdirectories, and that runs the test process.
    """
    debug = False

    def __init__(
            self,
            file_path,
            test_program,
            debug=False,
            custom_args='',
            ignore_dirs=None,
        ):
        self.debug = debug
        # Safe filter
        custom_args = escapearg(custom_args)

        self.file_path = file_path
        self.ignore_dirs = list(IGNORE_DIRS)
        if ignore_dirs:
            self.ignore_dirs.extend([d for d in ignore_dirs.split(',')])

        self.file_list = self.walk(file_path)
        self.test_program = test_program
        self.custom_args = custom_args

        # check configuration
        self.check_configuration(file_path, test_program, custom_args)

        self.check_dependencies()
        self.cmd = self.get_cmd()


    def check_configuration(self, file_path, test_program, custom_args):
        """Checks if configuration is ok."""
        # checking filepath
        if not os.path.isdir(file_path):
            raise InvalidFilePath("INVALID CONFIGURATION: file path %s is not a directory" %
                os.path.abspath(file_path)
            )

        if not test_program in IMPLEMENTED_TEST_PROGRAMS:
            raise InvalidTestProgram('The `%s` is unknown, or not yet implemented. Please chose another one.' % test_program)

        if custom_args:
            if not ask("WARNING!!!\nYou are about to run the following command\n\n   $ %s\n\nAre you sure you still want to proceed [y/N]? " % self.get_cmd()):
                raise CancelDueToUserRequest('Test cancelled...')

    def check_dependencies(self):
        "Checks if the test program is available in the python environnement"
        if self.test_program == 'nose':
            try:
                import nose
            except ImportError:
                sys.exit('Nosetests is not available on your system. Please install it and try to run it again')
        if self.test_program == 'py':
            try:
                import py
            except:
                sys.exit('py.test is not available on your system. Please install it and try to run it again')
        if self.test_program == 'django':
            try:
                import django
            except:
                sys.exit('django is not available on your system. Please install it and try to run it again')


    def get_cmd(self):
        """Returns the full command to be executed at runtime"""

        cmd = None
        if self.test_program in ('nose', 'nosetests'):
            cmd = "nosetests %s" % self.file_path
        elif self.test_program == 'django':
            executable = "%s/manage.py" % self.file_path
            if os.path.exists(executable):
                cmd = "python %s/manage.py test" % self.file_path
            else:
                cmd = "django-admin.py test"
        elif self.test_program == 'py':
            cmd = 'py.test %s' % self.file_path
        elif self.test_program == 'symfony':
            cmd = 'symfony test-all'
        elif self.test_program == 'jelix':
            # as seen on http://jelix.org/articles/fr/manuel-1.1/tests_unitaires
            cmd = 'php tests.php'

        if not cmd:
            raise InvalidTestProgram("The test program %s is unknown. Valid options are: `nose`, `django` and `py`" % self.test_program)

        # adding custom args
        if self.custom_args:
            cmd = '%s %s' % (cmd, self.custom_args)
        return cmd

    # Path manipulation
    def include(self, path):
        """Returns `True` if the file is not ignored"""
        for extension in IGNORE_EXTENSIONS:
            if path.endswith(extension):
                return False
        parts = path.split(os.path.sep)
        for part in parts:
            if part in self.ignore_dirs:
                return False
        return True

    def walk(self, top):
        """Walks through the tree and stores files mtimes.
        """
        file_list = {}
        stats = defaultdict(int)
        start = time()

        for root, dirs, files in os.walk(top):
            # this removes './' from begining of the line
            root = os.path.normpath(root)
            stats['dirs_checked'] += 1

            ignore = False
            for dir in self.ignore_dirs:
                if root.startswith(dir):
                    ignore = True
                    break
            if ignore:
            #if os.path.basename(root) in self.ignore_dirs:
                # Do not dig in ignored dirs
                stats['dirs_ignored'] += 1
                continue

            for name in files:
                full_path = os.path.join(root, name)
                stats['files_checked'] += 1

                if self.include(full_path):
                    if os.path.isfile(full_path):
                        file_list[full_path] = os.path.getmtime(full_path)
                else:
                    stats['files_ignored'] += 1

        if self.debug:
            stats['time'] = time() - start
            print ', '.join('%s: %s' % (key, value) for key, value in sorted(stats.items()))

        return file_list

    def diff_list(self, list1, list2):
        """Extracts differences between lists. For debug purposes"""
        for key, value in list1.iteritems():
            if key in list2 and list2[key] != list1[key]:
                print key, 'changed'
            elif key not in list2:
                print key, 'is new'

    def run(self, cmd):
        """Runs the appropriate command"""
        print datetime.datetime.now()
        subprocess.call(cmd, shell=True)

    def run_tests(self):
        """Execute tests"""
        self.run(self.cmd)

    def loop(self):
        """Main loop daemon."""
        while True:
            sleep(1)
            new_file_list = self.walk(self.file_path)
            if new_file_list != self.file_list:
                if self.debug:
                    self.diff_list(new_file_list, self.file_list)
                self.run_tests()
                self.file_list = new_file_list

def main(prog_args=None):
    """
    What do you expect?
    """
    if prog_args is None:
        prog_args = sys.argv

    parser = optparse.OptionParser()
    parser.usage = """Usage: %[prog] [options] [<path>]"""
    parser.add_option("-t", "--test-program", dest="test_program",
        default="nose", help="specifies the test-program to use. Valid values"
        " include `nose` (or `nosetests`), `django`, `py` (for `py.test`), "
        '`symfony` and `jelix`')
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
        default=False)
    parser.add_option('-s', '--size-max', dest='size_max', default=25,
        type="int", help="Sets the maximum size (in MB) of files.")
    parser.add_option('--custom-args', dest='custom_args', default='',
        type="str",
        help="Defines custom arguments to pass after the test program command")
    parser.add_option('--ignore-dirs', dest='ignore_dirs', default='',
        type="str",
        help="Defines directories to ignore.  Use a comma-separated list.")

    opt, args = parser.parse_args(prog_args)

    if args[1:]:
        path = args[1]
    else:
        path = '.'

    try:
        watcher = Watcher(
            path,
            opt.test_program,
            debug=opt.debug,
            custom_args=opt.custom_args,
            ignore_dirs=opt.ignore_dirs,
        )
        print "Ready to watch file changes..."
        watcher.loop()
    except (KeyboardInterrupt, SystemExit):
        # Ignore when you exit via Crtl-C
        pass

    print "Bye"

if __name__ == '__main__':
    main()

