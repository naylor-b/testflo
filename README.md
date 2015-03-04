testflo
=======

testflo is a python testing framework that uses a simple pipeline of
iterators to process test specifications, run the tests, and process the
results.

testflow doesn't use any of the unittest or nose frameworks,
aside from unittest.TestCase, which it treats basically as a container of test
methods, and the unittest.SkipTest exception, which it uses to identify
skipped tests.  Aside from executing test methods within a TestCase, along
with the setUp and tearDown methods if found, no other methods or attributes of
TestCase are used.  testflo simply executes the setUp, test_, and tearDown
methods and catches exceptions to detect failures or skips.

By default, testflo uses the multiprocessing library to run tests concurrently,
setting the number of processes equal to the number of CPUs on your computer.
If you want serial execution instead, just specify -n 1 on the command line.  
As usual, -h on the command line will list all of the available command line
arguments.

So far, testflo has only been tested on linux and OS X with python 2.7.  
If you try it out and have any feedback, submit it as an issue on github.
