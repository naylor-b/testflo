

class TestSpec(object):
    def __init__(self, spec):
        self._spec = spec
        self.fname, self.module, self.testcase, self.func = \
                  _parse_test_path(spec)

        if testcase is not None:
            self.nprocs = getattr(testcase, 'N_PROCS', 1)
        else:
            self.nprocs = 1

    def __str__(self):
        return self._spec


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
