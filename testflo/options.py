import sys

from testflo.util import _get_parser

_options = None

def get_options(args=None):
    global _options
    if _options is None:
        if args is None:
            args = sys.argv[1:]

        _options = _get_parser().parse_args(args)
    return _options
