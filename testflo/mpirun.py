
"""
This is meant to be executed using mpirun.  It is called as a subprocess
to run an MPI test.

"""

if __name__ == '__main__':
    import sys
    import os
    import traceback

    os.environ['OPENMDAO_USE_MPI'] = '1'

    from mpi4py import MPI
    from testflo.test import Test
    from testflo.cover import setup_coverage, save_coverage
    from testflo.qman import get_client_queue
    from testflo.options import get_options

    exitcode = 0  # use 0 for exit code of all ranks != 0 because otherwise,
                  # MPI will terminate other processes

    queue = get_client_queue()
    os.environ['TESTFLO_QUEUE'] = ''

    options = get_options()
    setup_coverage(options)

    try:
        try:
            comm = MPI.COMM_WORLD
            test = Test(sys.argv[1], options)
            test.nocapture = True # so we don't lose stdout
            tests = test.run()
        except:
            print(traceback.format_exc())
            test.status = 'FAIL'
            test.err_msg = traceback.format_exc()
            tests = [test]

        # collect results
        results = comm.gather(tests, root=0)
        if comm.rank == 0:
            for r in results:
                for tst in r:
                    if not isinstance(r, Test):
                        print("\nNot all results gathered are Test objects.  "
                              "You may have out-of-sync collective MPI calls.\n")
                        break
            total_mem_usage = 0.
            for r in results:
                for tst in r:
                    if isinstance(r, Test):
                        total_mem_usage += r.memory_usage
                    break  # subtests don't track their own memory usage, so break after 1st one
            for tst in tests:
                tst.memory_usage = total_mem_usage

            # check for errors and record error message
            for r in results:
                for test, tst in zip(tests, r):
                    if test.status != 'FAIL' and tst.status in ('SKIP', 'FAIL'):
                        test.err_msg = tst.err_msg
                        test.status = tst.status

        save_coverage()

    except Exception:
        test.err_msg = traceback.format_exc()
        test.status = 'FAIL'

    finally:
        sys.stdout.flush()
        sys.stderr.flush()

        if comm.rank == 0:
            queue.put(tests)
