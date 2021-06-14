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

## [0.0.4] - ****-**-**
- Smart Order Module