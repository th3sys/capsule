import unittest
import ibmarketdata as ib
import contracts as cont
import datetime


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

    def test_vix_expiry(self):
        sec = cont.Security()
        fut = sec.get_next_expiry('VX', datetime.date(2017, 11, 14))
        print(fut)
        self.assertEqual(fut, 'VXX7')
        fut = sec.get_next_expiry('VX', datetime.date(2017, 11, 15))
        print(fut)
        self.assertEqual(fut, 'VXZ7')
        futures = sec.get_futures('VX', 3, datetime.date(2017, 11, 2))
        print(futures)
        self.assertEqual(futures, ['VXX7', 'VXZ7', 'VXF8'])
        futures = sec.get_futures('VX', 2, datetime.date(2017, 11, 2))
        print(futures)
        self.assertEqual(futures, ['VXX7', 'VXZ7'])
        futures = sec.get_futures('VX', 2, datetime.date(2017, 11, 15))
        print(futures)
        self.assertEqual(futures, ['VXZ7', 'VXF8'])
        futures = sec.get_futures('VX', 3, datetime.date(2017, 12, 19))
        print(futures)
        self.assertEqual(futures, ['VXZ7', 'VXF8', 'VXG8'])
        futures = sec.get_futures('VX', 2, datetime.date(2017, 12, 20))
        print(futures)
        self.assertEqual(futures, ['VXF8', 'VXG8'])
        futures = sec.get_futures('VX', 3, datetime.date(2018, 1, 10))
        print(futures)
        self.assertEqual(futures, ['VXF8', 'VXG8', 'VXH8'])

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
