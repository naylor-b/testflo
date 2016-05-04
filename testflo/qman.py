
"""
This runs a multiprocessing manager in a separate process given command
line args indicating the adress and authkey.  This is an attempt to avoid
some of the non-forking nonsense that comes with using multiprocessing on
Windows. This process does nothing except maintain a shared queue that
subprocesses can use to report test results.

"""

import sys
import os
import traceback

from multiprocessing.managers import SyncManager
from multiprocessing import Queue

from testflo.test import Test
from testflo.util import get_addr_auth_from_args

class QueueManager(SyncManager):
    pass

def get_client_manager(addr, authkey):
    QueueManager.register('get_queue')
    manager = QueueManager(address=addr, authkey=bytes(authkey))
    manager.connect()
    return manager

if __name__ == '__main__':

    queue = Queue()

    QueueManager.register('get_queue', callable=lambda:queue)

    address, authkey = get_addr_auth_from_args(sys.argv[1:])

    manager = QueueManager(address=address, authkey=authkey)
    server = manager.get_server()
    server.serve_forever()
