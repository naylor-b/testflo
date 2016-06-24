
import sys
import os
import pickle
import multiprocessing
import socket
from multiprocessing.managers import SyncManager, RebuildProxy, AutoProxy, Token

from testflo.test import Test


# pickling the queue proxy gets rid of the authkey, so use a fixed authkey here
# for server and clients
_testflo_authkey = b'foobarxxxx'

def get_server_queue():
    manager = SyncManager(address=(socket.gethostname(), 0),
                          authkey=_testflo_authkey)
    manager.start()
    q = manager.Queue()
    return manager, q

def get_client_queue():
    qstr = os.environ.get('TESTFLO_QUEUE')

    if qstr:
        addr0, addr1, tid = qstr.split(':')
        tok = Token('Queue', (addr0, int(addr1)), tid)
        #multiprocessing.current_process().authkey = _testflo_authkey
        queue = RebuildProxy(AutoProxy, tok, 'pickle',
                             {'authkey':_testflo_authkey})
    else:
        queue = None

    return queue


# RebuildProxy(func, token, serializer, kwds)
# AutoProxy(token, serializer, manager=None, authkey=None,
#               exposed=None, incref=True)
