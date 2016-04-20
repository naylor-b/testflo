from __future__ import print_function

class TimeFilter(object):
    """This iterator saves only tests that complete successfully
    in max_time or less.
    """
    def __init__(self, max_time, outfile='quicktests.in'):
        self.outfile = outfile
        self.max_time = max_time

    def get_iter(self, input_iter):
        with open(self.outfile, 'w') as f:
            for result in input_iter:
                if result.status == 'OK' and result.elapsed() <= self.max_time:
                    print(result.spec, file=f)
                yield result
