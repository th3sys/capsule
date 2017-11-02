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

NumberOfAttempts = []


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
                if 'setting nextValidOrderId' in line['message']:
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

    def EndOfDay(self):
        if self.AttemptsCount() > 3 or len(NumberOfAttempts) > 3:
            self.SendEmail('Capsule could not retrieve market data after %s attempts' % len(NumberOfAttempts))
            return

        allFound = True
        for security in self.GetSecurities():
            today = datetime.date.today().strftime("%Y%m%d")
            symbols = []
            if security['ProductType'] == 'IND':
                symbols = [security['Symbol']]
            if security['ProductType'] == 'FUT':
                symbols = self.secDef.get_futures(security['Symbol'], 2) # get two front months
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
        else:
            self.Logger.info('Not All Found. Will try again. Restarting EC2 Instance')
            if self.IsInstanceRunning():
                self.StopInstance()
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
    NumberOfAttempts.append(1)
    params = CapsuleParams()
    params.Region = os.environ["NIGHT_WATCH_REGION"]
    params.Instance = os.environ["NIGHT_WATCH_INSTANCE"]
    params.Email = os.environ["NIGHT_WATCH_EMAIL"]
    params.Iam = os.environ["NIGHT_WATCH_IAM"]
    params.User = os.environ["NIGHT_WATCH_USER"]
    params.Password = os.environ["NIGHT_WATCH_PASSWORD"]
    params.Smtp = os.environ["NIGHT_WATCH_SMTP"]

    controller = CapsuleController(params)
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
    args = parser.parse_args()
    os.environ["NIGHT_WATCH_REGION"] = args.region
    os.environ["NIGHT_WATCH_INSTANCE"] = args.instance
    os.environ["NIGHT_WATCH_EMAIL"] = args.email
    os.environ["NIGHT_WATCH_IAM"] = args.iam
    os.environ["NIGHT_WATCH_USER"] = args.user
    os.environ["NIGHT_WATCH_PASSWORD"] = args.password
    os.environ["NIGHT_WATCH_SMTP"] = args.smtp
    event = ''
    context = ''
    lambda_handler(event, context)


if __name__ == "__main__":
    main()
