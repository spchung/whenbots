import json
import pprint
import talib
import datetime
import numpy as np
import pandas as pd

from functools import partial

from utils import WsKline

class SignalGenerator:
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
    def EMAS(self, df, short=7, mid=25, long=99, period=1):
        closePrice = np.array(df['close'])

        shortEMA = talib.EMA(closePrice, short)
        mediumEMA = talib.EMA(closePrice, mid)
        longEMA = talib.EMA(closePrice, long)


        start = -1 - period
        return (shortEMA[start:-1], mediumEMA[start:-1], longEMA[start:-1])
    
    ## get macd form DataFrame
    def MACD(self, df, fast=12, slow=26, signal=9, period=1):
        macd, signal, hist =talib.MACD(np.array(df['close']), fastperiod=fast, slowperiod=slow, signalperiod=signal)

        start = -1 - period
        return (macd[start:-1], signal[start:-1], hist[start:-1])

    ## GENERATE INDICATORS - returns last n number of indicators
    def generateIndicatorsPeriod(self, indicators, period=1):
        # generate list of indicators according to input

        # base df 
        df = self.pricesDataFrame()

        res = list()
        for indicator in indicators:
            
            if indicator == "MACD":
                res.append(self.MACD(df, period=period))
            
            elif indicator == "EMAS":
                res.append(self.EMAS(df, period=period))

        return res
    
    # return list of indicators generated from the last completed kline
    def generateIndicatorsLatest(self, indicators):
        # base df 
        df = self.pricesDataFrame()

        res = dict()
        for indicator in indicators:
            
            if indicator == "MACD":
                res0, res1, res2 = self.MACD(df, period=1)
                res[indicator] = (res0[0], res1[0], res2[0])
            
            elif indicator == "EMAS":
                res0, res1, res2 = self.EMAS(df, period=1)
                res[indicator] = (res0[0], res1[0], res2[0])

        return res

    ## ws helpers
    def getOnMessage(self, botState, indicators=['EMAS']):
        def on_message(self, botState, ws, message):

            # this kline to WsKline instance
            try:                
                wsKline = WsKline(json.loads(message))

                # log time stamp
                print(wsKline.eventTime, "-", wsKline.closePrice, flush=True)
            
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

                    # # get data
                    indiactorDict = self.generateIndicatorsLatest(indicators)
                    pprint.pprint(indiactorDict)

                    ## main loop trading logic
                    # use -2 index because -1 is the currently opened candle
                    botState.intervalLogic(wsKline, **indiactorDict)

                # check if stop loss reached
                botState.continuousLogic(wsKline)

            except Exception as e:
                print(str(e))

        return partial(on_message, self, botState)
    
    def getOnOpen(self):
        def on_open(ws):
            print("WS connection established\n", flush=True)

        return on_open
    
    def getOnClose(self):
        def on_close(ws):
            print("WS connection closed for Simple Macd Strategy")
        
        return on_close

