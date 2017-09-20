import ibapi.wrapper
from ibapi.client import EClient
from ibapi.common import *
from ibapi.contract import *
from ibapi.ticktype import TickType, TickTypeEnum
from ibapi.utils import *
import datetime
import json
import decimal
import boto3
import time
from botocore.exceptions import ClientError


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


class IbApp(EClient, ibapi.wrapper.EWrapper):
    def __init__(self):
        self.Logger = logging.getLogger()
        self.Logger.setLevel(logging.INFO)
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
        EClient.__init__(self, self)
        self.nextValidOrderId = None
        self.nextValidReqId = None
        self.requestedContracts = []
        self.validatedContracts = []
        self.contractLookup = {}
        db = boto3.resource('dynamodb', region_name='us-east-1')
        self.__Securities = db.Table('Securities')

    @Utils.reliable
    def getSecurities(self):
        try:
            self.Logger.info('Calling securities scan ...')
            response = self.__Securities.scan()
        except ClientError as e:
            self.Logger.error(e.response['Error']['Message'])
            return None
        except Exception as e:
            self.Logger.error(e)
            return None
        else:
            # self.Logger.info(json.dumps(security, indent=4, cls=DecimalEncoder))
            if 'Items' in response:
                return response['Items']

    def start(self):
        items = self.getSecurities()

        for sec in items:
            if sec['SubscriptionEnabled']:
                contract = Contract()
                contract.symbol = sec['Symbol']
                contract.secType = sec['ProductType']
                contract.exchange = sec['Description']['Exchange']
                if contract.secType == 'FUT':
                    contract.tradingClass = sec['Symbol']
                self.requestedContracts.append(contract)
                self.reqContractDetails(self.nextReqId(), contract)

    def nextReqId(self):
        reqId = self.nextValidReqId
        self.nextValidReqId += 1
        return reqId

    def nextOrderId(self):
        orderId = self.nextValidOrderId
        self.nextValidOrderId += 1
        return orderId

    @iswrapper
    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super(IbApp, self).contractDetails(reqId, contractDetails)
        self.Logger.info(contractDetails.summary)
        for contract in self.requestedContracts:
            if contract.symbol == contractDetails.summary.symbol or contract.symbol == contractDetails.marketName:
                validated = Contract()
                validated.symbol = contractDetails.summary.symbol
                validated.secType = contractDetails.summary.secType
                validated.exchange = contractDetails.summary.exchange
                validated.tradingClass = contractDetails.summary.tradingClass
                validated.lastTradeDateOrContractMonth = contractDetails.summary.lastTradeDateOrContractMonth
                validated.localSymbol = contractDetails.summary.localSymbol
                self.validatedContracts.append((validated, contractDetails, True))

    @iswrapper
    def contractDetailsEnd(self, reqId: int):
        super(IbApp, self).contractDetailsEnd(reqId)
        self.Logger.info("ContractDetailsEnd. %s" % reqId)
        for contract, details, valid in self.validatedContracts:
            if valid:
                cId = self.nextOrderId()
                self.contractLookup[cId] = contract.localSymbol
                # self.reqMktData(cId, contract, "", True, False, [])
                self.reqHistoricalData(cId, contract, '', "2 Y", "1 day", "TRADES", 1, 1, [])
        del self.validatedContracts[:]

    @iswrapper
    def historicalData(self, reqId: TickerId, date: str, opn: float, high: float,
                       low: float, close: float, volume: int, barCount: int, WAP: float, hasGaps: int):
        self.Logger.info("HistoricalData. " + str(reqId) + " Date: " + date + " Open: " + str(opn) +
                         " High: " + str(high) + " Low: " + str(low) + " Close: " + str(close) + " Volume: "
                         + str(volume) + " Count: " + str(barCount) + " WAP: " + str(WAP))

    @iswrapper
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super(IbApp, self).historicalDataEnd(reqId, start, end)
        self.Logger.info("HistoricalDataEnd " + str(reqId) + "from" + start + "to" + end)

    @iswrapper
    def tickSnapshotEnd(self, reqId: int):
        super(IbApp, self).tickSnapshotEnd(reqId)
        self.Logger.info("TickSnapshotEnd: %s", reqId)

    @iswrapper
    def nextValidId(self, orderId: int):
        super(IbApp, self).nextValidId(orderId)

        self.Logger.info("setting nextValidOrderId: %d", orderId)
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
        self.Logger.error('error received. ReqId: %s' % args[0])

    @iswrapper
    def winError(self, *args):
        super(IbApp, self).error(*args)

    @iswrapper
    def currentTime(self, tim: int):
        super(IbApp, self).currentTime(tim)
        self.Logger.info('currentTime: %s' % tim)

    @iswrapper
    def tickPrice(self, tickerId: TickerId, tickType: TickType, price: float, attrib):
        super(IbApp, self).tickPrice(tickerId, tickType, price, attrib)
        symbol = self.contractLookup[tickerId]
        self.Logger.info('%s %s %s %s IB' % (datetime.datetime.now(), symbol, TickTypeEnum.to_str(tickType), price))

    @iswrapper
    def tickSize(self, tickerId: TickerId, tickType: TickType, size: int):
        super(IbApp, self).tickSize(tickerId, tickType, size)
        symbol = self.contractLookup[tickerId]
        self.Logger.info('%s %s %s %s IB' % (datetime.datetime.now(), symbol, TickTypeEnum.to_str(tickType), size))


def main():
    app = IbApp()
    app.connect("127.0.0.1", 7496, 0)
    app.Logger.info("serverVersion:%s connectionTime:%s" % (app.serverVersion(), app.twsConnectionTime()))

    app.run()


if __name__ == "__main__":
    main()
