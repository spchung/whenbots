import config 
import datetime
import pprint
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
macdAccount = BinanceAccount(client, "ETHUSDT")
macdBot = MACDStateMachine(macdAccount, symbol, isTestNet=True)


print(sMacd.generateIndicatorsLatest(['MACD','EMAS']))
