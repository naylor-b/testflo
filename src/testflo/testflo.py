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
from multiprocessing import Process, Queue, current_process, freeze_support
import networkx as nx

from fileutil import find_files, get_module_path, find_module

_start_time = 0.0

def _get_parser():
    """Sets up the plugin arg parser and all of its subcommand parsers."""

    parser = ArgumentParser()
    parser.usage = "testease [options]"
    parser.add_argument('-c', '--config', action='store', dest='cfg',
                        metavar='CONFIG',
                        help='Path of config file where tests are specified.')
    parser.add_argument('tests', metavar='test', nargs='*',
                       help='a test method/case/module/directory to run')

    return parser

def _exclude_dir(dname):
    return dname in ('devenv', 'site-packages', 'dist-packages', 'contrib')

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
    module, _, rest = testpath.partition(':')
    fname, mod = get_module(module)
    testcase = method = None

    if rest:
        objname, _, method = rest.partition('.')
        obj = getattr(mod, objname)
        if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
            testcase = obj
            if method:
                method = getattr(obj, method)
        elif isinstance(obj, FunctionType):
            method = obj
        else:
            raise TypeError("'%s' is not a TestCase or a function" %
                            objname)

    return (fname, mod, testcase, method)


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
        stream = StringIO()
        stream.write(self.testpath)
        stream.write(' ... ')
        stream.write(self.status)
        if self.status != 'OK':
            stream.write('\n')
            stream.write(self.err_msg)
        return stream.getvalue()

    def elapsed(self):
        return self.end_time - self.start_time


class ResultProcessor(object):
    """Processes the TestResult objects after tests have
    been run.
    """

    def __init__(self, stream=sys.stdout):
        self.stream = stream

    def get_iter(self, input_iter):
        return self.process_results(input_iter)

    def process_results(self, input_iter):
        for result in input_iter:
            self.process(result)
            yield result

    def process(self, result):
        stream = self.stream
        stream.write("%s ... %s\n" % (result.testpath, result.status))
        if result.err_msg:
            stream.write(result.err_msg)
            stream.write('\n')


class TestPreview(object):
    def get_iter(self, input_iter):
        return self.show_preview(input_iter)

    def show_preview(self, input_iter):
        for test in input_iter:
            sys.stdout.write("%s ... " % test)
            sys.stdout.flush()
            yield test


class TestStatus(object):
    def get_iter(self, input_iter):
        return self.show_status(input_iter)

    def show_status(self, input_iter):
        for test in input_iter:
            sys.stdout.write("%s (%s)\n" %
                               (test.status, elapsed_str(test.elapsed())))
            if test.status != 'OK':
                sys.stdout.write(test.err_msg)
            sys.stdout.flush()
            yield test


class TestSummary(object):
    def get_iter(self, input_iter):
        return self.summarize(input_iter)

    def summarize(self, input_iter):
        global _start_time

        oks = 0
        total = 0
        total_time = 0.
        fails = []
        skips = []

        for test in input_iter:
            total += 1
            total_time += test.elapsed()

            if test.status == 'OK':
                oks += 1
            elif test.status == 'FAIL':
                fails.append(test.testpath)
            elif test.status == 'SKIP':
                skips.append(test.testpath)
            yield test

        if skips:
            print "\n\nThe following tests were skipped:\n"
            for s in sorted(skips):
                print s

        if fails:
            print "\n\nThe following tests failed:\n"
            for f in sorted(fails):
                print f
        else:
            print "OK"

        print "\nFails: %d\nSkips: %d\n" % (len(fails), len(skips))

        wallclock = time.time() - _start_time

        s = "s" if total > 1 else ""
        print "\n\nRan %d test%s  (elapsed time: %s, speedup: %.2f)\n\n" % \
                         (total, s, elapsed_str(wallclock),
                          total_time/wallclock)


class TestRunner(object):
    """Runs each test specified in results."""

    def get_iter(self, input_iter):
        return self.process_tests(input_iter)

    def process_tests(self, input_iter):
        for test in input_iter:
            yield self.run_test(test)

    def _try_call(self, method, outstream, errstream):
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
                err = sys.exc_info()
                if isinstance(e, unittest.SkipTest):
                    status = 'SKIP'
                else:
                    status = 'FAIL'
                    msg = ''.join(traceback.format_exception(err[0],err[1],err[2]))
                    sys.stderr.write(msg)
            finally:
                sys.stderr = old_err
                sys.stdout = old_out

        return status

    def run_test(self, test):
        fname, mod, testcase, method = parse_test_path(test)
        if testcase:
            testcase = testcase(methodName=method.__name__)
            parent = testcase
        else:
            parent = mod

        outstream = StringIO()
        errstream = StringIO()

        start_time = time.time()

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

_test_runner = TestRunner()

def _worker(task_queue, done_queue):
    global _test_runner
    for testpath in iter(task_queue.get, 'STOP'):
        done_queue.put(_test_runner.run_test(testpath))


class MPTestRunner(TestRunner):
    """TestRunner that uses a worker poll to execute tests
    concurrently.
    """
    def __init__(self, num_procs=4):
        # Create queues
        self.task_queue = Queue()
        self.done_queue = Queue()

        self.procs = []
        # Start worker processes
        for i in range(num_procs):
            self.procs.append(Process(target=_worker,
                    args=(self.task_queue,self.done_queue)))
        for proc in self.procs:
            proc.start()

    def get_iter(self, input_iter):
        return self.process_mp_tests(input_iter)

    def process_mp_tests(self, input_iter):
        it = iter(input_iter)
        numtests = 0
        try:
            for proc in self.procs:
                testpath = it.next()
                self.task_queue.put(testpath)
                numtests += 1
        except StopIteration:
            for i in range(numtests):
                yield self.task_queue.get()
            return

        try:
            while True:
                yield self.done_queue.get()
                testpath = it.next()
                self.task_queue.put(testpath)
        except StopIteration:
            for i in range(numtests-1):
                yield self.done_queue.get()

        for proc in self.procs:
            proc.terminate()


class TestDiscoverer(object):

    def __init__(self, module_pattern='test*.py',
                       func_pattern='test*'):
        self.module_pattern = module_pattern
        self.func_pattern = func_pattern

    def get_iter(self, input_iter):
        return self.process_test_strings(input_iter)

    def process_test_strings(self, input_iter):
        """Returns an iterator over the expanded testpath
        strings based on the starting list of
        directories/modules/testcases/testmethods.
        """
        seen = set()
        for test in input_iter:
            if os.path.isdir(test):
                for result in self.process_dir(test):
                    if result not in seen:
                        seen.add(result)
                        yield result
            else:
                for result in self.process_test_path(test):
                    if result not in seen:
                        seen.add(result)
                        yield result

    def process_dir(self, dname):
        for f in find_files(dname, match=self.module_pattern,
                            direxclude=_exclude_dir):
            for result in self.process_module(f):
                yield result

    def process_module(self, filename):
        try:
            fname, mod = get_module(filename)
        except ImportError:
            pass
        else:
            for name, obj in inspect.getmembers(mod):
                if inspect.isclass(obj):
                    if issubclass(obj, unittest.TestCase):
                        for result in self.process_testcase(filename, obj):
                            yield result

                elif inspect.isfunction(obj):
                    if fnmatch(name, self.func_pattern):
                        yield ':'.join((filename, obj.__name__))

    def process_testcase(self, fname, testcase):
        for name, method in inspect.getmembers(testcase, inspect.ismethod):
            if fnmatch(name, self.func_pattern):
                yield fname + ':' + testcase.__name__ + '.' + method.__name__

    def process_test_path(self, testpath):
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
                    for result in self.process_testcase(fname, tcase):
                        yield result
        else:
            for result in self.process_module(module):
                yield result


class TestPipeline(object):
    """This class manages a graph of test iteration objects
    that process tests and test results.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add(self, name, obj):
        """Add a new test iteration object to the graph."""
        self.graph.add_node(name, iter=None, obj=obj)

    def connect(self, *args):
        """Connect two or more test iteration objects together."""
        for i, name in enumerate(args[1:]):
            self.graph.add_edge(args[i], name)

    def _check_graph(self):
        """Analyse the graph to make sure all connections are
        legal, e.g., a node cannot have multiple input connections.
        (later maybe this can be relaxed by automatically creating
        aggregator nodes...)
        """
        srcs = False
        sinks = False

        for n in self.graph:
            indeg = self.graph.in_degree(n)
            outdeg = self.graph.out_degree(n)

            if indeg and indeg > 1:
                raise RuntimeError(
                  "Node '%s' of iterator graph has multiple inputs" %
                  n)

            if outdeg and outdeg > 1:
                raise RuntimeError(
                  "Node '%s' of iterator graph has multiple outputs" %
                  n)

            if not indeg:
                srcs = True

            if not outdeg:
                sinks = True

        if not srcs:
            raise RuntimeError("iterator graph nas no sources")

        if not sinks:
            raise RuntimeError("iterator graph has no sinks")

    def run(self):
        """Run a graph of test iteration objects."""

        self._check_graph()

        g = self.graph
        srcs = []
        sinks = []
        for n, data in g.nodes_iter(data=True):
            if not g.in_degree(n):
                srcs.append(n)
                if hasattr(data['obj'], 'get_iter'):
                    data['iter'] = data['obj'].get_iter(None)
                else:
                    data['iter'] = iter(data['obj'])

            elif not g.out_degree(n):
                sinks.append(n)

        visited = set(srcs)
        for src in srcs:
            for u,v in nx.bfs_edges(g, src):
                if v not in visited:
                    visited.add(v)
                    iter_in = g.node[u]['iter']
                    g.node[v]['iter'] = g.node[v]['obj'].get_iter(iter_in)

        iterdict = {}
        for sink in sinks:
            iterdict[sink] = g.node[sink]['iter']

        while iterdict:
            for name, iterator in iterdict.items():
                try:
                    iterator.next()
                except StopIteration:
                    del iterdict[name]

class MyTestPipeline(TestPipeline):
    def __init__(self, tests):
        super(MyTestPipeline, self).__init__()

        self.add('source', tests)
        self.add('discovery', TestDiscoverer())
        self.add('preview', TestPreview())
        self.add('runner', MPTestRunner())
        self.add('saver', ResultProcessor(open('test_report.out', 'w')))
        self.add('status', TestStatus())
        self.add('summary', TestSummary())

        self.connect('source', 'discovery', 'preview',
                     'runner', 'saver', 'status', 'summary')

def main():
    global _start_time

    parser = _get_parser()
    options = parser.parse_args()


    # pipeline
    #   source(s) of unexpanded test path names (could be dir/module/testcase/method)
    #      --> optional filter here
    #      --> test discoverer(s)
    #      --> iterator of expanded test path names (full module:testcase.method names)
    #      --> optional filter here
    #      --> test runner  (may branch to test workers)
    #      --> result processor(s)

    tests = options.tests
    if options.cfg:
        tests.extend(read_config_file(options.cfg))

    if not tests:
        tests = [os.getcwd()]

    pipeline = MyTestPipeline(tests)

    _start_time = time.time()
    pipeline.run()

def run_tests():
    main()

if __name__ == '__main__':
    main()
