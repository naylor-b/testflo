"""
Method and class for running tests under MPI.
"""

import sys
import os
import traceback
import time
import subprocess
import json

from testflo.runner import exit_codes
from testflo.isolated import IsolatedTestRunner, run_isolated
from testflo.test import Test


def run_mpi(testspec, nprocs, args):
    """This runs the test using mpirun in a subprocess,
    then returns the Test object.
    """

    info_file = None
    info = {}

    try:
        start = time.time()

        from distutils import spawn
        mpirun_exe = None
        if spawn.find_executable("mpirun") is not None:
            mpirun_exe = "mpirun"
        elif spawn.find_executable("mpiexec") is not None:
            mpirun_exe = "mpiexec"

        if mpirun_exe is None:
            raise Exception("mpirun or mpiexec was not found in the system path.")

        cmd = [mpirun_exe, '-n', str(nprocs),
               sys.executable,
               os.path.join(os.path.dirname(__file__), 'mpirun.py'),
               testspec]
        cmd = cmd+args

        p = subprocess.Popen(cmd, env=os.environ)
        p.wait()

        end = time.time()

        for status, val in exit_codes.items():
            if val == p.returncode:
                break
        else:
            status = 'FAIL'

        try:
            info_file = 'testflo.%d' % p.pid
            with open(info_file, 'r') as f:
                s = f.read()
            info = json.loads(s)
        except:
            # fail silently if we can't get subprocess info
            pass

        result = Test(testspec, status, info)

    except:
        # we generally shouldn't get here, but just in case,
        # handle it so that the main process doesn't hang at the
        # end when it tries to join all of the concurrent processes.
        result = Test(testspec, 'FAIL', err_msg=traceback.format_exc())

    finally:
        sys.stdout.flush()
        sys.stderr.flush()

    if info_file:
        try:
            os.remove(info_file)
        except OSError:
            pass

    return result


class IsolatedMPITestRunner(IsolatedTestRunner):
    def run_isolated_tests(self, input_iter):
        """Run test in isolation, possibly under MPI."""

        for test in input_iter:
            if test.status is not None:
                # test already failed during discovery, probably an
                # import failure
                yield test
            else:
                if test.nprocs > 0:
                    yield run_mpi(test, test.nprocs, self.args)
                else:
                    yield run_isolated(test, self.args)
