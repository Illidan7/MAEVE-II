import time
import os
import requests

import urllib.parse
import hashlib
import hmac
import base64
import sys

sys.path.append("/root/data/Config/")
from config import *

import pandas as pd

from datetime import datetime
from dateutil.relativedelta import relativedelta

class KrakenTrader:
    
    def __init__(self):
        self.api_url = "https://api.kraken.com"
        self.fee_factor = 1 - FEES
        self.offset = 100
    
    
    def get_kraken_signature(self, urlpath, data, secret):

        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    
    def kraken_request(self, uri_path, data):
        headers = {}
        headers['API-Key'] = API_KEY
        # get_kraken_signature()
        headers['API-Sign'] = self.get_kraken_signature(uri_path, data, SECRET_KEY)
        req = requests.post((self.api_url + uri_path), headers=headers, data=data)
        return req


    def BUY(self, qty, price, symbol="XBTUSD"):
        
        resp = self.kraken_request('/0/private/AddOrder', {
                                                        "nonce": str(int(1000*time.time())),
                                                        "ordertype": "limit",
                                                        "type": "buy",
                                                        "volume": qty,
                                                        "pair": symbol,
                                                        "price": price
                                                    })
        
        # return resp.json()['result']['ordernum']
        return
    
    
    def SELL(self, qty, price, symbol="XBTUSD"):
        
        resp = self.kraken_request('/0/private/AddOrder', {
                                                        "nonce": str(int(1000*time.time())),
                                                        "ordertype": "limit",
                                                        "type": "sell",
                                                        "volume": qty,
                                                        "pair": symbol,
                                                        "price": price
                                                    })
        
        # return resp.json()['result']['ordernum']
        return
    
    
    def STOPLOSS(self, qty, price, symbol="XBTUSD"):
        resp = self.kraken_request('/0/private/AddOrder', {
                                                        "nonce": str(int(1000*time.time())),
                                                        "ordertype": "stop-loss-limit",
                                                        "type": "sell",
                                                        "volume": qty,
                                                        "pair": symbol,
                                                        "price": price,
                                                        "price2": price+2000
                                                    })
        
        # return resp.json()['result']['ordernum']
        return
    
    
    def CHK_ORDER(self, ordernum):
        pass
    
    
    def GET_PRICE(self, symbol="XXBTZUSD"):

        url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"
        response = requests.get(url)
        data = response.json()
        price = data['result'][symbol]['c'][0]
        
        return round(float(price),2)
    
    
    def CHK_BTC(self):
        resp = self.kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))})
        return round(float(resp.json()['result']['XXBT']),8)
    
    
    def CHK_CASH(self):
        resp = self.kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))})
        return round(float(resp.json()['result']['ZUSD']),2)
    
    
    def CHK_BAL(self):
        return self.CHK_BTC(), self.CHK_CASH()
    
    
    def HIST_PRICE(self, symbol='XBTUSD', timeframe=60):
        
        resp = requests.get(f'https://api.kraken.com/0/public/OHLC?pair={symbol}&interval={timeframe}')

        df = pd.DataFrame(resp.json()['result']['XXBTZUSD'], columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['time'] = pd.to_datetime(df['time'], unit='s')

        return df
    
    
    def CALC_MA(self, df, timeperiod):
        df[f'MA{timeperiod}'] = df['close'].rolling(window=timeperiod).mean()
        return df
    
    
    def CALC_ATR(self, df, n):
        tr = pd.DataFrame()
        tr['h-l'] = df['high'].astype(float) - df['low'].astype(float)
        tr['h-pc'] = abs(df['high'].astype(float) - df['close'].astype(float).shift(1))
        tr['l-pc'] = abs(df['low'].astype(float) - df['close'].astype(float).shift(1))
        tr['true_range'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        atr = tr['true_range'].rolling(n).mean()
        df[f'ATR{n}'] = atr
        return df
    
    
    def GET_MA(self, MA, symbol="XBTUSD", timeframe=60):
        hist_df = self.HIST_PRICE(symbol=symbol, timeframe=timeframe)
        MA1 = self.CALC_MA(hist_df, timeperiod=MA)
        maxtime = MA1['time'].max()        
        return MA1[MA1['time']==maxtime][f'MA{MA}'].values[0]
    
    
    def GET_ATR(self, ATR, symbol="XBTUSD", timeframe=60):
        hist_df = self.HIST_PRICE(symbol=symbol, timeframe=timeframe)
        ATR1 = self.CALC_ATR(hist_df, n=ATR)
        maxtime = ATR1['time'].max()        
        return ATR1[ATR1['time']==maxtime][f'ATR{ATR}'].values[0]
    
    
    def TG_ALERT(self, alert):
        requests.get(tg_baseurl+f'{alert}')

        

        

