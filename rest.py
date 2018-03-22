import json
import aiohttp
import asyncio
import copy
import async_timeout

class Side:
    Buy = 'BUY'
    Sell = 'SELL'


class OrderType:
    Market = 'MARKET'
    Limit = 'LIMIT'


class IGParams(object):
    def __init__(self):
        self.Url = ''
        self.Key = ''
        self.Identifier = ''
        self.Password = ''


class Order(object):
    def __init__(self, epic, side, money, ordType, maturity, stop=None):
        self.Side = side
        self.Size = float(money.Amount)
        self.OrdType = ordType
        # self.Maturity = datetime.strptime(maturity, '%Y%m').strftime('%b-%y').upper()
        self.Maturity = maturity
        self.Epic = epic
        self.Ccy = money.Ccy
        self.StopDistance = stop


class Money(object):
    def __init__(self, amount, ccy):
        self.Ccy = ccy
        self.Amount = amount


class IGClient:
    """IG client."""

    def __init__(self, params, log, loop=None):
        self.__timeout = 10
        self.__logger = log
        self.__id = params.Identifier
        self.__password = params.Password
        self.__url = params.Url
        self.__key = params.Key
        self.__tokens = None
        self.__loop = loop if loop is not None else asyncio.get_event_loop()

    async def Logout(self):
        try:
            url = '%s/%s' % (self.__url, 'session')
            with async_timeout.timeout(self.__timeout):
                self.__logger.info('Calling Logout ...')
                response = await self.__connection.delete(url=url, headers=self.__tokens)
                self.__logger.info('Logout Response Code: {}'.format(response.status))
                return True
        except Exception as e:
            self.__logger.error('Logout: %s, %s' % (self.__url, e))
            return False

    async def Login(self):
        try:
            url = '%s/%s' % (self.__url, 'session')
            with async_timeout.timeout(self.__timeout):
                authenticationRequest = {
                    'identifier': self.__id,
                    'password': self.__password,
                    'encryptedPassword': None
                }
                self.__logger.info('Calling authenticationRequest ...')
                response = await self.__connection.post(url=url, json=authenticationRequest, headers={'Version': '2'})
                self.__logger.info('Login Response Code: {}'.format(response.status))
                self.__logger.info('Headers: {}'.format(response.headers))
                security = response.headers['X-SECURITY-TOKEN'] if 'X-SECURITY-TOKEN' \
                                                                   in response.headers else None
                cst = response.headers['CST'] if 'CST' in response.headers else None
                self.__tokens = {'X-SECURITY-TOKEN': security, 'CST': cst}
                payload = await response.json()
                return payload
        except Exception as e:
            self.__logger.error('Login: %s, %s' % (self.__url, e))
            return None

    async def CreatePosition(self, order):
        try:
            url = '%s/%s' % (self.__url, 'positions/otc')
            with async_timeout.timeout(self.__timeout):
                request = {
                    "currencyCode": order.Ccy,
                    "direction": order.Side,
                    "epic": order.Epic,
                    "expiry": order.Maturity,
                    "forceOpen": False if order.StopDistance is None else True,
                    "guaranteedStop": False if order.StopDistance is None else True,
                    "level": None,
                    "limitDistance": None,
                    "limitLevel": None,
                    "orderType": order.OrdType,
                    "quoteId": None,
                    "size": order.Size,
                    "stopDistance": order.StopDistance,
                    "stopLevel": None,
                    "timeInForce": "FILL_OR_KILL",
                    "trailingStop": None,
                    "trailingStopIncrement": None,
                }
                self.__logger.info('Calling CreatePosition ...')
                tokens = copy.deepcopy(self.__tokens)
                tokens['Version'] = "2"
                response = await self.__connection.post(url=url, headers=tokens, json=request)
                self.__logger.info('CreatePosition Response Code: {}'.format(response.status))
                payload = await response.json()
                return payload
        except Exception as e:
            self.__logger.error('CreatePosition: %s, %s' % (self.__url, e))
            return None

    async def GetPositions(self):
        try:
            url = '%s/positions' % self.__url
            with async_timeout.timeout(self.__timeout):
                self.__logger.info('Calling GetPositions ...')
                tokens = copy.deepcopy(self.__tokens)
                tokens['Version'] = "2"
                response = await self.__connection.get(url=url, headers=tokens)
                self.__logger.info('GetPositions Response Code: {}'.format(response.status))
                payload = await response.json()
                return payload
        except Exception as e:
            self.__logger.error('GetPositions: %s, %s' % (self.__url, e))
            return None

    async def GetActivities(self, fromDate, details=False):
        try:
            url = '%s/history/activity?from=%s&detailed=%s' % (self.__url, fromDate, details)
            with async_timeout.timeout(self.__timeout):
                self.__logger.info('Calling GetActivities ...')
                tokens = copy.deepcopy(self.__tokens)
                tokens['Version'] = "3"
                response = await self.__connection.get(url=url, headers=tokens)
                self.__logger.info('GetActivities Response Code: {}'.format(response.status))
                payload = await response.json()
                return payload
        except Exception as e:
            self.__logger.error('GetActivities: %s, %s' % (self.__url, e))
            return None

    async def GetPosition(self, dealId):
        try:
            url = '%s/positions/%s' % (self.__url, dealId)
            with async_timeout.timeout(self.__timeout):
                self.__logger.info('Calling GetPosition ...')
                response = await self.__connection.get(url=url, headers=self.__tokens)
                self.__logger.info('GetPosition Response Code: {}'.format(response.status))
                payload = await response.json()
                return payload
        except Exception as e:
            self.__logger.error('GetPosition: %s, %s' % (self.__url, e))
            return None

    async def SearchMarkets(self, term):
        try:
            url = '%s/markets?searchTerm=%s' % (self.__url, term)
            with async_timeout.timeout(self.__timeout):
                self.__logger.info('Calling SearchMarkets ...')
                response = await self.__connection.get(url=url, headers=self.__tokens)
                self.__logger.info('SearchMarkets Response Code: {}'.format(response.status))
                payload = await response.json()
                return payload
        except Exception as e:
            self.__logger.error('SearchMarkets: %s, %s' % (self.__url, e))
            return None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(verify_ssl=False)
        self.__session = aiohttp.ClientSession(loop=self.__loop, connector=connector,
                                               headers={'X-IG-API-KEY': self.__key})
        self.__connection = await self.__session.__aenter__()
        self.__logger.info('Session created')
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.__session.__aexit__(*args, **kwargs)
        self.__logger.info('Session destroyed')
