import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import config
import datetime
import kline_lookback_config
from binance.client import Client
from signal_generators import SignalGenerator
from binance_account import BinanceAccount

from models.order import Order

from utils import WsKline

## API_KEY
api_key = config.API_KEY
api_secret = config.API_SECRET

startTime = datetime.datetime.now() - datetime.timedelta(hours=100)
timestamp = startTime.timestamp()

# print start time
startTimeStr = startTime.strftime("%m/%d/%Y - %H:%M:%S")
print(startTimeStr)

## run 
cc  = 'bnbbusd' # must be lower case
interval, lookback = kline_lookback_config.FIVE_MINUTE

socket = f"wss://stream.binance.com:9443/ws/{cc}@kline_{interval}"
client = Client(config.API_KEY, config.API_SECRET)
symbol = "BNBBUSD"

# signal generator
signal = SignalGenerator(client, symbol, lookback, interval)

#BinanceAccount
account = BinanceAccount(client, symbol)

symbols = config.TRACKED_SYMBOLS

# get all trade symbols
for symbol in symbols:
    # get all orders uder this symbol
    orders = client.get_all_orders(
        symbol=symbol
    )

    for order in orders:
       
        order = Order.fromGetOrder(order)
        Order.update(order)
