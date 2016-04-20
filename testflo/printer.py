
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

        if result.mpi and result.nprocs > 0:
            run_type = '(mpi) '
        elif result.isolated:
            run_type = '(isolated) '
        else:
            run_type = ''

        if self.verbose or result.err_msg:
            if result.err_msg:
                stream.write("%s%s ... %s (%s, %d MB)\n%s\n" % (
                                                     run_type,
                                                     result.spec,
                                                     result.status,
                                                     stats, result.memory_usage,
                                                     result.err_msg))
            else:
                stream.write("%s%s ... %s (%s, %d MB)\n" % (
                                                    run_type,
                                                    result.spec,
                                                    result.status,
                                                    stats, result.memory_usage))
        elif result.status == 'OK':
            stream.write('.')

        stream.flush()
