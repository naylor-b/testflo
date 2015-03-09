
"""
This is for running a test in a subprocess.
"""

if __name__ == '__main__':
    import sys
    import traceback

    from testflo.main import _get_parser
    from testflo.runner import TestRunner, exit_codes

    exitcode = 0

    try:
        options = _get_parser().parse_args()
        runner = TestRunner(options)
        result = runner.run_testspec(options.tests[0])
        if result.status != 'OK':
            sys.stderr.write(result.err_msg)
            exitcode = exit_codes[result.status]

    except:
        sys.stderr.write(traceback.format_exc())
        exitcode = exit_codes['FAIL']

    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(exitcode)
