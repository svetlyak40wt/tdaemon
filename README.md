## Test Daemon

The daemon watches the content of files in a directory and if any of them
changes (the content is edited), it runs the given command.

### Installation

If you are on Windows, you will have to add the <python_install_dir>/Scripts
directory.

#### With pip

    $ pip install 'git+https://github.com/svetlyak40wt/tdaemon@develop#egg=tdaemon'

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

Also, tdaemon takes these patterns from the ``.gitignore`` file if it
is available.

### Development

Feel free to fork this project and to send patches back. If you found
a bug or want to propose a feature, [file theissue](https://github.com/svetlyak40wt/tdaemon/issues)
at the GitHub.

To run tdaemon's tests, install nose and run: `nosetests --with-doctest tdaemon.py`