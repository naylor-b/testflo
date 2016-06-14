
"""
This is meant to be executed as a subprocess of testflo.

"""

if __name__ == '__main__':
    import sys
    import os
    import traceback

    from testflo.test import Test
    from testflo.cover import save_coverage
    from testflo.qman import get_client_queue

    queue = get_client_queue()
    os.environ['TESTFLO_QUEUE'] = ''

    try:
        try:
            test = Test(sys.argv[1])
            test.nocapture = True # so we don't lose stdout
            test.run()
        except:
            print(traceback.format_exc())
            test.status = 'FAIL'
            test.err_msg = traceback.format_exc()

        save_coverage()

    except:
        test.err_msg = traceback.format_exc()
        test.status = 'FAIL'

    sys.stdout.flush()
    sys.stderr.flush()

    queue.put(test)
