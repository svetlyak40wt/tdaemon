#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Multi-engine Test Daemon in Python

Original concept by Jeff Winkler in:
http://jeffwinkler.net/nosy-run-python-unit-tests-automatically/

The present code is published under the terms of the MIT License. See LICENSE
file for more details.
"""


import contextlib
import datetime
import fnmatch
import optparse
import os
import re
import shelve
import subprocess
import sys
import types

from collections import defaultdict
from time import sleep, time

IGNORE = (
    '.bzr', '.git', '.hg', '.darcs', '.svn',
    '*.pyc', '*.pyo', '*.swp',
)

def parse_ignore(lines):
    """
    This function builds a regex to check file ignorence
    and tries to keep to the .gitignore's syntax as close
    as possible.

    For reference: http://www.kernel.org/pub/software/scm/git/docs/gitignore.html#_pattern_format

    >>> parse_ignore('*.pyc').search('blah.pyc') is not None
    True
    >>> parse_ignore('*.pyc').search('blah/minor.pyc') is not None
    True
    >>> parse_ignore('*.c').search('blah/minor.cpp') is not None
    False
    >>> parse_ignore('*.pyc\\n!blah.pyc').search('blah.pyc').groupdict()
    {'invert': 'blah.pyc'}
    >>> parse_ignore('Documentation/*.html').search('Documentation/git.html') is not None
    True
    >>> parse_ignore('Documentation/*.html').search('Documentation/pps/git.html') is not None
    False
    >>> parse_ignore('/ctags').search('subdir/ctags') is not None
    False
    >>> parse_ignore('ctags').search('subdir/ctags') is not None
    True
    >>> parse_ignore('/ctags').search('ctags') is not None
    True
    >>> parse_ignore('# *.pyc').search('blah.pyc') is not None
    False
    """
    if isinstance(lines, types.StringTypes):
        lines = lines.split('\n')

    def process(line):
        leading_slash = False
        negate = False

        if line.startswith('!'):
            negate = True
            line = line[1:]

        if line.startswith('/'):
            leading_slash = True
            line = line[1:]

        line = fnmatch.translate(line)

        if '/' in line:
            line = line.replace('.*', '[^\\/]*')

        line = line.replace('\\Z', '').replace('(?ms)', '')


        if negate:
            line = '(?P<invert>{0})'.format(line)

        if not leading_slash:
            if not line.startswith('.*'):
                line = '.*' + line

        line = '^{0}$'.format(line)

        return line

    ignore = '(%s)' % '|'.join(
        process(line)
        for line in filter(None, lines)
    )
    ignore = re.compile(ignore)
    return ignore


class Watcher(object):
    """
    Watcher class. This is the daemon that is watching every file in the
    directory and subdirectories, and that runs the test process.
    """
    def __init__(
            self,
            file_path,
            command,
            verbosity=0,
            custom_args='',
            ignore=None,
        ):
        self.verbosity = verbosity

        self.file_path = file_path
        self.command = command
        self.ignore = list(IGNORE)

        # add patterns given from command line
        if ignore:
            self.ignore.extend(d for d in ignore.split(','))

        # add patterns from .gitignore if any
        if os.path.exists('.gitignore'):
            self.ignore.extend(d for d in open('.gitignore').read().split('\n'))

        self.ignore = parse_ignore(self.ignore)

        with contextlib.closing(shelve.open('.tdaemon.state')) as shelf:
            # a cache with last modified files
            self.hot_top = shelf.get('hot-top', defaultdict(int))

        self.hot_top_limit = 20

        # check configuration
        self.check_configuration()

        self.file_list = self.walk()


    def check_configuration(self):
        """Checks if configuration is ok."""
        # checking filepath
        if not os.path.isdir(self.file_path):
            raise RuntimeError("INVALID CONFIGURATION: file path %s is not a directory" %
                os.path.abspath(self.file_path)
            )

    def walk(self, quick=False):
        """Walks through the tree and stores files mtimes.
        """

        stats = defaultdict(int)
        start = time()

        if quick:
            file_list = self.file_list.copy()
            for filename in self.hot_top:
                if os.path.isfile(filename):
                    file_list[filename] = os.path.getmtime(filename)
                    stats['files_checked'] += 1
                else:
                    file_list.pop(filename, None)
        else:
            file_list = {}

            for root, dirs, files in os.walk(self.file_path):
                stats['dirs_checked'] += 1

                # don't walk into ignored directories
                dirs_len = len(dirs)
                dirs[:] = [
                    dir
                    for dir in dirs
                    if self.ignore.search(os.path.normpath(os.path.join(root, dir))) is None
                ]
                stats['dirs_ignored'] += dirs_len - len(dirs)

                # now check files
                for name in files:
                    full_path = os.path.normpath(os.path.join(root, name))

                    stats['files_checked'] += 1

                    match = self.ignore.search(full_path)

                    if match is not None and match.groupdict().get('invert', None) is None:
                        stats['files_ignored'] += 1
                    else:
                        if os.path.isfile(full_path):
                            file_list[full_path] = os.path.getmtime(full_path)

        if self.verbosity >= 2:
            stats['time'] = time() - start
            print ', '.join('%s: %s' % (key, value) for key, value in sorted(stats.items()))

        return file_list

    def diff_list(self, list1, list2):
        """Extracts differences between lists."""
        changed = []
        new = []
        for key, value in list1.iteritems():
            if key in list2 and list2[key] != list1[key]:
                changed.append(key)
            elif key not in list2:
                new.append(key)
        return changed, new

    def run(self):
        """Runs the appropriate command"""
        print datetime.datetime.now()
        subprocess.call(self.command, shell=True)

    def loop(self):
        """Main loop daemon."""
        iteration = 0
        while True:
            sleep(1)
            # every 20 time do full rescan
            new_file_list = self.walk(quick=iteration % 30)

            if new_file_list != self.file_list:
                changed, new = self.diff_list(new_file_list, self.file_list)

                if self.verbosity >= 1:
                    if changed:
                        print 'changed:', ', '.join(changed)
                    if new:
                        print 'new:', ', '.join(new)

                for filename in changed + new:
                    self.hot_top[filename] += 1

                self.hot_top = defaultdict(
                    int,
                    sorted(self.hot_top.iteritems(), key=lambda x: x[1], reverse=True)[:self.hot_top_limit]
                )

                self.run()
                self.file_list = new_file_list
            iteration += 1

    def close(self):
        with contextlib.closing(shelve.open('.tdaemon.state')) as shelf:
            shelf['hot-top'] = self.hot_top

def main(prog_args=None):
    if prog_args is None:
        prog_args = sys.argv

    parser = optparse.OptionParser()
    parser.usage = """%s [options] 'command to run'""" % sys.argv[0]
    parser.add_option('-V', '--verbose', dest='verbosity', action='count')
    parser.add_option('--path', dest='path', default='.',
        type='str',
        help='Path to watch on.'
    )
    parser.add_option('--ignore', dest='ignore', default='',
        type='str',
        help='Defines patterns to ignore.  Use a comma-separated list. Use * to substitute many symbols.'
    )

    opt, args = parser.parse_args(prog_args)

    if args[1:]:
        command = args[1]
    else:
        print 'Please, specify a command to run'
        sys.exit(1)

    try:
        watcher = Watcher(
            opt.path,
            command,
            verbosity=opt.verbosity,
            ignore=opt.ignore,
        )
        print "Ready to watch file changes..."
        watcher.loop()
    except (KeyboardInterrupt, SystemExit):
        # Ignore when you exit via Crtl-C
        watcher.close()

    print "Bye"


if __name__ == '__main__':
    main()

