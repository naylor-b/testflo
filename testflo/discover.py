
import traceback
from inspect import getmembers, isclass, isfunction
from unittest import TestCase
import six

from os.path import basename, dirname, isdir

from testflo.util import find_files, get_module, ismethod
from testflo.test import Test

def _has_class_fixture(tcase):
    if tcase is not None:
        for klass in tcase.__mro__:
            if klass is TestCase:
                break
            if 'setUpClass' in klass.__dict__ or 'tearDownClass' in klass.__dict__:
                return  True
    return False


class TestDiscoverer(object):

    def __init__(self, module_pattern=six.text_type('test*.py'),
                       func_match=lambda f: fnmatchcase(f, 'test*'),
                       dir_exclude=None):
        self.module_pattern = module_pattern
        self.func_match = func_match
        self.dir_exclude = dir_exclude

        # to support module and class fixtures, we need to be able to
        # process all tests in a module or TestCase in the same process,
        # so these are to keep track of which tests need to be grouped
        # together.
        self._mod_fixture_groups = {}
        self._tcase_fixture_groups = {}

    def get_iter(self, input_iter):
        """Returns an iterator of Test objects
        based on the starting list of directories/modules/testspecs.
        """
        seen = set()
        for tests in input_iter:
            if isdir(tests):
                itr = self._dir_iter
            else:
                itr = self._testspec_iter

            for result in itr(tests):
                if result.spec not in seen:
                    seen.add(result.spec)
                    result = self._filter(result)
                    if result is not None:
                        yield result

        # Every test left has been group together either by module or
        # TestCase or both, due to the presense of module or testcase class level
        # setup/teardown, and we need to run each group on the same
        # process so that we can execute the module or class level setup/teardown
        # only once while impacting all of the tests in that group.
        new_tcase_groups = []
        for tcase, tests in self._tcase_fixture_groups.items():
            tests = sorted(tests, key=lambda t: t.spec)

            # mark the first and last tests so that we know when to
            # run setUpClass and tearDownClass
            tests[0]._tcase_fixture_first = True
            tests[-1]._tcase_fixture_last = True

            # check to see if this TestCase is part of a module with setUpModule/tearDownModule
            if tests[0].mod in self._mod_fixture_groups:
                # these tests are already part of a module fixture, so we
                # don't want to execute them a second time
                continue

            new_tcase_groups.append(tests)

        # yield any tests that are grouped because of a module level fixture.
        for tests in self._mod_fixture_groups.values():
            tests = sorted(tests, key=lambda t: t.spec)

            # mark the first and last tests so that we know when to
            # run setUpModule and tearDownModule
            tests[0]._mod_fixture_first = True
            tests[-1]._mod_fixture_last = True
            yield tests  # yield them together as a group

        # yield grouped tests for all remaining TestCases with setUpClass/tearDownClass
        for tests in new_tcase_groups:
            yield tests

    def _filter(self, test):
        """
        If the given test is part of a module with setUpModule/tearDownModule
        and/or part of a TestCase with setUpClass/tearDownClass, then save it
        for later, else return it.
        """

        if test.mod in self._mod_fixture_groups:
            self._mod_fixture_groups[test.mod].append(test)
        elif hasattr(test.mod, 'setUpModule') or hasattr(test.mod, 'tearDownModule'):
            self._mod_fixture_groups[test.mod] = [test]

        if test.tcase in self._tcase_fixture_groups:
            self._tcase_fixture_groups[test.tcase].append(test)
        elif _has_class_fixture(test.tcase):
            self._tcase_fixture_groups[test.tcase] = [test]

        if not (test.mod in self._mod_fixture_groups or test.tcase in self._tcase_fixture_groups):
            return test

    def _dir_iter(self, dname):
        """Iterate over all tests in modules found in the given
        directory and its subdirectories. Returns an iterator
        of Test objects.
        """
        for f in find_files(dname, match=self.module_pattern,
                                   direxclude=self.dir_exclude):
            if not basename(f).startswith(six.text_type('__init__.')):
                for result in self._module_iter(f):
                    yield result

    def _module_iter(self, filename):
        """Returns an iterator of Test objects for the contents of
        the given python module file.
        """

        try:
            fname, mod = get_module(filename)
        except:
            yield Test(filename, 'FAIL', err_msg=traceback.format_exc())
        else:
            if basename(fname).startswith(six.text_type('__init__.')):
                for result in self._dir_iter(dirname(fname)):
                    yield result
            else:
                for name, obj in getmembers(mod):
                    if isclass(obj) and issubclass(obj, TestCase):
                        for result in self._testcase_iter(filename, obj):
                            yield result

                    elif isfunction(obj) and self.func_match(name):
                        yield Test(':'.join((filename, obj.__name__)))

    def _testcase_iter(self, fname, testcase):
        """Returns an iterator of Test objects coming from a given
        TestCase class.
        """
        tcname = ':'.join((fname, testcase.__name__))
        for name, method in getmembers(testcase, ismethod):
            if self.func_match(name):
                yield Test('.'.join((tcname, method.__name__)))

    def _testspec_iter(self, testspec):
        """Returns an iterator of Test objects found in the
        module/testcase/method specified in testspec.  The format of
        testspec is one of the following:
            <module>
            <module>:<testcase>
            <module>:<testcase>.<method>
            <module>:<function>

        where <module> is either the python module path or the actual
        file system path to the .py file.
        """

        module, _, rest = testspec.partition(':')
        if rest:
            tcasename, _, method = rest.partition('.')
            if method:
                yield Test(testspec)
            else:  # could be a test function or a TestCase
                try:
                    fname, mod = get_module(module)
                except:
                    yield Test(testspec, 'FAIL', err_msg=traceback.format_exc())
                    return
                try:
                    tcase = get_testcase(fname, mod, tcasename)
                except (AttributeError, TypeError):
                    yield Test(testspec)
                else:
                    for test in self._testcase_iter(fname, tcase):
                        yield test
        else:
            for test in self._module_iter(module):
                yield test


def get_testcase(filename, mod, tcasename):
    """Given a module and the name of a TestCase
    class, return a TestCase class object or raise an exception.
    """

    try:
        tcase = getattr(mod, tcasename)
    except AttributeError:
        raise AttributeError("Couldn't find TestCase '%s' in module '%s'" %
                               (tcasename, filename))
    if issubclass(tcase, TestCase):
        return tcase
    else:
        raise TypeError("'%s' in file '%s' is not a TestCase." %
                        (tcasename, filename))
