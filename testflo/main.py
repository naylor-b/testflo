"""
testflo is a python testing framework that takes an iterator of test
specifier names e.g., <test_module>:<testcase>.<test_method>, and feeds
them through a pipeline of iterators that operate on them and transform them
into TestResult objects, then pass them on to other objects in the pipeline.

The objects passed through the pipline are either strings that
indicate which test to run (test specifiers), or TestReult
objects, which contain only the test specifier string, a status indicating
whether the test passed or failed, and captured stderr from the
running of the test.

The API necessary for objects that participate in the pipeline is a callable
that takes an input iterator and returns an output iterator.

"""
from __future__ import print_function

import os
import sys
import time

from fnmatch import fnmatch

from testflo.runner import ConcurrentTestRunner
from testflo.isolated import IsolatedTestRunner
from testflo.result import ResultPrinter, ResultSummary, TestResult
from testflo.discover import TestDiscoverer
from testflo.timefilt import TimeFilter

from testflo.util import read_config_file, read_test_file, _get_parser
from testflo.cover import setup_coverage, finalize_coverage
from testflo.profile import setup_profile, finalize_profile

def dryrun(input_iter):
    """Iterator added to the pipeline when user only wants
    a dry run, listing all of the discovered tests but not
    actually running them.
    """
    for spec in input_iter:
        print(spec)
        yield TestResult(spec, 0, 0)

def run_pipeline(source, pipe):
    """Run a pipeline of test iteration objects."""

    global _start_time
    _start_time = time.time()

    iters = [source]

    # give each object the iterator from upstream in the pipeline
    for i,p in enumerate(pipe):
        iters.append(p(iters[i]))

    return_code = 0

    # iterate over the last iter in the pipline and we're done
    for result in iters[-1]:
        if result.status == 'FAIL':
            return_code = 1

    return return_code

runner = None

def main(args=None):
    global runner

    if args is None:
        args = sys.argv[1:]

    options = _get_parser().parse_args(args)

    print('options:', options)

    options.skip_dirs = []

    # read user prefs from ~/.testflo file.  create one if it
    # isn't there
    homedir = os.path.expanduser('~')
    rcfile = os.path.join(homedir, '.testflo')
    if not os.path.isfile(rcfile):
        with open(rcfile, 'w') as f:
            f.write("""[testflo]
skip_dirs=site-packages,
    dist-packages,
    build,
    contrib
""" )
    read_config_file(rcfile, options)
    if options.cfg:
        read_config_file(options.cfg, options)

    tests = options.tests
    if options.testfile:
        tests += list(read_test_file(options.testfile))

    if not tests:
        tests = [os.getcwd()]

    def dir_exclude(d):
        for skip in options.skip_dirs:
            if fnmatch(os.path.basename(d), skip):
                return True
        return False

    setup_coverage(options)
    setup_profile(options)

    with open(options.outfile, 'w') as report:
        pipeline = [
            TestDiscoverer(dir_exclude=dir_exclude).get_iter,
        ]

        if options.dryrun:
            pipeline.extend([
                dryrun,
            ])
        else:
            if options.isolated:
                try:
                    import mpi4py
                except ImportError:
                    runner = IsolatedTestRunner(options, args)
                else:
                    from testflo.mpi import IsolatedMPITestRunner
                    runner = IsolatedMPITestRunner(options, args)
            else:
                runner = ConcurrentTestRunner(options)

            pipeline.append(runner.get_iter)

            pipeline.extend([
                ResultPrinter(verbose=options.verbose).get_iter,
                ResultSummary().get_iter,
            ])
            if not options.noreport:
                # mirror results and summary to a report file
                pipeline.extend([
                    ResultPrinter(report, verbose=options.verbose).get_iter,
                    ResultSummary(report).get_iter,
                ])

        if options.maxtime > 0:
            pipeline.append(TimeFilter(options.maxtime).get_iter)

        retval = run_pipeline(tests, pipeline)

        finalize_coverage(options)
        finalize_profile(options)

        return retval


def run_tests(args=None):
    """This can be executed from within an "if __name__ == '__main__'" block
    to execute the tests found in that module.
    """
    if args is None:
        args = []
    sys.exit(main(list(args) + [__import__('__main__').__file__]))


if __name__ == '__main__':
    sys.exit(main())
