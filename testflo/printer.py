
import sys

from testflo.util import elapsed_str

_result_map = {
    ('FAIL', False): 'F',
    ('FAIL', True): 'X',  # expected failure
    ('SKIP', False): 'S',
    ('SKIP', True): 'S',
    ('OK', False): '.',
    ('OK', True): 'U',  # unexpected success
}

class ResultPrinter(object):
    """Prints the status and error message (if any) of each Test object
    after its test has been run if verbose is True.  If verbose is False,
    it displays a dot for each successful test, but skips or failures are
    still displayed in verbose form.
    """

    def __init__(self, options, stream=sys.stdout, verbose=0):
        self.stream = stream
        self.options = options
        self.verbose = verbose

    def get_iter(self, input_iter):
        for result in input_iter:
            self._print_result(result)
            yield result

    def _print_result(self, result):
        stream = self.stream

        stats = elapsed_str(result.elapsed())

        if ((result.expected_fail and result.status != 'FAIL') or
            (not result.expected_fail and result.status == 'FAIL')):
            show_msg = True
        else:
            show_msg = False

        if (self.verbose == 0 and (result.err_msg and show_msg)) or self.verbose > 0:
            if result.mpi and result.nprocs > 0:
                run_type = '(mpi) '
            elif result.isolated:
                run_type = '(isolated) '
            else:
                run_type = ''

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
        else:
            stream.write(_result_map[(result.status, result.expected_fail)])
            if self.options.pre_announce:
                stream.write('\n')

        stream.flush()
