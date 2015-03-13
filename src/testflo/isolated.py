
"""
This is for running a test in a subprocess.
"""

import sys
import os
import traceback
import time
import subprocess
from tempfile import TemporaryFile

from testflo.util import _get_parser
from testflo.runner import TestRunner, exit_codes
from testflo.result import TestResult


def run_isolated(testspec, args):
    """This runs the test in a subprocess,
    then returns the TestResult object.
    """

    ferr = None
    try:
        start = time.time()
        ferr = TemporaryFile(mode='w+t')

        cmd = '%s %s %s' % (sys.executable,
                         os.path.join(os.path.dirname(__file__), 'isolated.py'),
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


class IsolatedTestRunner(TestRunner):
    """TestRunner that runs each test in a separate process."""

    def __init__(self, options, args):
        super(IsolatedTestRunner, self).__init__(options)
        self.get_iter = self.run_isolated_tests
        self.options = options
        self.args = [a for a in args if a.startswith('-')]

    def run_isolated_tests(self, input_iter):
        """Run test concurrently."""

        # use this test runner in the subprocesses
        self.options.isolated = False
        self.options.num_procs = 1

        for testspec in input_iter:
            result = run_isolated(testspec, self.args)
            yield result


if __name__ == '__main__':

    exitcode = 0

    try:
        options = _get_parser().parse_args()
        runner = TestRunner(options)
        result = runner.run_testspec(options.tests[0])
        if result.status != 'OK':
            sys.stderr.write(result.err_msg)
            exitcode = exit_codes[result.status]

    except:
        sys.stderr.write(traceback.format_exc())
        exitcode = exit_codes['FAIL']

    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(exitcode)
