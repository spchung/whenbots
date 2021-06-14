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
macdAccount = BinanceAccount(client, "USDT")
macdBot = MACDStateMachine(macdAccount, symbol, isTestNet=True)

payload = sMacd.generate(period=1)


df = sMacd.pricesDataFrame()
ema_s, ema_m, ema_l = sMacd.EMAS(df)
macd, signal, hist = sMacd.MACD(df)

d =dict()
d['ema7'] = ema_s[-2]
d['ema25'] = ema_m[-2]
d['ema99'] = ema_l[-2]
d['macd'] = macd[-2]
d['signal'] = signal[-2]

pprint.pprint(d)

