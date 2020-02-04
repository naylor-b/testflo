import os
import sys

import socket


# pickling the queue proxy gets rid of the authkey, so use a fixed authkey here
# for server and clients
_testflo_authkey = b'foobarxxxx'

def get_server_queue():
    from multiprocessing.managers import SyncManager
    #FIXME: some OSX users were getting "Can't assign requested address" errors
    # if we use socket.gethostname() for the address. Changing it to
    # 'localhost' seems to fix the issue, but I don't know why. We had to
    # use socket.gethostname() in order to get our benchmark tests to run
    # using qsub on a linux cluster, so with this 'fix', testflo benchmark tests
    # will likely not work on a cluster of OSX machines.
    if sys.platform == 'darwin':
        addr = 'localhost'
    else:
        addr = socket.gethostname()

    manager = SyncManager(address=(addr, 0), authkey=_testflo_authkey)
    manager.start()
    return manager, manager.Queue()

def get_client_queue():
    from multiprocessing.managers import RebuildProxy, AutoProxy, Token
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
