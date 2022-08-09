# RELEASE NOTES

***********************
# testflo version 1.4.9
July 25, 2022

- added --durations option and fixed some config file issues [#71](https://github.com/OpenMDAO/testflo/pull/71)
  - added --durations option that prints the n longest running tests (similar to pytest)
  - fixed the way the .testflo config file is processed so it should support setting any, or at least most of the command line options
  - added the --skip_dirs command line option (skip_dirs could be defined in the config file but it wasn't a valid command line option)

***********************
# testflo version 1.4.8
February 14, 2022

- added env var to tell other code when it's running under testflo [#64](https://github.com/OpenMDAO/testflo/pull/64)

***********************
# testflo version 1.4.7
October 13, 2021

- setting N_PROCS=1 will now run under MPI in OpenMDAO [#60](https://github.com/OpenMDAO/testflo/pull/60)
- fixed version regex (old one couldn't handle *-dev versions [#59](https://github.com/OpenMDAO/testflo/pull/59)

***********************
# testflo version 1.4.6
October 13, 2021

- fix for bad testcase comm [#55](https://github.com/OpenMDAO/testflo/pull/55)

***********************
# testflo version 1.4.5.1
April 13, 2021

- fixes places in the code that weren't properly handling Windows file paths that included a colon.

***********************
# testflo version 1.4.5
April 13, 2021

- add an argument to specify that any skipped tests should cause testflo to return a non-zero exit code

***********************
# testflo version 1.4.4
April 13, 2021

- made testflo work better with tests that aren't part of an installed package

***********************
# testflo version 1.4.3
Feb 3, 2021

- added a check for non-package test files with duplicate local names

***********************
# testflo version 1.4.2
Jun 10, 2020

- fix for discovery issue
  - issue happened when a test function has a decorator that doesn't rename the wrapped function to match the parent TestCase attribute
- added `--excludes` option to add glob patterns to exclude test functions
- fixed dryrun output to include only test specs
  - This change now allows you to pipe the output from `--dryrun` into a file you can later run using `-t`, making it easier to assemble custom lists of tests to run.
- declare support for more Python versions

***********************
# testflo version 1.4.1
Feb 28, 2020

- fix for bug in isolated tests

***********************
# testflo version 1.4.0
Feb 28, 2020

- **NOTE:** this version requires python 3.5 or higher
- fix for a change to multiprocessing spawn behavior on OSX for python 3.8

***********************
# testflo version 1.3.6
Feb 13, 2020

- add option to show skipped tests (even if not verbose)

***********************
# testflo version 1.3.5
Jan 6, 2020

- use setuptools
- filter out expected fails from failtests.in
- added msg when there are out-of-sync collective MPI calls
- require coverage <5.0

***********************
# testflo version 1.3.4
Dec 6, 2018

- bug fix

***********************
# testflo version 1.3.3
Dec 3, 2018

- bug fix

***********************
# testflo version 1.3.2
Nov 17, 2018

- added support for ISOLATED attribute

***********************
# testflo version 1.3.1
Aug 17, 2018

- output from `--pre_announce` now looks better, with the result (`.`, `S`, or `F`) showing on the same line as the "about to run ..." instead of on the following line
- comments are now allowed inside of a test list file
- added a `--full_path` option so that full testspec paths will be displayed. Having the full path make it easier to copy and paste the testspec to run testflo on just that single test.
- updated the long_description in setup.py for pypi.

*********************
# testflo version 1.1
September 27, 2016

- supports setUpModule/tearDownModule
- supports setUpClass/tearDownClass
- supports expected failures
- supports unittest.skip class decorator
- added `--compact` option to print only single character test results without showing error or skip messages
