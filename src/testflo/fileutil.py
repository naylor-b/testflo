"""
Misc. file utility routines.
"""

import os
import sys
import itertools
import ConfigParser

from fnmatch import fnmatch
from os.path import join, dirname, basename, isfile, \
                    abspath, split, splitext


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
    startdirs = [start] if isinstance(start, basestring) else start
    if len(startdirs) == 0:
        return iter([])

    if match is None:
        matcher = bool
    elif isinstance(match, basestring):
        matcher = lambda name: fnmatch(name, match)
    else:
        matcher = match

    if dirmatch is None:
        dmatcher = bool
    elif isinstance(dirmatch, basestring):
        dmatcher = lambda name: fnmatch(name, dirmatch)
    else:
        dmatcher = dirmatch

    if isinstance(exclude, basestring):
        fmatch = lambda name: matcher(name) and not fnmatch(name, exclude)
    elif exclude is not None:
        fmatch = lambda name: matcher(name) and not exclude(name)
    else:
        fmatch = matcher

    if isinstance(direxclude, basestring):
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
    config = ConfigParser.ConfigParser()
    config.readfp(open(cfgfile))

    if config.has_option('testflo', 'skip_dirs'):
        skips = config.get('testflo', 'skip_dirs')
        options.skip_dirs = [s.strip() for s in skips.split(',') if s.strip()]


