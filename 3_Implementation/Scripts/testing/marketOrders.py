import AlpacaTrader as alp

trader = alp.AlpacaTrader(live=False)

symbol = "BTC/USD"

# Get current price
price = trader.GET_PRICE()
# Get current balances
sats, usd = trader.CHK_BAL()

# Buy side
qty_buy = round(round(usd/price, 8) * trader.alp_factor, 8)
qty_sell = round(sats * trader.alp_factor, 8)

print(f"BTC price: {price}")
print(f"BTC balance: {sats}")
print(f"USD balance: {usd}")
print(f"QTY buy: {qty_buy}, {qty_buy*price}")
print(f"QTY sell: {qty_sell}")



if qty_buy > 0.01:
    print("Executing Market order: BUY")
    trader.BUY(symbol=symbol, qty=qty_buy)
else:
    print("Executing Market order: SELL")
    trader.SELL(symbol=symbol, qty=qty_sell)


# Get current balances
sats, usd = trader.CHK_BAL()

print(f"BTC balance: {sats}")
print(f"USD balance: {usd}")
