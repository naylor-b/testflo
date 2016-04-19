import os
import sys
import time


class TestResult(object):
    """Contains the path to the test function/method, status
    of the test (if finished), error and stdout messages (if any),
    start/end times and optionally resource usage data.
    """

    def __init__(self, testspec, start_time, end_time,
                 status='OK', info={}):
        self.testspec = testspec
        self.status = status
        self.err_msg = info.get('err_msg', '')
        self.start_time = start_time
        self.end_time = end_time
        self.memory_usage = info.get('memory_usage', 0)

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
