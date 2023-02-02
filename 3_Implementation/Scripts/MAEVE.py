import AlpacaTrader as alp

import pandas as pd

import logging
from datetime import datetime

trader = alp.AlpacaTrader()

symbol = "BTC/USD"

save_loc = "S://Docs//Personal//MAEVE//MAEVE-II//3_Implementation//Scripts//logs//"

##################
# Logging
##################

# Process logging
log_loc = "S://Docs//Personal//MAEVE//MAEVE-II//3_Implementation//Scripts//logs//MAEVE.log"
logging.basicConfig(filename=log_loc, level=logging.INFO)

# Event logging
events_df = pd.DataFrame()
# datetime, price, usd, sats, MA12, MA20, init_cash, profit/loss, cooldown

# Trade logging
trades_df = pd.DataFrame()
# datetime, trigger, tradetype, price, usd, sats, init_cash, cur_cash, profit/loss, streak, return


def event_log(event):
    path = save_loc + f"event_log.csv"
    # feats_df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
    
    pass

def trade_log(event):
    pass



logging.info("############################")
logging.info(datetime.today())
logging.info("MAEVE Starting")
logging.info("############################")


# Strategy parameters
MAEVE = {
            'MA1': 12,
            'MA2': 20,
            'stoploss': 0.01,
            'streaklim': 2,
            'cooldown': 48,
            'trailing': True
        }


# Position management
stop_price = 0
orig_stop_price = 0
streak = 0
idle = 0



while True:
    
    logging.info("############################################")
    logging.info("Strategy Run @" + str(datetime.now()))
    logging.info("#############################################")
    
    
    ################
    # Market pulse
    ################
    
    logging.info("Market pulse")
    
    # Get current price
    price = trader.GET_PRICE()
    # Get current balances
    usd, sats = trader.CHK_BAL()

    # Get MAs
    MA1 = trader.GET_MA(MAEVE.MA1)
    MA2 = trader.GET_MA(MAEVE.MA2)
    
    # event_log()
    
    ############
    # Cooldown
    ############
            
    if streak >= MAEVE.streaklim:
        
        idle += 1
        # strat_sats.append(row_sats)
        # strat_usd.append(row_usd)

        if idle >= MAEVE.cooldown:
            streak = 0
            idle = 0
    
    
    #######################
    # Position management
    #######################
    
    # Trailing stop loss
    if trailing:
        new_stop = round((1-stoploss) * row['Close'], 2)
        if stop_price == orig_stop_price:
            if new_stop > (stop_price * (1+stoploss)): stop_price = new_stop
        else:
            if new_stop > (stop_price * (1+0.01)): stop_price = new_stop
    
    # Check stop loss trigger
    if row['Close'] < stop_price and current_position == "buy":
        
        # Update position
        current_position = "sell"
        cash = round(sats * row['Close'], 2)
        sats = 0
        # row_usd = cash

        # Log trade
        trades_df = pd.concat([trades_df, log_trade(row, current_position, cash, sats)])
        trade_trigger.append('STOP')
        
        # Update streak
        streak += 1

        continue

    break
    

# hist_df = trader.HIST_PRICE(symbol, hours=30)

# print(hist_df.tail())

# MA = trader.CALC_MA(hist_df, timeperiod=12)
# MA = trader.CALC_MA(MA, timeperiod=24)
# maxtime = MA['timestamp'].max()

# MA12 = MA[MA['timestamp']==maxtime]['MA12'].values[0]
# MA24 = MA[MA['timestamp']==maxtime]['MA24'].values[0]


# print(MA12, MA24)

# if MA12 > MA24: print("BUY")
# else: print("SELL")

# print(trader.CHK_BAL())

# (MA1, MA2, stoploss, streaklim, cooldown)
# combo = ('MA12', 'MA20', 0.01, 2, 48, True)
