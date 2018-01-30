import logging
import datetime
from dateutil.relativedelta import relativedelta


class Futures:
    VX = 'VX'


class SecurityDefinition(object):
    def __init__(self):
        self.Logger = logging.getLogger()
        self.Logger.setLevel(logging.INFO)
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
        self.Logger.info('Security Created.')
        self.__M = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M", 7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
        self.__Supported = {'VX': 'VX'}  # symbols and future prefix

    # lifted from https://github.com/conor10/examples/blob/master/python/expiries/vix.py
    @staticmethod
    def __get_vix_expiry_date(date):
        """
        http://cfe.cboe.com/products/spec_vix.aspx

        TERMINATION OF TRADING:

        Trading hours for expiring VIX futures contracts end at 7:00 a.m. Chicago
        time on the final settlement date.

        FINAL SETTLEMENT DATE:

        The Wednesday that is thirty days prior to the third Friday of the
        calendar month immediately following the month in which the contract
        expires ("Final Settlement Date"). If the third Friday of the month
        subsequent to expiration of the applicable VIX futures contract is a
        CBOE holiday, the Final Settlement Date for the contract shall be thirty
        days prior to the CBOE business day immediately preceding that Friday.
        """
        # Date of third friday of the following month
        if date.month == 12:
            third_friday_next_month = datetime.date(date.year + 1, 1, 15)
        else:
            third_friday_next_month = datetime.date(date.year,
                                                    date.month + 1, 15)

        one_day = datetime.timedelta(days=1)
        thirty_days = datetime.timedelta(days=30)
        while third_friday_next_month.weekday() != 4:
            # Using += results in a timedelta object
            third_friday_next_month = third_friday_next_month + one_day

        # TODO: Incorporate check that it's a trading day, if so move the 3rd
        # Friday back by one day before subtracting
        return third_friday_next_month - thirty_days

    def __get_vix(self, date):
        return "%s%s%s" % (self.__Supported[Futures.VX], self.__M[date.month], str(date.year)[-1:])

    def get_next_expiry_date(self, symbol, today):
        try:
            if symbol not in self.__Supported:
                raise Exception('Symbol %s not supported' % symbol)
            # TODO: add support for more contracts
            if symbol == Futures.VX:
                return self.__get_vix_expiry_date(today)

        except Exception as e:
            self.Logger.error(e)
            return None

    def get_next_expiry(self, symbol, today):
        try:
            if symbol not in self.__Supported:
                raise Exception('Symbol %s not supported' % symbol)
            # TODO: add support for more contracts
            if symbol == Futures.VX:
                expiry = self.__get_vix_expiry_date(today)
                return self.__get_vix(today if today < expiry else today + relativedelta(months=+1))

        except Exception as e:
            self.Logger.error(e)
            return None

    def get_front_month_future(self, symbol):
        today = datetime.datetime.today().date()
        return self.get_next_expiry(symbol, today)

    def get_futures(self, symbol, n, date=None):
        try:
            if n < 2:
                raise Exception('Just use get_front_month_future if n < 2')
            if symbol not in self.__Supported:
                raise Exception('Symbol %s not supported' % symbol)
            today = datetime.datetime.today().date() if date is None else date
            futures = []
            front = self.get_next_expiry(symbol, today)
            futures.append(front)
            # TODO: add support for more contracts
            if symbol == Futures.VX:
                expiry = self.__get_vix_expiry_date(today)
            else:
                expiry = today
            roll = 1 if today < expiry else 2
            nextMonth = datetime.date(today.year, today.month, 1) + relativedelta(months=+roll)
            for i in range(1, n):
                future = self.get_next_expiry(symbol, nextMonth)
                futures.append(future)
                nextMonth += relativedelta(months=+1)
            return futures

        except Exception as e:
            self.Logger.error(e)
            return None
