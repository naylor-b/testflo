"""
Methods to provide code coverage using coverage.py.
"""

import os
import sys
import webbrowser

try:
    from coverage import coverage
except ImportError:
    coverage = None


# use to hold a global coverage obj
_coverobj = None

def setup_coverage(options):
    global _coverobj
    if _coverobj is None and (options.coverage or options.coveragehtml):
        if not coverage:
            raise RuntimeError("coverage has not been installed.")
        if not options.coverpkgs:
            raise RuntimeError("No packages specified for coverage")
        _coverobj = coverage(data_suffix=True, source=options.coverpkgs)
    return _coverobj

def start_coverage():
    if _coverobj:
        _coverobj.start()

def stop_coverage():
    if _coverobj:
        _coverobj.stop()

def save_coverage():
    if _coverobj:
        _coverobj.save()

def finalize_coverage(options):
    if _coverobj:
        from testflo.util import find_files, find_module
        excl = lambda n: (n.startswith('test_') and n.endswith('.py')) or \
                         n.startswith('__init__.')
        dirs = []
        for n in options.coverpkgs:
            if os.path.isdir(n):
                dirs.append(n)
            else:
                path = find_module(n)
                if path is None:
                    raise RuntimeError("Can't find module %s" % n)
                dirs.append(os.path.dirname(path))

        morfs = list(find_files(dirs, match='*.py',exclude=excl))
        _coverobj.combine()
        if options.coverage:
            _coverobj.report(morfs=morfs)
        else:
            dname = '_html'
            _coverobj.html_report(morfs=morfs, directory=dname)
            outfile = os.path.join(os.getcwd(), dname, 'index.html')

            if sys.platform == 'darwin':
                os.system('open %s' % outfile)
            else:
                webbrowser.get().open(outfile)
