from __future__ import print_function

import os
import sys
import time
import traceback
from inspect import isclass
from subprocess import Popen, PIPE
from tempfile import mkstemp

from types import FunctionType, ModuleType
from six.moves import cStringIO
from six import PY2, PY3

from unittest import TestCase, SkipTest
if PY2:
    from unittest.case import _ExpectedFailure, _UnexpectedSuccess
else:
    from unittest.case import _UnexpectedSuccess

from testflo.cover import start_coverage, stop_coverage

from testflo.util import get_module, ismethod, get_memory_usage, \
                         _get_testflo_subproc_args
from testflo.devnull import DevNull
from testflo.options import get_options

try:
    from mpi4py import MPI
except ImportError:
    MPI = None

options = get_options()


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

    def __init__(self, testspec, status=None, err_msg=''):
        self.spec = testspec
        self.status = status
        self.err_msg = err_msg
        self.memory_usage = 0
        self.nprocs = 0
        self.start_time = 0
        self.end_time = 0
        self.load1m = 0.0
        self.load5m = 0.0
        self.load15m = 0.0
        self.nocapture = options.nocapture
        self.isolated = options.isolated
        self.mpi = not options.nompi
        self.timeout = options.timeout
        self.expected_fail = False
        self.test_dir = os.path.dirname(testspec.split(':',1)[0])
        self._mod_fixture_first = False
        self._mod_fixture_last = False
        self._tcase_fixture_first = False
        self._tcase_fixture_last = False

        if not err_msg:
            with TestContext(self):
                self.mod, self.tcase, self.funcname, self.nprocs, isolated = self._get_test_info()
                if isolated:
                    self.isolated = isolated
        else:
            self.mod = self.tcase = self.funcname = None

        if self.err_msg:
            self.start_time = self.end_time = time.time()

    def __getstate__(self):
        """ Get rid of module and testcase so we don't pickle them. """
        state = self.__dict__.copy()
        state['mod'] = None
        state['tcase'] = None
        return state

    def __iter__(self):
        """Allows Test to be iterated over so we don't have to check later
        for Test vs. iter of Tests.
        """
        return iter((self,))

    def _get_test_info(self):
        """Get the test's module, testcase (if any), function name,
        N_PROCS (for mpi tests) and ISOLATED.
        """
        parent = funcname = mod = testcase = None
        nprocs = 0
        isolated = False

        try:
            mod, testcase, funcname = _parse_test_path(self.spec)
        except Exception:
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
        else:
            if funcname is None:
                self.status = 'FAIL'
                self.err_msg = 'ERROR: test function not specified.'
            else:
                if testcase is not None:
                    parent = testcase
                    nprocs = getattr(testcase, 'N_PROCS', 0)
                    isolated = getattr(testcase, 'ISOLATED', False)
                else:
                    parent = mod

        return mod, testcase, funcname, nprocs, isolated

    def _run_sub(self, cmd, queue):
        """
        Run a command in a subprocess.
        """
        try:
            add_queue_to_env(queue)

            if self.nocapture:
                out = sys.stdout
            else:
                out = open(os.devnull, 'w')

            errfd, tmperr = mkstemp()
            err = os.fdopen(errfd, 'w')

            p = Popen(cmd, stdout=out, stderr=err, env=os.environ,
                      universal_newlines=True)  # text mode
            count = 0
            timedout = False

            if self.timeout < 0.0:  # infinite timeout
                p.wait()
            else:
                poll_interval = 0.2
                while p.poll() is None:
                    if count * poll_interval > self.timeout:
                        p.terminate()
                        timedout = True
                        break
                    time.sleep(poll_interval)
                    count += 1

            err.close()

            with open(tmperr, 'r') as f:
                errmsg = f.read()
            os.remove(tmperr)

            os.environ['TESTFLO_QUEUE'] = ''

            if timedout:
                result = self
                self.status = 'FAIL'
                self.err_msg = 'TIMEOUT after %s sec. ' % self.timeout
                if errmsg:
                    self.err_msg += errmsg
            else:
                if p.returncode != 0:
                    print(errmsg)
                result = queue.get()
        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
            result = self

            err.close()
        finally:
            if not self.nocapture:
                out.close()
            sys.stdout.flush()
            sys.stderr.flush()

        return result

    def _run_isolated(self, queue):
        """This runs the test in a subprocess,
        then returns the Test object.
        """

        cmd = [sys.executable,
               os.path.join(os.path.dirname(__file__), 'isolatedrun.py'),
               self.spec]

        try:
            result = self._run_sub(cmd, queue)
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

            cmd = [mpirun_exe, '-n', str(self.nprocs),
                   sys.executable,
                   os.path.join(os.path.dirname(__file__), 'mpirun.py'),
                   self.spec] + _get_testflo_subproc_args()

            result = self._run_sub(cmd, queue)

        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
            result = self

        return result

    def run(self, queue=None):
        """Runs the test, assuming status is not already known."""
        if self.status is not None:
            # premature failure occurred (or dry run), just return
            return self

        if queue is not None:
            if MPI is not None and self.mpi and self.nprocs > 0:
                return self._run_mpi(queue)
            elif self.isolated:
                return self._run_isolated(queue)

        with TestContext(self):
            if self.tcase is None:
                mod, testcase, funcname, nprocs, _ = self._get_test_info()
            else:
                mod, testcase, funcname, nprocs = (self.mod, self.tcase, self.funcname, self.nprocs)

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
                # if we get here an nprocs > 0, we need
                # to set .comm in our TestCase instance.
                if nprocs > 0:
                    if MPI is not None and self.mpi:
                        parent.comm = MPI.COMM_WORLD
                    else:
                        parent.comm = FakeComm()

                setup = getattr(parent, 'setUp', None)
                teardown = getattr(parent, 'tearDown', None)
            else:
                parent = mod
                setup = teardown = None

            if self.nocapture:
                outstream = sys.stdout
            else:
                outstream = DevNull()
            errstream = cStringIO()

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
                    self.load1m, self.load5m, self.load15m = (0.0, 0.0, 0.0)
                else:
                    self.load1m, self.load5m, self.load15m = os.getloadavg()

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

    testcase = funcname = None
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

    return (mod, testcase, funcname)

def _try_call(func):
    """Calls the given method, captures stdout and stderr,
    and returns the status (OK, SKIP, FAIL).
    """
    status = 'OK'
    if PY3 and getattr(func, '__unittest_expecting_failure__', False):
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
        if PY2 and isinstance(err, _ExpectedFailure):
            expected = True
        status = 'FAIL'
        sys.stderr.write(traceback.format_exc())

    return status, expected
