import os
import sys
import time
import traceback
import inspect
import unittest

from six.moves import cStringIO

from testflo.cover import start_coverage, stop_coverage
from testflo.profile import start_profile, stop_profile

from testflo.util import get_module, ismethod
from testflo.devnull import DevNull
from testflo.options import get_options


class Test(object):
    """Contains the path to the test function/method, status
    of the test (if finished), error and stdout messages (if any),
    start/end times and optionally resource usage data.
    """

    def __init__(self, testspec, status=None, err_msg=''):
        assert(isinstance(testspec,basestring))
        self.testspec = testspec
        self.status = status
        self.err_msg = err_msg
        self.memory_usage = 0
        self.parent = self.method = None

        if not err_msg:
            self._get_test_parent()

        if self.err_msg:
            self.start_time = self.end_time = time.time()

    def _get_test_parent(self):
        try:
            mod, testcase, method = _parse_test_path(self.testspec)
        except Exception:
            self.status = 'FAIL'
            self.err_msg = traceback.format_exc()
        else:
            if method is None:
                self.status = 'FAIL'
                self.err_msg = 'ERROR: test method not specified.'
            else:
                self.method = method
                if testcase is not None:
                    self.parent = testcase
                    self.nprocs = getattr(testcase, 'N_PROCS', 0)
                else:
                    self.parent = mod

    def run(self):
        """Runs the test, assuming status is not already known."""
        if self.status is not None:
            # premature failure occurred during discovery, just return
            return self

        self.start_time = time.time()

        if self.parent is None:
            self._get_test_parent()

        parent = self.parent
        method = self.method
        if issubclass(parent, unittest.TestCase):
            parent = parent(methodName=method)

        if get_options().nocapture:
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
        parts = self.testspec.split(':', 1)
        fname = os.path.basename(parts[0])
        return ':'.join((fname, parts[-1]))

    def __str__(self):
        if self.err_msg:
            return "%s: %s\n%s" % (self.testspec, self.status, self.err_msg)
        else:
            return "%s: %s" % (self.testspec, self.status)


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
    testspec = str(testspec)
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
            method = obj
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
