class MACDStateMachine:
    def __init__(self, account, pair, fundPercentage=1.0, riskTolerancePercentage=3, isTestNet=False):
        self.account = account
        # self.account.isTestNet=isTestNet
        self.funPercentage = fundPercentage # the amount of funs you are willing to put into trade 

        self.isTestNet = isTestNet
        self.pair = pair # trading pair
        
        # meta
        self.inPosition=False
        
        # long order variables
        self.activeOrderID = None

        # stop loss
        self.riskTolerancePercentage = riskTolerancePercentage
        self.stopLossOrderID = None
        self.stopLossOrderPlaced = False

        ## prices
        self.stopLossPrice = 0.0
        self.activeOrderPrice = 0.0
    
    # executed in ws.onMessage 15MIN interval
    def receive(self, wsPayload):
        
        '''
        wsPayload schema:
        {
            "ema_short": float,
            "ema_medium": float,
            "ema_long": float,
            "macd": float,
            "signal": float,
            "closing": float  # last candle closing price
        }
        '''
        if not self.inPosition:
            ## ENTRY TRADE LOGIC

            # 1. EMA are in ascension
            if (wsPayload['ema_short'] > wsPayload['ema_medium'] > wsPayload['ema_long']):
                # 2. MACD is in ascension
                if (wsPayload['macd'] > wsPayload['signal']):
                    print("ENTERING LONG POSITION")

                    ## MAKE TRADE
                    order = self.account.placeOrder(self.pair, fundPercentage=self.funPercentage, testNet=self.isTestNet)
                    
                    # set trailing stop loss price -> place when long order is filled
                    # self.stopLossPrice = order.price * float(100 - self.riskTolerancePercentage)

                    # save active order id
                    self.activeOrderID = order.orderID
                    
                    # update inposition status
                    self.inPosition = True

                    # update current price
                    self.activeOrderPrice = order.price

                    # id and if order is TestNet ORder
                    return self.activeOrderID, self.isTestNet 

            print("ENTRY REQ NOT MET - Trade rejected")
            return None, False
        
        else:
            # exit trade logic
            
            # A1. check active order status
            activeOrder = self.account.getOrder(self.activeOrderID, self.pair, testNet=self.isTestNet)
            
            ## WIP - if active order have not been filled since last 15 minute candle
            if activeOrder.status == "NEW":
                print("Active Order not filled since last 15MIN candle")
                
                '''
                If active order is not filled - no stop losses should be places
                '''
                
                # exit and wait for order to fill
                return self.activeOrderID, self.isTestNet

            # B1. Active order filled but stop loss is places - try placing stop loss
            if self.stopLossOrderPlaced is False:
                '''
                if not yet placed, place it. Even when the placeStopLossIfActiveOrderFilled will
                be called on every 2 second candle stick update. The likely hood of the stop loss being 
                placed by this method is extremely low.
                '''

                stopLossOrder, env = self.placeStopLossIfActiveOrderFilled()

            # B2. Active order filled AND stop loss places - check stop loss status to CLOSE TRADE or UPDATE STOP LOSS
            else:
                print("TRY TO UPDATE STOPLOSS - ID:", self.stopLossOrderID)
                stopLossOrder = self.account.getOrder(self.stopLossOrderID, self.pair, testNet=self.isTestNet)

                # if filled CLOSE TRADE
                if stopLossOrder.status == 'FILLED':
                    print("CLOSING TRADE")
                    print("ENTRY ORDER ID:", self.activeOrderID)
                    print("EXIT STOP LOSS ORDER ID:", self.stopLossOrderID)

                    # update status
                    self.inPosition = False
                    self.activeOrderPrice = 0.0
                    self.stopLossOrderPlaced = False
                    self.stopLossPrice = 0.0

                    return None, self.isTestNet
                
                else:
                    ## get current price and adjust stop loss
                    lastClosePrice = wsPayload['closing']
                    
                    print("Laste Close Price:", lastClosePrice)

                    ## get current stoploss order price
                    stopLossOrder = self.account.getOrder(self.stopLossOrderID, self.pair, self.isTestNet)
                    print("Current Stop Loss Order:", stopLossOrder)

                    newStopLossPrice = float(((100 - self.riskTolerancePercentage)/100) * float(lastClosePrice))
                    print("New Stop Loss:", newStopLossPrice)

                    # if new stop loss price is greater than existing stop loss order price - update
                    if newStopLossPrice > float(stopLossOrder.price):
                        print("UPDATING STOP LOSS")
                        print("Deleting sell order id:", self.stopLossOrderID)

                        # cancell Stoploss
                        oldStopLoss = self.account.cancelOrder(
                            self.stopLossOrderID,
                            self.pair,
                            self.isTestNet
                        )

                        print("StopLoss order id "+ str(self.stopLossOrderID) + " deleted")

                        # place updated order
                        print("Placing new StopLoss Order at price " + str(newStopLossPrice) + ".")
                        
                        newStopLossOrder = self.account.placeStopLossOrder(
                            activeOrder,
                            riskTolerancePercentage=self.riskTolerancePercentage,
                            testNet=self.isTestNet
                        )

                        # update status
                        self.stopLossOrderID = newStopLossOrder.orderID

                        return self.stopLossOrderID, self.isTestNet

    # conditionally place stop loss - executed in onMessage 2 second interval
    def placeStopLossIfActiveOrderFilled(self):
        # if in position but stoploss is not placed
        if self.inPosition and not self.stopLossOrderPlaced:
            print("CHECKING IF STOP LOSS IS PLACES")
            # check if activeOrder has been filled
            activeOrder = self.account.getOrder(self.activeOrderID, self.pair, testNet=self.isTestNet)
            # if active order filled - then place stop loss
            if activeOrder.status == 'FILLED':
                print("PLACING STOP LOSS")

                stopLossOrder = self.account.placeStopLossOrder(
                    activeOrder, 
                    riskTolerancePercentage = self.riskTolerancePercentage, 
                    testNet=self.isTestNet
                )
                

                # update stop loss Status
                self.stopLossOrderPlaced = True
                # update stop loss orderID
                self.stopLossOrderID = stopLossOrder.orderID
                # update stop loss price
                self.stopLossPrice = stopLossOrder.price

                return stopLossOrder, self.isTestNet

        return None, self.isTestNet
            
    ## get overall state of bot 
    def getState(self):
        d = dict()
        d['isTestNet'] = self.isTestNet
        d['tradingPair'] = self.pair
        d['inPosition'] = self.inPosition
        d['activeOrderID'] = self.activeOrderID
        d['stopLossOrderplaced'] = self.stopLossOrderPlaced
        d['stopLossOrderID'] = self.stopLossOrderID

        d['orderPrice'] = self.activeOrderPrice
        d['stopLossPrice'] = self.stopLossPrice

        # stoploss = self.account.getOrder(self.stopLossOrderID, self.pair, testNet=self.isTestNet)
        # order = self.account.getOrder(self.activeOrderID, self.pair, testNet=self.isTestNet)

        return d


'''
ETH TEST:
target 1%
risk tolerance 0.5%
'''

# class MACDTrade:
#     def __init__(self, botState):
