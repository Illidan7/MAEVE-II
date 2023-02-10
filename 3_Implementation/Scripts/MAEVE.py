import KrakenTrader as krkn

import pandas as pd

import os
import time
import logging
from datetime import datetime

trader = krkn.KrakenTrader()

save_loc = "S://Docs//Personal//MAEVE//Data//logs//"


##################
# Logging
##################

# Process logging
log_loc = "S://Docs//Personal//MAEVE//Data//logs//MAEVE.log"
logging.basicConfig(filename=log_loc, level=logging.INFO)


####################
# Custom functions
####################

# Event logging
# datetime, price, usd, sats, MA12, MA20, cur_cash, profit/loss, cooldown
def event_log(event):
    event_df = pd.DataFrame(event)
    path = save_loc + f"event_log.csv"
    event_df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
    return

# Trade logging
# datetime, trigger, tradetype, price, usd, sats, init_cash, cur_cash, profit/loss, streak, return
def trade_log(trade):
    trade_df = pd.DataFrame(trade)
    path = save_loc + f"trade_log.csv"
    trade_df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
    return

# Text logging
def text_log(text, tg=True, padding=False):

    if padding:
        
        logging.info("############################################")
        logging.info(text)
        logging.info("############################################")
        
        if tg:
            trader.TG_ALERT("############################################")
            trader.TG_ALERT(text)
            trader.TG_ALERT("############################################")
    else:
        logging.info(text)
        if tg:
            trader.TG_ALERT(text)


###########################
# Strategy Implementation
###########################

logging.info("############################")
logging.info(datetime.today())
logging.info("MAEVE Starting")
logging.info("############################")

trader.TG_ALERT("############################################")
trader.TG_ALERT("MAEVE Starting")
trader.TG_ALERT("############################################")


# Strategy parameters
MAEVE = {
            'MA1': 12,
            'MA2': 20,
            'stoploss': 0.01,
            'streaklim': 2,
            'cooldown': 48,
            'trailing': True,
            'sleepMin': 30,
            'symbol': "BTC/USD"
        }


# Position management
stop_price = 0
orig_stop_price = 0
streak = 0
idle = 0
stopped = 0



while True:
    
    text = "Strategy Run @" + str(datetime.now())
    text_log(text=text, tg=True, padding=True)
    
    ################
    # Market pulse
    ################
     
    text_log("Market pulse", tg=True, padding=False)
    
    # Get current price
    price = trader.GET_PRICE()
    # Get current balances
    sats, usd = trader.CHK_BAL()
    # Buy side
    qty_buy = round(round(usd/(price+100), 8) * trader.fee_factor, 8)
    qty_sell = round(sats * trader.fee_factor, 8)
    
    text = f"BTC price: {price}, USD: {usd}, BTC: {sats}, Total (USD): {round(usd + (sats*price), 2)}"
    text_log(text=text, tg=True, padding=False)
    
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
        
        text = f"Cooldown: {idle}"
        text_log(text=text, tg=True, padding=True)
        
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
                
                stop_price = new_stop
                text = f"Trailing Stop price -> break even -> {stop_price}"
                text_log(text=text, tg=True, padding=True)
                
        else:
            if new_stop > (stop_price * (1+0.01)):
                
                stop_price = new_stop
                text = f"Trailing Stop price -> +0.01 -> {stop_price}"
                text_log(text=text, tg=True, padding=True)
                
    
    # Check stop loss trigger
    if price < stop_price and usd < 5:
        
        text = f"Stop loss triggered at ${stop_price}"
        text_log(text=text, tg=True, padding=True)
        
        # Update position
        trader.SELL(qty=qty_sell, price=price-100, symbol="XBTUSD")
        
        # Update streak
        streak += 1
        stopped = 1
        
        logging.info("Trade log")
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
            
            text = f"BUY signal triggered at ${price}"
            text_log(text=text, tg=True, padding=True)
            
            # Update position
            trader.BUY(qty=qty_buy, price=price+100, symbol="XBTUSD")
        
            # Position management
            orig_stop_price = round((1-MAEVE['stoploss']) * price, 2)
            stop_price = round((1-MAEVE['stoploss']) * price, 2)
            stopped = 0

            logging.info("Trade log")
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
            
            text = f"SELL signal triggered at ${price}"
            text_log(text=text, tg=True, padding=True)
            
            # Update position
            trader.SELL(qty=qty_sell, price=price-100, symbol="XBTUSD")
            
            stopped = 0
            
            logging.info("Trade log")
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

    text = f"Sleeping for {MAEVE['sleepMin']} min"
    text_log(text=text, tg=True, padding=False)
    
    time.sleep(MAEVE['sleepMin']*60)
