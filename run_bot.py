import config
import datetime
import websocket
import kline_lookback_config
from binance.client import Client
from signal_generators import SignalGenerator
from base_strategy import MACDStateMachine
from binance_account import BinanceAccount
from models.run_setting import RunSetting
from models.run import Run

import time
import sys, getopt

# get arguments from command line

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "quoteFundAmount=", "runSettingId=", "resume"])
except getopt.GetoptError as e:
    raise Exception(str(e))
    sys.exit(2)

## ========= IMPORTANT VARS ===========
quoteFundAmount = None # TEMP - how much the bot is going to trade
runSettingId = "60db2ea06bc049f8904e560d" # general settings of a run
resumeRunIfAny = False # if there is an unfinished run - resume

for o, v in opts:
    if o == "--quoteFundAmount":
        try:
            quoteFundAmount = int(v)
        except Exception as e:
            raise Exception("Quote Fund Amount must be an integer or floating point value.")
        
    elif o  == "--runSettingId":
        runSettingId = str(v)
        setting = RunSetting.get(str(v))
        if setting is None:
            raise Exception("Run Setting with ID " + str(v)+ " not found.")
    
    elif o == "--resume":
        resumeRunIfAny = True
    
    elif o == "--help":
        print("HELP MESSAGE", flush=True)
        sys.exit(2)

    else:
        assert False, "Unhandled option " + str(o)

## API_KEY
api_key = config.API_KEY
api_secret = config.API_SECRET

# search for any if resumeRun is enabled
inturruptedRun = None
if resumeRunIfAny:
    runs = Run.query(limit=1, end=None)
    if len(runs) > 0: 
        inturruptedRun = runs[0]

# start fresh
if inturruptedRun is None:
    # get run settings
    runSetting = RunSetting.get(runSettingId)
else:
    runSettingId = inturruptedRun.runSettingId
    runSetting = RunSetting.get(runSettingId)

## run 
interval, lookback = None, None
if runSetting.tradeInterval == "ONE_MINUTE":
    interval, lookback = kline_lookback_config.ONE_MINUTE
elif runSetting.tradeInterval == "FIVE_MINUTE":
    interval, lookback = kline_lookback_config.FIVE_MINUTE
elif runSetting.tradeInterval == "FIFTEEN_MINUTE":
    interval, lookback = kline_lookback_config.FIFTEEN_MINUTE

cc = runSetting.websocketSymbol
socket = f"wss://stream.binance.com:9443/ws/{cc}@kline_{interval}"

# TODO - gat from account
client = Client(config.API_KEY, config.API_SECRET)

symbol = runSetting.symbol

indicators = runSetting.indicators # EMAS MACD

# signal generator
signal = SignalGenerator(client, symbol, lookback, interval)

#BinanceAccount
account = BinanceAccount(client, symbol)

'''
riskTolerancePercentage=runSetting.riskTolerancePercentage
testNet = runSetting.testNet
'''
# start fresh
if inturruptedRun is None:
    botState = MACDStateMachine(account, symbol, riskTolerancePercentage=0.5, quoteFundAmount=quoteFundAmount, isTestNet=False)
else:
    botState = MACDStateMachine.resumeRun(account, inturruptedRun)
    print("PICKED UP RUN")

print(botState.getState())

## pre flight check
# 1. quote amount is enough
preflightPassed = account.preflight(runSetting, quoteFundAmount)

if preflightPassed:

    # print start time
    startTimeStr = datetime.datetime.now().strftime("%m/%d/%Y - %H:%M:%S")
    print(startTimeStr)
    
    # set up ws class
    ws = websocket.WebSocketApp(socket, on_message=signal.getOnMessage(botState, indicators=indicators), on_close=signal.getOnClose())
    ws.on_open = signal.getOnOpen()

    ws.run_forever()