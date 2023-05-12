import sys
sys.path.append("S://Docs//Personal//MAEVE//MAEVE-II//3_MAEVEBuild//Scripts//Kraken//")
import KrakenTrader as krkn

trader = krkn.KrakenTrader()

symbol = "BTC/USD"

def position_status():
    # Get current price
    price = trader.GET_PRICE()
    # Get current balances
    sats, usd = trader.CHK_BAL()

    # Order amounts
    qty_buy = round(round(usd/(price), 8) * trader.fee_factor, 8)
    qty_sell = round(sats * trader.fee_factor, 8)

    return price, sats, usd, qty_buy, qty_sell

price, sats, usd, qty_buy, qty_sell = position_status()

print(f"BTC price: {price}")
print(f"BTC balance: {sats}")
print(f"USD balance: {usd}")
print(f"QTY buy: {qty_buy}, {qty_buy*price}")
print(f"QTY sell: {qty_sell}")


# print("Set stoploss")
# price, sats, usd, qty_buy, qty_sell = position_status()
# stop_price = round((1-0.05) * price, 2)
# trader.STOPLOSS(qty=qty_sell, price=stop_price, symbol="XBTUSD")


if qty_buy > 0.0001:
    print("Executing Market order: BUY")
    trader.BUY(qty=qty_buy, price=price, symbol="XBTUSD")
    
else:
    print("Executing Market order: SELL")
    trader.SELL(qty=qty_sell, price=price, symbol="XBTUSD")


# Get current balances
sats, usd = trader.CHK_BAL()

print(f"BTC balance: {sats}")
print(f"USD balance: {usd}")
