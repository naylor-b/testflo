
"""
This is meant to be executed as a subprocess of testflo.

"""

if __name__ == '__main__':
    try:
        import coverage
    except ImportError:
        pass
    else:
        coverage.process_startup()

    import sys
    import os
    import traceback

    from testflo.test import Test
    from testflo.qman import get_client_queue
    from testflo.options import get_options

    queue = get_client_queue()
    os.environ['TESTFLO_QUEUE'] = ''

    options = get_options()

    try:
        try:
            test = Test(sys.argv[1], options)
            test.nocapture = True # so we don't lose stdout
            test.run()
        except:
            print(traceback.format_exc())
            test.status = 'FAIL'
            test.err_msg = traceback.format_exc()

    except:
        test.err_msg = traceback.format_exc()
        test.status = 'FAIL'

    sys.stdout.flush()
    sys.stderr.flush()

    queue.put(test)
