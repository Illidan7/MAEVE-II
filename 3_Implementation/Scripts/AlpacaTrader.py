import alpaca_trade_api as tradeapi
import pandas as pd

class AlpacaTrader:
    def __init__(self, api_key, secret_key):
        self.api = tradeapi.REST(api_key, secret_key, base_url='https://paper-api.alpaca.markets')

    def place_buy_order(self, symbol, qty, order_type, limit_price=None):
        if order_type == 'limit':
            self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                type=order_type,
                time_in_force='gtc',
                limit_price=limit_price
            )
        elif order_type == 'market':
            self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                type=order_type,
                time_in_force='gtc'
            )
        else:
            print('Invalid order type')

    def place_sell_order(self, symbol, qty, order_type, limit_price=None):
        if order_type == 'limit':
            self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type=order_type,
                time_in_force='gtc',
                limit_price=limit_price
            )
        elif order_type == 'market':
            self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type=order_type,
                time_in_force='gtc'
            )
        else:
            print('Invalid order type')

    def cancel_order(self, order_id=None):
        if order_id:
            self.api.cancel_order(order_id)
        else:
            open_orders = self.api.list_orders()
            for order in open_orders:
                self.api.cancel_order(order.id)
    
    def get_price(self, symbol, cadence='1Min'):
    barset = api.get_barset(symbol, cadence, limit=1)
    latest_bar = barset[symbol][0]
    return latest_bar.c
