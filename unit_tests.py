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
        pass

    def test_reliable(self):
        t = Tester()
        res = t.RemoteCall()
        self.assertEqual(res, [1, 2, 3])

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
