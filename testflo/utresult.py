import sys
import io
import unittest
from collections import namedtuple


class ResultData(object):
    __slots__ = ['testcase', 'status', 'error', 'subtests']
    def __init__(self, tcase):
        self.testcase = tcase
        self.status = None
        self.error = ''
        self.subtests = []

    def __iter__(self):
        yield self.testcase
        yield self.status
        yield self.error
        yield self.subtests

    def add_subtest(self, subtest, err):
        self.subtests.append((subtest, err))


class UnitTestResult(unittest.TestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tests = {}

    def startTest(self, test):
        self._tests[test.id()] = ResultData(test)
        super().startTest(test)

    def _setupStdout(self):
        pass  # avoid base class mods to stdout and stderr

    def _restoreStdout(self):
        pass  # avoid base class mods to stdout and stderr

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().  Not called for subtests.
        """
        resdata = self._tests[test.id()]
        resdata.error = self._exc_info_to_string(err, test)
        resdata.status = 'FAIL'
        super().addError(test, err)

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().  Not called for subtests.
        """
        resdata = self._tests[test.id()]
        resdata.error = self._exc_info_to_string(err, test)
        resdata.status = 'FAIL'
        super().addFailure(test, err)

    def addSubTest(self, test, subtest, err):
        """Called at the end of a subtest.
        'err' is None if the subtest ended successfully, otherwise it's a
        tuple of values as returned by sys.exc_info().
        """
        if err is not None:  # only save info if subtest fails
            resdata = self._tests[test.id()]
            resdata.add_subtest(subtest, self._exc_info_to_string(err, subtest))
            resdata.status = 'FAIL'
        super().addSubTest(test, subtest, err)

    def addSuccess(self, test):
        "Called when a test has completed successfully."
        self._tests[test.id()].status = 'OK'
        print(f"Success for test {test}")

    def addSkip(self, test, reason):
        """Called when a test is skipped."""
        resdata = self._tests[test.id()]
        resdata.status = 'SKIP'
        resdata.error = reason
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        """Called when an expected failure/error occurred."""
        super().addExpectedFailure(test, err)
        resdata = self._tests[test.id()]
        resdata.status = 'OK'

    def addUnexpectedSuccess(self, test):
        """Called when a test was expected to fail, but succeed."""
        super().addUnexpectedSuccess(test)
        resdata = self._tests[test.id()]
        resdata.status = 'FAIL'
