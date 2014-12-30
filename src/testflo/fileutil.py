"""
Misc. file utility routines.
"""

import os
import stat
import sys
import shutil
import warnings
import itertools
import string
from hashlib import md5

from fnmatch import fnmatch
from os.path import isdir, join, dirname, basename, exists, isfile, \
                    abspath, expanduser, expandvars, \
                    split, splitext


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


def _file_dir_gen(dname, fmatch=bool, dmatch=None):
    """A generator returning files and directories under
    the given directory, with optional file and directory filtering..

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

        for name in dirlist:
            yield join(path, name)


def find_files(start, match=None, exclude=None,
               showdirs=False, dirmatch=None, direxclude=None):
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

    showdirs: bool
        If True, return names of files AND directories.

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

    gen = _file_dir_gen if showdirs else _file_gen
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
        dmatch = lambda name: dmatcher(name) and not fnmatch(name, direxclude)
    elif direxclude is not None:
        dmatch = lambda name: dmatcher(name) and not direxclude(name)
    else:
        dmatch = dmatcher

    iters = [gen(d, fmatch=fmatch, dmatch=dmatch) for d in startdirs]
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


def find_module(name, path=None, py=True):
    """Return the pathname of the Python file corresponding to the
    given module name, or None if it can't be found. If path is set, search in
    path for the file; otherwise, search in sys.path. If py is True, the
    file must be an uncompiled Python (.py) file.
    """
    if path is None:
        path = sys.path
    nameparts = name.split('.')

    endings = [join(*nameparts)]
    endings.append(join(endings[0], '__init__.py'))
    endings[0] += '.py'
    if not py:
        endings.append(endings[0]+'c')
        endings.append(endings[0]+'o')
        endings.append(endings[0]+'d')

    for entry in path:
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
