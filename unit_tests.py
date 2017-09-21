import unittest
import ibmarketdata as ib


class Tester(object):
    def __init__(self):
        self.count = 0

    @ib.Utils.reliable
    def RemoteCall(self):
        self.count += 1
        if self.count < 3:
            return None
        return [1, 2, 3]


class TestUtils(unittest.TestCase):

    def setUp(self):
        self.symbols = {1: 'A', 2: 'B', 3: 'C'}

    def test_dict(self):
        items = [value for key, value in self.symbols.items() if value == 'A']
        for i in items:
            self.assertEqual(i, 'A')

        del self.symbols[1]
        keys = [key for key in self.symbols]
        self.assertEqual(keys, [2, 3])

        for k, v in self.symbols.items():
            self.assertTrue(v in ['B', 'C'])

    def test_reliable(self):
        t = Tester()
        res = t.RemoteCall()
        self.assertEqual(res, [1, 2, 3])

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
