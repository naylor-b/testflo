from distutils.core import setup

import re

__version__ = re.findall(
    r"""__version__ = ["']+([0-9\.]*)["']+""",
    open('testflo/__init__.py').read(),
)[0]

setup(name='testflo',
      version=__version__,
      description="A simple flow-based testing framework",
      long_description="""
        usage: testflo [options]

        positional arguments:
          test                  A test method, test case, module, or directory to run.

        optional arguments:
          -h, --help            show this help message and exit
          -c FILE, --config FILE
                                Path of config file where preferences are specified.
          -t FILE, --testfile FILE
                                Path to a file containing one testspec per line.
          --maxtime TIME_LIMIT  Specifies a time limit in seconds for tests to be
                                saved to the quicktests.in file.
          -n NUM_PROCS, --numprocs NUM_PROCS
                                Number of processes to run. By default, this will use
                                the number of CPUs available. To force serial
                                execution, specify a value of 1.
          -o FILE, --outfile FILE
                                Name of test report file. Default is
                                testflo_report.out.
          -v, --verbose         Include testspec and elapsed time in screen output.
                                Also shows all stderr output, even if test doesn't
                                fail
          --compact             Limit output to a single character for each test.
          --dryrun              Don't actually run tests, but print which tests would
                                have been run.
          --pre_announce        Announce the name of each test before it runs. This
                                can help track down a hanging test. This automatically
                                sets -n 1.
          -f, --fail            Save failed tests to failtests.in file.
          --full_path           Display full test specs instead of shortened names.
          -i, --isolated        Run each test in a separate subprocess.
          --nompi               Force all tests to run without MPI. This can be useful
                                for debugging.
          -x, --stop            Stop after the first test failure, or as soon as
                                possible when running concurrent tests.
          -s, --nocapture       Standard output (stdout) will not be captured and will
                                be written to the screen immediately.
          --coverage            Perform coverage analysis and display results on
                                stdout
          --coverage-html       Perform coverage analysis and display results in
                                browser
          --coverpkg PKG        Add the given package to the coverage list. You can
                                use this option multiple times to cover multiple
                                packages.
          --cover-omit FILE     Add a file name pattern to remove it from coverage.
          -b, --benchmark       Specifies that benchmarks are to be run rather than
                                tests, so only files starting with "benchmark\_" will
                                be executed.
          -d FILE, --datafile FILE
                                Name of benchmark data file. Default is
                                benchmark_data.csv.
          --noreport            Don't create a test results file.
          -m GLOB, --match GLOB, --testmatch GLOB
                                Pattern to use for test discovery. Multiple patterns
                                are allowed.
          --timeout TIMEOUT     Timeout in seconds. Test will be terminated if it
                                takes longer than timeout. Only works for tests
                                running in a subprocess (MPI and isolated).
      """,
      license='Apache 2.0',
      install_requires=[
        'six',
        'coverage'
      ],
      packages=['testflo'],
      entry_points="""
          [console_scripts]
          testflo=testflo.main:main
      """
      )
