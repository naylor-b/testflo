"""
Methods to provide code coverage using coverage.py.
"""
import os
import sys
import shutil
import webbrowser

try:
    import coverage
    from coverage.config import HandyConfigParser
except ImportError:
    coverage = None
else:
    coverage.process_startup()


# use to hold a global coverage obj
_coverobj = None

def _to_ini(lst):
    if lst:
        return ','.join(lst)
    return ''


def _write_temp_config(options, rcfile):
    """
    Read any .coveragerc file if it exists, and override parts of it then generate our temp config.

    Parameters
    ----------
    options : cmd line options
        Options from the command line parser.
    rcfile : str
        The name of our temporary coverage config file.
    """
    tmp_cfg = {
        'run': {
            'branch': False,
            'parallel': True,
            'concurrency': 'multiprocessing',
        },
        'report': {
            'ignore_errors': True,
            'skip_empty': True,
            'sort': '-cover',
        },
        'html': {
            'skip_empty': True,
        }
    }

    if options.coverpkgs:
        tmp_cfg['run']['source_pkgs'] = _to_ini(options.coverpkgs)

    if options.cover_omits:
        tmp_cfg['run']['omit'] = _to_ini(options.cover_omits)
        tmp_cfg['report']['omit'] = _to_ini(options.cover_omits)

    cfgparser = HandyConfigParser(our_file=True)

    if os.path.isfile('.coveragerc'):
        cfgparser.read(['.coveragerc'])

    cfgparser.read_dict(tmp_cfg)

    with open(rcfile, 'w') as f:
        cfgparser.write(f)


def setup_coverage(options):
    global _coverobj
    if _coverobj is None and (options.coverage or options.coveragehtml):
        if not coverage:
            raise RuntimeError("coverage has not been installed.")
        if not options.coverpkgs:
            raise RuntimeError("No packages specified for coverage. "
                               "Use the --coverpkg option to add a package.")
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
        _write_temp_config(options, rcfile)
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
