testflo
=======

testflo is a python testing framework that uses a pipeline of
iterators to process test specifications, run the tests, and process the
results.

Why write another testing framework?
------------------------------------

testflo was written to support testing of the OpenMDAO framework.
Some OpenMDAO features require execution under MPI while some others don't,
so we wanted a testing framework that could run all of our tests in the same
way and would allow us to build all of our tests using unittest.TestCase
objects that we were already familiar with.  The MPI testing functionality
was originally implemented using the nose testing framework.  It worked, but
was always buggy, and the size and complexity of the nose framework made it
difficult to know exactly what was going on.

Enter testflo, an attempt to build a simpler testing framework that would have
the basic functionality of other test frameworks, with the additional
ability to run MPI unit tests that are very similar to regular unit tests.


Some testflo features
---------------------

*    MPI unit testing
*    *pre_announce* option to print test name before running in order to
     quickly identify hanging MPI tests
*    concurrent testing  (on by default, use '-n 1' to turn it off)
*    test coverage
*    flexible execution - can be given a directory, a file, a module path,
     *file:testcase.method*, *module:testcase.method*, or a file containing
     a list of any of the above. Has options to generate test list files
     containing all failed tests or all tests that execute within a certain
     time limit.
*    end of testing summary


Usage
-----

For a full list of testflo options, execute the following:

`testflo -h`


NOTE: Because testflo runs tests concurrently by default, your tests must be
written with concurrency in mind or they may fail.  For example, if multiple
tests write output to a file with the same name, you have to make sure that those
tests are executed in different directories to prevent that file from being
corrupted.  If your tests are not written to run concurrently, you can always
just run them with `testflo -n 1` and run them in serial instead.

The following is an example of what an MPI unit test looks like.  To tell
testflo that a TestCase is an MPI TestCase, you add a class attribute
called N_PROCS to it and set it to the number of MPI processes to use for the
test.  That's all there is to it. Of course, depending on what sort of MPI code
you're testing, it's up to you to potentially test for different things on
different ranks.


```python

class MyMPI_TestCase(TestCase):

    N_PROCS = 4  # this is how many MPI processes to use for this TestCase.

    def test_foo(self):

        # do your MPI testing here, e.g.,

        if self.comm.rank == 0:
            # some test only valid on rank 0...


```


Here's an example of testflo output for openmdao.core:


```

openmdao$ testflo openmdao.core
............................................................................
............................................................................
............................................................................
..............................

OK

Passed:  258
Failed:  0
Skipped: 0


Ran 258 tests using 8 processes
Wall clock time:   00:00:1.82

```

Running testflo in verbose mode on openmdao.core.test.test_problem is shown
below. The verbose output contains the full test name as well as the elapsed
time and memory usage.


```

openmdao$ testflo openmdao.core.test.test_problem -v
openmdao.core.test.test_problem:TestCheckSetup.test_pbo_messages ... OK (00:00:0.02, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_check_promotes ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_conflicting_connections ... OK (00:00:0.02, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_conflicting_promoted_state_vars ... OK (00:00:0.00, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_conflicting_promotions ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestCheckSetup.test_out_of_order ... OK (00:00:0.02, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_explicit_connection_errors ... OK (00:00:0.02, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_find_subsystem ... OK (00:00:0.00, 69 MB)
openmdao.core.test.test_problem:TestCheckSetup.test_cycle ... OK (00:00:0.06, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_input_input_explicit_conns_no_conn ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_illegal_desvar ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_input_input_explicit_conns_w_conn ... OK (00:00:0.02, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_check_connections ... OK (00:00:0.06, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_mode_auto ... OK (00:00:0.03, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_check_parallel_derivs ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_simplest_run ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_basic_run ... OK (00:00:0.03, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_change_solver_after_setup ... OK (00:00:0.04, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_no_vecs ... OK (00:00:0.08, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_src_idx_gt_src_size ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_src_idx_neg ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_simplest_run_w_promote ... OK (00:00:0.02, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_unconnected_param_access ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_variable_access_before_setup ... OK (00:00:0.00, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_scalar_sizes ... OK (00:00:0.07, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_byobj_run ... OK (00:00:0.01, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_error_change_after_setup ... OK (00:00:0.31, 70 MB)
openmdao.core.test.test_problem:TestProblem.test_unconnected_param_access_with_promotes ... OK (00:00:0.04, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_variable_access ... OK (00:00:0.06, 69 MB)
openmdao.core.test.test_problem:TestProblem.test_iprint ... OK (00:00:0.25, 73 MB)


OK

Passed:  30
Failed:  0
Skipped: 0


Ran 30 tests using 8 processes
Wall clock time:   00:05:5.01

```

Operating Systems and Python Versions
-------------------------------------

testflo is used to test OpenMDAO as part of its CI process,
so we run it nearly every day on linux, Windows and OS X under
python 2.7 and 3.6.


You can install testflo directly from github using the following command:

`pip install git+https://github.com/OpenMDAO/testflo.git`


or install from PYPI using:


`pip install testflo`



If you try it out and find any problems, submit them as issues on github at
https://github.com/OpenMDAO/testflo.
