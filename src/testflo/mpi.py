
import sys
import os
import traceback
import time
import subprocess
from tempfile import TemporaryFile

from mpi4py import MPI


from testflo.runner import TestRunner, parse_test_path, \
                           exit_codes
from testflo.isolated import IsolatedTestRunner, run_isolated
from testflo.result import TestResult

def under_mpirun():
    """Return True if we're being executed under mpirun."""
    # TODO: this is a bit of a hack and there appears to be
    # no consistent set of environment vars between MPI
    # implementations.
    for name in os.environ.keys():
        if name.startswith('OMPI_COMM') or name.startswith('MPIR_'):
            return True
    return False

def run_mpi(testspec, nprocs, args):
    """This runs the test using mpirun in a subprocess,
    then returns the TestResult object.
    """

    ferr = None
    try:
        start = time.time()
        ferr = TemporaryFile(mode='w+t')

        cmd = 'mpirun -n %d %s %s %s' % (nprocs,
                         sys.executable,
                         os.path.join(os.path.dirname(__file__), 'mpirun.py'),
                         testspec)
        cmd = ' '.join([cmd]+args)
        p = subprocess.Popen(cmd, stderr=ferr, shell=True)
        p.wait()
        end = time.time()

        for status, val in exit_codes.items():
            if val == p.returncode:
                break
        else:
            status = 'FAIL'

        ferr.seek(0)

        result = TestResult(testspec, start, end,
                            status, ferr.read())

    except:
        # we generally shouldn't get here, but just in case,
        # handle it so that the main process doesn't hang at the
        # end when it tries to join all of the concurrent processes.
        result = TestResult(testspec, 0., 0., 'FAIL',
                            traceback.format_exc())

    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        if ferr:
            ferr.close()

    return result


class IsolatedMPITestRunner(IsolatedTestRunner):
    def run_isolated_tests(self, input_iter):
        """Run test concurrently."""

        for testspec in input_iter:
            fname, mod, testcase, method = parse_test_path(testspec)
            self.testcase = testcase
            if testcase and hasattr(testcase, 'N_PROCS'):
                yield run_mpi(testspec, testcase.N_PROCS, self.args)
            else:
                yield run_isolated(testspec, self.args)
