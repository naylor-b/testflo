testflo
=======

testflo is a python testing framework that uses a simple pipeline of
iterators to process test specifications, run the tests, and process the
results.

testflo will work with the same test files that you might use with unittest
or nose.

By default, testflo uses the multiprocessing library to run tests concurrently,
setting the number of processes equal to the number of CPUs on your computer.
If you want serial execution instead, just specify -n 1 on the command line.  
As usual, -h on the command line will list all of the available command line
arguments.

Operating Systems
-----------------

testflo has been tested on linux, Windows and OS X.

Python Versions
---------------

testflo has been tested with python 2.7 and python 3.5.

You can install testflo directly from github using the following command:

`pip install git+https://github.com/naylor-b/testflo.git`

If you try it out and find any problems, submit them as issues on github at
https://github.com/naylor-b/testflo.
