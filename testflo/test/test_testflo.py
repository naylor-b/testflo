
import os

import unittest

class TestfloTestCase(unittest.TestCase):
    def test_ok(self):
        pass

    def test_env_var(self):
        testflo_running = os.getenv("TESTFLO_RUNNING", default=False)
        self.assertNotEqual(testflo_running, False)

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


class TestSubTests(unittest.TestCase):
    def test_subtests(self):
        # Base price by item
        base_price = {"gum": 1.00, "milk": 2.50, "eggs": 2.75}
        # Sales tax by state
        sales_tax = {"Michigan": 0.06, "Ohio": 0.0575, "New Hampshire": 0.00}

        # Loop through each state and item and precompute expected price
        precalculated_price = {}
        for state in sales_tax:
            precalculated_price[state] = {}
            for item in base_price:
                precalculated_price[state][item] = (1.0 + sales_tax[state]) * base_price[item]

        # Intentionally mess up michigan price for gum and ohio price for eggs
        precalculated_price["Michigan"]["gum"] = 100.0
        precalculated_price["Ohio"]["eggs"] = -3.14159

        # Run through nested subtests, by state and item, and double check that logged price matches expected
        for state in sales_tax:
            with self.subTest(state=state):
                for item in base_price:
                    with self.subTest(item=item):
                        expected_price = (1.0 + sales_tax[state]) * base_price[item]
                        logged_price = precalculated_price[state][item]
                        assert logged_price == expected_price


class TestSubTestsMPI(TestSubTests):
    N_PROCS = 2
