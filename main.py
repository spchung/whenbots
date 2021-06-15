import config
import datetime
import websocket
import kline_lookback_config
from binance.client import Client
from signal_generators import SimpleMacd
from base_strategy import MACDStateMachine
from binance_account import BinanceAccount

## API_KEY
api_key = config.API_KEY
api_secret = config.API_SECRET

startTime = datetime.datetime.now() - datetime.timedelta(hours=100)
timestamp = startTime.timestamp()

# print start time
startTimeStr = startTime.strftime("%m/%d/%Y - %H:%M:%S")
print(startTimeStr)

## run 
cc  = 'ethusdt' # must be lower case
interval, lookback = kline_lookback_config.FIVE_MINUTE

socket = f"wss://stream.binance.com:9443/ws/{cc}@kline_{interval}"
client = Client(config.API_KEY, config.API_SECRET)
symbol = "ETHUSDT"

# signal generator
signal = SimpleMacd(client, symbol, lookback, interval)

#BinanceAccount
account = BinanceAccount(client, symbol)

# bot state
botState = MACDStateMachine(account, symbol, riskTolerancePercentage=0.5, USDTFundAmount=20, isTestNet=False)

ws = websocket.WebSocketApp(socket, on_message=signal.getOnMessage(botState), on_close=signal.getOnClose())
ws.on_open = signal.getOnOpen()

ws.run_forever()