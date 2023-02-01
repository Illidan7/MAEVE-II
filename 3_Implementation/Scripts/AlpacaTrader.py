import sys

sys.path.append("S://Docs//Personal//MAEVE//Data//Config//")
from config import *

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoLatestQuoteRequest

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
    
    
    def GET_PRICE(self, symbol):
        # no keys required
        client = CryptoHistoricalDataClient()

        # single symbol request
        request_params = CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
        latest_quote = client.get_crypto_latest_quote(request_params)

        return latest_quote[symbol].ask_price
    
    
    def CHK_POS(self, symbol):
        symbol = symbol.replace('/','')
        portfolio = self.trading_client.get_all_positions()
        
        for position in portfolio:           
            if dict(position)['symbol'] == symbol:    
                return dict(position)['qty']
        

        

