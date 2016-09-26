
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
    def test_expected_fail_bad(self):
        pass

    @unittest.skip("skipping 1")
    def test_skip(self):
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
