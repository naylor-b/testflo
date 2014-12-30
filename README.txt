testflo is a python testing framework that uses a simple pipeline of
iterators to process test specifications, run the tests, and process the
results.

In terms of behavior, I tried to make it similar to the python 'nose' framework,
although testflo has only a small subset of the command line options that
nosetests has.

By default, testflo uses the multiprocessing library to run tests concurrently,
setting the number of processes equal to the number of CPUs on your computer.
If you want serial execution instead, just specify -n 1 on the command line.  
As usual, -h on the command line will list all of the available command line 
arguments.

So far, testflo has only been tested on linux with python 2.7.  If you try it
out and have any feedback, put it in the testflo issue tracker on bitbucket.
