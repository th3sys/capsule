import argparse
import datetime
from dateutil.relativedelta import relativedelta
import decimal
import json
import queue
import time

import boto3
from botocore.exceptions import ClientError
from contracts import SecurityDefinition

import ibapi.wrapper
from ibapi import (comm)
from ibapi.client import EClient
from ibapi.common import *
from ibapi.contract import Contract
from ibapi.errors import *
from ibapi.ticktype import TickType, TickTypeEnum
from ibapi.utils import *
from ibapi.utils import (BadMessage)


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


class Utils(object):
    def __init__(self):
        pass

    @staticmethod
    def reliable(func):
        def _decorator(self, *args, **kwargs):
            tries = 0
            result = func(self, *args, **kwargs)
            if result is None:
                while result is None and tries < 10:
                    tries += 1
                    time.sleep(2 ** tries)
                    result = func(self, *args, **kwargs)
            return result

        return _decorator


class InterruptableClient(EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.lastStamp = datetime.datetime.utcnow()

    def runnable(self, func):
        """This is the function that has the message loop."""

        try:
            while not self.done and (self.conn.isConnected()
                                     or not self.msg_queue.empty()):
                try:
                    try:
                        text = self.msg_queue.get(block=True, timeout=0.2)
                        if len(text) > MAX_MSG_LEN:
                            self.wrapper.error(NO_VALID_ID, BAD_LENGTH.code(),
                                               "%s:%d:%s" % (BAD_LENGTH.msg(), len(text), text))
                            self.disconnect()
                            break
                    except queue.Empty:
                        if datetime.datetime.utcnow() - self.lastStamp > datetime.timedelta(seconds=30):
                            func()
                            self.lastStamp = datetime.datetime.utcnow()
                        logging.debug("queue.get: empty")
                    else:
                        fields = comm.read_fields(text)
                        logging.debug("fields %s", fields)
                        self.decoder.interpret(fields)
                except (KeyboardInterrupt, SystemExit):
                    logging.info("detected KeyboardInterrupt, SystemExit")
                    self.keyboardInterrupt()
                    self.keyboardInterruptHard()
                except BadMessage:
                    logging.info("BadMessage")
                    self.conn.disconnect()

                logging.debug("conn:%d queue.sz:%d",
                              self.conn.isConnected(),
                              self.msg_queue.qsize())
        finally:
            self.disconnect()


class IbApp(InterruptableClient, ibapi.wrapper.EWrapper):
    def __init__(self, start, end):
        self.__start = start.date()
        self.__end = end.date()
        self.months = int((end.date() - start.date()).days / 30)

        self.Logger = logging.getLogger()
        self.Logger.setLevel(logging.INFO)
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
        InterruptableClient.__init__(self)
        self.nextValidOrderId = None
        self.nextValidReqId = None
        self.requestedHistoricalData = {}
        self.historicalLookup = {}
        self.sec = SecurityDefinition()
        db = boto3.resource('dynamodb', region_name='us-east-1')
        self.__Securities = db.Table('Securities')
        self.__QuotesEod = db.Table('Quotes.EOD.UAT')

    def __del__(self):
        self.disconnect()

    def UpdateQuote(self, symbol, date, opn, close, high, low, volume, barCount):
        try:
            details = {"Open": decimal.Decimal(str(opn)), "Close": decimal.Decimal(str(close)),
                       "High": decimal.Decimal(str(high)), "Low": decimal.Decimal(str(low)),
                       "Volume": volume, "Count": barCount}
            response = self.__QuotesEod.update_item(
                Key={
                    'Symbol': symbol,
                    'Date': date,
                },
                UpdateExpression="set #d = :d, #s = :s",
                ExpressionAttributeNames={
                    '#d': 'Details',
                    '#s': 'Source',
                },
                ExpressionAttributeValues={
                    ':d': details,
                    ':s': 'IB',
                },
                ReturnValues="UPDATED_NEW")

        except ClientError as e:
            self.Logger.error(e.response['Error']['Message'])
        except Exception as e:
            self.Logger.error(e)
        else:
            self.Logger.debug(json.dumps(response, indent=4, cls=DecimalEncoder))

    def verify(self):
        self.Logger.info('requesting server time')
        self.reqCurrentTime()

        for key, value in self.requestedHistoricalData.items():
            if value.lastTradeDateOrContractMonth != '':
                expiry = datetime.datetime.strptime(value.lastTradeDateOrContractMonth, '%Y%m%d')
                end = expiry.strftime('%Y%m%d %H:%M:%S')
                duration = "30 D"
            else:
                end = self.__end.strftime('%Y%m%d %H:%M:%S')
                duration = "%s M" % self.months

            self.reqHistoricalData(key, value, end, duration, "1 day", "TRADES", 1, 1, False, list("XYZ"))
            self.Logger.info('re-requesting Historical Data for ReqId: %s' % key)

    def loop(self):
        self.runnable(self.verify)

    def GetContract(self, date):
        symbol = self.sec.get_next_expiry('VX', date)
        exp = self.sec.get_next_expiry_date('VX', date)
        contract = ('VIX', 'FUT', 'CFE', 'VX', exp.strftime('%Y%m%d'), symbol)
        return contract

    def start(self):

        # items = [('VIX', 'FUT', 'CFE', 'VX', '20171220', 'VXZ7')]
        items = [('VIX', 'IND', 'CBOE', '', '', 'VIX')]
        # items = [('VIX', 'FUT', 'CFE', 'VX', '20180214', 'VXG8')]
        # items = []
        nxt = self.__start
        while nxt <= self.__end:
            contract = self.GetContract(nxt)
            items.append(contract)
            nxt = nxt + relativedelta(months=1)

        for sym, typ, exch, tc, exp, loc in items:

            validated = Contract()
            validated.symbol = sym
            validated.secType = typ
            validated.exchange = exch
            validated.tradingClass = tc
            validated.lastTradeDateOrContractMonth = exp
            validated.includeExpired = True
            validated.localSymbol = loc

            hId = self.nextReqId()
            self.historicalLookup[hId] = validated.localSymbol
            self.requestedHistoricalData[hId] = validated
            if exp != '':
                expiry = datetime.datetime.strptime(exp, '%Y%m%d')
                end = expiry.strftime('%Y%m%d %H:%M:%S')
                duration = "30 D"
            else:
                end = self.__end.strftime('%Y%m%d %H:%M:%S')
                duration = "%s M" % self.months
            self.Logger.info('ReqId: %s. Requesting Historical %s %s %s %s %s %s' % (hId, sym, typ, exch, tc, exp, loc))
            self.reqHistoricalData(hId, validated, end, duration, "1 day", "TRADES", 1, 1, False, list("XYZ"))

    def nextReqId(self):
        reqId = self.nextValidReqId
        self.nextValidReqId += 1
        return reqId

    def nextOrderId(self):
        orderId = self.nextValidOrderId
        self.nextValidOrderId += 1
        return orderId

    @iswrapper
    def historicalData(self, reqId: TickerId, bar: BarData):
        sym = self.historicalLookup[reqId]

        self.Logger.info("ReqId: " + str(reqId) + " HistoricalData. " + sym + " Date: " + bar.date + " Open: "
                         + str(bar.open) + " High: " + str(bar.high) + " Low: " + str(bar.low) + " Close: "
                         + str(bar.close) + " Volume: " + str(bar.volume) + " Count: " + str(bar.barCount))
        if reqId in self.requestedHistoricalData:
            del self.requestedHistoricalData[reqId]

        self.UpdateQuote(sym, bar.date, bar.open, bar.close, bar.high, bar.low, bar.volume, bar.barCount)

    @iswrapper
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super(IbApp, self).historicalDataEnd(reqId, start, end)
        self.Logger.info("HistoricalDataEnd " + str(reqId) + " from " + start + " to " + end)

    @iswrapper
    def tickSnapshotEnd(self, reqId: int):
        super(IbApp, self).tickSnapshotEnd(reqId)
        self.Logger.info("TickSnapshotEnd: %s" % reqId)

    @iswrapper
    def nextValidId(self, orderId: int):
        super(IbApp, self).nextValidId(orderId)

        self.Logger.info("setting nextValidOrderId: %d" % orderId)
        self.nextValidOrderId = orderId
        self.nextValidReqId = orderId
        self.start()

    @iswrapper
    def marketDataType(self, reqId: TickerId, marketDataType: int):
        super(IbApp, self).marketDataType(reqId, marketDataType)
        self.Logger.info("MarketDataType. %s Type: %s" % (reqId, marketDataType))

    @iswrapper
    def error(self, *args):
        super(IbApp, self).error(*args)

    @iswrapper
    def winError(self, *args):
        super(IbApp, self).error(*args)

    @iswrapper
    def currentTime(self, tim: int):
        super(IbApp, self).currentTime(tim)
        self.Logger.info('currentTime: %s' % tim)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='IB host', required=True)
    parser.add_argument('--port', help='IB port', type=int, required=True)
    parser.add_argument('--clientId', help='IB client id', type=int, required=True)
    parser.add_argument('--start', help='Start', type=lambda x: datetime.datetime.strptime(x, '%Y%m%d'), required=True)
    parser.add_argument('--end', help='End', type=lambda x: datetime.datetime.strptime(x, '%Y%m%d'), required=True)
    args = parser.parse_args()

    app = IbApp(args.start, args.end)
    app.connect(args.host, args.port, args.clientId)
    app.Logger.info("serverVersion:%s connectionTime:%s" % (app.serverVersion(), app.twsConnectionTime()))

    app.loop()


if __name__ == "__main__":
    main()
