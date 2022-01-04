"""
Methods to provide code coverage using coverage.py.
"""
import os
import sys
import shutil
import webbrowser

try:
    import coverage
except ImportError:
    coverage = None
else:
    coverage.process_startup()

_covrc_template = """
[run]
branch = False
parallel = True
concurrency = multiprocessing
source_pkgs = %s
omit = %s


[report]
ignore_errors = True
skip_empty = True
omit = %s


[html]
skip_empty = True
"""

# use to hold a global coverage obj
_coverobj = None

def _to_ini(lst):
    return ','.join(lst)


def setup_coverage(options):
    global _coverobj
    if _coverobj is None and (options.coverage or options.coveragehtml):
        oldcov = os.path.join(os.getcwd(), '.coverage')
        if os.path.isfile(oldcov):
            os.remove(oldcov)
        covdir = os.path.join(os.getcwd(), '_covdir')
        if os.path.isdir('_covdir'):
            shutil.rmtree('_covdir')
        os.mkdir('_covdir')
        os.environ['COVERAGE_RUN'] = 'true'
        os.environ['COVERAGE_RCFILE'] = rcfile = os.path.join(covdir, '_coveragerc_')
        os.environ['COVERAGE_FILE'] = covfile = os.path.join(covdir, '.coverage')
        os.environ['COVERAGE_PROCESS_START'] = rcfile
        if not coverage:
            raise RuntimeError("coverage has not been installed.")
        if not options.coverpkgs:
            raise RuntimeError("No packages specified for coverage. "
                               "Use the --coverpkg option to add a package.")
        with open(rcfile, 'w') as f:
            content = _covrc_template % (_to_ini(options.coverpkgs), _to_ini(options.cover_omits),
                                         _to_ini(options.cover_omits))
            f.write(content)
        _coverobj = coverage.Coverage(data_file=covfile, data_suffix=True, config_file=rcfile)
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
    if _coverobj and options.coverpkgs:
        rank = 0
        if not options.nompi:
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
            _coverobj.save()

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

            shutil.copy(_coverobj.get_data().data_filename(),
                        os.path.join(os.getcwd(), '.coverage'))
