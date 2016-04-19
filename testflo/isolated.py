"""
This is for running a test in a subprocess.
"""

import sys
import os
import traceback
import time
import subprocess
import json

from testflo.util import _get_parser, get_memory_usage
from testflo.runner import TestRunner, exit_codes
from testflo.test import Test
from testflo.cover import save_coverage
from testflo.options import get_options

def run_isolated(testspec, args):
    """This runs the test in a subprocess,
    then returns the Test object.
    """

    info_file = None
    info = {}

    try:
        start = time.time()

        cmd = [sys.executable,
               os.path.join(os.path.dirname(__file__), 'isolated.py'),
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

        result = Test(testspec, start, end, status, info)

    except:
        # we generally shouldn't get here, but just in case,
        # handle it so that the main process doesn't hang at the
        # end when it tries to join all of the concurrent processes.
        result = Test(testspec, 0., 0., 'FAIL',
                            {'err_msg': traceback.format_exc()})

    finally:
        sys.stdout.flush()
        sys.stderr.flush()

    if info_file:
        try:
            os.remove(info_file)
        except OSError:
            pass

    return result


class IsolatedTestRunner(TestRunner):
    """TestRunner that runs each test in a separate process."""

    def __init__(self, options, args):
        super(IsolatedTestRunner, self).__init__(options)
        self.get_iter = self.run_isolated_tests
        self.options = options
        self.args = [a for a in args if a not in options.tests]

    def run_isolated_tests(self, input_iter):
        """Run each test isolated in a separate process."""

        # use this test runner in the subprocesses
        self.options.isolated = False
        self.options.num_procs = 1

        for test in input_iter:
            if test.status is not None:
                # test already failed during discovery, probably an
                # import failure
                yield test
            else:
                yield run_isolated(test, self.args)


if __name__ == '__main__':

    exitcode = 0
    info = {}

    try:
        options = get_options()
        test = Test(options.tests[0])
        runner = TestRunner(options)
        for result in runner.get_iter([test]):
            break

        info['memory_usage'] = get_memory_usage()

        if result.status != 'OK':
            info['err_msg'] = result.err_msg
            exitcode = exit_codes[result.status]

        save_coverage()

    except:
        info['err_msg'] = traceback.format_exc()
        exitcode = exit_codes['FAIL']

    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        with open('testflo.%d' % os.getpid(), 'w') as f:
            f.write(json.dumps(info))
        sys.exit(exitcode)
