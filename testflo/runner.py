"""
Methods and class for running tests.
"""
from __future__ import print_function

import sys
import os

from six import advance_iterator
from multiprocessing import Queue, Process

from testflo.cover import save_coverage
from testflo.test import Test
from testflo.options import get_options
from testflo.qman import get_client_queue


def worker(test_queue, done_queue, subproc_queue, worker_id):
    """This is used by concurrent test processes. It takes a test
    off of the test_queue, runs it, then puts the Test object
    on the done_queue.
    """
    test_count = 0
    for tests in iter(test_queue.get, 'STOP'):

        done_tests = []
        for test in tests:
            try:
                test_count += 1
                done_tests.append(test.run(subproc_queue))
            except:
                # we generally shouldn't get here, but just in case,
                # handle it so that the main process doesn't hang at the
                # end when it tries to join all of the concurrent processes.
                done_tests.append(test)

        done_queue.put(done_tests)

    # don't save anything unless we actually ran a test
    if test_count > 0:
        save_coverage()


class TestRunner(object):

    def __init__(self, options, subproc_queue):
        self.stop = options.stop
        self.pre_announce = options.pre_announce
        self._queue = subproc_queue

    def get_iter(self, input_iter):
        """Run tests serially."""

        for tests in input_iter:
            stop = False
            for test in tests:
                if self.pre_announce:
                    print("    about to run %s " % test.short_name(), end='')
                    sys.stdout.flush()
                result = test.run(self._queue)
                yield result
                if self.stop:
                    if (result.status == 'FAIL' and not result.expected_fail) or (
                                  result.status == 'OK' and result.expected_fail):
                          stop = True
                          break
            if stop:
                break

        save_coverage()


class ConcurrentTestRunner(TestRunner):
    """TestRunner that uses the multiprocessing package
    to execute tests concurrently.
    """

    def __init__(self, options, subproc_queue):
        super(ConcurrentTestRunner, self).__init__(options, subproc_queue)
        self.num_procs = options.num_procs

        # only do concurrent stuff if num_procs > 1
        if self.num_procs > 1:
            self.get_iter = self.run_concurrent_tests

            # Create queues
            self.task_queue = Queue()
            self.done_queue = Queue()

            self.procs = []

            # Start worker processes
            for i in range(self.num_procs):
                worker_id = "%d_%d" % (os.getpid(), i)
                self.procs.append(Process(target=worker,
                                          args=(self.task_queue,
                                                self.done_queue, subproc_queue,
                                                worker_id)))

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
                    stop = False
                    results = self.done_queue.get()
                    for result in results:
                        yield result
                        if self.stop:
                            if (result.status == 'FAIL' and not result.expected_fail) or (
                                  result.status == 'OK' and result.expected_fail):
                                stop = True
                                break
                    if stop:
                        break
                    numtests -= 1
                    self.task_queue.put(advance_iterator(it))
                    numtests += 1
            except StopIteration:
                pass

        for proc in self.procs:
            self.task_queue.put('STOP')

        for i in range(numtests):
            results = self.done_queue.get()
            for result in results:
                yield result

        for proc in self.procs:
            proc.join()
