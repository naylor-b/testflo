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


def mem_str(pdata):
    if pdata is None:
        return ''
    else:
        return str(pdata['ru_maxrss']/1000.0) + ' MB'


class TestResult(object):
    """Contains the path to the test function/method, status
    of the test (if finished), error and stdout messages (if any),
    start/end times and optionally data about the process in
    which the test was run (e.g. memory usage).
    """

    def __init__(self, testspec, start_time, end_time,
                 status='OK', err_msg='', pdata=None):
        self.testspec = testspec
        self.status = status
        self.err_msg = err_msg
        self.start_time = start_time
        self.end_time = end_time
        self.pdata = pdata

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
        for result in input_iter:
            self._print_result(result)
            yield result

    def _print_result(self, result):
        stream = self.stream

        if result.pdata is not None:
            stats = elapsed_str(result.elapsed()) + ', ' + mem_str(result.pdata)
        else:
            stats = elapsed_str(result.elapsed())

        if self.verbose:
            stream.write("%s ... %s (%s)\n%s" % (result.testspec,
                                                 result.status,
                                                 stats,
                                                 result.err_msg))
            if result.err_msg:
                stream.write("\n")
        elif result.status == 'OK':
            stream.write('.')
        elif result.status == 'FAIL':
            stream.write('F')
        elif result.status == 'SKIP':
            stream.write('S')

        if not self.verbose and result.err_msg:
            if result.status == 'FAIL':
                stream.write("\n%s ... %s (%s)\n%s\n" % (result.testspec,
                                                         result.status,
                                                         stats,
                                                         result.err_msg))
            elif result.status == 'SKIP':
                stream.write("\n%s: SKIP: %s\n" % (result.short_name(),
                                                   result.err_msg))

        stream.flush()


class ResultSummary(object):
    """Writes a test summary after all tests are run."""

    def __init__(self, options, stream=sys.stdout):
        self.stream = stream
        self.options = options
        self._start_time = time.time()

    def get_iter(self, input_iter):
        oks = 0
        total = 0
        fails = []
        skips = []
        test_sum_time = 0.

        write = self.stream.write

        for test in input_iter:
            total += 1

            if test.status == 'OK':
                oks += 1
                test_sum_time += (test.end_time-test.start_time)
            elif test.status == 'FAIL':
                fails.append(test.short_name())
                test_sum_time += (test.end_time-test.start_time)
            elif test.status == 'SKIP':
                skips.append(test.short_name())
            yield test

        # now summarize the run
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

        s = "" if total == 1 else "s"
        if self.options.isolated:
            procstr = " in isolated processes"
        else:
            procstr = " using %d processes" % self.options.num_procs
        write("\n\nRan %d test%s%s\nSum of test times: %s\n"
              "Wall clock time:   %s\nSpeedup: %f\n\n" %
                      (total, s, procstr,
                       elapsed_str(test_sum_time), elapsed_str(wallclock),
                       test_sum_time/wallclock))


class BenchmarkWriter(object):
    """Writes benchmark data to a file for postprocessing.
       Data is written as comma separated values (CSV)
    """

    def __init__(self, stream=sys.stdout):
        self.timestamp = time.time()
        self.stream = stream

    def get_iter(self, input_iter):
        for result in input_iter:
            self._write_data(result)
            yield result

    def _write_data(self, result):
        stream = self.stream
        stream.write('%d,%s,%s,%f,%f\n' % (
            self.timestamp,
            result.testspec,
            result.status,
            result.elapsed(),
            result.pdata['ru_maxrss']/1000.0
        ))
        stream.flush()
