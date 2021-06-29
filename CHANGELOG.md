# Change Log
All notable changes to this project will be documented in this file.

## [0.0.2] - 2021-06-07
- Switch main kline loop from 15MIN to 5MIN
- klinie_lookback_config.py

## [0.0.3] - 2021-06-15
- WS kline data class
- Simple MCAD Generator now produces data in pandas.DataFrame
- New SimpleMacd class methods to derive TA signals from dataframe
- Added Market Order methods to BinanceAccount
- renamed BotSate main trading logic methods to `intervalLogic` and `continuousLogic`
- Update Order class and Trade class 
- Added self.trades to Account to keep track of closed Trades
- Added `resource.md` for Binance or Binance related technical articles
- Stop loss placing moved into main `intervalLogic` and uses Market Order
- Stop loss order is not placed until stop loss price level is violated

## [0.0.4] - 2021-06-16
- pymongo 
- MongoDB instance
- Market stop loss order placing

## [0.0.5] - 2021-06-19
- mongodb database_manager singleton class
- Signal generator now dynamically generates TA indicators by given input
- `tradingPair` variable name depricated. Using `symbol` as per Binance convention
- `Order` and `Trade` classes seperated from individual files and connects to mongodb cluster
- SELECT, WRITE, and QUERY operations for class `Order` and `Trade`

## [0.0.6] - 2021-06-29
- RunSettings class and mongo collection
- Get bot and websocket variables dynamically from RunSettings instead for static variables
- Depricated `SimpleMacd` singal_generator class and consolidate into one standard class

## [0.0.7] - ****-**-**
- Smart Order Module