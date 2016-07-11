import os
import sys
import multiprocessing

import socket
from multiprocessing.managers import SyncManager, RebuildProxy, AutoProxy, Token


# pickling the queue proxy gets rid of the authkey, so use a fixed authkey here
# for server and clients
_testflo_authkey = b'foobarxxxx'

def get_server_queue():
    if sys.platform == 'darwin':
        addr = 'localhost'
    else:
        addr = socket.gethostname()

    manager = SyncManager(address=(addr, 0), authkey=_testflo_authkey)
    manager.start()
    return manager, manager.Queue()

def get_client_queue():
    qstr = os.environ.get('TESTFLO_QUEUE')

    if qstr:
        # if TESTFLO_QUEUE is set, use that info to create a proxy that
        # points to the shared Queue.
        addr0, addr1, token_id = qstr.split(':')
        tok = Token('Queue', (addr0, int(addr1)), token_id)
        queue = RebuildProxy(AutoProxy, tok, 'pickle',
                             {'authkey':_testflo_authkey})
    else:
        queue = None

    return queue
