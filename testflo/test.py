import os
import sys
import time
import traceback
import inspect
import unittest
from subprocess import Popen, PIPE

from types import FunctionType, ModuleType
from six.moves import cStringIO
from six import PY3

from testflo.cover import start_coverage, stop_coverage
from testflo.profile import start_profile, stop_profile

from testflo.util import get_module, ismethod, get_memory_usage, to_bytes
from testflo.devnull import DevNull
from testflo.options import get_options

try:
    from mpi4py import MPI
except ImportError:
    MPI = None

options = get_options()

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

        self.nocapture = options.nocapture
        self.isolated = options.isolated
        self.mpi = not options.nompi

        if not err_msg:
            _, _, self.nprocs = self._get_test_parent()

        if self.err_msg:
            self.start_time = self.end_time = time.time()

    def _get_test_parent(self):
        """Get the parent of the test function, which will be either a
        TestCase or a module. Also get the N_PROCS value if found.
        """
        parent = method = None
        nprocs = 0

        try:
            mod, testcase, method = _parse_test_path(self.spec)
        except Exception:
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
        else:
            if method is None:
                self.status = 'FAIL'
                self.err_msg = 'ERROR: test method not specified.'
            else:
                if testcase is not None:
                    parent = testcase
                    nprocs = getattr(testcase, 'N_PROCS', 0)
                else:
                    parent = mod

        return parent, method, nprocs

    def _run_isolated(self, server, addr, authkey):
        """This runs the test in a subprocess,
        then returns the Test object.
        """

        if sys.platform == 'win32':
            cmd = [sys.executable,
                   os.path.join(os.path.dirname(__file__), 'isolatedrun.py'),
                   self.spec, addr, authkey]
        else:
            cmd = [sys.executable,
                   os.path.join(os.path.dirname(__file__), 'isolatedrun.py'),
                   self.spec, addr[0], str(addr[1]), authkey]

        p = Popen(cmd, stdout=PIPE, stderr=PIPE, env=os.environ)
        out, err = p.communicate()
        if self.nocapture:
            sys.stdout.write(out)
            sys.stderr.write(err)

        q = server.get_queue()
        result = q.get()
        result.isolated = True

        return result

    def _run_mpi(self, server, addr, authkey):
        """This runs the test using mpirun in a subprocess,
        then returns the Test object.
        """

        try:
            from distutils import spawn
            mpirun_exe = None
            if spawn.find_executable("mpirun") is not None:
                mpirun_exe = "mpirun"
            elif spawn.find_executable("mpiexec") is not None:
                mpirun_exe = "mpiexec"

            if mpirun_exe is None:
                raise Exception("mpirun or mpiexec was not found in the system path.")

            if sys.platform == 'win32':
                cmd = [mpirun_exe, '-n', str(self.nprocs),
                       sys.executable,
                       os.path.join(os.path.dirname(__file__), 'mpirun.py'),
                       self.spec, addr, authkey]
            else:
                cmd = [mpirun_exe, '-n', str(self.nprocs),
                       sys.executable,
                       os.path.join(os.path.dirname(__file__), 'mpirun.py'),
                       self.spec, addr[0], str(addr[1]), authkey]

            p = Popen(cmd, stdout=PIPE, stderr=PIPE, env=os.environ)
            out, err = p.communicate()
            if self.nocapture:
                sys.stdout.write(out)
                sys.stderr.write(err)

            q = server.get_queue()
            result = q.get()

        except:
            # we generally shouldn't get here, but just in case,
            # handle it so that the main process doesn't hang at the
            # end when it tries to join all of the concurrent processes.
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
            result = self

        finally:
            sys.stdout.flush()
            sys.stderr.flush()

        return result

    def run(self, server=None, addr=None, authkey=None):
        """Runs the test, assuming status is not already known."""
        if self.status is not None:
            # premature failure occurred , just return
            return self

        if server is not None:
            if MPI is not None and self.mpi and self.nprocs > 0:
                return self._run_mpi(server, addr, authkey)
            elif self.isolated:
                return self._run_isolated(server, addr, authkey)

        # this is for test files without an __init__ file.  This MUST
        # be done before the call to _get_test_parent.
        sys.path.insert(0, os.path.dirname(self.spec.split(':',1)[0]))

        parent, method, _ = self._get_test_parent()

        if not isinstance(parent, ModuleType) and issubclass(parent, unittest.TestCase):
            parent = parent(methodName=method)

        if self.nocapture:
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

            self.start_time = time.time()

            # if there's a setUp method, run it
            if setup:
                status = _try_call(setup)
                if status != 'OK':
                    run_method = False
                    run_td = False

            if run_method:
                status = _try_call(getattr(parent, method))

            if teardown and run_td:
                tdstatus = _try_call(teardown)
                if status == 'OK':
                    status = tdstatus

            self.end_time = time.time()
            self.status = status
            self.err_msg = errstream.getvalue()
            self.memory_usage = get_memory_usage()

        finally:
            sys.path = sys.path[1:]

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

    testcase = method = None
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
        objname, _, method = rest.partition('.')
        obj = getattr(mod, objname)
        if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
            testcase = obj
            if method:
                meth = getattr(obj, method)
                if not ismethod(meth):
                    raise TypeError("'%s' is not a method." % rest)
        elif isinstance(obj, FunctionType):
            method = obj.__name__
        else:
            raise TypeError("'%s' is not a TestCase or a function." %
                            objname)

    return (mod, testcase, method)

def _try_call(method):
    """Calls the given method, captures stdout and stderr,
    and returns the status (OK, SKIP, FAIL).
    """
    status = 'OK'
    try:
        start_profile()
        method()
    except unittest.SkipTest as e:
        status = 'SKIP'
        sys.stderr.write(str(e))
    except:
        status = 'FAIL'
        sys.stderr.write(traceback.format_exc())
    finally:
        stop_profile()

    return status
