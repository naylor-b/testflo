testflo
=======

testflo is a python testing framework that uses a simple pipeline of
iterators to process test specifications, run the tests, and process the
results.

Why write another testing framework?
------------------------------------

testflo was written to support testing of the OpenMDAO software framework.
Some OpenMDAO features require execution under MPI while some others don't,
so we wanted a testing framework that could run all of our tests in the same
way and would allow us to build all of our tests using unittest.TestCase
objects that we were already familiar with.  The MPI testing functionality
was originally implemented using the nose testing framework.  It worked, but
was always buggy, and the size and complexity of the nose framework made it
difficult to know exactly what was going on.

Enter testflo, an attempt to build a simpler testing framework that would have
the basic functionality that other test frameworks have, with the additional
ability to run MPI unit tests that are very similar to regular unit tests.


Some testflo features
---------------------

    - MPI unit testing
    - *pre_announce* option to print test name before running in order to
      quickly identify hanging MPI tests
    - concurrent testing  (on by default, use '-n 1' to turn it off)
    - test coverage
    - flexible execution - can be given a directory, a file, a module path,
      a file:testcase.method, a module:testcase.method, or a file containing
      a list of any of the above. Has options to generate test list files
      containing all failed tests or all tests that execute within a certain
      time limit.
    - end of testing summary


Operating Systems and Python Versions
-------------------------------------

testflo is used to test OpenMDAO as part of its CI process,
so we run it nearly every day on linux, Windows and OS X under
python 2.7 and 3.5.


You can install testflo directly from github using the following command:

`pip install git+https://github.com/OpenMDAO/testflo.git`

If you try it out and find any problems, submit them as issues on github at
https://github.com/OpenMDAO/testflo.
