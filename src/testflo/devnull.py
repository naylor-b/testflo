
class DevNull(object):
    """A class for throwaway stream output."""

    def write(self, s):
        pass

    def writelines(self, iterable):
        pass

    def flush(self):
        pass

    def isatty(self):
        return False
