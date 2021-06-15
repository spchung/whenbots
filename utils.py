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

'''   
class Trade:
    def __init__(self):
        # entry
        self.entryTime = None
        self.positionType = None # enum ['LONG', 'SHORT']
        self.pair = None
        self.entryUSDTAmount = 0.0
        self.purchasedCoinAmount = 0.0
        
        # trade status
        self.isOpen = True
        
        # orders
        self.entryOrderID = None
        self.exitOrderID = None

        # exit
        self.exitUSDTAmount = 0.0
        self.exitTime = None
    
    @staticmethod
    def closedByStopLoss(order, stoploss):
        trade = Trade()
        trade.entryTime = order.time
        trade.positionType = 'LONG'
        trade.pair = order.pair
        trade.entryUSDTAmount = order.price
        trade.purchasedCoinAmount = order.executedQty
        trade.complete = True
        trade.exitUSDTAmount = stoploss.price
        trade.exitTime = stoploss.time
        return trade
    
    def toDict(self):

        d = dict()
        d['entryTime'] = self.entryTime
        d['positionType'] = self.positionType
        d['pair'] = self.pair
        d['entryUSDTAmount'] = self.entryUSDTAmount
        d['purchasedCoinAmount'] = self.purchasedCoinAmount
        d['complete'] = self.complete
        d['exitUSDTAmount'] = self.exitUSDTAmount
        d['exitTime'] = self.exitTime

        return d

class Order:
    def __init__(self, orderPayload):
        # take a binace place_order response as input
        
        self.isTestNet = False
        self.pair = orderPayload['symbol']
        self.orderID = orderPayload['orderId']
        self.price = orderPayload['price']
        self.origQty = orderPayload['origQty']
        self.executedQty = orderPayload['executedQty']
        self.side = orderPayload['side']
        self.status = orderPayload['status'] # enum ['NEW', 'FILLED', 'CANCELED']

        if 'time' in orderPayload:
            self.time = orderPayload['time']

        if 'transactTime' in orderPayload:
            self.time = orderPayload['transactTime']

    def toDict(self):
        d = dict()
        d['pair'] = self.pair
        d['orderID'] = self.orderID
        d['price'] = self.price
        d['origQty'] = self.origQty
        d['executedQty'] = self.executedQty
        d['side'] = self.side
        d['time'] = self.time
        d['status'] = self.status

        return d 
    
    # update self - check if filled and if adjustment is required
    def update(self, orderID):
        pass
'''