####################
# Setup
####################

import yfinance as yf
import datetime
from datetime import timedelta
import sys

save_loc = "S://Docs//Personal//MAEVE//Data//"

####################################
# Parse args and define data scope
####################################

# Find number of arguments passed
n = len(sys.argv)

# Verify expected number of arguments
if n != 2:
    print("Expected 1 value")
    sys.exit()

timeperiod = str(sys.argv[1])


# Define the start and end dates for the data
end = datetime.datetime.now()

if timeperiod == "1d":
    start = datetime.datetime(2010, 1, 1)
elif timeperiod == "1h":
    start = end + timedelta(days=-730)
elif timeperiod == "1m":
    start = end + timedelta(days=-7)




###########################
# Download BTC price data
###########################

# Use the `yf.download` function to download the data
df = yf.download("BTC-USD", 
                 start=start, 
                 end=end, 
                 interval=timeperiod)
df = df.reset_index()


##############
# Save file
##############

# Save the data to a CSV file
path = save_loc + f"BTC_price_{timeperiod}.csv"
df.to_csv(path, index=False)
