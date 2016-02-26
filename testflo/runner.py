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
from testflo.result import TestResult
from testflo.devnull import DevNull

exit_codes = {
    'OK': 0,
    'SKIP': 42,
    'FAIL': 43,
}


def parse_test_path(testspec):
    """Return a tuple of the form (fname, module, testcase, func)
    based on the given testspec.

    The format of testspec is one of the following:
        <module>
        <module>:<testcase>
        <module>:<testcase>.<method>
        <module>:<function>

    where <module> is either the python module path or the actual
    file system path to the .py file.  A value of None in the tuple
    indicates that that part of the testspec was not present.
    """

    testspec = testspec.strip()
    testcase = method = None
    parts = testspec.split(':')
    if len(parts) > 1 and parts[1].startswith('\\'):  # windows abs path
        module = ':'.join(parts[:2])
        if len(parts) == 3:
            rest = parts[2]
        else:
            rest = ''
    else:
        module, _, rest = testspec.partition(':')

    fname, mod = get_module(module)

    if rest:
        objname, _, method = rest.partition('.')
        obj = getattr(mod, objname)
        if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
            testcase = obj
            if method:
                meth = getattr(obj, method)
                if not ismethod(meth):
                    raise TypeError("'%s' is not a method." % rest)
        elif isinstance(obj, FunctionType):
            method = obj
        else:
            raise TypeError("'%s' is not a TestCase or a function." %
                            objname)

    return (fname, mod, testcase, method)

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

def try_call(method):
    """Calls the given method, captures stdout and stderr,
    and returns the status (OK, SKIP, FAIL).
    """
    status = 'OK'
    try:
        start_profile()
        method()
    except Exception as e:
        msg = traceback.format_exc()
        if isinstance(e, unittest.SkipTest):
            status = 'SKIP'
            sys.stderr.write(str(e))
        else:
            status = 'FAIL'
            sys.stderr.write(msg)
    except:
        msg = traceback.format_exc()
        status = 'FAIL'
        sys.stderr.write(msg)
    finally:
        stop_profile()

    return status

def worker(runner, test_queue, done_queue, worker_id):
    """This is used by concurrent test processes. It takes a test
    off of the test_queue, runs it, then puts the TestResult object
    on the done_queue.
    """

    # need a unique profile output file for each worker process
    testflo.profile._prof_file = 'profile_%s.out' % worker_id

    test_count = 0
    for testspec in iter(test_queue.get, 'STOP'):
        try:
            test_count += 1
            done_queue.put(runner.run_testspec(testspec))
        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            done_queue.put(TestResult(testspec, 0., 0., 'FAIL',
                           {'err_msg': traceback.format_exc()}))

    # don't save anything unless we actually ran a test
    if test_count > 0:
        save_coverage()
        save_profile()


class TestRunner(object):
    def __init__(self, options):
        self.nocap_stdout = options.nocapture
        self.stop = options.stop
        setup_coverage(options)

    def get_iter(self, input_iter):
        """Run tests serially."""

        for test in input_iter:
            result = self.run_testspec(test)
            yield result
            if self.stop and result.status == 'FAIL':
                break

        save_coverage()

    def get_test_parent(self, mod, testcase_class, method):
        """Return the parent object that contains the test"""
        if testcase_class:
            return testcase_class(methodName=method)
        else:
            return mod

    def run_testspec(self, test):
        """Runs the test indicated by the given 'specific' testspec, which
        specifies an individual test function or method.
        """
        if isinstance(test, TestResult):
            # premature failure occurred during discovery, just return it
            return test

        start_time = time.time()
        try:
            fname, mod, testcase, method = parse_test_path(test)
        except Exception:
            return TestResult(test, start_time, time.time(), 'FAIL',
                              {'err_msg': traceback.format_exc()})
        if method is None:
            return TestResult(test, start_time, time.time(), 'FAIL',
                              {'err_msg': 'ERROR: test method not specified.'})

        parent = self.get_test_parent(mod, testcase, method)

        return self.run_test(test, parent, method)

    def run_test(self, testspec, parent, method):
        start_time = time.time()

        if self.nocap_stdout:
            outstream = sys.stdout
        else:
            outstream = DevNull()
        errstream = cStringIO()

        setup = getattr(parent, 'setUp', None)
        teardown = getattr(parent, 'tearDown', None)

        run_method = True
        run_td = True

        try:
            old_err = sys.stderr
            old_out = sys.stdout
            sys.stdout = outstream
            sys.stderr = errstream

            start_coverage()

            # if there's a setUp method, run it
            if setup:
                status = try_call(setup)
                if status != 'OK':
                    run_method = False
                    run_td = False

            if run_method:
                status = try_call(getattr(parent, method))

            if teardown and run_td:
                tdstatus = try_call(teardown)
                if status == 'OK':
                    status = tdstatus

            result = TestResult(testspec, start_time, time.time(), status,
                                {'err_msg': errstream.getvalue()})

        finally:
            stop_coverage()

            sys.stderr = old_err
            sys.stdout = old_out

        return result


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
