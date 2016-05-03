
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

class QueueManager(SyncManager):
    pass

class _DictHandler(object):
    def __init__(self):
        self.dct = {}

    def get_item(self, name):
        return self.dct[name]

    def set_item(self, name, obj):
        self.dct[name] = obj

    def remove_item(self, name):
        del self.dct[name]


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

def get_client_manager(port, authkey):
    QueueManager.register('get_queue')
    QueueManager.register('run_test')
    QueueManager.register('dict_handler')
    manager = QueueManager(address=('', port), authkey=bytes(authkey))
    manager.connect()
    return manager

if __name__ == '__main__':

    port = int(sys.argv[1])
    authkey = b'foo'

    queue = Queue()
    _dict_handler = _DictHandler()

    QueueManager.register('get_queue', callable=lambda:queue)
    QueueManager.register('dict_handler', callable=lambda:_dict_handler)
    QueueManager.register('run_test', run_isolated)

    manager = QueueManager(address=('', port), authkey=bytes(authkey))
    server = manager.get_server()
    server.serve_forever()
