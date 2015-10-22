
"""
This is meant to be executed using mpirun.

NOTE: Currently some tests run using this hang mysteriously.
"""

if __name__ == '__main__':
    import sys
    import traceback

    from mpi4py import MPI
    from testflo.main import _get_parser
    from testflo.runner import TestRunner, exit_codes
    from testflo.result import TestResult
    from testflo.cover import save_coverage

    exitcode = 0 # use 0 for exit code of all ranks != 0 because otherwise,
                 # MPI will terminate other processes

    try:
        try:
            comm = MPI.COMM_WORLD
            options = _get_parser().parse_args()
            runner = TestRunner(options)
            result = runner.run_testspec(options.tests[0])
        except:
            result = TestResult(options.tests[0], 0., 0., 'FAIL',
                                traceback.format_exc())

        results = comm.gather(result, root=0)

        if comm.rank == 0:
            for r in results:
                if r.status != 'OK':
                    sys.stderr.write(r.err_msg)
                    exitcode = exit_codes[r.status]
                    break
        save_coverage()

    except Exception:
        exc = sys.exc_info()
        sys.stderr.write(traceback.format_exc())
        exitcode = exit_codes['FAIL']

    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(exitcode)
