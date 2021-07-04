import datetime

# some wrapper classes for binance websockets and api responses

class WsKline:
    # takes in a websocket payload on init -> https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-streams
    def __init__(self, ws_kline):
        self.eventTime=datetime.datetime.fromtimestamp( float(ws_kline['E'])/1000 ).strftime("%m-%d-%Y %H:%M:%S") 
        self.symbol=ws_kline['s']
        self.klineStartTime=datetime.datetime.fromtimestamp( float(ws_kline['k']['t'])/1000).strftime("%m-%d-%Y %H:%M:%S") 
        self.klineCloseTime=datetime.datetime.fromtimestamp( float(ws_kline['k']['c'])/1000).strftime("%m-%d-%Y %H:%M:%S") 
        self.interval=ws_kline['k']['i']
        self.openPrice=float(ws_kline['k']['o'])
        self.closePrice=float(ws_kline['k']['c'])
        self.highPrice=float(ws_kline['k']['h'])
        self.lowPrice=float(ws_kline['k']['l'])
        self.baseAssetVolume=float(ws_kline['k']['v'])
        self.numberOfTrades=int(ws_kline['k']['n'])
        self.klineClosed=ws_kline['k']['x']
        self.quoteAssetVolume=float(ws_kline['k']['q'])
        self.takerBaseAssetVolume=float(ws_kline['k']['V'])
        self.takerQuoteAssetVolume=float(ws_kline['k']['Q'])

    def toDict(self):
        d = dict()

        d['time'] = self.klineCloseTime
        d['open'] = self.openPrice
        d['high'] = self.highPrice
        d['low'] = self.lowPrice
        d['close'] = self.closePrice

        return d

