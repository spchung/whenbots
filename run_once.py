import config 
import datetime
from binance.client import Client

from signal_generators import SimpleMacd
from base_strategy import MACDStateMachine
from binance_account import BinanceAccount, Order

api_key = config.API_KEY
api_secret = config.API_SECRET

client = Client(api_key, api_secret)

# set up start time
lookBackHours = 100

startTime = datetime.datetime.now() - datetime.timedelta(hours=lookBackHours)
timestamp = startTime.timestamp()
millisecondTimstamp = timestamp*1000

symbol="ETHUSDT"
interval = '15m'

sMacd = SimpleMacd(client, symbol, lookBackHours, interval)
macdAccount = BinanceAccount(client, "USDT")
macdBot = MACDStateMachine(macdAccount, symbol, isTestNet=True)

payload = sMacd.generate()

orderID, isTestNet = macdBot.receive(payload[0])

