
"""
This runs a multiprocessing manager in a separate process given an command
line arg indicating the port.  This is an attempt to avoid some of the
non-forking nonsense that comes with using multiprocessing on Windows.

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


def _run_single_test(test, q):
    test.run()
    q.put(test)

def run_isolated(test, q):
    """This runs the test in a subprocess,
    then puts the Test object on the queue.
    """
    p = Process(target=_run_single_test, args=(test, q))
    p.start()
    t = q.get()
    p.join()
    q.put(t)

def get_client_manager(addr, authkey):
    QueueManager.register('get_queue')
    QueueManager.register('run_test')
    manager = QueueManager(address=addr, authkey=bytes(authkey))
    manager.connect()
    return manager

if __name__ == '__main__':

    queue = Queue()

    QueueManager.register('get_queue', callable=lambda:queue)
    QueueManager.register('run_test', run_isolated)

    address, authkey = get_addr_auth_from_args(sys.argv[1:])

    manager = QueueManager(address=address, authkey=authkey)
    server = manager.get_server()
    server.serve_forever()
