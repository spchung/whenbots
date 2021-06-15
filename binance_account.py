import uuid
import pprint
import config
from decimal import Decimal
from datetime import datetime
from binance.client import Client
import binance.enums as binanceEnums

class BinanceAccount:
    def __init__(self, client, symbol, fundAmount=float('inf'), fundPercentage=0.1):
        self.client = client
        self.symbol = symbol

        # gather symbol Order Filters
        res = self.client.get_symbol_info(symbol)
        if res is None:
            raise Exception("Invalid trading symbol.")

        self.extractFilters(res)

        # tade logs
        self.trades = list() # list of all trades
        self.currentOpenTrade = None
        self.USDTAmount = None
        
    # extract symbol info into instance variables
    def extractFilters(self, symbol_info):
        
        # parse filters
        filters = dict()
        for filter in symbol_info['filters']:
            key = filter['filterType']
            del filter['filterType']
            filters[key] = filter
        
        self.filters = filters

    ## order validator
    def validateMarketOrder(self, quoteAsset, quoteAssetAmount, baseAssetPrice, quantity, testNet=False):
        minNotiational = float(self.filters['MIN_NOTIONAL']['minNotional'])
        minLotSize = float(self.filters['LOT_SIZE']['minQty'])
        maxLotSize = float(self.filters['LOT_SIZE']['maxQty'])
        stepSize = self.filters['LOT_SIZE']['stepSize']

        # 1. check if quote asset is valid and enough
        free, locked = self.getAssetBalance(quoteAsset, testNet=testNet)
        
        print("FREE:", free)

        if free is None:
            print("INVALID QUOTA ASSET")
            return False

        if free < quoteAssetAmount:
            # insufficient amount
            print("INSUFFICIENT QUOTA ASSET BALANCE")
            return False

        # 2. check notional
        notional = quantity * baseAssetPrice
        if not notional > minNotiational:
            print("TOTAL VALUE BELOW MIN ALLOWED - INSUFFICIENT NOTIONAL AMOUNT")
            return False
        
        # 3. check quantity
        if not (minLotSize < quantity < maxLotSize):
            print("INVALID QUANTITY")
            return False
        
        # 4. check quantity percision
        print("STEPSIZE:", stepSize)
        stepDecimalPlaces = abs(Decimal(stepSize).as_tuple().exponent)
        quantityDecimalPlaces = abs(Decimal(str(quantity)).as_tuple().exponent)

        if  quantityDecimalPlaces > stepDecimalPlaces:
            print("INVALID QUANTITY DECIMAL POINT PERCISION")
            return False
        
        return True

    # helpers
    def roundQuantity(self, quantity):
        stepSize = float(self.filters['LOT_SIZE']['stepSize'])
        
        if not stepSize == 0.0:
            c = 0
            while stepSize < 1:
                stepSize*=10
                c += 1
        
            return round(quantity, c)
        return quantity

    # account Status
    def getAssetBalance(self, asset, testNet=False):

        client = self.client

        if testNet:
            client = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)

        res = client.get_asset_balance(asset=asset)

        if res is None:
            return None, None
        
        return float(res['free']), float(res['locked'])

    ## order placing
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
                
                return Order.fromOrderPlacement(orderRes)
            
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
            return Order.fromOrderPlacement(testNetStopLossOrder)

        return order

        # except Exception as e:
        #     raise Exception(f"Place Stoploss in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    # market order
    def placeMarketBuyOrder(self, quoteAsset, quoteAssetAmount, baseAssetPrice, testNet=False):
        
        # check if funds are sufficient
        client = self.client
        if testNet:
            client = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            
        # derive quantity
        quantity = quoteAssetAmount/baseAssetPrice

        # order validation
        quantity = self.roundQuantity(quantity)

        valid = self.validateMarketOrder(quoteAsset, quoteAssetAmount, baseAssetPrice, quantity, testNet=testNet)

        if not valid:
            return None

        order = client.order_market_buy(
            symbol=self.symbol,
            quantity=quantity
        )
        
        return Order.fromOrderPlacement(order)

    def placeMarketStopLoss(self, order, testNet=False):
        client = self.client

        if testNet:
            client = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)

        quantity = self.roundQuantity(order.executedQty)

        # valid = self.validateMarketOrder(quoteAsset, quoteAssetAmount, baseAssetPrice, quantity, testNet=testNet)

        stopOrder = client.order_market_sell(
            symbol=self.symbol,
            quantity=quantity
        )
        
        return Order.fromOrderPlacement(stopOrder)
    
    ## Trade 
    def openTrade(self, order):
        
        trade = Trade()
        trade.pair = order.pair
        trade.entryTime = order.time
        trade.positionType = 'LONG'
        trade.entryUSDTAmount = order.getQuoteAmount()
        trade.purchasedCoinAmount = order.executedQty
        trade.openOrderID = order.orderID
        trade.complete = False

        self.currentOpenTrade = trade

        return trade
    
    def closeTrade(self, order):

        trade = self.currentOpenTrade
        trade.complete = True
        trade.exitUSDTAmount = order.getQuotaAmount()
        trade.exitTime = order.time

        # update account amount
        self.USDTAmount = trade.exitUSDTAmount
        
        # append to closed trades
        self.closedTrades.append(trade)

        return self.USDTAmount
    
    # order status
    def getOrder(self, orderId, tradingPair, testNet=False):
        try:
            if not testNet:
                return Order.fromGetOrder(self.client.get_order(symbol=tradingPair, orderId=int(orderId)))
            
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            return Order.fromGetOrder(testNetClient.get_order(symbol=tradingPair, orderId=int(orderId)))

        except Exception as e:
            raise Exception(f"Get Order in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    def cancelOrder(self, orderId, tradingPair, testNet=False):
        try:
            if not testNet:
                return Order.fromGetOrder(self.client.cancel_order(symbol=tradingPair, orderId=orderId))
            
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            return Order.fromGetOrder(testNetClient.cancel_order(symbol=tradingPair, orderId=orderId))
        except Exception as e:
            raise Exception(f"Cancel Order in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    def getAllOpenOrders(self, tradingPair, testNet=False):
        if testNet:
            testNetClient = Client.fromGetOrder(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            orders = testNetClient.get_open_orders(symbol=tradingPair)
            
            res = list()
            for order in orders:
                order = Order(order)
                res.append(order.toDict())
            
            return res, testNet

        else:
            print("WIP - Purge All open orders")
            pass



## Trade
class Trade:
    def __init__(self):
        self.entryTime = None
        self.positionType = None # enum ['LONG', 'SHORT']
        self.pair = None
        self.entryUSDTAmount = 0.0
        self.purchasedCoinAmount = 0.0
        
        # orders
        self.openOrderID = None
        self.closeOrderID = None

        # exit
        self.complete = False
        self.exitUSDTAmount = 0.0
        self.exitTime = None
    
    def toDict(self):
        d = dict()
        d['entryTime'] = self.entryTime
        d['positionType'] = self.positionType
        d['pair'] = self.pair
        d['entryUSDTAmount'] = self.entryUSDTAmount
        d['purchasedCoinAmount'] = self.purchasedCoinAmount
        d['openOrderID'] = self.openOrderID
        d['closeOrderID'] = self.closeOrderID
        d['complete'] = self.complete
        d['exitUSDTAmount'] = self.exitUSDTAmount
        d['exitTime'] = self.exitTime

## order v2 -> derive price from fills
class Order:
    def __init__(self):
        self.originalPayload = None
        self.isTestNet=False
        self.pair = None
        self.orderID = None
        self.origQty = None
        self.executedQty = None
        self.side = None 
        self.fills = None
        self.price = None
        self.time = None

    @staticmethod
    def fromOrderPlacement(orderPayload):
        order = Order()
        order.originalPayload = orderPayload
        order.isTestNet = False
        order.pair = orderPayload['symbol']
        order.orderID = orderPayload['orderId']
        order.origQty = float(orderPayload['origQty'])
        order.executedQty = float(orderPayload['executedQty'])
        order.side = orderPayload['side']
        order.status = orderPayload['status'] # enum ['NEW', 'FILLED', 'CANCELED']

        # derive avg price
        order.fills = orderPayload['fills']

        totalCost = 0.0
        totalQuantity = 0.0
        for fill in orderPayload['fills']:
            cost = float(fill['price']) * float(fill['qty'])

            totalCost += cost
            totalQuantity += float(fill['qty'])

        avg_price = totalCost/totalQuantity

        order.price = avg_price
        
        if 'time' in orderPayload:
            order.time = orderPayload['time']

        if 'transactTime' in orderPayload:
            order.time = orderPayload['transactTime']
        
        return order

    @staticmethod
    def fromGetOrder(orderPayload):
        order = Order()
        order.originalPayload = orderPayload
        order.isTestNet = False
        order.pair = orderPayload['symbol']
        order.orderID = orderPayload['orderId']
        order.origQty = float(orderPayload['origQty'])
        order.executedQty = float(orderPayload['executedQty'])
        order.side = orderPayload['side']
        order.status = orderPayload['status'] # enum ['NEW', 'FILLED', 'CANCELED'

        # derive price from
        quoteQty = float(orderPayload['cummulativeQuoteQty'])
        executedQty = float(orderPayload['executedQty'])
        order.price = quoteQty/executedQty
        
        if 'time' in orderPayload:
            order.time = orderPayload['time']

        if 'transactTime' in orderPayload:
            order.time = orderPayload['transactTime']
        
        return order

    def toDict(self):
        d = dict()  
        d['pair'] = self.pair
        d['orderID'] = self.orderID
        d['price'] = self.price
        d['origQty'] = self.origQty
        d['executedQty'] = self.executedQty
        d['side'] = self.side
        d['time'] = datetime.fromtimestamp(self.time/1000).strftime("%m-%d-%Y %H:%M:%S")
        d['status'] = self.status

        return d

    # quota amount 
    def getQuoteAmount(self):
        return self.executedQty * self.price

## backTest account
class BackTestAccount:
    def __init__(self):
        self.inPosition=False
        
        self.openTrades=list()

        self.closedTrades=list()
        self.currentOpenTrade=None

        # ACCOUNT FUND
        self.USDTAmount = 1000

    # no smart order placing system -> place at kline closing price
    def placeSimpleOrder(self, tradingPair, price, side='BUY', testNet=False):
        order = TestOrder()
        order.pair = tradingPair
        order.orderID = uuid.uuid4()
        order.USDTAmount = self.USDTAmount
        order.executedQty = self.USDTAmount/price
        order.origQty = self.USDTAmount/price
        order.price = price
        order.side = side
        order.time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        order.status = 'FILLED'

        return order
    
    def openTrade(self, order):
        trade = TestTrade()
        trade.pair = order.pair
        trade.entryTime = order.time
        trade.positionType = 'LONG'
        trade.entryUSDTAmount = order.USDTAmount
        trade.purchasedCoinAmount = order.executedQty
        trade.openOrderID = order.orderID
        trade.complete = False

        self.currentOpenTrade = trade

        return trade

    def closeTrade(self, order):
        trade = self.currentOpenTrade
        trade.complete = True
        trade.exitUSDTAmount = order.origQty*order.price
        trade.exitTime = order.time

        # update account amount
        self.USDTAmount = trade.exitUSDTAmount
        
        # append to closed trades
        self.closedTrades.append(trade)

class TestOrder:
    def __init__(self):
        self.isTestNet = None
        self.pair = None 
        self.orderID = None
        self.price = None 
        self.USDTAmount = None
        self.origQty = None
        self.executedQty = None
        self.side = None
        self.time = None
        self.status = None
    
    def toDict(self):
        d = dict()
        d['pair'] = self.pair
        d['orderID'] = self.orderID
        d['price'] = self.price
        d['USDTAmount'] = self.USDTAmount
        d['origQty'] = self.origQty
        d['executedQty'] = self.executedQty
        d['side'] = self.side
        d['status'] = self.status
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
        
        # orders
        self.openOrderID = None
        self.closeOrderID = None

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
'''