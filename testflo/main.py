"""
testflo is a python testing framework that takes an iterator of test
specifier names e.g., <test_module>:<testcase>.<test_method>, and feeds
them through a pipeline of iterators that operate on them and transform them
into Test objects, then pass them on to other objects in the pipeline.

The Discoverer object takes an initial list of directory names, module names,
or test specifier strings and returns an iterator of Test objects representing
all of the tests found.  The rest of the pipeline operates on these Test
objects, which contain a test specifier string, a status indicating
whether the test passed or failed, and captured stderr from the
running of the test.

The only real API function for objects added to the pipline is:

    def get_iter(self, input_iter)

Functions can also be added directly to the pipeline as long as they
take a Test object iterator as an arg and return a Test object iterator.

The get_iter function should expect to receive an iterator over Test objects
and should return an iterator over Test objects.

"""
from __future__ import print_function

import os
import sys
import six
import time
import subprocess

from fnmatch import fnmatch

from testflo.runner import ConcurrentTestRunner, TestRunner
from testflo.test import Test
from testflo.printer import ResultPrinter
from testflo.benchmark import BenchmarkWriter
from testflo.summary import ResultSummary
from testflo.discover import TestDiscoverer
from testflo.timefilt import TimeFilter

from testflo.util import read_config_file, read_test_file, _get_parser, get_open_address
from testflo.cover import setup_coverage, finalize_coverage
from testflo.profile import setup_profile, finalize_profile
from testflo.options import get_options

options = get_options()


def dryrun(input_iter):
    """Iterator added to the pipeline when user only wants
    a dry run, listing all of the discovered tests but not
    actually running them.
    """
    for spec in input_iter:
        print(spec)
        yield Test(spec, 'OK')

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


def main(args=None):
    # FIXME: get rid of this
    if args is None:
        args = sys.argv[1:]

    options = get_options(args)

    options.skip_dirs = []

    # read user prefs from ~/.testflo file.
    # create one if it doesn't exist
    homedir = os.path.expanduser('~')
    rcfile = os.path.join(homedir, '.testflo')
    if not os.path.isfile(rcfile):
        with open(rcfile, 'w') as f:
            f.write("""[testflo]
skip_dirs=site-packages,
    dist-packages,
    build,
    contrib
""")
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

    if options.benchmark:
        options.num_procs = 1
        options.isolated = True
        discoverer = TestDiscoverer(module_pattern=six.text_type('benchmark*.py'),
                                    func_pattern=six.text_type('benchmark*'),
                                    dir_exclude=dir_exclude)
        benchmark_file = open(options.benchmarkfile, 'a')
    else:
        discoverer = TestDiscoverer(dir_exclude=dir_exclude)
        benchmark_file = open(os.devnull, 'a')

    try:
        retval = 0
        server_proc = None

        if options.isolated or not options.nompi:
            addr = get_open_address()
            authkey = 'foo'

            cmd = [sys.executable,
                   os.path.join(os.path.dirname(__file__), 'qman.py')]
            if 'win' in sys.platform:
                cmd.extend((addr, authkey))
            else:
                cmd.extend((addr[0], str(addr[1]), authkey))

            server_proc = subprocess.Popen(cmd, env=os.environ)

            if 'win' in sys.platform:
                # wait for named pipe to exist before we continue and let
                # clients try to connect
                while True:
                    if os.path.exists(addr):
                        break
                    time.sleep(.1)
        else:
            addr = authkey = None

        with open(options.outfile, 'w') as report, benchmark_file as bdata:
            pipeline = [
                discoverer.get_iter,
            ]

            if options.dryrun:
                pipeline.extend([
                    dryrun,
                ])
            else:
                runner = ConcurrentTestRunner(options, addr, authkey)

                pipeline.append(runner.get_iter)

                if options.benchmark:
                    pipeline.append(BenchmarkWriter(stream=bdata).get_iter)

                pipeline.extend([
                    ResultPrinter(verbose=options.verbose).get_iter,
                    ResultSummary(options).get_iter,
                ])
                if not options.noreport:
                    # print verbose results and summary to a report file
                    pipeline.extend([
                        ResultPrinter(report, verbose=True).get_iter,
                        ResultSummary(options, stream=report).get_iter,
                    ])

            if options.maxtime > 0:
                pipeline.append(TimeFilter(options.maxtime).get_iter)

            retval = run_pipeline(tests, pipeline)

            finalize_coverage(options)
            finalize_profile(options)
    finally:
        if server_proc is not None and (options.isolated or not options.nompi):
            server_proc.terminate()

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
