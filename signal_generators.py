import json
import pprint
import talib
import datetime
import numpy as np
from functools import partial

'''
class MacdGenerator:
    
    def __init__(self, client, symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_1MINUTE, lookBackHours=2):
        self.client = client # binance client 
        try:
            startTime = datetime.datetime.now() - datetime.timedelta(hours=lookBackHours)
            timestamp = startTime.timestamp()
            self.klines = self.client.get_klines(symbol=symbol, interval=interval, startTime=int(timestamp*1000))
        except Exception as e:
            raise Exception("Unable to inirializ klines data. Error msg: "+str(e))

        # prices
        self.open = np.array([ float(candle[1]) for candle in self.klines])
        self.high = np.array([ float(candle[2]) for candle in self.klines])
        self.low = np.array([ float(candle[3]) for candle in self.klines])
        self.close = np.array([ float(candle[4]) for candle in self.klines])
        
        # time 
        self.closeTime = np.array([ float(candle[6]) for candle in self.klines])
        self.openTime = np.array([ float(candle[0]) for candle in self.klines])

        # volume
        self.volume = np.array([ float(candle[5]) for candle in self.klines])

        # MACD
        self.macd, self.macdsignal, self.macdhist  = talib.MACD(self.close, fastperiod=12, slowperiod=26, signalperiod=9)   

        # running EMA
        self.ema99 = talib.EMA(self.close, 99)
        self.ema25 = talib.EMA(self.close, 25)
        self.ema7 = talib.EMA(self.close, 7)

    def update(self, priceArray):
        # update
        try:
            self.open = self.open[1:]
            self.open = np.append(self.open, np.array(priceArray[0]))

            self.high = self.high[1:]
            self.high = np.append(self.high, np.array(priceArray[1]))

            self.low = self.low[1:]
            self.low = np.append(self.low, np.array(priceArray[2]))

            self.close = self.close[1:]
            self.close = np.append(self.close, np.array(priceArray[3]))
            
            # update time
            self.closeTime = self.closeTime[1:]
            self.closeTime = np.append(self.closeTime, np.array(priceArray[4]))
        except Exception as e:
            print("Generator Update Error -",str(e))
        
        # update macd 
        self.tick()

    def updateMACD(self):
        self.macd, self.macdsignal, self.macdhist  = talib.MACD(self.close, fastperiod=12, slowperiod=26, signalperiod=9)

    def tick(self):
        self.macd, self.macdsignal, self.macdhist  = talib.MACD(self.close, fastperiod=12, slowperiod=26, signalperiod=9)
        self.ema99 = talib.EMA(self.close, 99)
        self.ema25 = talib.EMA(self.close, 25)
        self.ema7 = talib.EMA(self.close, 7)
'''

class SimpleMacd:
    def __init__(self, binanceClient, symbol, lookback, interval):
        self.client = binanceClient
        self.symbol = symbol
        self.lookback = lookback
        self.interval = interval
    
    def generate(self, period=1):
        startTime = datetime.datetime.utcnow() - datetime.timedelta(hours=self.lookback)
        timestamp = startTime.timestamp()
        millisecondTimstamp = timestamp*1000
        
        klines = self.client.get_klines(symbol=self.symbol, interval=self.interval, startTime=int(millisecondTimstamp))
        
        closing = [float(k[4]) for k in klines]
        
        macd, signal, hist = self.macd(closing)
        
        periodIndex = (period + 1) * -1
        
        # returns lists
        l = list()
        
        for i in range(period):
            d = {
                "ema_short": self.ema(closing, 7)[periodIndex:-1][i], 
                "ema_medium": self.ema(closing, 25)[periodIndex:-1][i],
                "ema_long": self.ema(closing, 99)[periodIndex:-1][i],
                "macd": macd[periodIndex:-1][i],
                "signal": signal[periodIndex:-1][i],
                "closing":closing[periodIndex:-1][i]
            }
            l.append(d)
        
        return l
    
    def generateLatest(self):
        # returns float values
        res = self.generate(period=1)
        
        floatRes = dict()
        for k,v in res.items():
            floatRes[k] = v[0]
        
        return res, floatRes

    def ema(self, closing, period):
        return talib.EMA(np.array(closing), period)
    
    def macd(self, closing, fast=12, slow=26, signal=9):
        return talib.MACD(np.array(closing), fastperiod=fast, slowperiod=slow, signalperiod=signal)
    
    ## ws helpers
    def getOnMessage(self, signal, botState):
        def on_message(signal, botState, ws, message):
            msg = json.loads(message)
            
            eventTimeStamp = msg["E"]
            eventTime = datetime.datetime.fromtimestamp(eventTimeStamp/1000)
            print(eventTime.strftime("%m/%d/%Y - %H:%M:%S"))
            
            # print status and kline periodically
            if eventTime.second % 7 == 0:
                print("\n== Kline Price Update ==")
                pprint.pprint(msg['k']['c'])

                state = botState.getState()
                pprint.pprint(state)

            if msg["k"]["x"]:
                
                print("\n===== ACTION KLINE =====")

                klineStartTimeStamp = msg["k"]["x"]
                klineStartTime = datetime.datetime.fromtimestamp(klineStartTimeStamp/1000)
                print(klineStartTime.strftime("%m/%d/%Y - %H:%M:%S"))

                res = signal.generate(period=1)
                ## print kline 
                pprint.pprint(res[0])
                
                botState.receive(res[0])

            # place stop loss 
            botState.placeStopLossIfActiveOrderFilled()

        return partial(on_message, signal, botState)
    
    def getOnOpen(self):
        def on_open(ws):
            print("WS connection established for SimpleMacd Strategy")
            print("Last three candles:")

            res = self.generate(period=3)
            pprint.pprint(res)

        return on_open
    
    def getOnClose(self):
        def on_close(ws):
            print("WS connection closed for Simple Macd Strategy")
        
        return on_close

