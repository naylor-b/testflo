"""
Misc. file utility routines.
"""

import os
import sys
import itertools
import inspect
import warnings

from six import string_types, PY3
from six.moves.configparser import ConfigParser

try:
    from multiprocessing import cpu_count
except ImportError:
    def cpu_count():
        return 1

from fnmatch import fnmatch
from os.path import join, dirname, basename, isfile, \
                    abspath, split, splitext

from argparse import ArgumentParser


def _get_parser():
    """Returns a parser to handle command line args."""

    parser = ArgumentParser()
    parser.usage = "testflo [options]"
    parser.add_argument('-c', '--config', action='store', dest='cfg',
                        metavar='CONFIG',
                        help='Path of config file where preferences are specified.')
    parser.add_argument('-t', '--testfile', action='store', dest='testfile',
                        metavar='TESTFILE',
                        help='Path to a file containing one testspec per line.')
    parser.add_argument('--maxtime', action='store', dest='maxtime',
                        metavar='TIME_LIMIT', default=-1, type=float,
                        help='Specifies a time limit for tests to be saved to '
                             'the quicktests.in file.')

    try:
        cpus = cpu_count()
    except:
        warnings.warn('CPU count could not be determined. Defaulting to 1')
        cpus = 1

    parser.add_argument('-n', '--numprocs', type=int, action='store',
                        dest='num_procs', metavar='NUM_PROCS', default=cpus,
                        help='Number of processes to run. By default, this will '
                             'use the number of CPUs available.  To force serial'
                             ' execution, specify a value of 1.')
    parser.add_argument('-o', '--outfile', action='store', dest='outfile',
                        metavar='OUTFILE', default='test_report.out',
                        help='Name of test report file')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='If true, include testspec and elapsed time in '
                             'screen output')
    parser.add_argument('--dryrun', action='store_true', dest='dryrun',
                        help="If true, don't actually run tests, but report"
                          "which tests would have been run")
    parser.add_argument('-i', '--isolated', action='store_true', dest='isolated',
                        help="If true, run each test in a separate subprocess."
                             " This is required to run MPI tests.")
    parser.add_argument('-x', '--stop', action='store_true', dest='stop',
                        help="If true, stop after the first test failure")
    parser.add_argument('-s', '--nocapture', action='store_true', dest='nocapture',
                        help="If true, stdout will not be captured and will be"
                             " written to the screen immediately")
    parser.add_argument('tests', metavar='test', nargs='*',
                       help='A test method/case/module/directory to run')

    return parser

def _file_gen(dname, fmatch=bool, dmatch=None):
    """A generator returning files under the given directory, with optional
    file and directory filtering.

    fmatch: predicate funct
        A predicate function that returns True on a match.
        This is used to match files only.

    dmatch: predicate funct
        A predicate function that returns True on a match.
        This is used to match directories only.
    """
    if dmatch is not None and not dmatch(dname):
        return

    for path, dirlist, filelist in os.walk(dname):
        if dmatch is not None: # prune directories to search
            newdl = [d for d in dirlist if dmatch(d)]
            if len(newdl) != len(dirlist):
                dirlist[:] = newdl # replace contents of dirlist to cause pruning

        for name in [f for f in filelist if fmatch(f)]:
            yield join(path, name)


def find_files(start, match=None, exclude=None,
               dirmatch=None, direxclude=None):
    """Return filenames (using a generator).

    start: str or list of str
        Starting directory or list of directories.

    match: str or predicate funct
        Either a string containing a glob pattern to match
        or a predicate function that returns True on a match.
        This is used to match files only.

    exclude: str or predicate funct
        Either a string containing a glob pattern to exclude
        or a predicate function that returns True to exclude.
        This is used to exclude files only.

    dirmatch: str or predicate funct
        Either a string containing a glob pattern to match
        or a predicate function that returns True on a match.
        This is used to match directories only.

    direxclude: str or predicate funct
        Either a string containing a glob pattern to exclude
        or a predicate function that returns True to exclude.
        This is used to exclude directories only.

    Walks all subdirectories below each specified starting directory,
    subject to directory filtering.

    """
    startdirs = [start] if isinstance(start, string_types) else start
    if len(startdirs) == 0:
        return iter([])

    if match is None:
        matcher = bool
    elif isinstance(match, string_types):
        matcher = lambda name: fnmatch(name, match)
    else:
        matcher = match

    if dirmatch is None:
        dmatcher = bool
    elif isinstance(dirmatch, string_types):
        dmatcher = lambda name: fnmatch(name, dirmatch)
    else:
        dmatcher = dirmatch

    if isinstance(exclude, string_types):
        fmatch = lambda name: matcher(name) and not fnmatch(name, exclude)
    elif exclude is not None:
        fmatch = lambda name: matcher(name) and not exclude(name)
    else:
        fmatch = matcher

    if isinstance(direxclude, string_types):
        if dmatcher is bool:
            dmatch = lambda name: not fnmatch(name, direxclude)
        else:
            dmatch = lambda name: dmatcher(name) and not fnmatch(name, direxclude)
    elif direxclude is not None:
        dmatch = lambda name: dmatcher(name) and not direxclude(name)
    else:
        dmatch = dmatcher

    iters = [_file_gen(d, fmatch=fmatch, dmatch=dmatch) for d in startdirs]
    if len(iters) > 1:
        return itertools.chain(*iters)
    else:
        return iters[0]


def get_module_path(fpath):
    """Given a module filename, return its full Python name including
    enclosing packages. (based on existence of ``__init__.py`` files)
    """
    if basename(fpath).startswith('__init__.'):
        pnames = []
    else:
        pnames = [splitext(basename(fpath))[0]]
    path = dirname(abspath(fpath))
    while isfile(join(path, '__init__.py')):
            path, pname = split(path)
            pnames.append(pname)
    return '.'.join(pnames[::-1])


def find_module(name):
    """Return the pathname of the Python file corresponding to the
    given module name, or None if it can't be found. The
    file must be an uncompiled Python (.py) file.
    """

    nameparts = name.split('.')

    endings = [join(*nameparts)]
    endings.append(join(endings[0], '__init__.py'))
    endings[0] += '.py'

    for entry in sys.path:
        for ending in endings:
            f = join(entry, ending)
            if isfile(f):
                return f
    return None

def get_module(fname):
    """Given a filename or module path name, return a tuple
    of the form (filename, module).
    """
    if fname.endswith('.py'):
        modpath = get_module_path(fname)
        if not modpath:
            raise RuntimeError("can't find module %s" % fname)
    else:
        modpath = fname
        fname = find_module(modpath)

        if not fname:
            raise ImportError("can't import %s" % modpath)

    try:
        __import__(modpath)
    except ImportError:
        sys.path.append(os.path.dirname(fname))
        try:
            __import__(modpath)
        finally:
            sys.path.pop()

    return fname, sys.modules[modpath]

def read_test_file(testfile):
    """Reads a file containing one testspec per line."""
    with open(os.path.abspath(testfile), 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                yield line

def read_config_file(cfgfile, options):
    config = ConfigParser()
    config.readfp(open(cfgfile))

    if config.has_option('testflo', 'skip_dirs'):
        skips = config.get('testflo', 'skip_dirs')
        options.skip_dirs = [s.strip() for s in skips.split(',') if s.strip()]


# in python3, inspect.ismethod doesn't work as you might expect, so...
if PY3:
    def ismethod(obj):
        return inspect.isfunction(obj) or inspect.ismethod(obj)
else:
    ismethod = inspect.ismethod
