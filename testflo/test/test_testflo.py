
import os

import unittest

class TestfloTestCase(unittest.TestCase):
    def test_ok(self):
        pass

    def test_fail(self):
        self.fail("failure 1")

    @unittest.expectedFailure
    def test_expected_fail_good(self):
        self.fail("I expected this")

    @unittest.expectedFailure
    def test_unexpected_success(self):
        pass

    @unittest.skip("skipping 1")
    def test_skip(self):
        pass

class TestfloTestCaseWFixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pid = os.getpid()
        print("setting up %s, pid=%d" % (cls.__name__, cls.pid))

    @classmethod
    def tearDownClass(cls):
        assert os.getpid() == cls.pid
        print("tearing down %s, pid=%d" % (cls.__name__, cls.pid))

    def test_tcase_grouped_ok(self):
        assert os.getpid() == self.pid

    def test_tcase_grouped_fail(self):
        self.fail("failure 2")

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
class SkippedTestCase(unittest.TestCase):
    def test_1(self):
        pass

    def test_2(self):
        pass

    def test_3(self):
        pass

    def test_4(self):
        pass
