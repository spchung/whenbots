import config 
import datetime
from pprint import pprint
import kline_lookback_config
from binance.client import Client

from signal_generators import SimpleMacd
from base_strategy import MACDStateMachine
from binance_account import BinanceAccount, Order

api_key = config.API_KEY
api_secret = config.API_SECRET

client = Client(api_key, api_secret)

# trade symbol
symbol="ETHUSDT"

# set up start time
# lookBackHours = 100
# interval = '15m'

interval, lookBackHours = kline_lookback_config.FIVE_MINUTE

startTime = datetime.datetime.now() - datetime.timedelta(hours=lookBackHours)
timestamp = startTime.timestamp()
millisecondTimstamp = timestamp*1000


sMacd = SimpleMacd(client, symbol, lookBackHours, interval)
macdAccount = BinanceAccount(client, "USDT")
macdBot = MACDStateMachine(macdAccount, symbol, isTestNet=True)

# macdBot.inPosition = True
# macdBot.inTestNEt=True
# macdBot.activeOrderID = 14606
# macdBot.stopLossOrderID = 14607
# macdBot.pair = "ETHUSDT"
# macdBot.stopLossOrderPlaced = True

payload = sMacd.generate(period=5)
pprint(payload)

# orderID, isTestNet = macdBot.receive(payload[0])
