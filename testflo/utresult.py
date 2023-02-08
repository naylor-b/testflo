import unittest

class UnitTestResult(unittest.TestResult):
    def startTest(self, test):
        print(f"Starting test {test}")
        super().startTest(test)

    # def _setupStdout(self):
    #     if self.buffer:
    #         if self._stderr_buffer is None:
    #             self._stderr_buffer = io.StringIO()
    #             self._stdout_buffer = io.StringIO()
    #         sys.stdout = self._stdout_buffer
    #         sys.stderr = self._stderr_buffer

    def startTestRun(self):
        """Called once before any tests are executed.

        See startTest for a method called before each test.
        """
        print("Starting test run...")

    def stopTest(self, test):
        """Called when the given test has been run"""
        print(f"Test {test} is done.")
        super().stopTest(test)

    # def _restoreStdout(self):
    #     if self.buffer:
    #         if self._mirrorOutput:
    #             output = sys.stdout.getvalue()
    #             error = sys.stderr.getvalue()
    #             if output:
    #                 if not output.endswith('\n'):
    #                     output += '\n'
    #                 self._original_stdout.write(STDOUT_LINE % output)
    #             if error:
    #                 if not error.endswith('\n'):
    #                     error += '\n'
    #                 self._original_stderr.write(STDERR_LINE % error)

    #         sys.stdout = self._original_stdout
    #         sys.stderr = self._original_stderr
    #         self._stdout_buffer.seek(0)
    #         self._stdout_buffer.truncate()
    #         self._stderr_buffer.seek(0)
    #         self._stderr_buffer.truncate()

    def stopTestRun(self):
        """Called once after all tests are executed.

        See stopTest for a method called after each test.
        """
        print("Stopping test run...")

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        print(f"Error occurred in test {test}: {self._exc_info_to_string(err, test)}")
        super().addError(test, err)

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        print(f"Failure occurred in test {test}: {self._exc_info_to_string(err, test)}")
        super().addFailure(test, err)

    def addSubTest(self, test, subtest, err):
        """Called at the end of a subtest.
        'err' is None if the subtest ended successfully, otherwise it's a
        tuple of values as returned by sys.exc_info().
        """
        print(f"Adding subtest: {test}, {subtest}, {err}")
        super().addSubTest(test, subtest, err)

    def addSuccess(self, test):
        "Called when a test has completed successfully"
        print(f"Success for test {test}")

    def addSkip(self, test, reason):
        """Called when a test is skipped."""
        print(f"Skipping test {test} for reason {reason}")
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
