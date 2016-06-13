
import sys
import os
import cPickle as pickle
import multiprocessing
from multiprocessing import managers

from testflo.test import Test


# pickling the queue proxy gets rid of the authkey, so use a fixed authkey here
# for server and clients
_testflo_authkey = 'fooooo'

def get_server_queue():
    manager = managers.SyncManager(authkey=_testflo_authkey)
    manager.start()
    return manager.Queue()

def get_client_queue():
    qstr = os.environ.get('TESTFLO_QUEUE')

    if qstr:
        multiprocessing.current_process().authkey = _testflo_authkey
        queue = pickle.loads(qstr)
    else:
        queue = None

    return queue
