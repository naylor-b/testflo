"""
This is for running a test in a subprocess.
"""

import sys
import os
import traceback
import time
import subprocess
import json

from multiprocessing.managers import BaseManager
from multiprocessing import Process, Queue
#import Queue

from testflo.util import _get_parser
from testflo.runner import TestRunner, exit_codes
from testflo.test import Test
from testflo.cover import save_coverage
from testflo.options import get_options


def run_single_test(test, q):
    test.run()
    q.put(test)

def run_isolated(test, q):
    """This runs the test in a subprocess,
    then puts the Test object on the queue.
    """

    p = Process(target=run_single_test, args=(test, q))
    p.start()
    t = q.get()
    p.join()
    q.put(t)
