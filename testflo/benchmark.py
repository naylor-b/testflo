import sys
import time

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
        stream.write('%d,%s,%s,%f,%f,%f,%f,%f\n' % (
            self.timestamp,
            result.spec,
            result.status,
            result.elapsed(),
            result.memory_usage,
            result.load[0],
            result.load[1],
            result.load[2]
        ))
        stream.flush()
