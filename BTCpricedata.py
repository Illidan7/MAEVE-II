import pandas_datareader as pdr
import datetime

# Define the start and end dates for the data
start = datetime.datetime(2010, 1, 1)
end = datetime.datetime.now()

# Use the `pdr.get_data_yahoo` function to download the data
df = pdr.get_data_yahoo("BTC-USD", start=start, end=end)

# Save the data to a CSV file
df.to_csv("bitcoin_price_data.csv")
