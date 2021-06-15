import json
import pprint
import talib
import datetime
import numpy as np
import pandas as pd

from functools import partial

from utils import WsKline

class SimpleMacd:
    def __init__(self, binanceClient, symbol, lookback, interval):
        self.client = binanceClient
        self.symbol = symbol
        self.lookback = lookback
        self.interval = interval
    
    ## klines to gemini dataframe
    def pricesDataFrame(self):
        '''
        index, date, high, low, open, close
        '''
        startTime = datetime.datetime.utcnow() - datetime.timedelta(hours=self.lookback)
        timestamp = startTime.timestamp()
        millisecondTimstamp = timestamp*1000
        
        klines = self.client.get_klines(symbol=self.symbol, interval=self.interval, startTime=int(millisecondTimstamp))
        
        df =list()

        for kline in klines:
            l = list()

            # starttime
            l.append( datetime.datetime.fromtimestamp(kline[0]/1000).strftime("%m-%d-%Y %H:%M:%S") )
            
            # high
            l.append(float(kline[2]))

            # low
            l.append(float(kline[3]))

            # open 
            l.append(float(kline[1]))

            # close 
            l.append(float(kline[4]))

            df.append(l)
        
        df = pd.DataFrame(df, index=list(range(0, len(df))), columns=['date', 'high', 'low', 'open', 'close'])

        return df
    
    ## get ema from DataFrame 
    def EMAS(self, df, short=7, mid=25, long=99):
        closePrice = np.array(df['close'])

        shortEMA = talib.EMA(closePrice, short)
        mediumEMA = talib.EMA(closePrice, mid)
        longEMA = talib.EMA(closePrice, long)

        return shortEMA, mediumEMA, longEMA
    
    ## get macd form DataFrame
    def MACD(self, df, fast=12, slow=26, signal=9):
        return talib.MACD(np.array(df['close']), fastperiod=fast, slowperiod=slow, signalperiod=signal)

    ## ws helpers
    def getOnMessage(self, botState):
        def on_message(self, botState, ws, message):

            # this kline to WsKline instance
            try:                
                wsKline = WsKline(json.loads(message))

                # log time stamp
                print(wsKline.eventTime, "-", wsKline.closePrice)
            
                # print status and kline periodically
                if datetime.datetime.strptime(wsKline.eventTime, "%m-%d-%Y %H:%M:%S").second % 7 == 0:
                    print("\n== Kline Price Update ==")
                    pprint.pprint(wsKline.closePrice)

                    state = botState.getState()
                    pprint.pprint(state)

                if wsKline.klineClosed:
                    
                    # log
                    print("\n===== ACTION KLINE - "+ wsKline.interval +" =====")
                    print(wsKline.klineStartTime)

                    # get data
                    df = self.pricesDataFrame()
                    ema_short, ema_medium, ema_long = self.EMAS(df)
                    macd, signal, hist = self.MACD(df)

                    ## main loop trading logic
                    # use -2 index because -1 is the currently opened candle
                    botState.intervalLogic(ema_short[-2], ema_medium[-2], ema_long[-2], macd[-2], signal[-2], hist[-2], wsKline)

                # check if stop loss reached
                botState.continuousLogic(wsKline)

            except Exception as e:
                print(str(e))

        return partial(on_message, self, botState)
    
    def getOnOpen(self):
        def on_open(ws):
            print("WS connection established for SimpleMacd Strategy")
            print("Last three candles:")

            df = self.pricesDataFrame()
            length = len(df)
            pprint.pprint(df[length-3:])
            print("\n")

        return on_open
    
    def getOnClose(self):
        def on_close(ws):
            print("WS connection closed for Simple Macd Strategy")
        
        return on_close

