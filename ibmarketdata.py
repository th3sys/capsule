import ibapi.wrapper
from ibapi.client import EClient
from ibapi.common import *
from ibapi.contract import *
from ibapi.ticktype import TickType, TickTypeEnum
from ibapi.utils import *
import datetime


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

    def start(self):
        contract1 = Contract()
        contract1.symbol = "VIX"
        contract1.secType = "IND"
        contract1.exchange = "CBOE"

        self.requestedContracts.append(contract1)
        self.reqContractDetails(self.nextReqId(), contract1)

        contract = Contract()
        contract.symbol = "VX"
        contract.secType = "FUT"
        contract.exchange = "CFE"
        contract.tradingClass = "VX"

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
        super().contractDetails(reqId, contractDetails)
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
            else:
                self.Logger.warning('contractDetails.marketName: %s unknown' % contractDetails.marketName)

    @iswrapper
    def contractDetailsEnd(self, reqId: int):
        super().contractDetailsEnd(reqId)
        self.Logger.info("ContractDetailsEnd. %s" % reqId)
        for contract, details, valid in self.validatedContracts:
            if valid:
                cId = self.nextOrderId()
                self.contractLookup[cId] = contract.localSymbol
                self.reqMktData(cId, contract, "", True, False, [])
        del self.validatedContracts[:]

    @iswrapper
    def tickSnapshotEnd(self, reqId: int):
        super().tickSnapshotEnd(reqId)
        self.Logger.info("TickSnapshotEnd: %s", reqId)

    @iswrapper
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        self.Logger.info("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
        self.nextValidReqId = orderId
        self.start()

    @iswrapper
    def marketDataType(self, reqId: TickerId, marketDataType: int):
        super().marketDataType(reqId, marketDataType)
        self.Logger.info("MarketDataType. %s Type: %s" % (reqId, marketDataType))

    @iswrapper
    def error(self, *args):
        super().error(*args)
        self.Logger.error('error received. ReqId: %s' % args[0])

    @iswrapper
    def winError(self, *args):
        super().error(*args)

    @iswrapper
    def currentTime(self, tim: int):
        super().currentTime(tim)
        self.Logger.info('currentTime: %s' % tim)

    @iswrapper
    def tickPrice(self, tickerId: TickerId, tickType: TickType, price: float, attrib):
        super().tickPrice(tickerId, tickType, price, attrib)
        symbol = self.contractLookup[tickerId]
        self.Logger.info('%s %s %s %s IB' % (datetime.datetime.now(), symbol, TickTypeEnum.to_str(tickType), price))

    @iswrapper
    def tickSize(self, tickerId: TickerId, tickType: TickType, size: int):
        super().tickSize(tickerId, tickType, size)
        symbol = self.contractLookup[tickerId]
        self.Logger.info('%s %s %s %s IB' % (datetime.datetime.now(), symbol, TickTypeEnum.to_str(tickType), size))


def main():
    app = IbApp()
    app.connect("127.0.0.1", 7496, 0)
    app.Logger.info("serverVersion:%s connectionTime:%s" % (app.serverVersion(), app.twsConnectionTime()))

    app.run()


if __name__ == "__main__":
    main()
