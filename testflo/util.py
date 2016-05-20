"""
Misc. utility routines.
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
    pass

from multiprocessing.connection import arbitrary_address
import socket

from fnmatch import fnmatch
from os.path import join, dirname, basename, isfile,  abspath, split, splitext

from argparse import ArgumentParser

from testflo.cover import start_coverage, stop_coverage

_store = {}

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
                        help='Name of test report file.  Default is test_report.out.')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help="Include testspec and elapsed time in "
                             "screen output. Also shows all stderr output, even if test doesn't fail")
    parser.add_argument('--dryrun', action='store_true', dest='dryrun',
                        help="Don't actually run tests, but print "
                          "which tests would have been run.")
    parser.add_argument('-f', '--fail', action='store_true', dest='save_fails',
                        help="Save specs of failed tests to failtests.in file.")
    parser.add_argument('-i', '--isolated', action='store_true', dest='isolated',
                        help="Run each test in a separate subprocess.")
    parser.add_argument('--nompi', action='store_true', dest='nompi',
                        help="Force all tests to run without MPI. This can be useful "
                             "for debugging.")
    parser.add_argument('-x', '--stop', action='store_true', dest='stop',
                        help="Stop after the first test failure, or as soon as possible"
                             " when running concurrent tests.")
    parser.add_argument('-s', '--nocapture', action='store_true', dest='nocapture',
                        help="Standard output (stdout) will not be captured and will be"
                             " written to the screen immediately.")
    parser.add_argument('--coverage', action='store_true', dest='coverage',
                        help="Perform coverage analysis and display results on stdout")
    parser.add_argument('--coverage-html', action='store_true', dest='coveragehtml',
                        help="Perform coverage analysis and display results in browser")
    parser.add_argument('--coverpkg', action='append', dest='coverpkgs',
                        metavar='COVERPKG',
                        help="Add the given package to the coverage list. You"
                              " can use this option multiple times to cover"
                              " multiple packages.")
    parser.add_argument('--profile', action='store_true', dest='profile',
                        help="Perform profiling.")
    parser.add_argument('--profile_port', action='store', dest='prof_port',
                        default=4242, type=int,
                        help='Port used for profile viewer server.')

    parser.add_argument('-b', '--benchmark', action='store_true', dest='benchmark',
                        help='Specifies that benchmarks are to be run rather '
                             'than tests.')
    parser.add_argument('-d', '--datafile', action='store', dest='benchmarkfile',
                        metavar='DATAFILE', default='benchmark_data.csv',
                        help='Name of benchmark data file.  Default is benchmark_data.csv.')

    parser.add_argument('--noreport', action='store_true', dest='noreport',
                        help="Don't create a test results file.")

    parser.add_argument('tests', metavar='test', nargs='*',
                        help='A test method, test case, module, or directory to run.')

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
        if dmatch is not None:  # prune directories to search
            newdl = [d for d in dirlist if dmatch(d)]
            if len(newdl) != len(dirlist):
                dirlist[:] = newdl  # replace contents of dirlist to cause pruning

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


def parent_dirs(fpath):
    """Return a list of the absolute paths of the parent directory and
    each of its parent directories for the given file.
    """
    parts = abspath(fpath).split(os.path.sep)
    pdirs = []
    for i in range(2, len(parts)):
        pdirs.append(os.path.sep.join(parts[:i]))
    return pdirs[::-1]


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

    start_coverage()

    try:
        __import__(modpath)
        mod = sys.modules[modpath]
    except ImportError:
        # this might be a module that's not in the same
        # environment as testflo, so try temporarily prepending
        # its parent dirs to sys.path so it'll (hopefully) be
        # importable
        pdirs = parent_dirs(fname)
        oldpath = sys.path[:]
        sys.path.extend(pdirs)
        try:
            __import__(modpath)
            mod = sys.modules[modpath]
            # don't keep this module around in sys.modules, but
            # keep a reference to it, else multiprocessing on Windows
            # will have problems
            _store[modpath] = sys.modules[modpath]
            del sys.modules[modpath]
        finally:
            sys.path = oldpath
    finally:
        stop_coverage()

    return fname, mod


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

    if config.has_option('testflo', 'num_procs'):
        options.num_procs = int(config.get('testflo', 'num_procs'))


def get_memory_usage():
    """return memory usage for the current process"""
    k = 1024.
    try:
        # prefer psutil, it works on all platforms including Windows
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss
        return mem/(k*k)
    except ImportError:
        try:
            # fall back to getrusage, which works only on Linux and OSX
            import resource
            mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == 'darwin':
                return mem/(k*k)
            else:
                return mem/k
        except:
            return 0.

def elapsed_str(elapsed):
    """return a string of the form hh:mm:sec"""
    hrs = int(elapsed/3600)
    elapsed -= (hrs * 3600)
    mins = int(elapsed/60)
    elapsed -= (mins * 60)
    return "%02d:%02d:%.2f" % (hrs, mins, elapsed)

def get_open_address():
    """Return an open address to use for a multiprocessing manager."""
    if sys.platform == 'win32':
        return arbitrary_address("AF_PIPE")
    else:
        s = socket.socket(socket.AF_INET)
        s.bind(('localhost', 0))
        addr = s.getsockname()
        s.close()
        return addr

def to_bytes(s):
    if PY3:
        return bytes(s, 'utf-8')
    else:
        return bytes(s)

def get_addr_auth_from_args(args):
    """Determine address and authkey based on command line args."""
    if sys.platform == 'win32':
        address = args[0]
        authkey = args[1]
    else:
        address = (args[0], int(args[1]))
        authkey = args[2]

    return address, authkey

# in python3, inspect.ismethod doesn't work as you might expect, so...
if PY3:
    def ismethod(obj):
        return inspect.isfunction(obj) or inspect.ismethod(obj)
else:
    ismethod = inspect.ismethod
