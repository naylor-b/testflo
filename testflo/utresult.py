import unittest
from collections import namedtuple


class ResultData(object):
    __slots__ = ['testcase', 'status', 'error', 'subtests']
    def __init__(self, tcase):
        self.testcase = tcase
        self.status = None
        self.error = None
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
        # print("Starting test", test, "TYPE:", type(test), "TEST:", test.id())
        self._tests[test.id()] = ResultData(test)
        super().startTest(test)

    def _setupStdout(self):
        pass  # don't do anything here.  It's done outside this class

    # def startTestRun(self):
    #     """Called once before any tests are executed.

    #     See startTest for a method called before each test.
    #     """
    #     print("Starting test run...")

    # def stopTest(self, test):
    #     """Called when the given test has been run"""
    #     print(f"Test {test} is done.")
    #     super().stopTest(test)

    def _restoreStdout(self):
        pass

    # def stopTestRun(self):
    #     """Called once after all tests are executed.

    #     See stopTest for a method called after each test.
    #     """
    #     print("Stopping test run...")

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().  Not called for subtests.
        """
        # print(f"Error occurred in test {test}: {self._exc_info_to_string(err, test)}")
        resdata = self._tests[test.id()]
        resdata.error = self._exc_info_to_string(err, test)
        resdata.status = 'FAIL'
        super().addError(test, err)

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().  Not called for subtests.
        """
        # print(f"Failure occurred in test {test}: {self._exc_info_to_string(err, test)}")
        resdata = self._tests[test.id()]
        resdata.error = self._exc_info_to_string(err, test)
        resdata.status = 'FAIL'
        super().addFailure(test, err)

    def addSubTest(self, test, subtest, err):
        """Called at the end of a subtest.
        'err' is None if the subtest ended successfully, otherwise it's a
        tuple of values as returned by sys.exc_info().
        """
        # print(f"Adding subtest: {test}, {subtest}, ID: {subtest.id()}, MSG: {subtest._message}, {err}")
        if err is not None:  # only save info if subtest fails
            resdata = self._tests[test.id()]
            resdata.add_subtest(subtest._message, self._exc_info_to_string(err, subtest))
            resdata.status = 'FAIL'
        super().addSubTest(test, subtest, err)

    def addSuccess(self, test):
        "Called when a test has completed successfully."
        self._tests[test.id()].status = 'OK'
        print(f"Success for test {test}")

    def addSkip(self, test, reason):
        """Called when a test is skipped."""
        # print(f"Skipping test {test} for reason {reason}")
        resdata = self._tests[test.id()]
        resdata.status = 'SKIP'
        resdata.error = reason
        super().addSkip(test, reason)

    # def addExpectedFailure(self, test, err):
    #     """Called when an expected failure/error occurred."""
    #     self.expectedFailures.append(
    #         (test, self._exc_info_to_string(err, test)))

    # def addUnexpectedSuccess(self, test):
    #     """Called when a test was expected to fail, but succeed."""
    #     self.unexpectedSuccesses.append(test)

    # def wasSuccessful(self):
    #     """Tells whether or not this result was a success."""
    #     # The hasattr check is for test_result's OldResult test.  That
    #     # way this method works on objects that lack the attribute.
    #     # (where would such result instances come from? old stored pickles?)
    #     return ((len(self.failures) == len(self.errors) == 0) and
    #             (not hasattr(self, 'unexpectedSuccesses') or
    #              len(self.unexpectedSuccesses) == 0))
