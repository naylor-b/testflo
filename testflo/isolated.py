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

server = None

def run_single_test(test, q):
    test.run()
    q.put(test)


def init_server():
    """Start up a manager that controls a shared queue and spawns isolated
    test processes.
    """
    global server

    class QueueManager(BaseManager): pass

    queue = Queue()
    QueueManager.register('get_queue', callable=lambda:queue)
    QueueManager.register('run_test', run_single_test)
    server = QueueManager(address=('', get_options().port), authkey='foo')
    server.start()

def shutdown():
    if server is not None:
        server.shutdown()


def run_isolated(test, args):
    """This runs the test in a subprocess,
    then returns the Test object.
    """

    # info_file = None
    # info = {}
    #
    # try:
    #     test.start_time = time.time()
    #
    #     cmd = [sys.executable,
    #            os.path.join(os.path.dirname(__file__), 'isolated.py'),
    #            test.testspec]
    #     cmd = cmd+args
    #
    #     p = subprocess.Popen(cmd, env=os.environ)
    #     p.wait()
    #
    #     end = time.time()
    #
    #     for status, val in exit_codes.items():
    #         if val == p.returncode:
    #             break
    #     else:
    #         status = 'FAIL'
    #
    #     try:
    #         info_file = 'testflo.%d' % p.pid
    #         with open(info_file, 'r') as f:
    #             s = f.read()
    #         info = json.loads(s)
    #     except:
    #         # fail silently if we can't get subprocess info
    #         pass
    #
    #     test.end_time = end
    #     test.status = status
    #     test.err_msg = info.get('err_msg','')
    #
    # except:
    #     # we generally shouldn't get here, but just in case,
    #     # handle it so that the main process doesn't hang at the
    #     # end when it tries to join all of the concurrent processes.
    #     test.status = 'FAIL'
    #     test.end_time = time.time()
    #     test.err_msg = traceback.format_exc()
    #
    # finally:
    #     sys.stdout.flush()
    #     sys.stderr.flush()
    #
    # if info_file:
    #     try:
    #         os.remove(info_file)
    #     except OSError:
    #         pass

#def run_sub(t):
    q = server.get_queue()
    p = Process(target=run_single_test, args=(test, q))
    p.start()
    t = q.get()
    p.join()
    return t

    #return run_sub(test)


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


def get_client_queue():
    class QueueManager(BaseManager): pass

    # connect to the shared queue
    QueueManager.register('get_queue')
    m = QueueManager(address=('', get_options().port), authkey='foo')
    m.connect()
    return m.get_queue()


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
