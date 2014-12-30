"""
testflo is a python testing framework that takes an iterator of test
specifier names e.g., <test_module>:<testcase>.<test_method>), and feeds
them through a pipeline of objects that operate on them and transform them
into TestResult objects, then pass them on to other objects in the pipeline.
The goal is to make it very easy to modify and extend because of the simplicity
of the API and the simplicity of the objects being passed through the
pipeline.

The objects passed through the pipline are either simple strings that
indicate which test to run, or TestReult objects, which are also simple
and contain only the test specifier string, a status indicating whether
the test passed or failed, and captured stdout and stderr from the running
of the test.

The API necessary for objects that participate in the pipeline is a single
method called get_iter(input_iter).

"""

import sys
import os
import time
from types import FunctionType, MethodType
import inspect
import traceback
from cStringIO import StringIO
from argparse import ArgumentParser
from fnmatch import fnmatch
import unittest
from multiprocessing import Process, Queue, current_process, \
                            freeze_support, cpu_count

from fileutil import find_files, get_module_path, find_module

_start_time = 0.0

def read_config_file(cfgfile):
    with open(os.path.abspath(cfgfile), 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                yield line

def elapsed_str(elapsed):
    hrs = int(elapsed/3600)
    elapsed -= (hrs * 3600)
    mins = int(elapsed/60)
    elapsed -= (mins * 60)
    if hrs:
        return "%02d:%02d:%.2f" % (hrs, mins, elapsed)
    elif mins:
        return "%02d:%.2f" % (mins, elapsed)
    else:
        return "%.2f" % elapsed

def get_module(fname):
    """Given a filename or module path name, return a tuple
    of the form (filename, module).
    """

    if fname.endswith('.py'):
        modpath = get_module_path(fname)
    else:
        modpath = fname
        fname = find_module(modpath)

    if fname is None:
        return None, None

    try:
        __import__(modpath)
    except ImportError:
        sys.path.append(os.path.dirname(fname))
        try:
            __import__(modpath)
        finally:
            sys.path.pop()

    return fname, sys.modules[modpath]

def get_testcase(filename, mod, tcasename):
    """Given a module and the name of a TestCase
    class, return a TestCase object or raise an exception.
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

def parse_test_path(testpath):
    """Return a tuple of the form (fname, module, testcase, func)
    based on the given testpath.

    The format of testpath is one of the following:
        <module>
        <module>:<testcase>
        <module>:<testcase>.<method>
        <module>:<function>

    where <module> is either the python module path or the actual
    file system path to the .py file.  A value of None in the tuple
    indicates that that part of the testpath was not present.
    """

    testpath = testpath.strip()
    testcase = method = errmsg = None
    module, _, rest = testpath.partition(':')
    
    try:
        fname, mod = get_module(module)

        if rest:
            objname, _, method = rest.partition('.')
            obj = getattr(mod, objname)
            if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
                testcase = obj
                if method:
                    method = getattr(obj, method)
                    if not isinstance(method, MethodType):
                        raise TypeError("'%s' is not a method." % rest)
            elif isinstance(obj, FunctionType):
                method = obj
            else:
                raise TypeError("'%s' is not a TestCase or a function." %
                                objname)
    except Exception:
        errmsg = traceback.format_exc()

    return (fname, mod, testcase, method, errmsg)


class TestResult(object):
    """Contains the path to the test function/method, status
    of the test (if finished), error and stdout messages (if any),
    and start/end times.
    """

    def __init__(self, testpath, start_time, end_time,
                 status='OK', out_msg='', err_msg=''):
        self.testpath = testpath
        self.status = status
        self.out_msg = out_msg
        self.err_msg = err_msg
        self.start_time = start_time
        self.end_time = end_time

    def __str__(self):
        return self.testpath

    def elapsed(self):
        return self.end_time - self.start_time
    
    def short_name(self):
        """Returns the testpath with only the file's basename instead
        of its full path.
        """
        parts = self.testpath.split(':', 1)
        fname = os.path.basename(parts[0])
        return ':'.join((fname, parts[1]))


class ResultPrinter(object):
    """Processes the TestResult objects after tests have
    been run.
    """

    def __init__(self, stream=sys.stdout, verbose=False):
        self.stream = stream
        self.verbose = verbose

    def get_iter(self, input_iter):
        return self.process_results(input_iter)

    def process_results(self, input_iter):
        for result in input_iter:
            self.process(result)
            yield result

    def process(self, result):
        stream = self.stream
        if self.verbose:
            stream.write("%s ... %s (%s)\n" % (result.short_name(), 
                                               result.status,
                                               elapsed_str(result.elapsed())))
        elif result.status == 'OK':
            stream.write('.')
        elif result.status == 'FAIL':
            stream.write('F')
        elif result.status == 'SKIP':
            stream.write('S')

        if result.err_msg and result.status == 'FAIL':
            if not self.verbose:
                stream.write("\n%s ... %s (%s)\n" % (result.short_name(), 
                                                     result.status,
                                                     elapsed_str(result.elapsed())))
            stream.write(result.err_msg)
            stream.write('\n')

        stream.flush()


class TestSummary(object):
    def __init__(self, stream=sys.stdout):
        self.stream = stream

    def get_iter(self, input_iter):
        return self.summarize(input_iter)

    def summarize(self, input_iter):
        global _start_time

        oks = 0
        total = 0
        total_time = 0.
        fails = []
        skips = []
        
        write = self.stream.write

        for test in input_iter:
            total += 1
            total_time += test.elapsed()

            if test.status == 'OK':
                oks += 1
            elif test.status == 'FAIL':
                fails.append(test.short_name())
            elif test.status == 'SKIP':
                skips.append(test.short_name())
            yield test

        if skips:
            write("\n\nThe following tests were skipped:\n")
            for s in sorted(skips):
                write(s)
                write('\n')

        if fails:
            write("\n\nThe following tests failed:\n")
            for f in sorted(fails):
                write(f)
                write('\n')
        else:
            write("\n\nOK")

        write("\n\nPassed:  %d\nFailed:  %d\nSkipped: %d\n" % 
                            (oks, len(fails), len(skips)))

        wallclock = time.time() - _start_time

        s = "s" if total > 1 else ""
        write("\n\nRan %d test%s  (elapsed time: %s)\n\n" %
                          (total, s, elapsed_str(wallclock)))


def _worker(test_queue, done_queue):
    global _test_runner
    for testpath in iter(test_queue.get, 'STOP'):
        done_queue.put(_test_runner.run_test(testpath))


class TestRunner(object):
    """TestRunner that uses the multiprocessing package
    to execute tests concurrently.
    """
    
    def __init__(self, num_procs=cpu_count()):
        self.num_procs = num_procs
        
        if num_procs > 1:
            # Create queues
            self.task_queue = Queue()
            self.done_queue = Queue()

            self.procs = []
            # Start worker processes
            for i in range(num_procs):
                self.procs.append(Process(target=_worker,
                        args=(self.task_queue, self.done_queue)))
            for proc in self.procs:
                proc.start()

    def get_iter(self, input_iter):
        if self.num_procs > 1:
            return self.run_concurrent_tests(input_iter)
        else:
            return self.run_tests(input_iter)

    def run_tests(self, input_iter):
        """Run tests serially."""
        for test in input_iter:
            yield self.run_test(test)

    def run_concurrent_tests(self, input_iter):
        it = iter(input_iter)
        numtests = 0
        try:
            for proc in self.procs:
                self.task_queue.put(it.next())
                numtests += 1
        except StopIteration:
            pass
        else:
            initial = numtests
            try:
                while numtests:
                    yield self.done_queue.get()
                    numtests -= 1
                    self.task_queue.put(it.next())
                    numtests += 1
            except StopIteration:
                pass

        for proc in self.procs:
            self.task_queue.put('STOP')

        for i in range(numtests):
            yield self.done_queue.get()

        for proc in self.procs:
            proc.join()

    def _try_call(self, method, outstream, errstream):
        """Calls the given method, captures stdout and stderr,
        and returns the status (OK, SKIP, FAIL).
        """
        outstr = errstr = ''
        status = 'OK'
        if method:
            try:
                old_err = sys.stderr
                old_out = sys.stdout
                sys.stdout = outstream
                sys.stderr = errstream
                method()
            except Exception as e:
                msg = traceback.format_exc()
                if isinstance(e, unittest.SkipTest):
                    status = 'SKIP'
                else:
                    status = 'FAIL'
                    #msg = ''.join(traceback.format_exception(err[0],err[1],err[2]))
                    sys.stderr.write(msg)
            finally:
                sys.stderr = old_err
                sys.stdout = old_out

        return status

    def run_test(self, test):
        """Runs the test indicated by the given testpath, which has
        the form: 
        """
        
        start_time = time.time()

        fname, mod, testcase, method, errmsg = parse_test_path(test)

        if errmsg:
            return TestResult(test, start_time, time.time(), 'FAIL',
                              '', errmsg)
        elif method is None:
            return TestResult(test, start_time, time.time(), 'FAIL',
                              '', 'ERROR: test method not specified.')

        if testcase:
            testcase = testcase(methodName=method.__name__)
            parent = testcase
        else:
            parent = mod

        outstream = StringIO()
        errstream = StringIO()

        status = self._try_call(getattr(parent, 'setUp', None),
                                outstream, errstream)
        if status == 'OK':
            status = self._try_call(getattr(parent, method.__name__,
                                            None),
                                    outstream, errstream)
            tdstatus = self._try_call(getattr(parent, 'tearDown',
                                              None),
                                      outstream, errstream)
            if status == 'OK':
                status = tdstatus

            result = TestResult(test, start_time, time.time(), status,
                                outstream.getvalue(), errstream.getvalue())
        else:
            result = TestResult(test, start_time, time.time(), status,
                                outstream.getvalue(), errstream.getvalue())

        return result


# use this test runner in the concurrent workers
_test_runner = TestRunner(num_procs=1)


class TestDiscoverer(object):

    def __init__(self, module_pattern='test*.py',
                       func_pattern='test*',
                       dir_exclude=None):
        self.module_pattern = module_pattern
        self.func_pattern = func_pattern
        self.dir_exclude = dir_exclude

    def _exclude_dir(dname):
        return dname in self.dir_exclude

    def get_iter(self, input_iter):
        return self._test_strings_iter(input_iter)

    def _test_strings_iter(self, input_iter):
        """Returns an iterator over the expanded testpath
        strings based on the starting list of
        directories/modules/testpaths.
        """
        seen = set()
        for test in input_iter:
            if os.path.isdir(test):
                for result in self._dir_iter(test):
                    if result not in seen:
                        seen.add(result)
                        yield result
            else:
                for result in self._test_path_iter(test):
                    if result not in seen:
                        seen.add(result)
                        yield result

    def _dir_iter(self, dname):
        for f in find_files(dname, match=self.module_pattern,
                            direxclude=self.dir_exclude):
            if not os.path.basename(f).startswith('__init__.'):
                for result in self._module_iter(f):
                    yield result

    def _module_iter(self, filename):
        try:
            fname, mod = get_module(filename)
        except ImportError:
            sys.stderr.write("couldn't import filename %s\n" % filename)
        else:
            if os.path.basename(fname).startswith('__init__.'):
                for result in self._dir_iter(os.path.dirname(fname)):
                    yield result
            else:
                for name, obj in inspect.getmembers(mod):
                    if inspect.isclass(obj):
                        if issubclass(obj, unittest.TestCase):
                            for result in self._testcase_iter(filename, obj):
                                yield result

                    elif inspect.isfunction(obj):
                        if fnmatch(name, self.func_pattern):
                            yield ':'.join((filename, obj.__name__))

    def _testcase_iter(self, fname, testcase):
        for name, method in inspect.getmembers(testcase, inspect.ismethod):
            if fnmatch(name, self.func_pattern):
                yield fname + ':' + testcase.__name__ + '.' + method.__name__

    def _test_path_iter(self, testpath):
        """Return an iterator of expanded testpath strings found in the
        module/testcase/method specified in testpath.  The format of
        testpath is one of the following:
            <module>
            <module>:<testcase>
            <module>:<testcase>.<method>
            <module>:<function>

        where <module> is either the python module path or the actual
        file system path to the .py file.
        """

        module, _, rest = testpath.partition(':')
        if rest:
            tcasename, _, method = rest.partition('.')
            if method:
                yield testpath
            else:  # could be a test function or a TestCase
                fname, mod = get_module(module)
                try:
                    tcase = get_testcase(fname, mod, tcasename)
                except (AttributeError, TypeError):
                    yield testpath
                else:
                    for result in self._testcase_iter(fname, tcase):
                        yield result
        else:
            for result in self._module_iter(module):
                yield result


def run_pipeline(pipe):
    """Run a pipeline of test iteration objects."""

    iters = []
    
    if len(pipe) < 2:
        raise RuntimeError("test pipeline must have at least 2 members.")
    
    if hasattr(pipe[0], 'get_iter'):
        iters.append(pipe[0].get_iter(None))
    else:
        iters.append(pipe[0])

    # give each object the iterator from upstream in the pipeline
    for i,p in enumerate(pipe[1:]):
        iters.append(p.get_iter(iters[i]))

    for result in iters[-1]:
        pass

def _get_parser():
    parser = ArgumentParser()
    parser.usage = "testease [options]"
    parser.add_argument('-c', '--config', action='store', dest='cfg',
                        metavar='CONFIG',
                        help='Path of config file where tests are specified.')
    parser.add_argument('-n', '--numprocs', type=int, action='store', 
                        dest='num_procs', metavar='NUM_PROCS', default=0,
                        help='Number of processes to run. By default, this will '
                             'use the number of CPUs available.  To force serial'
                             ' execution, specify a value of 1.')
    parser.add_argument('-o', '--outfile', action='store', dest='outfile',
                        metavar='OUTFILE', default='test_report.out',
                        help='Name of test report file')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='if true, include testpath and elapsed time in '
                             'screen output')
    parser.add_argument('tests', metavar='test', nargs='*',
                       help='a test method/case/module/directory to run')

    return parser

def main():
    global _start_time

    options = _get_parser().parse_args()

    tests = options.tests
    if options.cfg:
        tests.extend(read_config_file(options.cfg))

    if not tests:
        tests = [os.getcwd()]

    skip_dirs = set(['devenv', 
                     'site-packages',
                     'dist-packages',
                     'build',
                     'contrib'])

    # by default, we'll use number of CPUs the system has.
    # User can force serial execution by specifying num_procs = 1
    if options.num_procs == 0:
        options.num_procs = cpu_count()

    with open(options.outfile, 'w') as report:
        pipeline = [
            tests,
            TestDiscoverer(dir_exclude=lambda t: t in skip_dirs),
            TestRunner(num_procs=options.num_procs),
            ResultPrinter(verbose=options.verbose),
            ResultPrinter(report),
            TestSummary(),
            TestSummary(report),
        ]
        
        _start_time = time.time()
        
        run_pipeline(pipeline)


if __name__ == '__main__':
    main()
