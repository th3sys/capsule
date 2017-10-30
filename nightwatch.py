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


class CapsuleController(object):
    def __init__(self, region, instance):
        self.Logger = logging.getLogger()
        self.Logger.setLevel(logging.INFO)
        ec2 = boto3.resource('ec2', region_name=region)
        self.__Instance = ec2.Instance(instance)
        db = boto3.resource('dynamodb', region_name=region)
        self.__QuotesEod = db.Table('Quotes.EOD')
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
        self.Logger.info('InstanceController Created. Region: %s Instance: %s' % (region, instance))

    def EndOfDay(self):
        self.GetQuotes()
        if not self.IsInstanceRunning():
            self.StartInstance()

    def IsInstanceRunning(self):
        self.Logger.info('Instance Id: %s, State: %s' % (self.__Instance.instance_id, self.__Instance.state))
        return self.__Instance.state['Name'] == 'running'

    def StartInstance(self):
        self.__Instance.start()
        self.Logger.info('Started instance: %s' % self.__Instance.instance_id)

    def StopInstance(self):
        self.__Instance.stop()
        self.Logger.info('Stopped instance: %s' % self.__Instance.instance_id)

    def GetQuotes(self):
        try:
            today = datetime.date.today().strftime("%Y%m%d")

            self.Logger.info('Calling quotes query Date key: %s' % today)
            response = self.__QuotesEod.query(
                                KeyConditionExpression=Key('Date').eq(today) 
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
    region = os.environ["NIGHT_WATCH_REGION"]
    instance = os.environ["NIGHT_WATCH_INSTANCE"]
    controller = CapsuleController(region, instance)
    controller.EndOfDay()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', help='AWS region', required=True)
    parser.add_argument('--instance', help='EC2 instance', required=True)
    args = parser.parse_args()
    os.environ["NIGHT_WATCH_REGION"] = args.region
    os.environ["NIGHT_WATCH_INSTANCE"] = args.instance
    event = ''
    context = ''
    lambda_handler(event, context)


if __name__ == "__main__":
    main()
