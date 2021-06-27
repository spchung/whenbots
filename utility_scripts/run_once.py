## import from parent
import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)


import config 
import datetime
import pprint
import kline_lookback_config
from binance.client import Client

from signal_generators import SignalGenerator
from base_strategy import MACDStateMachine
from binance_account import BinanceAccount

from database_manager import DatabaseManager
from models.order import Order
from models.trade import Trade

import pprint

api_key = config.API_KEY
api_secret = config.API_SECRET

client = Client(api_key, api_secret)

order_coll = DatabaseManager.connect(dbName='whenbots')['orders']

account = BinanceAccount(client, "ETHUSDT")

# sync order to mongodb
symbols = ['BNBUSDT']

update = False
create = not update

i = 0 

import time

order = client.get_order(symbol='ETHUSDT', orderId=4683708480)
order = Order.fromGetOrder(order)

trade = account.openTrade(order)

trade = Trade.insert(trade)

trade = Trade.get(trade._id)

print("opened")
print("Sleep for 10 seconds")
time.sleep(10)

print("Closing Trade")
order = client.get_order(symbol='ETHUSDT', orderId=4684739371)
order = Order.fromGetOrder(order)

trade = account.closeTrade(order, trade)

trade = Trade.update(trade)

# res = order_coll.update_one({'orderID':order.orderID}, {
#         "$set":order.toDict()
#     }, upsert=True)


'''
for symbol in symbols:
    binOrders = client.get_all_orders(symbol=symbol)

    for binOrder in binOrders:
        order = Order.fromGetOrder(binOrder)

        if update:
            order_coll.update_one({'orderID':order.orderID}, {
                "$set":order.toDict()
            }, upsert=True)

        # if create:
        #     Order.insert(order)
'''
# 2263103281