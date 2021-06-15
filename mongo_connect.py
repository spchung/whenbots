import config
from pymongo import MongoClient

access_key = config.AWS_ACCESS
secret_key = config.AWS_SECRET

uri = f"mongodb://{access_key}:{secret_key}@localhost/?authMechanism=MONGODB-AWS"


client = MongoClient(uri)


