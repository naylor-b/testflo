"""
This is for running a test in a subprocess.
"""

import sys
import os
import traceback
import time
import subprocess
import json

from multiprocessing.managers import BaseManager
from multiprocessing import Process, Queue
#import Queue

from testflo.util import _get_parser
from testflo.runner import TestRunner, exit_codes
from testflo.test import Test
from testflo.cover import save_coverage
from testflo.options import get_options


def run_single_test(test, q):
    test.run()
    q.put(test)

def run_isolated(test, q):
    """This runs the test in a subprocess,
    then returns the Test object.
    """

    p = Process(target=run_single_test, args=(test, q))
    p.start()
    t = q.get()
    p.join()
    q.put(t)


class IsolatedTestRunner(TestRunner):
    """TestRunner that runs each test in a separate process."""

    def __init__(self, options, args, server):
        super(IsolatedTestRunner, self).__init__(options)
        self.get_iter = self.run_isolated_tests
        self.options = options
        self.args = [a for a in args if a not in options.tests]
        self.server = server

    def run_isolated_tests(self, input_iter):
        """Run each test isolated in a separate process."""

        # use this test runner in the subprocesses
        self.options.isolated = False
        self.options.num_procs = 1

        q = self.server.get_queue()
        for test in input_iter:
            if test.status is not None:
                # test already failed during discovery, probably an
                # import failure
                yield test
            else:
                self.server.run_test(test, q)
                yield q.get()


def get_client_manager():
    class QueueManager(BaseManager): pass

    # connect to the shared queue
    QueueManager.register('get_queue')
    QueueManager.register('run_test')
    m = QueueManager(address=('', get_options().port), authkey='foo')
    m.connect()
    return m


# if __name__ == '__main__':
#
#     exitcode = 0
#     info = {}
#
#     class QueueManager(BaseManager): pass
#
#     # connect to the shared queue
#     QueueManager.register('get_queue')
#     m = QueueManager(address=('', get_options().port), authkey='foo')
#     m.connect()
#     queue = m.get_queue()
#
#     try:
#         options = get_options()
#         test = Test(options.tests[0])
#         runner = TestRunner(options)
#         for result in runner.get_iter([test]):
#             break
#
#         info['memory_usage'] = get_memory_usage()
#
#         if result.status != 'OK':
#             info['err_msg'] = result.err_msg
#             exitcode = exit_codes[result.status]
#
#         save_coverage()
#
#     except:
#         info['err_msg'] = traceback.format_exc()
#         exitcode = exit_codes['FAIL']
#
#     finally:
#         sys.stdout.flush()
#         sys.stderr.flush()
#         with open('testflo.%d' % os.getpid(), 'w') as f:
#             f.write(json.dumps(info))
#         sys.exit(exitcode)
