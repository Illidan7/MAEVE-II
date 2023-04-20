import KrakenTrader as krkn

import pandas as pd

import os
import time
import logging
from datetime import datetime

trader = krkn.KrakenTrader()

save_loc = "/root/data/logs/"


##################
# Logging
##################

# Process logging
log_loc = "/root/data/logs/MAEVE.log"
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
            # BUY
            'MA1': 8,
            'MA2': 30,
            'mult1': 3,
            'ATR1': 49,
            # SELL
            'MA3': 48,
            'MA4': 30,
            'mult2': 2.5,
            'ATR2': 35,
            # Position management
            'stoploss': 0.05,
            'streaklim': 0,
            'trailing': True,
            # Deployment
            'sleepMin': 5,
            'symbol': "BTC/USD"
        }


# Position management
stop_price = 0
orig_stop_price = 0
streak = 0
stopped = 0

# Telegram update management
tgcounter = 0
tgind = False

while True:
    
    if tgcounter % 60 == 0:
        tgind = True
    
    text = "Strategy Run @" + str(datetime.now())
    text_log(text=text, tg=tgind, padding=True)
    
    ################
    # Market pulse
    ################
     
    text_log("Market pulse", tg=tgind, padding=False)
    
    # Get current price
    price = trader.GET_PRICE()
    # Get current balances
    sats, usd = trader.CHK_BAL()
    # Buy side
    qty_buy = round(round(usd/(price+100), 8) * trader.fee_factor, 8)
    qty_sell = round(sats * trader.fee_factor, 8)
    
    
    ################
    # Strategy eval
    ################
    
    # Get Technical indicator values
    MA1 = trader.GET_MA(MAEVE['MA1'])
    MA2 = trader.GET_MA(MAEVE['MA2'])
    ATR1 = trader.GET_ATR(MAEVE['ATR1'])
    
    MA3 = trader.GET_MA(MAEVE['MA3'])
    MA4 = trader.GET_MA(MAEVE['MA4'])
    ATR2 = trader.GET_ATR(MAEVE['ATR2'])
    
    BUY_trigger = MA1 > (MA2 + (MAEVE['mult1'] * ATR1)) if streak >= MAEVE['streaklim'] else MA1 > MA2
    SELL_trigger = MA3 < (MA4 - (MAEVE['mult2'] * ATR2)) if streak >= MAEVE['streaklim'] else MA3 < MA4
    
    
    logging.info("Text Log")
    text = f'''
BTC price: {price}
USD: {usd}
BTC: {sats}
Total (USD): {round(usd + (sats*price), 2)}

MA8: {MA1},
MA30: {MA2},
mult1: 3,
ATR49: {ATR1},

MA48: {MA3},
MA30: {MA2},
mult2: 2.5,
ATR35: {ATR2},

BUY_trigger: {BUY_trigger},
SELL_trigger: {SELL_trigger}
    '''
    text_log(text=text, tg=tgind, padding=False)
    
    
    logging.info("Event Log")
    # Event log
    event = {
            
                'datetime': [str(datetime.now())],
                'price': [price],
                'usd': [usd],
                'sats': [sats],
                
                f"MA{MAEVE['MA1']}": [MA1],
                f"MA{MAEVE['MA2']}": [MA2],
                'mult1': [MAEVE['mult1']],
                f"ATR{MAEVE['ATR1']}": [ATR1],
                
                f"MA{MAEVE['MA3']}": [MA3],
                f"MA{MAEVE['MA4']}": [MA4],
                'mult2': [MAEVE['mult2']],
                f"ATR{MAEVE['ATR2']}": [ATR2],
                
                'BUY_trigger': [BUY_trigger],
                'SELL_trigger': [SELL_trigger],
                
                'stopped': [stopped],
                'cur_cash': [round(usd + (sats*price), 2)] 
            }
    event_log(event)
    
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
                text_log(text=text, tg=tgind, padding=True)
                
        else:
            if new_stop > (stop_price * (1+0.01)):
                
                stop_price = new_stop
                text = f"Trailing Stop price -> +0.01 -> {stop_price}"
                text_log(text=text, tg=tgind, padding=True)
                
    
    # Check stop loss trigger
    if price < stop_price and usd < 5:
        
        text = f"Stop loss triggered at ${stop_price}"
        text_log(text=text, tg=tgind, padding=True)
        
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
                    f"MA{MAEVE['MA1']}": [MA1],
                    f"MA{MAEVE['MA2']}": [MA2],
                    'mult1': [MAEVE['mult1']],
                    f"ATR{MAEVE['ATR1']}": [ATR1],  
                    f"MA{MAEVE['MA3']}": [MA3],
                    f"MA{MAEVE['MA4']}": [MA4],
                    'mult2': [MAEVE['mult2']],
                    f"ATR{MAEVE['ATR2']}": [ATR2],
                    'BUY_trigger': [BUY_trigger],
                    'SELL_trigger': [SELL_trigger],
                    'cur_cash': [round(usd + (sats*price), 2)],
                    'streak': [streak] 
                }
        trade_log(trade)
        
    ###############
    # BUY signal
    ###############

    # Check if the MA1 is higher than the MA2
    if BUY_trigger:
        
        if usd > 5:
            
            text = f"BUY signal triggered at ${price}"
            text_log(text=text, tg=tgind, padding=True)
            
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
                    'trigger': ['STOP'],
                    'tradetype': ['SELL'],
                    'price': [price],
                    'stopprice': [stop_price],
                    'usd': [usd],
                    'sats': [sats],
                    f"MA{MAEVE['MA1']}": [MA1],
                    f"MA{MAEVE['MA2']}": [MA2],
                    'mult1': [MAEVE['mult1']],
                    f"ATR{MAEVE['ATR1']}": [ATR1],  
                    f"MA{MAEVE['MA3']}": [MA3],
                    f"MA{MAEVE['MA4']}": [MA4],
                    'mult2': [MAEVE['mult2']],
                    f"ATR{MAEVE['ATR2']}": [ATR2],
                    'BUY_trigger': [BUY_trigger],
                    'SELL_trigger': [SELL_trigger],
                    'cur_cash': [round(usd + (sats*price), 2)],
                    'streak': [streak] 
                }
            trade_log(trade)

    ###############
    # SELL signal
    ###############

    # Check if the MA1 is lower than the MA2
    elif SELL_trigger:
        # If we're currently holding BTC, sell
        if usd < 5:
            
            text = f"SELL signal triggered at ${price}"
            text_log(text=text, tg=tgind, padding=True)
            
            # Update position
            trader.SELL(qty=qty_sell, price=price-100, symbol="XBTUSD")
            
            stopped = 0
            
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
                    f"MA{MAEVE['MA1']}": [MA1],
                    f"MA{MAEVE['MA2']}": [MA2],
                    'mult1': [MAEVE['mult1']],
                    f"ATR{MAEVE['ATR1']}": [ATR1],  
                    f"MA{MAEVE['MA3']}": [MA3],
                    f"MA{MAEVE['MA4']}": [MA4],
                    'mult2': [MAEVE['mult2']],
                    f"ATR{MAEVE['ATR2']}": [ATR2],
                    'BUY_trigger': [BUY_trigger],
                    'SELL_trigger': [SELL_trigger],
                    'cur_cash': [round(usd + (sats*price), 2)],
                    'streak': [streak] 
                }
            trade_log(trade)

    text = f"Sleeping for {MAEVE['sleepMin']} min"
    text_log(text=text, tg=tgind, padding=False)
    
    tgcounter += MAEVE['sleepMin']
    
    time.sleep(MAEVE['sleepMin']*60)
