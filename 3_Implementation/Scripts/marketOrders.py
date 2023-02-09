import KrakenTrader as krkn

trader = krkn.KrakenTrader()

symbol = "BTC/USD"

# Get current price
price = trader.GET_PRICE()
# Get current balances
sats, usd = trader.CHK_BAL()


# Buy side
qty_buy = round(round(usd/(price+100), 8) * trader.fee_factor, 8)
qty_sell = round(sats * trader.fee_factor, 8)

print(f"BTC price: {price}")
print(f"BTC balance: {sats}")
print(f"USD balance: {usd}")
print(f"QTY buy: {qty_buy}, {qty_buy*price}")
print(f"QTY sell: {qty_sell}")



if qty_buy > 0.0001:
    print("Executing Market order: BUY")
    trader.BUY(qty=qty_buy, price=price+100, symbol="XBTUSD")
else:
    print("Executing Market order: SELL")
    trader.SELL(qty=qty_sell, price=price-100, symbol="XBTUSD")


# Get current balances
sats, usd = trader.CHK_BAL()

print(f"BTC balance: {sats}")
print(f"USD balance: {usd}")
