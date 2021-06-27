from os import EX_CANTCREAT
import sys
import pprint
from models.order import Order
from models.trade import Trade

class MACDStateMachine:
    def __init__(self, account, symbol, riskTolerancePercentage=10, quoteFundAmount=1000 ,isTestNet=False):
        # self.account.isTestNet=isTestNet
        self.account = account

        # fund 
        self.quoteFundAmount = quoteFundAmount

        self.isTestNet = isTestNet
        self.symbol = symbol # trading symbol
        
        # meta
        self.inPosition=False
        
        # active trade
        self.activeTrade = None

        # long order variables
        self.activeOrder = None
        self.activeOrderID = None

        # stop loss
        self.riskTolerancePercentage = riskTolerancePercentage
        self.stopLossOrderID = None
        self.stopLossOrderPlaced = False

        ## prices
        self.stopLossPrice = None
        self.activeOrderPrice = None
    
    ## reset botstate -> after closing a trade
    def reset(self):
        self.inPosition = False
        self.activeOrder = None
        self.activeOrderID = None
        self.activeOrderPrice = None
        self.stopLossPrice = None
        self.stopLossOrderID = None

    ## get overall state of bot 
    def getState(self):
        d = dict()
        d['isTestNet'] = self.isTestNet
        d['symbol'] = self.symbol
        d['inPosition'] = self.inPosition
        d['activeOrderID'] = self.activeOrderID
        d['stopLossOrderplaced'] = self.stopLossOrderPlaced
        d['stopLossOrderID'] = self.stopLossOrderID

        d['orderPrice'] = self.activeOrderPrice
        d['stopLossPrice'] = self.stopLossPrice

        # stoploss = self.account.getOrder(self.stopLossOrderID, self.pair, testNet=self.isTestNet)
        # order = self.account.getOrder(self.activeOrderID, self.pair, testNet=self.isTestNet)

        d['riskTolerancePercentage'] = self.riskTolerancePercentage
        d['trades'] = [ trade.toDict() for trade in self.account.trades]

        return d

    ## INTERVAL LOGIC - whenever a candle officially closes 
    def intervalLogic(self, wsKline, **kwargs):
        '''
        MAKE TRADES
        '''
        # input

        if not 'EMAS' in kwargs:
            raise Exception("MACDStateMachine.intervalLogic requires a EMA indicator object.")

        if not 'MACD' in kwargs:
            raise Exception("MACDStateMachine.intervalLogic requires a MACD indicator object.")
        
        # extract EMA
        emaShort, emaMedium, emaLong = kwargs['EMAS']

        #extract MACD 
        macd, signal, hist = kwargs['MACD']

        # log items
        ordePlaced = False

        try:
            if not self.inPosition:
                # 1. EMA are in ascension
                # if emaShort > emaMedium > emaLong:
                if emaShort > emaMedium:
                    # 2. MACD is in ascension
                    if macd > signal:
                        
                        # MAKE ORDER
                        print("MAKE TRADE at Kline:")
                        pprint.pprint(wsKline.toDict())

                        # order = self.account.placeOrder(self.pair, fundPercentage=self.funPercentage, testNet=self.isTestNet)
                        order = self.account.placeMarketBuyOrder(
                            "USDT",
                            self.quoteFundAmount,
                            wsKline.closePrice,
                            self.isTestNet
                        )

                        trade = self.account.openTrade(order)
                        self.activeTrade = Trade.insert(trade)

                        # active order object
                        self.activeOrder = order

                        # update current price
                        self.activeOrderPrice = order.price

                        # Calculate stop loss price
                        self.stopLossPrice = self.activeOrderPrice * float((100 - self.riskTolerancePercentage)/100)

                        # save active order id
                        self.activeOrderID = order.orderID
                        
                        # update inposition status
                        self.inPosition = True

                        ## log state
                        pprint.pprint(self.getState())

                        # id and if order is TestNet ORder
                        return self.activeOrderID, self.isTestNet
            else:
                if self.inPosition:
                    
                    currStopLoss = wsKline.closePrice * float((100-self.riskTolerancePercentage)/100)
                    
                    print("new stop loss:", currStopLoss)
                    
                    if currStopLoss > self.stopLossPrice:

                        # update stopLoss price
                        self.stopLossPrice = currStopLoss

                        print("Updated Stop Loss -", self.stopLossPrice)

                    if wsKline.closePrice < self.stopLossPrice:

                        # sell
                        stopLossOrder = self.account.placeMarketStopLoss(self.activeOrder)

                        print("Closing Trade")
                        print("stopLossOrder:", stopLossOrder.toDict())

                        trade = self.account.closeTrade(stopLossOrder, self.activeTrade)
                        trade = Trade.update(trade)

                        # realigh fund amount 
                        self.quoteFundAmount = trade.exitUSDTAmount

                        # reset bot state
                        self.reset()
        
        except Exception as e:
            print(str(e))

    ## CONSTANT LOGIC - run on each ws update (every 2 seconds)
    def continuousLogic(self, wsKline):
        '''
        Track order fill progress and cancel/adjust orders according to moving price
        '''
        pass

    ## back testing
    def backTestIntervalLogic(self, *args):
        '''
        MAKE TRADES
        '''
        # input
        emaShort, emaMedium, emaLong, macd, signal, hist, wsKline = args
        
        # log items
        ordePlaced = False
        
        if not self.inPosition:
            # 1. EMA are in ascension
            if emaShort > emaMedium > emaLong:
                # 2. MACD is in ascension
                if macd > signal:
                    
                    # MAKE ORDER 
                    order = self.account.placeSimpleOrder(
                        self.symbol, 
                        wsKline.closePrice, 
                        side='BUY', 
                        testNet=self.isTestNet
                    )

                    openedTrade = self.openTrade(order)

                    # Calculate stop loss price
                    self.stopLossPrice = order.price * float(100 - self.riskTolerancePercentage)

                    # save active order id
                    self.activeOrderID = order.orderID
                    
                    # update inposition status
                    self.inPosition = True

                    # update current price
                    self.activeOrderPrice = order.price

                    # id and if order is TestNet ORder
                    return self.activeOrderID, self.isTestNet
        # stop loss
        else:  
            if wsKline.closePrice < self.stopLossPrice:
                stopLossOrder = self.account.placeSimpleOrder(self.pair, wsKline.closePrice, side='SELL')
                closedTrade = self.account.closeTrade(stopLossOrder)

