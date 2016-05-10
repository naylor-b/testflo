
"""
This is meant to be executed as a subprocess of testflo.

"""

if __name__ == '__main__':
    import sys
    import os
    import traceback

    from testflo.test import Test
    from testflo.cover import save_coverage
    from testflo.qman import get_client_manager
    from testflo.util import get_addr_auth_from_args, to_bytes

    address, authkey = get_addr_auth_from_args(sys.argv[2:])

    manager = get_client_manager(address, authkey)

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

    manager.get_queue().put(test)
