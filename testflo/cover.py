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
    print "setup coverage..."
    global _coverobj
    if _coverobj is None and (options.coverage or options.coveragehtml):
        if not coverage:
            raise RuntimeError("coverage has not been installed.")
        if not options.coverpkgs:
            raise RuntimeError("No packages specified for coverage. "
                               "Use the --coverpkg option to add a package.")
        _coverobj = coverage(data_suffix=True, source=options.coverpkgs)
    return _coverobj

def start_coverage():
    print "starting coverage..."
    if _coverobj:
        _coverobj.start()

def stop_coverage():
    print "stopping coverage..."
    if _coverobj:
        _coverobj.stop()

def save_coverage():
    print "saving coverage..."
    if _coverobj:
        _coverobj.save()
    import subprocess
    subprocess.call(["ls", "-ltra"])

def finalize_coverage(options):
    print "finalizing coverage..."
    if _coverobj and options.coverpkgs:
        rank = 0
        if options.isolated:
            try:
                from mpi4py import MPI
                rank = MPI.COMM_WORLD.rank
            except ImportError:
                pass
        if rank == 0:
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

            morfs = list(find_files(dirs, match='*.py', exclude=excl))

            _coverobj.combine()

            # write combined data to default filename (needed for coveralls)
            # (NOTE: get_data() should prob be used here, but it returns None)
            _coverobj.data.write_file('.coverage')

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
