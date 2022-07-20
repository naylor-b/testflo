import sys
import os

class DurationSummary(object):
    """Writes a summary of the tests taking the longest time."""

    def __init__(self, options, stream=sys.stdout):
        self.stream = stream
        self.options = options
        self.startdir = os.getcwd()

    def get_iter(self, input_iter):
        durations = []

        for test in input_iter:
            durations.append((test.spec, test.end_time - test.start_time))
            yield test

        write = self.stream.write
        mintime = self.options.durations_min

        if mintime > 0.:
            title = " Max duration tests with duration >= {} sec ".format(mintime)
        else:
            title = " Max duration tests "

        eqs = "=" * 16

        write("\n\n{}{}{}\n\n".format(eqs, title, eqs))
        count = self.options.durations

        for spec, duration in sorted(durations, key=lambda t: t[1], reverse=True):
            if duration < mintime:
                break

            if spec.startswith(self.startdir):
                spec = spec[len(self.startdir):]

            write("{:8.3f} sec - {}\n".format(duration, spec))

            count -= 1
            if count <= 0:
                break

        write("\n" + "=" * (len(title) + 2 * len(eqs)) + "\n")
