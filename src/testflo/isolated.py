
"""
This is for running a test in a subprocess.
"""

if __name__ == '__main__':
    import sys
    import os
    import traceback

    from testflo.main import _get_parser
    from testflo.runner import TestRunner, exit_codes
    from testflo.result import TestResult

    exitcode = 0

    try:
        try:
            options = _get_parser().parse_args()
            runner = TestRunner(options)
            result = runner.run_testspec(options.tests[0])
        except:
            result = TestResult(options.tests[0], 0., 0., 'FAIL',
                                traceback.format_exc())

        if result.status != 'OK':
            sys.stderr.write(result.err_msg)
            exitcode = exit_codes[result.status]

    except:
        exc = sys.exc_info()
        sys.stderr.write(traceback.format_exc())
        exitcode = exit_codes['FAIL']
        #raise exc[0], exc[1], exc[2]

    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(exitcode)
