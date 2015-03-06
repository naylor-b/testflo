
"""
This is meant to be executed using mpirun.
"""

if __name__ == '__main__':
    import sys
    import os
    import traceback

    from mpi4py import MPI
    from testflo.main import _get_parser
    from testflo.runner import TestRunner
    from testflo.result import TestResult

    # exitcode = 0 # use 0 for exit code of all ranks != 0 because otherwise,
    #              # MPI will terminate other processes

    try:
        try:
            comm = MPI.COMM_WORLD
            options = _get_parser().parse_args()
            runner = TestRunner(options)
            result = runner.run_test(options.tests[0])
        except:
            result = TestResult(options.tests[0], 0., 0., 'FAIL',
                                traceback.format_exc())

        results = comm.gather(result, root=0)

        if comm.rank == 0:
            for r in results:
                if r.status != 'OK':
                    sys.stderr.write(r.err_msg)
                    #exitcode = exit_codes[r.status]
                    break

    except Exception:
        exc = sys.exc_info()
        sys.stderr.write(traceback.format_exc())
        #exitcode = exit_codes['FAIL']
        raise exc[0], exc[1], exc[2]

    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        #sys.exit(exitcode)
