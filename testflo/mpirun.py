
"""
This is meant to be executed using mpirun.

NOTE: Currently some tests run using this hang mysteriously.
"""

if __name__ == '__main__':
    import sys
    import traceback
    import resource
    import json

    from mpi4py import MPI
    from testflo.main import _get_parser
    from testflo.util import attr_dict
    from testflo.runner import TestRunner, exit_codes
    from testflo.result import TestResult
    from testflo.cover import save_coverage

    exitcode = 0 # use 0 for exit code of all ranks != 0 because otherwise,
                 # MPI will terminate other processes
    info = {}

    try:
        try:
            comm = MPI.COMM_WORLD
            options = _get_parser().parse_args()
            runner = TestRunner(options)
            result = runner.run_testspec(options.tests[0])
        except:
            print traceback.format_exc()
            result = TestResult(options.tests[0], 0., 0., 'FAIL',
                                traceback.format_exc())

        # collect resource usage data
        rusage = attr_dict(resource.getrusage(resource.RUSAGE_SELF))
        rusages = comm.gather(rusage, root=0)

        # collect results
        results = comm.gather(result, root=0)

        if comm.rank == 0:
            # sum all resource usage data
            rdata = {}
            for r in rusages:
                for key, val in r.items():
                    rdata[key] = rdata.setdefault(key, 0) + val
            info['rdata'] = rdata

            # check for errors and record error message
            for r in results:
                if r.status != 'OK':
                    info['err_msg'] = result.err_msg
                    exitcode = exit_codes[r.status]
                    break

        save_coverage()

    except Exception:
        exc = sys.exc_info()
        info['err_msg'] = traceback.format_exc()
        exitcode = exit_codes['FAIL']

    finally:
        if comm.rank == 0:
            sys.stderr.write(json.dumps(info))
        sys.stderr.flush()
        sys.stdout.flush()
        sys.exit(exitcode)
