"""
Methods and class for running tests serially or concurrently.
"""

import os
import sys
import traceback
import time
import unittest
import inspect

from six import advance_iterator
from six.moves import cStringIO
from types import FunctionType
from multiprocessing import Queue, Process

from testflo.util import get_module, ismethod
from testflo.cover import setup_coverage, start_coverage, stop_coverage, \
                          save_coverage
from testflo.profile import start_profile, stop_profile, save_profile
import testflo.profile
from testflo.test import Test

exit_codes = {
    'OK': 0,
    'SKIP': 42,
    'FAIL': 43,
}


def get_testcase(filename, mod, tcasename):
    """Given a module and the name of a TestCase
    class, return a TestCase class object or raise an exception.
    """

    try:
        tcase = getattr(mod, tcasename)
    except AttributeError:
        raise AttributeError("Couldn't find TestCase '%s' in module '%s'" %
                               (tcasename, filename))
    if issubclass(tcase, unittest.TestCase):
        return tcase
    else:
        raise TypeError("'%s' in file '%s' is not a TestCase." %
                        (tcasename, filename))


def worker(runner, test_queue, done_queue, worker_id):
    """This is used by concurrent test processes. It takes a test
    off of the test_queue, runs it, then puts the Test object
    on the done_queue.
    """

    # need a unique profile output file for each worker process
    testflo.profile._prof_file = 'profile_%s.out' % worker_id

    test_count = 0
    for testspec in iter(test_queue.get, 'STOP'):
        try:
            test_count += 1
            done_queue.put(testspec.run())
        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            done_queue.put(Test(testspec, 'FAIL', err_msg=traceback.format_exc()))

    # don't save anything unless we actually ran a test
    if test_count > 0:
        save_coverage()
        save_profile()


class TestRunner(object):
    def __init__(self, options):
        self.stop = options.stop
        setup_coverage(options)

    def get_iter(self, input_iter):
        """Run tests serially."""

        for test in input_iter:
            result = test.run()
            yield result
            if self.stop and result.status == 'FAIL':
                break

        save_coverage()


class ConcurrentTestRunner(TestRunner):
    """TestRunner that uses the multiprocessing package
    to execute tests concurrently.
    """

    def __init__(self, options):
        super(ConcurrentTestRunner, self).__init__(options)
        self.num_procs = options.num_procs

        # only do concurrent stuff if num_procs > 1
        if self.num_procs > 1:
            self.get_iter = self.run_concurrent_tests

            # use this test runner in the concurrent workers
            worker_runner = TestRunner(options)

            # Create queues
            self.task_queue = Queue()
            self.done_queue = Queue()

            self.procs = []

            # Start worker processes
            for i in range(self.num_procs):
                worker_id = "%d_%d" % (os.getpid(), i)
                self.procs.append(Process(target=worker,
                                          args=(worker_runner, self.task_queue,
                                                self.done_queue, worker_id)))

            for proc in self.procs:
                proc.start()

    def run_concurrent_tests(self, input_iter):
        """Run tests concurrently."""

        it = iter(input_iter)
        numtests = 0
        try:
            for proc in self.procs:
                self.task_queue.put(advance_iterator(it))
                numtests += 1
        except StopIteration:
            pass
        else:
            try:
                while numtests:
                    result = self.done_queue.get()
                    yield result
                    numtests -= 1
                    if self.stop and result.status == 'FAIL':
                        break
                    self.task_queue.put(advance_iterator(it))
                    numtests += 1
            except StopIteration:
                pass

        for proc in self.procs:
            self.task_queue.put('STOP')

        for i in range(numtests):
            yield self.done_queue.get()

        for proc in self.procs:
            proc.join()
