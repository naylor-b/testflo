from __future__ import print_function

import os
import sys
import time
import traceback
from inspect import isclass
import subprocess
from tempfile import mkstemp
from importlib import import_module

from types import FunctionType, ModuleType
from io import StringIO

from unittest import TestCase, SkipTest
from unittest.case import _UnexpectedSuccess

from testflo.cover import start_coverage, stop_coverage

from testflo.util import get_module, ismethod, get_memory_usage, \
                         _options2args
from testflo.devnull import DevNull


from distutils import spawn
mpirun_exe = None
if spawn.find_executable("mpirun") is not None:
    mpirun_exe = "mpirun"
elif spawn.find_executable("mpiexec") is not None:
    mpirun_exe = "mpiexec"


def add_queue_to_env(queue):
    """Store enough info in the env to be able to create a proxy to
    the queue in a subprocess.
    """
    addr = queue._token.address
    os.environ['TESTFLO_QUEUE'] = "%s:%s:%s" % (addr[0], addr[1],
                                                queue._token.id)


class FakeComm(object):
    def __init__(self):
        self.rank = 0
        self.size = 1


# create a copy of sys.path with an extra entry at the beginning so that
# we can quickly replace the first entry with the curent test's dir rather
# than constantly copying the whole sys.path
_testing_path = ['.'] + sys.path


class TestContext(object):
    """Supports using the 'with' statement in place of try-finally to
    set sys.path for a test.
    """

    def __init__(self, test):
        self.test = test
        self.old_sys_path = sys.path

    def __enter__(self):
        global _testing_path
        _testing_path[0] = self.test.test_dir
        sys.path = _testing_path

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.path = self.old_sys_path


class Test(object):
    """Contains the path to the test function/method, status
    of the test (if finished), error and stdout messages (if any),
    start/end times and resource usage data.
    """

    def __init__(self, testspec, options):
        self.spec = testspec
        self.options = options
        self.test_dir = os.path.dirname(testspec.split(':',1)[0])

        self.status = None
        self.err_msg = ''
        self.mpi = False

        self.memory_usage = 0
        self.nprocs = 0
        self.isolated = False
        self.start_time = 0
        self.end_time = 0
        self.modpath = None
        self.tcasename = None
        self.funcname = None
        self.load = (0.0, 0.0, 0.0)
        self.expected_fail = False
        self._mod_fixture_first = False
        self._mod_fixture_last = False
        self._tcase_fixture_first = False
        self._tcase_fixture_last = False

        self._get_test_info()

    def __iter__(self):
        """Allows Test to be iterated over so we don't have to check later
        for Test vs. iter of Tests.
        """
        return iter((self,))

    def _get_test_info(self):
        """Get the test's module, testcase (if any), function name,
        N_PROCS (for mpi tests) and ISOLATED and set our attributes.
        """
        with TestContext(self):
            try:
                mod, self.tcasename, self.funcname = _parse_test_path(self.spec)
                self.modpath = mod.__name__
            except Exception:
                self.status = 'FAIL'
                self.err_msg = traceback.format_exc()
            else:
                if self.funcname is None:
                    self.status = 'FAIL'
                    self.err_msg = 'ERROR: test function not specified.'
                else:
                    if self.tcasename is not None:
                        testcase = getattr(mod, self.tcasename)
                        self.nprocs = getattr(testcase, 'N_PROCS', 0)
                        self.isolated = getattr(testcase, 'ISOLATED', False)

        if self.err_msg:
            self.start_time = self.end_time = time.time()

    def _run_sub(self, cmd, queue, env):
        """
        Run a command in a subprocess.
        """
        try:
            add_queue_to_env(queue)

            if self.options.nocapture:
                stdout = subprocess.PIPE
                stderr = subprocess.STDOUT
            else:
                stdout = subprocess.DEVNULL
                stderr = subprocess.PIPE

            p = subprocess.run(cmd, stdout=stdout, stderr=stderr, env=env,
                               timeout=self.options.timeout, universal_newlines=True)

            if p.returncode != 0:
                self.status = 'FAIL'
                self.err_msg = p.stdout if self.options.nocapture else p.stderr
                result = self
            else:
                if self.options.nocapture:
                    print(p.stdout)
                result = queue.get()
        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
            result = self

        return result

    def _run_isolated(self, queue):
        """This runs the test in a subprocess,
        then returns the Test object.
        """

        cmd = [sys.executable,
               os.path.join(os.path.dirname(__file__), 'isolatedrun.py'),
               self.spec]

        try:
            result = self._run_sub(cmd, queue, os.environ)
        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
            result = self

        result.isolated = True

        return result

    def _run_mpi(self, queue):
        """This runs the test using mpirun in a subprocess,
        then returns the Test object.
        """
        try:
            if mpirun_exe is None:
                raise Exception("mpirun or mpiexec was not found in the system path.")

            cmd =  [mpirun_exe, '-n', str(self.nprocs),
                   sys.executable,
                   os.path.join(os.path.dirname(__file__), 'mpirun.py'),
                   self.spec] + _options2args()

            result = self._run_sub(cmd, queue, os.environ)

        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
            result = self

        result.mpi = True

        return result

    def run(self, queue=None):
        """Runs the test, assuming status is not already known."""
        if self.status is not None:
            # premature failure occurred (or dry run), just return
            return self

        MPI = None
        if queue is not None and self.nprocs > 0 and not self.options.nompi:
            try:
                from mpi4py import MPI
            except ImportError:
                pass
            else:
                return self._run_mpi(queue)
        elif self.options.isolated:
            return self._run_isolated(queue)

        with TestContext(self):
            mod = import_module(self.modpath)

            testcase = getattr(mod, self.tcasename) if self.tcasename is not None else None
            funcname, nprocs = (self.funcname, self.nprocs)

            mod_setup = mod_teardown = tcase_setup = tcase_teardown = None

            if self._mod_fixture_first:
                mod_setup = getattr(mod, 'setUpModule', None)
            if self._mod_fixture_last:
                mod_teardown = getattr(mod, 'tearDownModule', None)

            if testcase is not None:
                if self._tcase_fixture_first:
                    tcase_setup = getattr(testcase, 'setUpClass', None)
                if self._tcase_fixture_last:
                    tcase_teardown = getattr(testcase, 'tearDownClass', None)

                parent = testcase(methodName=funcname)
                # if we get here and nprocs > 0, we need
                # to set .comm in our TestCase instance.
                if nprocs > 0:
                    if MPI is not None and not self.options.nompi:
                        parent.comm = MPI.COMM_WORLD
                    else:
                        parent.comm = FakeComm()

                setup = getattr(parent, 'setUp', None)
                teardown = getattr(parent, 'tearDown', None)
            else:
                parent = mod
                setup = teardown = None

            if self.options.nocapture:
                outstream = sys.stdout
            else:
                outstream = DevNull()
            errstream = StringIO()

            done = False
            expected = expected2 = expected3 = False

            try:
                old_err = sys.stderr
                old_out = sys.stdout
                sys.stdout = outstream
                sys.stderr = errstream

                start_coverage()

                self.start_time = time.time()

                # if there's a module setup, run it
                if mod_setup:
                    status, expected = _try_call(mod_setup)
                    if status != 'OK':
                        done = True
                        mod_teardown = None # don't do teardown if setup failed

                # handle @unittest.skip class decorator
                if not done and hasattr(parent, '__unittest_skip__') and parent.__unittest_skip__:
                    sys.stderr.write("%s\n" % parent.__unittest_skip_why__)
                    status = 'SKIP'
                    done = True
                    tcase_setup = None
                    tcase_teardown = None

                if tcase_setup:
                    status, expected = _try_call(tcase_setup)
                    if status != 'OK':
                        done = True
                        tcase_teardown = None

                # if there's a setUp method, run it
                if not done and setup:
                    status, expected = _try_call(setup)
                    if status != 'OK':
                        done = True

                if not done:
                    status, expected2 = _try_call(getattr(parent, funcname))

                if not done and teardown:
                    tdstatus, expected3 = _try_call(teardown)
                    if status == 'OK':
                        status = tdstatus

                if tcase_teardown:
                    _try_call(tcase_teardown)

                if mod_teardown:
                    _try_call(mod_teardown)

                self.end_time = time.time()
                self.status = status
                self.err_msg = errstream.getvalue()
                self.memory_usage = get_memory_usage()
                self.expected_fail = expected or expected2 or expected3

                if sys.platform == 'win32':
                    self.load = (0.0, 0.0, 0.0)
                else:
                    self.load = os.getloadavg()

            finally:
                stop_coverage()

                sys.stderr = old_err
                sys.stdout = old_out

        return self

    def elapsed(self):
        return self.end_time - self.start_time

    def short_name(self):
        """Returns the testspec with only the file's basename instead
        of its full path.
        """
        parts = self.spec.split(':', 1)
        fname = os.path.basename(parts[0])
        return ':'.join((fname, parts[-1]))

    def __str__(self):
        if self.err_msg:
            return "%s: %s\n%s" % (self.spec, self.status, self.err_msg)
        else:
            return "%s: %s" % (self.spec, self.status)


def _parse_test_path(testspec):
    """Return a tuple of the form (module, testcase, func)
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

    testcase = funcname = tcasename = None
    testspec = testspec.strip()
    parts = testspec.split(':')
    if len(parts) > 1 and parts[1].startswith('\\'):  # windows abs path
        module = ':'.join(parts[:2])
        if len(parts) == 3:
            rest = parts[2]
        else:
            rest = ''
    else:
        module, _, rest = testspec.partition(':')

    _, mod = get_module(module)

    if rest:
        objname, _, funcname = rest.partition('.')
        obj = getattr(mod, objname)
        if isclass(obj) and issubclass(obj, TestCase):
            tcasename = objname
            testcase = obj
            if funcname:
                meth = getattr(obj, funcname)
                if not ismethod(meth):
                    raise TypeError("'%s' is not a method." % rest)
        elif isinstance(obj, FunctionType):
            funcname = obj.__name__
        else:
            raise TypeError("'%s' is not a TestCase or a function." %
                            objname)

    return (mod, tcasename, funcname)


def _try_call(func):
    """Calls the given method, captures stdout and stderr,
    and returns the status (OK, SKIP, FAIL).
    """
    status = 'OK'
    if getattr(func, '__unittest_expecting_failure__', False):
        expected = True
    else:
        expected = False
    try:
        func()
    except SkipTest as e:
        status = 'SKIP'
        sys.stderr.write(str(e))
    except _UnexpectedSuccess:
        status = 'OK'
        expected = True
    except Exception as err:
        status = 'FAIL'
        sys.stderr.write(traceback.format_exc())

    return status, expected
