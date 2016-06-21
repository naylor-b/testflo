import os
import pickle
import multiprocessing
from multiprocessing import managers
import socket


# pickling the queue proxy gets rid of the authkey, so use a fixed authkey here
# for server and clients
_testflo_authkey = b'foobarxxxx'

def get_server_queue():
    manager = managers.SyncManager(address=(socket.gethostname(), 0), authkey=_testflo_authkey)
    manager.start()
    return manager.Queue()

def get_client_queue():
    qstr = os.environ.get('TESTFLO_QUEUE')

    if qstr:
        multiprocessing.current_process().authkey = _testflo_authkey
        queue = pickle.loads(qstr.encode('latin1'))
    else:
        queue = None

    return queue
