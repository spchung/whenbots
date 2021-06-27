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

class Trade:
    
    collectionName = 'trades'

    def __init__(self):
        self._id = None
        self.entryTime = None
        self.positionType = None # enum ['LONG', 'SHORT']
        self.symbol = None
        self.entryQuoteAmount = 0.0
        self.purchasedCoinAmount = 0.0
        
        # orders
        self.openOrderID = None
        self.closeOrderID = None

        # exit
        self.complete = False
        self.exitUSDTAmount = 0.0
        self.exitTime = None
    
    def toDict(self):
        d = dict()

        # when inserting leave out _id field for mongo to generate
        if not self._id is None:
            d['_id'] = self._id

        d['entryTime'] = self.entryTime
        d['positionType'] = self.positionType
        d['symbol'] = self.symbol
        d['entryQuoteAmount'] = self.entryQuoteAmount
        d['purchasedCoinAmount'] = self.purchasedCoinAmount
        d['openOrderID'] = self.openOrderID
        d['closeOrderID'] = self.closeOrderID
        d['complete'] = self.complete
        d['exitUSDTAmount'] = self.exitUSDTAmount
        d['exitTime'] = self.exitTime

        return d
    
    @staticmethod
    def fromDict(tradeDict):
        
        trade = Trade()
        trade._id = tradeDict['_id']
        trade.entryTime = tradeDict['entryTime']
        trade.positionType = tradeDict['positionType']
        trade.symbol = tradeDict['symbol']
        trade.entryQuoteAmount = tradeDict['entryQuoteAmount']
        trade.purchasedCoinAmount = tradeDict['purchasedCoinAmount']
        trade.openOrderID = tradeDict['openOrderID']
        trade.closeOrderID = tradeDict['closeOrderID']
        trade.complete = tradeDict['complete']
        trade.exitUSDTAmount = tradeDict['exitUSDTAmount'] 
        trade.exitTime = tradeDict['exitTime']

        return trade

    # db methods
    @staticmethod
    def insert(trade):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Trade.collectionName]

        res = collection.insert_one(trade.toDict())

        if not res.acknowledged:
            return None
        
        return Trade.get(res.inserted_id)
        
    @staticmethod
    def get(_id):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Trade.collectionName]

        res = collection.find_one({'_id':ObjectId(_id)})

        trade = Trade.fromDict(res)
        return trade
    
    @staticmethod
    def query(sortBy=[("entryTime", pymongo.DESCENDING)], limit=10, **kwargs):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Trade.collectionName]

        trades = collection.find(kwargs).limit(limit).sort(sortBy)

        res = list()

        for trade in trades:
            res.append(Trade.fromDict(trades))
        
        return res
    
    @staticmethod
    def update(trade, upsert=False):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Trade.collectionName]

        searchTerm = dict()
        searchTerm['_id'] = trade._id

        res = collection.update_one(searchTerm,{
            "$set":trade.toDict()
        }, upsert=upsert)

        # update fail
        if not res.acknowledged is True:
            raise Exception(f"UPDATE trade object with _id:{trade._id} failed.")

        return Trade.get(trade._id)

