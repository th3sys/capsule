from __future__ import print_function # Python 2/3 compatibility
import boto3
import json
import uuid
import time
import decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

sec_table = dynamodb.Table('Securities')
quotes_table = dynamodb.Table('Quotes.EOD')

with open("quotes.json") as json_file:
    quotes = json.load(json_file, parse_float = decimal.Decimal)
    for quote in quotes:
        Symbol = quote['Symbol']
        Date = str(time.time())
        Source = quote['Source']
        Details = quote['Details']

        print("Adding quote:", Symbol, Date)

        quotes_table.put_item(
           Item={
               'Symbol': Symbol,
               'Date': Date,
               'Source': Source,
               'Details': Details
            }
        )
        
with open("securities.json") as json_file:
    securities = json.load(json_file, parse_float = decimal.Decimal)
    for security in securities:
        Symbol = security['Symbol']
        Broker = security['Broker']
        ProductType = security['ProductType']
        SubscriptionEnabled = bool(security['SubscriptionEnabled'])
        TradingEnabled = bool(security['TradingEnabled'])
        Description = security['Description']
        Risk = security['Risk']

        print("Adding security:", Symbol)

        sec_table.put_item(
           Item={
               'Symbol': Symbol,
               'Broker' : Broker,
               'ProductType': ProductType,
               'SubscriptionEnabled': SubscriptionEnabled,
               'TradingEnabled':TradingEnabled,
               'Description':Description,
               'Risk':Risk
            }
        )

