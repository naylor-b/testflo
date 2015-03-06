"""
testflo is a python testing framework that takes an iterator of test
specifier names e.g., <test_module>:<testcase>.<test_method>, and feeds
them through a pipeline of iterators that operate on them and transform them
into TestResult objects, then pass them on to other objects in the pipeline.

The objects passed through the pipline are either strings that
indicate which test to run (I call them test specifiers), or TestReult
objects, which contain only the test specifier string, a status indicating
whether the test passed or failed, and captured stderr from the
running of the test.

The API necessary for objects that participate in the pipeline is a callable
that takes an input iterator and returns an output iterator.

"""

import os
import time

from argparse import ArgumentParser

from fnmatch import fnmatch
from multiprocessing import cpu_count

from testflo.runner import ConcurrentTestRunner, IsolatedTestRunner
from testflo.result import ResultPrinter, ResultSummary
from testflo.discover import TestDiscoverer, dryrun
from testflo.timefilt import TimeFilter

from testflo.fileutil import read_config_file, read_test_file


def _get_parser():
    """Returns a parser to handle command line args."""

    parser = ArgumentParser()
    parser.usage = "testflo [options]"
    parser.add_argument('-c', '--config', action='store', dest='cfg',
                        metavar='CONFIG',
                        help='Path of config file where preferences are specified.')
    parser.add_argument('-t', '--testfile', action='store', dest='testfile',
                        metavar='TESTFILE',
                        help='Path to a file containing one testspec per line.')
    parser.add_argument('--maxtime', action='store', dest='maxtime',
                        metavar='TIME_LIMIT', default=-1, type=float,
                        help='Specifies a time limit for tests to be saved to '
                             'the quicktests.in file.')
    parser.add_argument('-n', '--numprocs', type=int, action='store',
                        dest='num_procs', metavar='NUM_PROCS', default=cpu_count(),
                        help='Number of processes to run. By default, this will '
                             'use the number of CPUs available.  To force serial'
                             ' execution, specify a value of 1.')
    parser.add_argument('-o', '--outfile', action='store', dest='outfile',
                        metavar='OUTFILE', default='test_report.out',
                        help='Name of test report file')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='If true, include testspec and elapsed time in '
                             'screen output')
    parser.add_argument('--dryrun', action='store_true', dest='dryrun',
                        help="If true, don't actually run tests, but report"
                          "which tests would have been run")
    parser.add_argument('-i', '--isolated', action='store_true', dest='isolated',
                        help="If true, run each test in a separate subprocess."
                             " This is required to run MPI tests.")
    parser.add_argument('-x', '--stop', action='store_true', dest='stop',
                        help="If true, stop after the first test failure")
    parser.add_argument('-s', '--nocapture', action='store_true', dest='nocapture',
                        help="If true, stdout will not be captured and will be"
                             " written to the screen immediately")
    parser.add_argument('tests', metavar='test', nargs='*',
                       help='A test method/case/module/directory to run')

    return parser

def run_pipeline(source, pipe):
    """Run a pipeline of test iteration objects."""

    global _start_time
    _start_time = time.time()

    iters = [source]

    # give each object the iterator from upstream in the pipeline
    for i,p in enumerate(pipe):
        iters.append(p(iters[i]))

    # iterate over the last iter in the pipline and we're done
    for result in iters[-1]:
        pass

def main(args=None):
    options = _get_parser().parse_args(args)

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

    with open(options.outfile, 'w') as report:
        pipeline = [
            TestDiscoverer(dir_exclude=dir_exclude).get_iter,
        ]

        if options.dryrun:
            pipeline.extend(
                [
                    dryrun,
                ]
            )
        else:
            if options.isolated:
                try:
                    import mpi4py
                except ImportError:
                    pipeline.append(IsolatedTestRunner(options).get_iter)
                else:
                    from testflo.mpi import IsolatedMPITestRunner
                    pipeline.append(IsolatedMPITestRunner(options).get_iter)
            else:
                pipeline.append(ConcurrentTestRunner(options).get_iter)

            pipeline.extend(
            [
                ResultPrinter(verbose=options.verbose).get_iter,
                ResultSummary().get_iter,

                # mirror results and summary to a report file
                ResultPrinter(report, verbose=options.verbose).get_iter,
                ResultSummary(report).get_iter,
            ])

        if options.maxtime > 0:
            pipeline.append(TimeFilter(options.maxtime).get_iter)

        run_pipeline(tests, pipeline)

def run_tests(args=None):
    """This can be executed from within an "if __name__ == '__main__'" block
    to execute the tests found in that module.
    """
    if args is None:
        args = []
    main(list(args) + [__import__('__main__').__file__])

if __name__ == '__main__':
    main()
