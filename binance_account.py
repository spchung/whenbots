import config
from binance.client import Client
import binance.enums as binanceEnums

class BinanceAccount:
    def __init__(self, client, baseCurrency, fundAmount=float('inf'), fundPercentage=0.1):
        self.client = client

        ## state
        self.inPosition=False
        self.positionType=None # enum ['long', 'short']
        # self.fundPercentage=fundPercentage
        self.lastTrade=None # trade object

        ## wallet
        self.usdtFund = min(float(self.client.get_asset_balance(asset='USDT')['free']), float(fundAmount))
    
    def placeOrder(self, tradingPair, fundPercentage=1.0, testNet=False):
        '''
        fundPercentage - the percentage of the available funds to put in this trade
        '''
        try:
            if testNet:
                print("IN TEST")
                ## test mode
                testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
                
                ## use last 5 minutes avg price as price
                res = self.client.get_avg_price(symbol=tradingPair)
                price = float(res['price'])

                print("PRICE:", price)

                # calculate buy quantity
                quantity = (self.usdtFund*fundPercentage)/price # alloted funds / current coin price

                print("Quantity:",quantity)

                ## place order on testNet

                print("inputs:", float(round(quantity,2)), float( max(round(price,5),0.01) ))

                orderRes = testNetClient.create_order(
                    symbol=tradingPair,
                    side=binanceEnums.SIDE_BUY,
                    type=binanceEnums.ORDER_TYPE_LIMIT,
                    timeInForce=binanceEnums.TIME_IN_FORCE_GTC,
                    quantity=float( max(round(quantity,5), 0.01)),
                    price=float(round(price,2))
                )
                
                print("PLACE ORDER RES:", orderRes)
                
                # get order 
                # order = testNetClient.get_order(symbol=tradingPair, orderId=orderRes['orderId'])
                
                return Order(orderRes)
            
            else:
                # production mode - placing valid orders to Binance
                print("TRYING TO PLACE REAL ORDER.")
                pass

        except Exception as e:
            raise Exception(f"Place Long Order in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    def placeStopLossOrder(self, order, riskTolerancePercentage=3, testNet=False):
        '''
        order - the long order which this stop loss is trying to risk manage
        riskTolerancePercentage - the percentage decrease from the original order's entry price you are willing to take
        '''
        # try:
            # stopLossPrice = order.price * float( (100 - riskTolerancePercentage)/100 )
        stopLossPrice = float(((100 - riskTolerancePercentage)/100) * float(order.price))
        quantity = float(order.executedQty)
        tradingPair = order.pair

        if testNet:
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)

            testNetStopLossOrder = testNetClient.create_order(
                symbol=tradingPair,
                side=binanceEnums.SIDE_SELL,
                type=binanceEnums.ORDER_TYPE_LIMIT,
                timeInForce=binanceEnums.TIME_IN_FORCE_GTC,
                quantity=float( max(round(quantity,5), 0.01)),
                price=float(round(stopLossPrice,2))
            )
            return Order(testNetStopLossOrder)

        return Order(order)

        # except Exception as e:
        #     raise Exception(f"Place Stoploss in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    def getOrder(self, orderId, tradingPair, testNet=False):
        try:
            if not testNet:
                return Order(self.client.get_order(symbol=tradingPair, orderId=int(orderId)))
            
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            return Order(testNetClient.get_order(symbol=tradingPair, orderId=int(orderId)))
        except Exception as e:
            raise Exception(f"Get Order in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    def cancelOrder(self, orderId, tradingPair, testNet=False):
        try:
            if not testNet:
                return Order(self.client.cancel_order(symbol=tradingPair, orderId=orderId))
            
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            return Order(testNetClient.cancel_order(symbol=tradingPair, orderId=orderId))
        except Exception as e:
            raise Exception(f"Cancel Order in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    def getAllOpenOrders(self, tradingPair, testNet=False):
        if testNet:
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            orders = testNetClient.get_open_orders(symbol=tradingPair)
            
            res = list()
            for order in orders:
                order = Order(order)
                res.append(order.toDict())
            
            return res, testNet

        else:
            print("WIP - Purge All open orders")
            pass

class Order:
    def __init__(self, orderPayload):
        '''
        take a binace place_order response as input
        '''
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

class Trade:
    def __init__(self):
        # entry
        self.entryTime = None
        self.positionType = None # enum ['LONG', 'SHORT']
        self.pair = None
        self.entryUSDTAmount = 0.0
        self.purchasedCoinAmount = 0.0
        
        # exit
        self.complete = False
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


    