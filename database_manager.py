import config
from pymongo import MongoClient

class DatabaseManager:
    connection = []
    maxConnection = 1

    @staticmethod
    def connect(userName=config.MONGO_USER_NAME, pwd=config.MONGO_USER_PWD, dbName=None):
        if len(DatabaseManager.connection) < DatabaseManager.maxConnection:

            uri = f"mongodb+srv://{userName}:{pwd}@whenbots.sejvj.mongodb.net/whenbots?retryWrites=true&w=majority"

            DatabaseManager.connection.append(MongoClient(uri))
        
        if dbName is None:
            return DatabaseManager.connection[0]
        
        return DatabaseManager.connection[0][dbName]