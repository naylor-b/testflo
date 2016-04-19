
import sys

from testflo.util import elapsed_str

class ResultPrinter(object):
    """Prints the status and error message (if any) of each Test object
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

        stats = elapsed_str(result.elapsed())
        if result.memory_usage:
            stats = stats + ', ' + str(result.memory_usage) + ' MB'

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
