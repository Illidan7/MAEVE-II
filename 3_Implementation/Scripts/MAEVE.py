import AlpacaTrader as alp

trader = alp.AlpacaTrader()

symbol = "BTC/USD"

price = trader.GET_PRICE(symbol)

print(price)
