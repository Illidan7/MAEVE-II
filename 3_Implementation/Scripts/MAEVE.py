import AlpacaTrader as alp

import pandas as pd

import os
import time
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
# datetime, price, usd, sats, MA12, MA20, cur_cash, profit/loss, cooldown

# Trade logging
trades_df = pd.DataFrame()
# datetime, trigger, tradetype, price, usd, sats, init_cash, cur_cash, profit/loss, streak, return

####################
# Custom functions
####################

def event_log(event):
    event_df = pd.DataFrame(event)
    path = save_loc + f"event_log.csv"
    event_df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
    return

def trade_log(trade):
    trade_df = pd.DataFrame(trade)
    path = save_loc + f"trade_log.csv"
    trade_df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
    return


###########################
# Strategy Implementation
###########################

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
            'trailing': True,
            'sleepMin': 30
        }


# Position management
stop_price = 0
orig_stop_price = 0
streak = 0
idle = 0
stopped = 0



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
    sats, usd = trader.CHK_BAL()
    
    print(usd, sats)

    # Get MAs
    MA1 = trader.GET_MA(MAEVE['MA1'])
    MA2 = trader.GET_MA(MAEVE['MA2'])
    
    logging.info("Event Log")
    # Event log
    # datetime, price, usd, sats, MA12, MA20, cur_cash, profit/loss, cooldown
    event = {
                'datetime': [str(datetime.now())],
                'price': [price],
                'usd': [usd],
                'sats': [sats],
                'MA12': [MA1],
                'MA20': [MA2],
                'bullish': [MA1>MA2],
                'stopped': [stopped],
                'cur_cash': [round(usd + (sats*price), 2)],
                'cooldown': [streak >= MAEVE['streaklim']] 
            }
    event_log(event)
    
    ############
    # Cooldown
    ############
            
    if streak >= MAEVE['streaklim']:
        
        logging.info(f"Cooldown: {idle}")
        
        idle += 1
        if idle >= MAEVE['cooldown']:
            streak = 0
            idle = 0
    
    
    #######################
    # Position management
    #######################
    
    # Trailing stop loss
    if MAEVE['trailing'] and usd < 5:
        
        new_stop = round((1-MAEVE['stoploss']) * price, 2)
        if stop_price == orig_stop_price:
            if new_stop > (stop_price * (1+MAEVE['stoploss'])): 
                logging.info(f"Trailing Stop price -> break even")
                stop_price = new_stop
        else:
            if new_stop > (stop_price * (1+0.01)): 
                logging.info(f"Trailing Stop price +0.01")
                stop_price = new_stop
    
    # Check stop loss trigger
    if price < stop_price and usd < 5:
        
        logging.info(f"Stop loss triggered at ${stop_price}")
        
        # Update position
        trader.SELL(symbol=symbol, qty=sats)
        
        # Update streak
        streak += 1
        stopped = 1
        
        # Log trade
        # datetime, trigger, tradetype, price, usd, sats, MA12, MA20, cur_cash, streak
        trade = {
                    'datetime': [str(datetime.now())],
                    'trigger': ['STOP'],
                    'tradetype': ['SELL'],
                    'price': [price],
                    'stopprice': [stop_price],
                    'usd': [usd],
                    'sats': [sats],
                    'MA12': [MA1],
                    'MA20': [MA2],
                    'cur_cash': [round(usd + (sats*price), 2)],
                    'streak': [streak] 
                }
        trade_log(trade)
        
    ###############
    # BUY signal
    ###############

    # Check if the MA1 is higher than the MA2
    if MA1 > MA2:
        
        if usd > 5:
            
            logging.info(f"BUY signal triggered at ${price}")
            
            # Update position
            trader.BUY(symbol=symbol, qty=usd)
        
            # Position management
            orig_stop_price = round((1-MAEVE['stoploss']) * price, 2)
            stop_price = round((1-MAEVE['stoploss']) * price, 2)
            stopped = 0

            # Log trade
            # datetime, trigger, tradetype, price, usd, sats, MA12, MA20, cur_cash, streak
            trade = {
                        'datetime': [str(datetime.now())],
                        'trigger': ['BUY'],
                        'tradetype': ['BUY'],
                        'price': [price],
                        'stopprice': [stop_price],
                        'usd': [usd],
                        'sats': [sats],
                        'MA12': [MA1],
                        'MA20': [MA2],
                        'cur_cash': [round(usd + (sats*price), 2)],
                        'streak': [streak]
                    }
            trade_log(trade)

    ###############
    # SELL signal
    ###############

    # Check if the MA1 is lower than the MA2
    elif MA1 < MA2:
        # If we're currently holding BTC, sell
        if usd < 5:
            
            logging.info(f"SELL signal triggered at ${price}")

            # Update position
            trader.SELL(symbol=symbol, qty=sats*0.9974)
            
            stopped = 0
            
            
           # Log trade
            # datetime, trigger, tradetype, price, usd, sats, MA12, MA20, cur_cash, streak
            trade = {
                        'datetime': [str(datetime.now())],
                        'trigger': ['SELL'],
                        'tradetype': ['SELL'],
                        'price': [price],
                        'stopprice': [stop_price],
                        'usd': [usd],
                        'sats': [sats],
                        'MA12': [MA1],
                        'MA20': [MA2],
                        'cur_cash': [round(usd + (sats*price), 2)],
                        'streak': [streak] 
                    }
            trade_log(trade)

    logging.info(f"Sleeping for {MAEVE['sleepMin']} min")
    time.sleep(MAEVE['sleepMin']*60)
