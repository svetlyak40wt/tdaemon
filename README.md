## Test Daemon

The test daemon watches the content of files in a directory and if any of them
changes (the content is edited), it runs the tests.

### Installation

If you are on Windows, you will have to add the <python_install_dir>/Scripts
directory.

#### From Source

Download the source and run:

    $ python setup.py install

#### With easy_install

    $ easy_install tdaemon

### Basic Usage

Simply run this:

    $ tdaemon nosetests

The daemon starts watching the current directory and subdirectories. As soon as
one file changes, the daemon runs ``nosetests`` and you may watch the result.

### Advanced usage

#### Change the scanned path

If you want to run the daemon from another directory than your current
directory, just run:

    $ tdaemon --path /path/to/your/project nosetests


#### Ignore directories and files

If you have a large sub-directory that will slow the scanning and contains no
tests, you can use the ``--ignore`` argument, which uses a comma-separated
list of patterns to not watch.

    $ tdaemon --ignore=docs
    $ tdaemon --ignore=docs,build,*.png

Also, tdaemon takes these patterns from the ``.gitignore`` file if it is available.

### TODO

    [ ] Make ``Watcher`` class usable from python.

### Done

    [X] implements py.test, if possible
    [X] Fixing bug: when a file vanished, the program fails.
    [X] I remember I made the first bits of the code after reading an article...
        [X] Find the link and name of the original author
        [X] add appropriate credits
    [X] Bugfix: When doing (e.g.) hg commit, it opens temporary files that are
        detected as "changed", and the daemon starts tests. It should be ignored
        (ref. ignore-directories)
    [X] Feature: If the scanned directory size if larger than the option limit,
    asking for the user to accept processing or not. Default option limit is 25MB
    [X] OBSOLETE: Add the possibility to run a custom command.
        (eg. ``python manage.py test myapp.MyTest``)
    [X] Erase the custom command option. Too dangerous
    [X] Check the only default dependency: ``nosetests``.
    [X] Add an "custom argument" option. The user may want to run specific
        commands, but the only way to do so is to send arguments rather than the
        whole external command. Tests must pass, though (no `&`, for example)
    [X] Install tdaemon as a script.
    [X] Add an "ignore" option to ignore other files (logs, sqlite database,
        image files, etc)
