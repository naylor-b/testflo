
import os

import unittest

modpid = None

def setUpModule():
    global modpid
    modpid = os.getpid()
    print("\ncalled setUpModule from pid %d\n" % modpid)

def tearDownModule():
    global modpid
    mypid = os.getpid()
    assert mypid == modpid
    print("\ncalled tearDownModule from pid %d\n" % mypid)


class TestfloTestCaseWFixture2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pid = os.getpid()
        print("\nsetting up %s, pid=%d\n" % (cls.__name__, cls.pid))

    @classmethod
    def tearDownClass(cls):
        assert os.getpid() == cls.pid
        print("\ntearing down %s, pid=%d\n" % (cls.__name__, cls.pid))

    def test_tcase_grouped_ok(self):
        assert os.getpid() == self.pid

    def test_tcase_grouped_fail(self):
        self.fail("failure 3")

    @unittest.expectedFailure
    def test_tcase_grouped_expected_fail(self):
        self.fail("I expected this")

    @unittest.expectedFailure
    def test_tcase_grouped_unexpected_success(self):
        pass

    @unittest.skip("skipping 2")
    def test_tcase_grouped_skip(self):
        pass


@unittest.skip("skipping a whole testcase...")
class SkippedTestCase2(unittest.TestCase):
    def test_1(self):
        pass

    def test_2(self):
        pass

    def test_3(self):
        pass

    def test_4(self):
        pass
