import unittest

# TODO: add some self-contained tests


class TestFloTestCase(unittest.TestCase):

    def test_upper(self):
        # just a dummy test for testing testflo itself
        self.assertEqual('foo'.upper(), 'FOO')


if __name__ == '__main__':
    unittest.main()
