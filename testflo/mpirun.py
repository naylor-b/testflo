
"""
This is meant to be executed using mpirun.

"""

if __name__ == '__main__':
    import sys
    import os
    import traceback
    import json

    from mpi4py import MPI
    from testflo.util import _get_parser, get_memory_usage
    from testflo.runner import TestRunner, exit_codes
    from testflo.test import Test
    from testflo.cover import save_coverage
    from testflo.options import get_options

    exitcode = 0  # use 0 for exit code of all ranks != 0 because otherwise,
                  # MPI will terminate other processes
    info = {}

    try:
        try:
            comm = MPI.COMM_WORLD
            options = get_options()
            test = Test(options.tests[0])
            result = test.run()
            # runner = TestRunner(options)
            # result = runner.run_testspec(options.tests[0])
        except:
            result = Test(options.tests[0], 'FAIL', err_msg=traceback.format_exc())

        # collect resource usage data
        memory_usage = get_memory_usage()
        memory_usages = comm.gather(memory_usage, root=0)

        # collect results
        results = comm.gather(result, root=0)

        if comm.rank == 0:
            # sum all resource usage data
            rdata = {}
            info['memory_usage'] = 0
            for mem in memory_usages:
                info['memory_usage'] +=  mem

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
        sys.stdout.flush()
        sys.stderr.flush()
        if comm.rank == 0:
            try:
                with open('testflo.%d' % os.getppid(), 'w') as f:
                    f.write(json.dumps(info))
            except AttributeError:
                # getppid() is not available on Windows with py27
                pass
        sys.exit(exitcode)
