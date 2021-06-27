## import from parent
import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import uuid
import pprint
from decimal import Decimal
from datetime import datetime
from binance.client import Client
import binance.enums as binanceEnums

import pymongo
from bson.objectid import ObjectId
from database_manager import DatabaseManager

## order v2 -> derive price from fills
class Order:
    collectionName = 'orders'

    def __init__(self):
        self._id = None
        self.isTestNet=False
        self.orderID = -1
        self.clientOrderID = None
        self.symbol = None
        self.cummulativeQuoteQty = None
        self.origQty = None
        self.executedQty = None
        self.status = None
        self.timeInForce = None
        self.type = None
        self.side = None 
        self.time = None
        self.stopPrice = None
        self.icebergQty = None

        self.price = None
        self.fills = None

    @staticmethod
    def fromOrderPlacement(orderPayload):
        order = Order()

        order.isTestNet = False
        order.orderID = orderPayload['orderId']
        order.clientOrderID = orderPayload['clientOrderId']
        order.symbol = orderPayload['symbol']
        order.origQty = float(orderPayload['origQty'])
        order.cummulativeQuoteQty = float(orderPayload['cummulativeQuoteQty'])
        order.executedQty = float(orderPayload['executedQty'])
        order.status = orderPayload['status'] # enum ['NEW', 'FILLED', 'CANCELED']
        order.timeInForce = orderPayload['timeInForce']
        order.type = orderPayload['type']
        order.side = orderPayload['side']
        
        # derive avg price
        order.fills = orderPayload['fills']

        totalCost = 0.0
        totalQuantity = 0.0
        for fill in orderPayload['fills']:
            cost = float(fill['price']) * float(fill['qty'])

            totalCost += cost
            totalQuantity += float(fill['qty'])

        avg_price = totalCost/totalQuantity

        order.price = avg_price
        
        # time
        if 'time' in orderPayload:
            order.time = orderPayload['time']

        if 'transactTime' in orderPayload:
            order.time = orderPayload['transactTime']
        
        return order

    @staticmethod
    def fromGetOrder(orderPayload):
        order = Order()

        order.isTestNet = False
        order.orderID = orderPayload['orderId']
        order.clientOrderID = orderPayload['clientOrderId']
        order.symbol = orderPayload['symbol']
        order.price = float(orderPayload['price'])
        order.cummulativeQuoteQty = float(orderPayload['cummulativeQuoteQty'])
        order.origQty = float(orderPayload['origQty'])
        order.executedQty = float(orderPayload['executedQty'])
        order.timeInForce = orderPayload['timeInForce']
        order.type = orderPayload['type']
        order.side = orderPayload['side']
        
        if 'time' in orderPayload:
            order.time = datetime.fromtimestamp(orderPayload['time']/1000).strftime("%m-%d-%Y %H:%M:%S")

        if 'transactTime' in orderPayload:
            order.time = datetime.fromtimestamp(orderPayload['transactTime']/1000).strftime("%m-%d-%Y %H:%M:%S")

        order.stopPrice = float(orderPayload['stopPrice'])
        order.icebergQty = float(orderPayload['icebergQty'])
        order.status = orderPayload['status'] # enum ['NEW', 'FILLED', 'CANCELED']
        
        return order

    def toDict(self):
        d = dict()
        
        # when inserting leave out _id field for mongo to generate
        if not self._id is None:
            d['_id'] = self._id

        d['isTestNet'] = self.isTestNet
        d['orderID'] = self.orderID
        d['clientOrderID'] = self.clientOrderID
        d['symbol'] = self.symbol
        d['price'] = self.price
        d['cummulativeQuoteQty'] = self.cummulativeQuoteQty
        d['origQty'] = self.origQty
        d['executedQty'] = self.executedQty
        d['timeInForce'] = self.timeInForce
        d['type'] = self.type
        d['side'] = self.side
        
        # when retrieving from binance api
        if not isinstance(self.time,str):
            d['time'] = datetime.fromtimestamp(self.time/1000).strftime("%m-%d-%Y %H:%M:%S")
        # when retrieving from mongo db
        else:
            d['time'] = self.time

        d['stopPrice'] = self.stopPrice
        d['icebergQty'] = self.icebergQty
        d['status'] = self.status

        return d

    # DB classes 
    @staticmethod
    def fromDict(orderRes):
        order = Order()
        order._id = orderRes['_id']
        order.isTestNet = orderRes['isTestNet']
        order.orderID = orderRes['orderID']
        order.clientOrderID = orderRes['clientOrderID']
        order.symbol = orderRes['symbol']
        order.origQty = orderRes['origQty']
        order.executedQty = orderRes['executedQty']
        order.status = orderRes['status']
        order.timeInForce = orderRes['timeInForce']
        order.type = orderRes['type']
        order.side = orderRes['side']
        order.time = orderRes['time']
        order.stopPrice = orderRes['stopPrice']
        order.icebergQty = orderRes['icebergQty']

        return order

    @staticmethod
    def insert(order):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Order.collectionName]
        
        res = collection.insert_one(order.toDict())
        
        if res.acknowledged:
            return Order.get(res.inserted_id)

        return None
    
    @staticmethod
    def get(_id):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Order.collectionName]

        res = collection.find_one({'_id':ObjectId(_id)})

        order = Order.fromDict(res)

        return order

    @staticmethod
    def update(order):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Order.collectionName]

        res = collection.update_one(
            {
                "orderID":order.orderID
            },
            {
                "$set":order.toDict()
            },
            upsert=True
        )

        return res.acknowledged

    @staticmethod
    def getWithOrderID(binanceOrderID):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Order.collectionName]

        res = collection.find_one({'orderID':binanceOrderID})

        return res
    
    @staticmethod
    def query(sortBy=[("time", pymongo.DESCENDING)], limit=10, **kwargs):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Order.collectionName]
        
        orders = collection.find(kwargs).limit(limit).sort(sortBy)
        
        res = list()

        for order in orders:
            res.append(Order.fromDict(order))

        return res


        