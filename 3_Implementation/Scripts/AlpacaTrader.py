import sys
import requests

sys.path.append("S://Docs//Personal//MAEVE//Data//Config//")
from config import *

import pandas as pd

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoLatestQuoteRequest
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame

from datetime import datetime
from dateutil.relativedelta import relativedelta

class AlpacaTrader:
    
    def __init__(self):
        self.trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
        
        
    def BUY(self, symbol, qty):
        # preparing orders
        market_order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.GTC
        )

        # Market order
        market_order = self.trading_client.submit_order(
            order_data=market_order_data
        )
        
        return
    
    
    def SELL(self, symbol, qty):
        # preparing orders
        market_order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.GTC
        )

        # Market order
        market_order = self.trading_client.submit_order(
            order_data=market_order_data
        )
        
        return
    
    
    def GET_PRICE(self, symbol="BTC/USD"):
        # no keys required
        client = CryptoHistoricalDataClient()

        # single symbol request
        request_params = CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
        latest_quote = client.get_crypto_latest_quote(request_params)

        return latest_quote[symbol].ask_price
    
    
    def CHK_BTC(self, symbol="BTC/USD"):
        symbol = symbol.replace('/','')
        portfolio = self.trading_client.get_all_positions()
        
        for position in portfolio:           
            if dict(position)['symbol'] == symbol:    
                return float(dict(position)['qty'])
        
        return 0.0
    
    
    def CHK_CASH(self):
        return float(self.trading_client.get_account().non_marginable_buying_power)
    
    
    def CHK_BAL(self):
        return self.CHK_BTC(), self.CHK_CASH()
    
    
    def HIST_PRICE(self, symbol, hours):
        
        time_diff = datetime.now() - relativedelta(hours=hours)
        # no keys required for crypto data
        client = CryptoHistoricalDataClient()

        request_params = CryptoBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Hour,
            start=time_diff
        )

        bars = client.get_crypto_bars(request_params)
        # convert to dataframe
        df = bars.df.reset_index()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    
    def CALC_MA(self, df, timeperiod):
        df[f'MA{timeperiod}'] = df['close'].rolling(window=timeperiod).mean()
        return df
    
    
    def GET_MA(self, MA, symbol="BTC/USD", hours=30):
        hist_df = self.HIST_PRICE(symbol=symbol, hours=hours)
        MA1 = self.CALC_MA(hist_df, timeperiod=MA)
        maxtime = MA1['timestamp'].max()        
        return MA1[MA1['timestamp']==maxtime][f'MA{MA}'].values[0]
    
    
    def TG_ALERT(self, alert):
        requests.get(tg_baseurl+f'{alert}')

        

        

