import os
import sys
import time

def elapsed_str(elapsed):
    """return a string of the form hh:mm:sec"""
    hrs = int(elapsed/3600)
    elapsed -= (hrs * 3600)
    mins = int(elapsed/60)
    elapsed -= (mins * 60)
    return "%02d:%02d:%.2f" % (hrs, mins, elapsed)


class TestResult(object):
    """Contains the path to the test function/method, status
    of the test (if finished), error and stdout messages (if any),
    and start/end times.
    """

    def __init__(self, testspec, start_time, end_time,
                 status='OK', err_msg=''):
        self.testspec = testspec
        self.status = status
        self.err_msg = err_msg
        self.start_time = start_time
        self.end_time = end_time

    def elapsed(self):
        return self.end_time - self.start_time

    def short_name(self):
        """Returns the testspec with only the file's basename instead
        of its full path.
        """
        parts = self.testspec.split(':', 1)
        fname = os.path.basename(parts[0])
        return ':'.join((fname, parts[1]))


class ResultPrinter(object):
    """Prints the status and error message (if any) of each TestResult object
    after its test has been run if verbose is True.  If verbose is False,
    it displays a dot for each successful test, an 'S' for skipped tests,
    and an 'F' for failed tests.  If a test fails, the error message is always
    displayed, even in non-verbose mode.
    """

    def __init__(self, stream=sys.stdout, verbose=False):
        self.stream = stream
        self.verbose = verbose

    def get_iter(self, input_iter):
        return self._print_iter(input_iter)

    def _print_iter(self, input_iter):
        for result in input_iter:
            self._print_result(result)
            yield result

    def _print_result(self, result):
        stream = self.stream
        if self.verbose:
            stream.write("%s ... %s (%s)\n%s\n" % (result.testspec,
                                                   result.status,
                                                   elapsed_str(result.elapsed()),
                                                   result.err_msg))
        elif result.status == 'OK':
            stream.write('.')
        elif result.status == 'FAIL':
            stream.write('F')
        elif result.status == 'SKIP':
            stream.write('S')

        if result.err_msg and result.status == 'FAIL':
            if not self.verbose:
                stream.write("\n%s ... %s (%s)\n%s\n" % (result.testspec,
                                                         result.status,
                                                         elapsed_str(result.elapsed()),
                                                         result.err_msg))
        stream.flush()


class ResultSummary(object):
    """Writes a test summary after all tests are run."""

    def __init__(self, stream=sys.stdout):
        self.stream = stream
        self._start_time = time.time()

    def get_iter(self, input_iter):
        return self._iter_then_summarize(input_iter)

    def _iter_then_summarize(self, input_iter):
        global _start_time

        oks = 0
        total = 0
        fails = []
        skips = []

        write = self.stream.write

        for test in input_iter:
            total += 1

            if test.status == 'OK':
                oks += 1
            elif test.status == 'FAIL':
                fails.append(test.short_name())
            elif test.status == 'SKIP':
                skips.append(test.short_name())
            yield test

        if skips:
            write("\n\nThe following tests were skipped:\n")
            for s in sorted(skips):
                write(s)
                write('\n')

        if fails:
            write("\n\nThe following tests failed:\n")
            for f in sorted(fails):
                write(f)
                write('\n')
        else:
            write("\n\nOK")

        write("\n\nPassed:  %d\nFailed:  %d\nSkipped: %d\n" %
                            (oks, len(fails), len(skips)))

        wallclock = time.time() - self._start_time

        s = "s" if total > 1 else ""
        write("\n\nRan %d test%s  (elapsed time: %s)\n\n" %
                          (total, s, elapsed_str(wallclock)))
