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

class Run:
    collectionName = 'runs'

    def __init__(self):
        self._id = None
        self.runSettingId = None
        self.start = datetime.utcnow().strftime("%m-%d-%Y %H:%M:%S")
        self.completedTradeIds = list()
        self.currentOpenTradeId = None
        self.end = None
    
    # done at end of manaul termination of run
    def complete(self):
        if not self.currentOpenTradeId is None:
            raise Exception("The current trade is not yet closed")
        
        self.end = datetime.datetime.utcnow().strftime("%m-%d-%Y %H:%M:%S")

        run = Run.update(self)
        if not run is None:
            print("RUN CLOSED SUCCESSFULLY")
            return run.toDict()

        raise Exception("ERROR WHEN UPDATING CLOSED RUN")

    def hasCompleted(self):
        return (self.end is None and not self.currentOpenTradeId is None)

    def toDict(self):
        res = vars(self)
        
        if '_id' in res and res['_id'] is None:
            del res['_id']
        
        return res
    
    @staticmethod
    def fromDict(runDict):
        run = Run()

        for k, v in runDict.items():
            if hasattr(run, k):
                setattr(run, k, v)
        
        return run
    
    @staticmethod
    def get(_id):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Run.collectionName]

        res = collection.find_one({'_id':ObjectId(_id)})

        return Run.fromDict(res)
    
    @staticmethod
    def insert(run):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Run.collectionName]

        if run.runSettingsId is None:
            raise Exception("`Run` object must have a runSettingId.")

        res = collection.insert_one(run.toDict())

        if res.acknowledged:
            return Run.get(res.inserted_id)
        
        return None

    @staticmethod
    def update(run):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Run.collectionName]

        res = collection.update_one(
            {
                "orderID":run.orderID
            },
            {
                "$set":run.toDict()
            },
            upsert=True
        )
        
        if res.acknowledged:
            return Run.get(res.upsertedId)
        
        return None

    @staticmethod
    def query(sortBy=[("entryTime", pymongo.DESCENDING)], limit=10, **kwargs):
        mongo = DatabaseManager.connect(dbName='whenbots')
        collection = mongo[Run.collectionName]

        res = list()

        runs = collection.find(kwargs).limit(limit).sort(sortBy)

        for run in runs:
            res.append(Run.fromDict(run))
        
        return res
