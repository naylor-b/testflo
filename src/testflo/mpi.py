
import sys
import os
import traceback
import time
import subprocess
from tempfile import TemporaryFile

from multiprocessing import Process
from mpi4py import MPI


from testflo.runner import TestRunner, IsolatedTestRunner, parse_test_path
from testflo.result import TestResult

exit_codes = {
    'OK': 0,
    'SKIP': 42,
    'FAIL': 43,
}


def mpi_worker(nprocs, test_queue, done_queue, options):
    """This is used by mpi test processes. It takes a test
    off of the test_queue, runs it using mpirun in a subprocess,
    then puts the TestResult object on the done_queue.
    """

    for testspec in iter(test_queue.get, 'STOP'):
        ferr = None
        try:
            start = time.time()
            ferr = TemporaryFile(mode='w+t')

            cmd = 'mpirun -n %d %s %s %s' % (nprocs,
                             sys.executable,
                             os.path.join(os.path.dirname(__file__), 'mpirun.py'),
                             testspec)
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
                                status,
                                ferr.read())

            done_queue.put(result)
        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            done_queue.put(TestResult(testspec, 0., 0., 'FAIL',
                           traceback.format_exc()))

        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            if ferr:
                ferr.close()


class IsolatedMPITestRunner(IsolatedTestRunner):
    def get_process(self, testspec):
        fname, mod, testcase, method = parse_test_path(testspec)
        self.testcase = testcase
        if testcase and hasattr(testcase, 'N_PROCS'):
            # Start worker process
            return Process(target=mpi_worker,
                           args=(testcase.N_PROCS,
                                 self.task_queue,
                                 self.done_queue,
                                 self.options))
        else:
            return super(IsolatedMPITestRunner, self).get_process(testspec)
