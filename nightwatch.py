import boto3
import logging
import argparse
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
import json
import decimal
import time
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import contracts
from rest import IGParams, IGClient
import asyncio
import uuid


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


class CapsuleParams(object):
    def __init__(self):
        self.Region = ''
        self.Instance = ''
        self.Email = ''
        self.Iam = ''
        self.User = ''
        self.Password = ''
        self.Smtp = ''


class CapsuleController(object):
    def __init__(self, params):
        self.secDef = contracts.SecurityDefinition()
        self.Email = params.Email
        self.Iam = params.Iam
        self.User = params.User
        self.Password = params.Password
        self.Smtp = params.Smtp
        self.Logger = logging.getLogger()
        self.Logger.setLevel(logging.INFO)
        ec2 = boto3.resource('ec2', region_name=params.Region)
        self.__Instance = ec2.Instance(params.Instance)
        db = boto3.resource('dynamodb', region_name=params.Region)
        self.__QuotesEod = db.Table('Quotes.EOD')
        self.__Securities = db.Table('Securities')
        self.__Orders = db.Table('Orders')
        s3 = boto3.resource('s3')
        debug = os.environ['DEBUG_FOLDER']
        self.__debug = s3.Object(debug, 'vix_roll.txt')
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
        self.Logger.info('InstanceController Created. Region: %s Instance: %s' % (params.Region, params.Instance))

    def AttemptsCount(self):
        timestamp = int((datetime.datetime.now() - datetime.timedelta(hours=2)).timestamp()) * 1000
        logs = boto3.client('logs')
        log_group = '/aws/docker/Capsule'
        data = logs.describe_log_streams(logGroupName=log_group, orderBy='LastEventTime', descending=True)
        streams = filter(lambda x: x['creationTime'] > timestamp, data['logStreams'])

        count = 0
        for stream in streams:
            lines = logs.get_log_events(logGroupName=log_group,
                                        logStreamName=stream['logStreamName'])
            for line in lines['events']:
                if 'LogStream Created:' in line['message']:
                    count += 1
        self.Logger.info('Capsule ran %s times in the last 2 hours' % count)

        return count

    def SendEmail(self, text):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'NIGHTWATCH ALERT'
        msg['From'] = self.Email
        msg['To'] = self.Email
        mime_text = MIMEText(text, 'html')
        msg.attach(mime_text)

        server = smtplib.SMTP(self.Smtp, 587, timeout=10)
        server.set_debuglevel(10)
        server.starttls()
        server.ehlo()
        server.login(self.User, self.Password)
        server.sendmail(self.Email, self.Email, msg.as_string())
        res = server.quit()
        self.Logger.info(res)

    def ValidateStrategy(self):
        today = datetime.date.today().strftime("%Y%m%d")
        fileObj = self.__debug.get()['Body']
        ch = fileObj.read(1)
        line = ''
        while ch:
            if ch.decode("utf-8") == '\n':
                if today in line:
                    return True
                line = ''
            else:
                line += ch.decode("utf-8")
            ch = fileObj.read(1)
        return False

    @Utils.reliable
    def SuspendTrading(self, symbol, broker):
        try:

            response = self.__Securities.update_item(
                Key={
                    'Symbol': symbol,
                    'Broker': broker,
                },
                UpdateExpression="set #te = :te",
                ExpressionAttributeNames={
                    '#te': 'TradingEnabled'
                },
                ExpressionAttributeValues={
                    ':te': False
                },
                ReturnValues="UPDATED_NEW")

        except ClientError as e:
            self.Logger.error(e.response['Error']['Message'])
        except Exception as e:
            self.Logger.error(e)
        else:
            self.Logger.info('Security Updated')
            self.Logger.info(json.dumps(response, indent=4, cls=DecimalEncoder))
            return response

    @Utils.reliable
    def SendOrder(self, symbol, maturity, side, size, price, orderType, fillTime, dealId, broker, productType):
        try:
            order = {
                "Side": side,
                "Size": decimal.Decimal(str(size)),
                "OrdType": orderType}
            trade = {
              "FillTime": fillTime,
              "Side": side,
              "FilledSize": decimal.Decimal(str(size)),
              "Price": decimal.Decimal(str(price)),
              "Broker": {"Name": broker, "RefType": "dealId", "Ref": dealId},
            }
            strategy = {
                "Name": "SYSTEM",
                "Reason": "STOP_TRIGGERED"
            }

            response = self.__Orders.update_item(
                Key={
                    'OrderId': str(uuid.uuid4().hex),
                    'TransactionTime': str(time.time()),
                },
                UpdateExpression="set #st = :st, #s = :s, #m = :m, #p = :p, #b = :b, #o = :o, #t = :t, #str = :str",
                ExpressionAttributeNames={
                    '#st': 'Status',
                    '#s': 'Symbol',
                    '#m': 'Maturity',
                    '#p': 'ProductType',
                    '#b': 'Broker',
                    '#o': 'Order',
                    '#t': 'Trade',
                    '#str': 'Strategy'
                },
                ExpressionAttributeValues={
                    ':st': 'FILLED',
                    ':s': symbol,
                    ':m': maturity,
                    ':p': productType,
                    ':b': broker,
                    ':o': order,
                    ':t': trade,
                    ':str': strategy
                },
                ReturnValues="UPDATED_NEW")

        except ClientError as e:
            self.Logger.error(e.response['Error']['Message'])
        except Exception as e:
            self.Logger.error(e)
        else:
            self.Logger.info('Order Created')
            self.Logger.info(json.dumps(response, indent=4, cls=DecimalEncoder))
            return response

    def FindSystemStopOrders(self):
        """
            Update Orders table if the stop order was executed by the broker
        :return:
            None
        """
        params = IGParams()
        params.Url = os.environ['IG_URL']
        params.Key = os.environ['X_IG_API_KEY']
        params.Identifier = os.environ['IDENTIFIER']
        params.Password = os.environ['PASSWORD']

        self.Logger.info('Checking if any stop order was triggered')

        async def read():
            async with IGClient(params, self.Logger) as client:
                auth = await client.Login()
                self.Logger.info('Auth: %s' % auth)

                lastMonth = datetime.date.today() - datetime.timedelta(days=30)
                activities = await client.GetActivities(lastMonth.strftime('%Y-%m-%d'), True)
                self.Logger.info('activities: %s' % activities)
                await client.Logout()

                if activities is not None and 'activities' in activities and len(activities['activities']) > 0:
                    stopTriggered = [tran for tran in activities['activities']
                                     if tran['channel'] == 'SYSTEM' and 'details' in tran]

                    if len(stopTriggered) == 0:
                        self.Logger.info('No stops were triggered')
                        return

                    filled = self.GetOrders('Status', 'FILLED')
                    self.Logger.info('All filled %s' % filled)
                    for tran in stopTriggered:
                        for action in tran['details']['actions']:
                            if action['actionType'] == 'POSITION_CLOSED':
                                self.Logger.info('affectedDealId: %s' % action['affectedDealId'])
                                already_done = [o for o in filled if 'Broker'in o['Trade'] and 'Ref'
                                                in o['Trade']['Broker'] and o['Trade']['Broker']['Ref'] == tran['dealId']
                                                and o['Strategy']['Name'] == 'SYSTEM']
                                if len(already_done) == 1:
                                    self.Logger.info('Already filled this unaccounted stop %s' % tran['dealId'])
                                    continue

                                found = [o for o in filled if 'Broker'in o['Trade'] and 'Ref' in o['Trade']['Broker']
                                         and o['Trade']['Broker']['Ref'] == action['affectedDealId']]
                                if len(found) == 1:
                                    f = found[0]
                                    self.Logger.info('Unaccounted stop found %s' % found)
                                    self.SuspendTrading(f['Symbol'], 'IG')

                                    self.SendOrder(f['Symbol'], f['Maturity'], tran['details']['direction'],
                                                   tran['details']['size'], tran['details']['level'],
                                                   'STOP', tran['date'], tran['dealId'], 'IG', f['ProductType'])

                                    self.SendEmail('STOP Order was triggered by IG. Trading in %s is suspended'
                                                   % f['Symbol'])

        app_loop = asyncio.get_event_loop()
        app_loop.run_until_complete(read())

    def ValidateExecutor(self):
        pending = self.GetOrders('Status', 'PENDING')
        if pending is not None and len(pending) > 0:
            self.SendEmail('There are %s PENDING Orders in Chaos' % len(pending))

        failed = self.GetOrders('Status', 'FAILED')
        if failed is not None and len(failed) > 0:
            self.SendEmail('There are %s FAILED Orders in Chaos' % len(failed))

    def EndOfDay(self):
        allFound = True
        for security in filter(lambda x: x['SubscriptionEnabled'], self.GetSecurities()):
            today = datetime.date.today().strftime("%Y%m%d")
            symbols = []
            if security['ProductType'] == 'IND':
                symbols = [security['Symbol']]
            if security['ProductType'] == 'FUT':
                symbols = self.secDef.get_futures(security['Symbol'], 2)  # get two front months
            for symbol in symbols:
                found = self.GetQuotes(symbol, today)
                if len(found) > 0:
                    self.Logger.info('Found Symbols: %s' % found)
                else:
                    self.Logger.error('Failed to find data for %s' % symbol)
                allFound &= len(found) > 0

        if allFound:
            self.Logger.info('All Found. Stopping EC2 Instance')
            if self.IsInstanceRunning():
                self.StopInstance()

            if not self.ValidateStrategy():
                self.SendEmail('The VIX Roll strategy left no TRACE file today')

        else:
            self.Logger.info('Not All Found. Will try again. Restarting EC2 Instance')
            if self.IsInstanceRunning():
                self.StopInstance()
            if self.AttemptsCount() >= 3:
                self.SendEmail('Capsule could not retrieve market data after %s attempts' % str(3))
                return
            self.StartInstance()

    def IsInstanceRunning(self):
        self.Logger.info('Instance Id: %s, State: %s' % (self.__Instance.instance_id, self.__Instance.state))
        return self.__Instance.state['Name'] == 'running'

    def StartInstance(self):
        self.__Instance.start()
        self.__Instance.wait_until_running()
        self.Logger.info('Started instance: %s' % self.__Instance.instance_id)

    def StopInstance(self):
        self.__Instance.stop()
        self.__Instance.wait_until_stopped()
        self.Logger.info('Stopped instance: %s' % self.__Instance.instance_id)

    @Utils.reliable
    def GetOrders(self, key, value):
        try:
            self.Logger.info('Calling orders scan attr: %s, %s' % (key, value))
            response = self.__Orders.scan(FilterExpression=Attr(key).eq(value))

        except ClientError as e:
            self.Logger.error(e.response['Error']['Message'])
            return None
        except Exception as e:
            self.Logger.error(e)
            return None
        else:
            if 'Items' in response:
                return response['Items']

    @Utils.reliable
    def GetSecurities(self):
        try:
            self.Logger.info('Calling securities scan ...')
            response = self.__Securities.scan(FilterExpression=Attr('SubscriptionEnabled').eq(True))
        except ClientError as e:
            self.Logger.error(e.response['Error']['Message'])
            return None
        except Exception as e:
            self.Logger.error(e)
            return None
        else:
            if 'Items' in response:
                return response['Items']

    @Utils.reliable
    def GetQuotes(self, symbol, date):
        try:
            self.Logger.info('Calling quotes query Date key: %s' % date)
            response = self.__QuotesEod.query(
                KeyConditionExpression=Key('Symbol').eq(symbol) & Key('Date').eq(date)
            )
        except ClientError as e:
            self.Logger.error(e.response['Error']['Message'])
            return None
        except Exception as e:
            self.Logger.error(e)
            return None
        else:
            self.Logger.info(json.dumps(response, indent=4, cls=DecimalEncoder))
            if 'Items' in response:
                return response['Items']


def lambda_handler(event, context):
    params = CapsuleParams()
    params.Region = os.environ["NIGHT_WATCH_REGION"]
    params.Instance = os.environ["NIGHT_WATCH_INSTANCE"]
    params.Email = os.environ["NIGHT_WATCH_EMAIL"]
    params.Iam = os.environ["NIGHT_WATCH_IAM"]
    params.User = os.environ["NIGHT_WATCH_USER"]
    params.Password = os.environ["NIGHT_WATCH_PASSWORD"]
    params.Smtp = os.environ["NIGHT_WATCH_SMTP"]

    controller = CapsuleController(params)

    try:
        controller.FindSystemStopOrders()
    except Exception as e:
        controller.Logger.error('FindSystemStopOrders: %s' % e)

    controller.ValidateExecutor()
    controller.EndOfDay()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', help='AWS region', required=True)
    parser.add_argument('--instance', help='EC2 instance', required=True)
    parser.add_argument('--email', help='Email address', required=True)
    parser.add_argument('--iam', help='IAM Role', required=True)
    parser.add_argument('--user', help='SMTP User', required=True)
    parser.add_argument('--password', help='SMTP Password', required=True)
    parser.add_argument('--smtp', help='SMTP Address', required=True)
    parser.add_argument('--debug', help='Debug Folder', required=True)
    args = parser.parse_args()
    os.environ["NIGHT_WATCH_REGION"] = args.region
    os.environ["NIGHT_WATCH_INSTANCE"] = args.instance
    os.environ["NIGHT_WATCH_EMAIL"] = args.email
    os.environ["NIGHT_WATCH_IAM"] = args.iam
    os.environ["NIGHT_WATCH_USER"] = args.user
    os.environ["NIGHT_WATCH_PASSWORD"] = args.password
    os.environ["NIGHT_WATCH_SMTP"] = args.smtp
    os.environ["DEBUG_FOLDER"] = args.debug
    event = ''
    context = ''
    lambda_handler(event, context)


if __name__ == "__main__":
    main()
