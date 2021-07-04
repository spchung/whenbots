import uuid
import pprint
import config
from decimal import Decimal
from datetime import datetime
from binance.client import Client
import binance.enums as binanceEnums

from models.order import Order
from models.trade import Trade

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
        # self.USDTAmount = None

    # preflight checks -> check if quote amount is enough and run setting is viable
    def preflight(self, runSetting, quoteFundAmount):
        # 1. make sure quote amoung is enough
        quoteAsset = runSetting.quoteAsset
        res = self.client.get_asset_balance(asset=quoteAsset)
        accountQuoteAmount = float(res['free'])

        if not accountQuoteAmount > quoteFundAmount:
            raise Exception("Insufficient "+ quoteAsset+ " balance.")
        
        return True
        
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
    def placeOrder(self, symbol, fundPercentage=1.0, testNet=False):
        '''
        fundPercentage - the percentage of the available funds to put in this trade
        '''
        try:
            if testNet:
                print("IN TEST")
                ## test mode
                testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
                
                ## use last 5 minutes avg price as price
                res = self.client.get_avg_price(symbol=symbol)
                price = float(res['price'])

                print("PRICE:", price)

                # calculate buy quantity
                quantity = (self.usdtFund*fundPercentage)/price # alloted funds / current coin price

                print("Quantity:",quantity)

                ## place order on testNet
                print("inputs:", float(round(quantity,2)), float( max(round(price,5),0.01) ))

                orderRes = testNetClient.create_order(
                    symbol=symbol,
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
        symbol = order.symbol

        if testNet:
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)

            testNetStopLossOrder = testNetClient.create_order(
                symbol=symbol,
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
        trade.symbol = order.symbol
        trade.entryTime = order.time
        trade.positionType = 'LONG'
        trade.entryUSDTAmount = order.cummulativeQuoteQty
        trade.purchasedCoinAmount = order.executedQty
        trade.openOrderID = order.orderID
        trade.complete = False

        self.currentOpenTrade = trade

        return trade
    
    def closeTrade(self, order, trade):

        trade.complete = True
        trade.exitUSDTAmount = order.cummulativeQuoteQty
        trade.exitTime = order.time
        trade.closeOrderID = order.orderID
        
        return trade
    
    # order status
    def getOrder(self, orderId, symbol, testNet=False):
        try:
            if not testNet:
                return Order.fromGetOrder(self.client.get_order(symbol=symbol, orderId=int(orderId)))
            
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            return Order.fromGetOrder(testNetClient.get_order(symbol=symbol, orderId=int(orderId)))

        except Exception as e:
            raise Exception(f"Get Order in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    def cancelOrder(self, orderId, symbol, testNet=False):
        try:
            if not testNet:
                return Order.fromGetOrder(self.client.cancel_order(symbol=symbol, orderId=orderId))
            
            testNetClient = Client(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
            return Order.fromGetOrder(testNetClient.cancel_order(symbol=symbol, orderId=orderId))
        except Exception as e:
            raise Exception(f"Cancel Order in { 'TESTNET' if testNet else 'PRODUCTION' } failed.\nMSG:{str(e)}")

    def queryOrder(self, symbol, testNet=False):
        
        client = self.client

        if testNet:
            client = Client.fromGetOrder(config.TEST_API_KEY, config.TEST_API_SECRET, testnet=True)
        
        orders = client.get_all_orders(symbol=symbol)
        
        res = list()
        for order in orders:
            order = Order.fromGetOrder(order)
            res.append(order)
        
        return res
