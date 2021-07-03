## import from parent
import os, sys
from typing import Collection
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

class RunSetting:
    collectionName = 'run_settings'

    def __init__(self):
        self._id = None
        self.name = None
        self.slug = None
        self.websocketSymbol = None
        self.symbol = None
        self.tradeInterval = None
        self.accountID = None # reservation for account system
        self.riskTolerancePercentage = None
        self.testNet = False
        self.indicators = list()

    def toDict(self):
        res = vars(self)
        
        if '_id' in res and res['_id'] is None:
            del res['_id']
        
        return res

    @staticmethod
    def fromDict(settingsDict):
        settings = RunSetting()

        for k, v in settingsDict.items():
            if hasattr(settings, k):
                setattr(settings, k, v)
        
        return settings

    @staticmethod
    def get(_id):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[RunSetting.collectionName]

        res = collection.find_one({'_id':ObjectId(_id)})

        return RunSetting.fromDict(res)
    
    @staticmethod
    def query(limit=10, **kwargs):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[RunSetting.collectionName]

        settings = collection.find(kwargs).limit(limit)

        res = list()

        for setting in settings:
            res.append(RunSetting.fromDict(setting))
        
        return res