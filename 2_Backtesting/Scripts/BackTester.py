import pandas as pd
import numpy as np

import optuna

import datetime
from datetime import timedelta

from tqdm.notebook import tqdm

import plotly.graph_objects as go

import logging


class BackTester:
    
    init_cash = 10000.00
    fees = 0.003
    

    ##########
    # Init
    ##########
    
    def __init__(self, btc_df, mode="opt"):
        
        self.btc_df = btc_df
        if mode == "opt": self.backtest_tracker = dict()
        
        alltime = (self.btc_df['Datetime'] >= "2010-01-01")

        ########################
        # Bull market
        ########################
        # Feb 01, 2021 - Apr 15, 2021
        # Jul 15, 2021 - Nov 15, 2021

        bull_market1 = (self.btc_df['Datetime'] >= "2021-02-01") & (self.btc_df['Datetime'] <= "2021-04-15")
        bull_market2 = (self.btc_df['Datetime'] >= "2021-07-15") & (self.btc_df['Datetime'] <= "2021-11-15")

        ########################
        # Bear market
        ########################
        # Apr 15, 2021 - Jul 15, 2021
        # Nov 15, 2021 - Feb 01, 2022
        # Apr 01, 2022 - Jul 01, 2022

        bear_market1 = (self.btc_df['Datetime'] >= "2021-04-15") & (self.btc_df['Datetime'] <= "2021-07-15")
        bear_market2 = (self.btc_df['Datetime'] >= "2021-11-15") & (self.btc_df['Datetime'] <= "2022-02-01")
        bear_market3 = (self.btc_df['Datetime'] >= "2022-04-01") & (self.btc_df['Datetime'] <= "2022-07-01")

        ########################
        # Accumulation/ flat
        ########################
        # Jul 1, 2022 - Nov 1, 2022
        # Dec 1, 2022 - Jan 1, 2023 

        accum_market1 = (self.btc_df['Datetime'] >= "2022-07-01") & (self.btc_df['Datetime'] <= "2022-11-01")
        accum_market2 = (self.btc_df['Datetime'] >= "2022-12-01") & (self.btc_df['Datetime'] <= "2023-01-01")

        ################
        # Bearish news
        ################

        # Luna / 3AC / Celcius
        # May 1, 2022 - Jul 1, 2022
        blackswan1 = (self.btc_df['Datetime'] >= "2022-05-01") & (self.btc_df['Datetime'] <= "2022-07-01")

        # FTX
        # Nov 1, 2022 - Dec 1, 2022
        blackswan2 = (self.btc_df['Datetime'] >= "2022-11-01") & (self.btc_df['Datetime'] <= "2022-12-01")

        ###################
        # Bullish news
        ###################

        # Tesla buy in
        # Feb 1, 2021 - Mar 1, 2021
        blackswan3 = (self.btc_df['Datetime'] >= "2021-02-01") & (self.btc_df['Datetime'] <= "2021-03-01")

        # Futures ETF approval
        # Sep 15, 2021 - Nov 1, 2021
        blackswan4 = (self.btc_df['Datetime'] >= "2021-09-15") & (self.btc_df['Datetime'] <= "2021-11-01")

        ##############################
        # Low volume time periods
        ##############################


        # All test timeframes
        self.timeframes = [alltime, bull_market1, bull_market2, bear_market1, bear_market2, bear_market3, accum_market1,
                    accum_market2, blackswan1, blackswan2, blackswan3, blackswan4]

        self.timeframenames = ['alltime','bull_market1', 'bull_market2', 'bear_market1', 'bear_market2', 'bear_market3', 'accum_market1',
                    'accum_market2', 'luna', 'ftx', 'tesla_buy', 'etf_approval']
                
    
    #########################
    # Utility functions
    #########################
    
    def pickle_dump(self, path, saveobj):
        import pickle
        filehandler = open(path,"wb")
        pickle.dump(saveobj,filehandler)
        print("File pickled")
        filehandler.close()


    def pickle_load(self, path):
        import pickle
        file = open(path,'rb')
        loadobj = pickle.load(file)
        file.close()
        return loadobj
    

    ###################
    # Calc functions
    ###################
    
    def calc_MA(self, df, timeperiod):
        df[f'MA{timeperiod}'] = df['Close'].rolling(window=timeperiod).mean()
        return df
    
    
    def calc_ATR(self, df, n):
        tr = pd.DataFrame()
        tr['h-l'] = df['High'] - df['Low']
        tr['h-pc'] = abs(df['High'] - df['Close'].shift(1))
        tr['l-pc'] = abs(df['Low'] - df['Close'].shift(1))
        tr['true_range'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        atr = tr['true_range'].rolling(n).mean()
        df[f'ATR{n}'] = atr
        return df
    
    
    def hodl_dca_perf(self, df, init_cash):
    
        hodl_buy = round(init_cash / df['Close'][0], 8)
        df['hodl_sats'] = hodl_buy
        df['hodl_usd'] = df['hodl_sats'] * df['Close']

        dcaamt = init_cash // 500
        dcabuy = len(df) // 500

        df['tmp_rownum'] = list(range(1, len(df)+1))
        df['tmp_dcabuyind'] = np.where(df['tmp_rownum'] % dcabuy == 0, 1, 0)

        df['tmp_dcabuys'] = 0
        df['tmp_dcabuys'] = np.where(df['tmp_dcabuyind'] == 1, round(dcaamt / df['Close'][0], 8),
                                    df['tmp_dcabuys'])

        df['dca_sats'] = df['tmp_dcabuys'].cumsum()
        
        df['tmp_dcanumbuys'] = df['tmp_dcabuyind'].cumsum()
        
        df['dca_usd'] = (df['dca_sats'] * df['Close']) + \
                        (init_cash - (df['tmp_dcanumbuys']*dcaamt))
        
        remCols = [col for col in df.columns if 'tmp' in col]
        df.drop(columns=remCols, inplace=True)
        
        return df
    
    
    #######################
    # Logging functions
    #######################
    
    def log_trade(self, row, pos, cash, sats, init_cash=100):

        df = pd.DataFrame()

        df['Datetime'] = [row['Datetime']]
        df['price'] = [row['Close']]
        df['tradeType'] = [pos]
        df['cash'] = [cash]
        df['sats'] = [sats]
        df['profit/loss'] = np.where(df['sats'] > 0,
                                    (df['sats']*df['price']) - init_cash, df['cash'] - init_cash)

        return df
    
    
    def strategy_summary(self, df):

        showCols = ['Datetime', 'Close', 'hodl_usd', 'dca_usd', 'maeve_usd']
        results_df = pd.concat([df[showCols].head(1), df[showCols].tail(1)])
        results_df.index = ['Start', 'End']

        results_df = pd.concat([results_df, pd.DataFrame({'Datetime': ['', ''], 'Close': ['Profit/Loss', '%'],
                                                        'hodl_usd': [results_df['hodl_usd'].End - results_df['hodl_usd'].Start, str(round(((results_df['hodl_usd'].End - results_df['hodl_usd'].Start)*100/BackTester.init_cash), 2)) + '%'],
                                                        'dca_usd': [results_df['dca_usd'].End - results_df['dca_usd'].Start, str(round(((results_df['dca_usd'].End - results_df['dca_usd'].Start)/BackTester.init_cash)*100, 2)) + '%'],
                                                        'maeve_usd': [results_df['maeve_usd'].End - results_df['maeve_usd'].Start, str(round(((results_df['maeve_usd'].End - results_df['maeve_usd'].Start)*100/BackTester.init_cash), 2)) + '%']})], ignore_index=True)

        results_df.index = ['Start', 'End', '', '']

        return results_df
    
    
    # MA1, MA2, stoploss, streaklim, cooldown, trailing
    def log_backtest(self, combo, timeframe, summary_df):
        
        temp = pd.DataFrame()
        
        for strategy_type in ['HODL','DCA','MAEVE']:

            if strategy_type == 'MAEVE':
                strategy_id = '-'.join(['MAEVE','BUY',combo[0], combo[1],'SELL',combo[2], combo[3], 
                                        'stop_'+str(combo[2]), 'streak_' + str(combo[3]), 'cooldown_'+str(combo[4]), 
                                        'trail_'+str(int(combo[5]))])

            else:
                strategy_id = strategy_type + '-' + timeframe
                        
            pnl = float(summary_df[strategy_type.lower()+"_usd"].values[-1][:-1])
            
            temp_ = pd.DataFrame({
                                'strategy_id': [strategy_id], 
                                'strategy_type': [strategy_type], 
                                'timeframe': [timeframe],
                                'MA1': [combo[0] if strategy_type == 'MAEVE' else ""],
                                'MA2': [combo[1] if strategy_type == 'MAEVE' else ""], 
                                'stoploss': [combo[2] if strategy_type == 'MAEVE' else ""], 
                                'streaklim': [combo[3] if strategy_type == 'MAEVE' else ""], 
                                'cooldown': [combo[4] if strategy_type == 'MAEVE' else ""],
                                'trailing': [combo[5] if strategy_type == 'MAEVE' else ""], 
                                'profit/loss': [pnl]
                                })
            
            if len(temp)==0:
                temp = temp_
            else:
                temp = pd.concat([temp, temp_])
                temp = temp.reset_index(drop=True)
        
            
        return temp
    
    
    # MA1, MA2, MA3, MA4, stoploss, streaklim, cooldown, trailing
    def log_backtest_maeve2_t1(self, combo, timeframe, summary_df):
        
        temp = pd.DataFrame()
        
        for strategy_type in ['HODL','DCA','MAEVE']:

            if strategy_type == 'MAEVE':
                strategy_id = '-'.join(['MAEVE','BUY',combo[0], combo[1],'SELL',combo[2], combo[3], 
                                        'stop_'+str(combo[4]), 'streak_' + str(combo[5]), 'cooldown_'+str(combo[6]), 
                                        'trail_'+str(int(combo[7]))])

            else:
                strategy_id = strategy_type + '-' + timeframe
                        
            pnl = float(summary_df[strategy_type.lower()+"_usd"].values[-1][:-1])
            
            temp_ = pd.DataFrame({
                                'strategy_id': [strategy_id], 
                                'strategy_type': [strategy_type], 
                                'timeframe': [timeframe],
                                'MA1': [combo[0] if strategy_type == 'MAEVE' else ""],
                                'MA2': [combo[1] if strategy_type == 'MAEVE' else ""], 
                                'MA3': [combo[2] if strategy_type == 'MAEVE' else ""],
                                'MA4': [combo[3] if strategy_type == 'MAEVE' else ""], 
                                'stoploss': [combo[4] if strategy_type == 'MAEVE' else ""], 
                                'streaklim': [combo[5] if strategy_type == 'MAEVE' else ""], 
                                'cooldown': [combo[6] if strategy_type == 'MAEVE' else ""],
                                'trailing': [combo[7] if strategy_type == 'MAEVE' else ""], 
                                'profit/loss': [pnl]
                                })
            
            if len(temp)==0:
                temp = temp_
            else:
                temp = pd.concat([temp, temp_])
                temp = temp.reset_index(drop=True)
        
            
        return temp


    # MA1,MA2,MA3,MA4,stoploss,streaklim,mult,ATR,trailing
    def log_backtest_maeve2_t2(self, combo, timeframe, summary_df):
        
        temp = pd.DataFrame()
        
        for strategy_type in ['HODL','DCA','MAEVE']:

            if strategy_type == 'MAEVE':
                strategy_id = '-'.join(['MAEVE','BUY',combo[0], combo[1],'SELL',combo[2], combo[3], 
                                        'stop_'+str(combo[4]), 'streak_' + str(combo[5]), 'mult_'+str(combo[6]),
                                        'ATR_'+str(combo[7]), 
                                        'trail_'+str(int(combo[8]))])

            else:
                strategy_id = strategy_type + '-' + timeframe
                        
            pnl = float(summary_df[strategy_type.lower()+"_usd"].values[-1][:-1])
            
            temp_ = pd.DataFrame({
                                'strategy_id': [strategy_id], 
                                'strategy_type': [strategy_type], 
                                'timeframe': [timeframe],
                                'MA1': [combo[0] if strategy_type == 'MAEVE' else ""],
                                'MA2': [combo[1] if strategy_type == 'MAEVE' else ""], 
                                'MA3': [combo[2] if strategy_type == 'MAEVE' else ""],
                                'MA4': [combo[3] if strategy_type == 'MAEVE' else ""], 
                                'stoploss': [combo[4] if strategy_type == 'MAEVE' else ""], 
                                'streaklim': [combo[5] if strategy_type == 'MAEVE' else ""], 
                                'mult': [combo[6] if strategy_type == 'MAEVE' else ""],
                                'ATR': [combo[7] if strategy_type == 'MAEVE' else ""],
                                'trailing': [combo[8] if strategy_type == 'MAEVE' else ""], 
                                'profit/loss': [pnl]
                                })
            
            if len(temp)==0:
                temp = temp_
            else:
                temp = pd.concat([temp, temp_])
                temp = temp.reset_index(drop=True)
        
            
        return temp
    
    
    # MA1,MA2,mult1,ATR1,MA3,MA4,mult2,ATR2,stoploss,streaklim,trailing
    def log_backtest_maeve2_t3(self, combo, timeframe, summary_df):
        
        temp = pd.DataFrame()
        
        for strategy_type in ['HODL','DCA','MAEVE']:

            if strategy_type == 'MAEVE':
                strategy_id = '-'.join(['MAEVE',
                                        'BUY',combo[0],combo[1],str(combo[2]),combo[3],
                                        'SELL',combo[4],combo[5],str(combo[6]),combo[7],
                                        'stop_'+str(combo[8]),
                                        'streak_' + str(combo[9]),
                                        'trail_'+str(int(combo[10]))])

            else:
                strategy_id = strategy_type + '-' + timeframe
                        
            pnl = float(summary_df[strategy_type.lower()+"_usd"].values[-1][:-1])
            
            temp_ = pd.DataFrame({
                                'strategy_id': [strategy_id], 
                                'strategy_type': [strategy_type], 
                                'timeframe': [timeframe],
                                'MA1': [combo[0] if strategy_type == 'MAEVE' else ""],
                                'MA2': [combo[1] if strategy_type == 'MAEVE' else ""],
                                'mult1': [combo[2] if strategy_type == 'MAEVE' else ""],
                                'ATR1': [combo[3] if strategy_type == 'MAEVE' else ""], 
                                'MA3': [combo[4] if strategy_type == 'MAEVE' else ""],
                                'MA4': [combo[5] if strategy_type == 'MAEVE' else ""],
                                'mult2': [combo[6] if strategy_type == 'MAEVE' else ""],
                                'ATR2': [combo[7] if strategy_type == 'MAEVE' else ""], 
                                'stoploss': [combo[8] if strategy_type == 'MAEVE' else ""], 
                                'streaklim': [combo[9] if strategy_type == 'MAEVE' else ""], 
                                'trailing': [combo[10] if strategy_type == 'MAEVE' else ""], 
                                'profit/loss': [pnl]
                                })
            
            if len(temp)==0:
                temp = temp_
            else:
                temp = pd.concat([temp, temp_])
                temp = temp.reset_index(drop=True)
        
            
        return temp
    
    
    #######################
    # Plotting functions
    #######################
    
    def plot_strategy_comparison(self, df):
        # Create the line plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.Datetime, y=df['hodl_usd'], name='HODL'))
        fig.add_trace(go.Scatter(x=df.Datetime, y=df['dca_usd'], name='DCA'))
        fig.add_trace(go.Scatter(x=df.Datetime, y=df['maeve_usd'], name='MAEVE'))

        # Set the title and axis labels
        fig.update_layout(title='Strategy returns over time',
                        xaxis_title='Time',
                        yaxis_title='USD')

        return fig
    
    
    def plot_strategy(self, df, trades_df, MA1, MA2, MA3, MA4):

        # Create a trace for the candle chart
        candle = go.Candlestick(x=df['Datetime'],
                                open=df['Open'],
                                high=df['High'],
                                low=df['Low'],
                                close=df['Close'])

        # Create a trace for the buy points
        buy = go.Scatter(x=trades_df.loc[trades_df.tradeType == "buy"]['Datetime'],
                        y=trades_df.loc[trades_df.tradeType == "buy"]['price'],
                        mode='markers',
                        name='Buy',
                        marker=dict(size=10, color='green'))

        # Create a trace for the sell points
        sell = go.Scatter(x=trades_df.loc[trades_df.tradeType == "sell"]['Datetime'],
                        y=trades_df.loc[trades_df.tradeType == "sell"]['price'],
                        mode='markers',
                        name='Sell',
                        marker=dict(size=10, color='red'))
        
        # Create a trace for the MA1
        ma1 = go.Scatter(x=df['Datetime'], y=df[MA1],
                        mode='lines', name='MA1',
                        line=dict(width=2, color='orange'))

        # Create a trace for the MA2
        ma2 = go.Scatter(x=df['Datetime'], y=df[MA2],
                        mode='lines', name='MA2',
                        line=dict(width=2, color='blue'))
        
        # Create a trace for the MA3
        ma3 = go.Scatter(x=df['Datetime'], y=df[MA3],
                        mode='lines', name='MA3',
                        line=dict(width=2, color='red'))
        
        # Create a trace for the MA4
        ma4 = go.Scatter(x=df['Datetime'], y=df[MA4],
                        mode='lines', name='MA4',
                        line=dict(width=2, color='red'))

        # Create the plot
        fig = go.Figure(data=[candle, buy, sell, ma1, ma2, ma3, ma4])
        fig.update_layout(yaxis=dict(autorange=True, scaleanchor='y',
                                    scaleratio=1, fixedrange=False))

        return fig
    
    
    ###########################
    # Backtesting functions
    ###########################
    
    # MA1, MA2, MA3, MA4, stoploss, streaklim, cooldown, trailing
    def maeve2_t1_backtest(self, *args):
        
        
        MA1,MA2,MA3,MA4,stoploss,streaklim,cooldown,trailing = args[0]
        
        # columns=['strategy_id','strategy_type','timeframe','MA1', 'MA2', 'stoploss', 'streaklim', 'cooldown', 'profit/loss']
        backtest_df = pd.DataFrame()
        figs = {}
        figs_strat = {}
        summary = {}
        trades = {}

        for timeframe, timeframename in zip(self.timeframes, self.timeframenames):
            
            if timeframename != "alltime":
                continue
            
            df = self.btc_df[timeframe].reset_index(drop=True)
            
            # Calculate HODL / DCA Performance
            df = self.hodl_dca_perf(df, init_cash=BackTester.init_cash)
            
            # Initialize the strategy variables
            current_position = None  # "buy" or "sell"
            cash = BackTester.init_cash  # Starting cash
            sats = 0  # Starting BTC

            # Strategy logging
            trades_df = pd.DataFrame()
            strat_sats = []
            strat_usd = []

            # Position management
            stop_price = 0
            orig_stop_price = 0
            streak = 0
            idle = 0

            # Iterate over the rows of the dataframe
            for index, row in df.iterrows():
                
                ############
                # Cooldown
                ############
                
                if streak >= streaklim:
                    
                    idle +=1
                    strat_sats.append(row_sats)
                    strat_usd.append(row_usd)
                    
                    if idle >= cooldown:
                        streak = 0
                        idle = 0
                        
                    continue
                
                
                #######################
                # Position management
                #######################
                
                # Trailing stop loss
                if trailing:
                    new_stop = round((1-stoploss) * row['Close'], 2)
                    if stop_price == orig_stop_price:
                        if new_stop > (stop_price * (1+stoploss)): stop_price = new_stop
                    else:
                        if new_stop > (stop_price * (1+0.01)): stop_price = new_stop
                
                # Check stop loss trigger
                if row['Close'] < stop_price and current_position == "buy":
                    
                    # Update streak
                    if stop_price == orig_stop_price:
                        streak += 1
                    else: 
                        streak = 0
                    
                    # Update position
                    current_position = "sell"
                    cash = round(sats * row['Close'], 2)
                    cash = (1-BackTester.fees) * cash 
                    sats = 0
                    # row_usd = cash

                    # Log trade
                    trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                    
                    

                ###############
                # BUY signal
                ###############
                
                # Check if the MA1 is higher than the MA2
                if row[MA1] > row[MA2]:
                    # If we're not currently holding any BTC, buy BTC
                    if current_position != "buy":
                        
                        # Update position
                        current_position = "buy"
                        cash = (1-BackTester.fees) * cash
                        sats = round(cash / row['Close'], 8)
                        cash = 0
                        # row_sats = sats
                        
                        # Position management
                        orig_stop_price = round((1-stoploss) * row['Close'], 2)
                        stop_price = round((1-stoploss) * row['Close'], 2)
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                
                
                ###############
                # SELL signal  
                ###############
                        
                # Check if the MA3 is lower than the MA4
                elif row[MA3] < row[MA4]:
                    # If we're currently holding BTC, sell
                    if current_position == "buy":
                        
                        # Update position
                        current_position = "sell"
                        cash = round(sats * row['Close'], 2)
                        cash = (1-BackTester.fees) * cash
                        sats = 0
                        # row_usd = cash
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                        
                        streak = 0
                        
                
                # Record row
                row_sats = sats
                row_usd = cash
                strat_sats.append(row_sats) 
                row_usd = (row_sats * row['Close']) + (row_usd)
                strat_usd.append(row_usd)

            df['maeve_sats'] = strat_sats
            df['maeve_usd'] = strat_usd
            
            

            summary_df = self.strategy_summary(df)
            summary[timeframename] = summary_df
            
            combo = (MA1,MA2,MA3,MA4,stoploss,streaklim,cooldown,trailing)
            
            if len(backtest_df) == 0:
                backtest_df = self.log_backtest_maeve2_t1(combo, timeframename, summary_df)
            else:
                backtest_df = pd.concat([backtest_df, self.log_backtest_maeve2_t1(combo, timeframename, summary_df)])
            
            backtest_df = backtest_df.reset_index(drop=True)
            backtest_df.drop_duplicates(inplace=True)
           
            fig = self.plot_strategy_comparison(df)
            figs[timeframename] = fig
        
        result = float(summary['alltime']['maeve_usd'][-1][:-1])
            
        logging.info(f"{combo} Completed | Profit/Loss: {result}")
        
        return backtest_df, trades_df, figs, summary
     
    
    # MA1,MA2,MA3,MA4,stoploss,streaklim,mult,ATR,trailing
    def maeve2_t2_backtest(self, *args):
        
        MA1,MA2,MA3,MA4,stoploss,streaklim,mult,ATR,trailing = args[0]
        
        # columns=['strategy_id','strategy_type','timeframe','MA1', 'MA2', 'stoploss', 'streaklim', 'cooldown', 'profit/loss']
        backtest_df = pd.DataFrame()
        figs = {}
        figs_strat = {}
        summary = {}
        trades = {}

        for timeframe, timeframename in zip(self.timeframes, self.timeframenames):
            
            # if timeframename != "alltime":
            #     continue
            
            df = self.btc_df[timeframe].reset_index(drop=True)
            
            # Calculate HODL / DCA Performance
            df = self.hodl_dca_perf(df, init_cash=BackTester.init_cash)
            
            # Initialize the strategy variables
            current_position = None  # "buy" or "sell"
            cash = BackTester.init_cash  # Starting cash
            sats = 0  # Starting BTC

            # Strategy logging
            trades_df = pd.DataFrame()
            strat_sats = []
            strat_usd = []

            # Position management
            stop_price = 0
            orig_stop_price = 0
            streak = 0
            idle = 0
            
            # Trade logging 
            trade_trigger = []

            # Iterate over the rows of the dataframe
            for index, row in df.iterrows():
                
                ####################################
                # Set BUY and SELL triggers
                ####################################
                
                BUY_trigger =  row[MA1] > (row[MA2] + (mult * row[ATR])) if streak >= streaklim else row[MA1] > row[MA2]
                SELL_trigger =  row[MA1] < (row[MA2] - (mult * row[ATR])) if streak >= streaklim else row[MA1] < row[MA2] 
                
                
                #######################
                # Position management
                #######################
                
                # Trailing stop loss
                if trailing:
                    new_stop = round((1-stoploss) * row['Close'], 2)
                    if stop_price == orig_stop_price:
                        if new_stop > (stop_price * (1+stoploss)): stop_price = new_stop
                    else:
                        if new_stop > (stop_price * (1+0.01)): stop_price = new_stop
                
                # Check stop loss trigger
                if row['Close'] < stop_price and current_position == "buy":
                    
                    # Update streak
                    if stop_price == orig_stop_price:
                        streak += 1
                    else: 
                        streak = 0
                    
                    # Update position
                    current_position = "sell"
                    cash = round(sats * row['Close'], 2)
                    cash = (1-BackTester.fees) * cash 
                    sats = 0
                    # row_usd = cash

                    # Log trade
                    trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                    trade_trigger.append('STOP')
                    
                    

                ###############
                # BUY signal
                ###############
                
                # Check if the MA1 is higher than the MA2
                if BUY_trigger:
                    # If we're not currently holding any BTC, buy BTC
                    if current_position != "buy":
                        
                        # Update position
                        current_position = "buy"
                        cash = (1-BackTester.fees) * cash
                        sats = round(cash / row['Close'], 8)
                        cash = 0
                        # row_sats = sats
                        
                        # Position management
                        orig_stop_price = round((1-stoploss) * row['Close'], 2)
                        stop_price = round((1-stoploss) * row['Close'], 2)
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                        trade_trigger.append('BUY')
                
                
                ###############
                # SELL signal  
                ###############
                        
                # Check if the MA3 is lower than the MA4
                elif SELL_trigger:
                    # If we're currently holding BTC, sell
                    if current_position == "buy":
                        
                        # Update position
                        current_position = "sell"
                        cash = round(sats * row['Close'], 2)
                        cash = (1-BackTester.fees) * cash
                        sats = 0
                        # row_usd = cash
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                        trade_trigger.append('SELL')
                        
                        streak = 0
                        
                
                # Record row
                row_sats = sats
                row_usd = cash
                strat_sats.append(row_sats) 
                row_usd = (row_sats * row['Close']) + (row_usd)
                strat_usd.append(row_usd)

            df['maeve_sats'] = strat_sats
            df['maeve_usd'] = strat_usd
            
            trades_df['trade_trigger'] = trade_trigger
            
            trades[timeframename] = trades_df
            
            summary_df = self.strategy_summary(df)
            summary[timeframename] = summary_df
            
            combo = (MA1,MA2,MA3,MA4,stoploss,streaklim,mult,ATR,trailing)
            
            if len(backtest_df) == 0:
                backtest_df = self.log_backtest_maeve2_t2(combo, timeframename, summary_df)
            else:
                backtest_df = pd.concat([backtest_df, self.log_backtest_maeve2_t2(combo, timeframename, summary_df)])
            
            backtest_df = backtest_df.reset_index(drop=True)
            backtest_df.drop_duplicates(inplace=True)
           
            fig = self.plot_strategy_comparison(df)
            figs[timeframename] = fig
        
        result = float(summary['alltime']['maeve_usd'][-1][:-1])
            
        logging.info(f"{combo} Completed | Profit/Loss: {result}")
        
        return backtest_df, trades, figs, summary


    # MA1,MA2,mult1,ATR1,MA3,MA4,mult2,ATR2,stoploss,streaklim,trailing
    def maeve2_t3_backtest(self, *args):
        
        MA1,MA2,mult1,ATR1,MA3,MA4,mult2,ATR2,stoploss,streaklim,trailing = args[0]
        combo = (MA1,MA2,mult1,ATR1,MA3,MA4,mult2,ATR2,stoploss,streaklim,trailing)
        
        # columns=['strategy_id','strategy_type','timeframe','MA1', 'MA2', 'stoploss', 'streaklim', 'cooldown', 'profit/loss']
        backtest_df = pd.DataFrame()
        figs = {}
        figs_strat = {}
        summary = {}
        trades = {}

        for timeframe, timeframename in zip(self.timeframes, self.timeframenames):
            
            df = self.btc_df[timeframe].reset_index(drop=True)
            
            # Calculate HODL / DCA Performance
            df = self.hodl_dca_perf(df, init_cash=BackTester.init_cash)
            
            # Initialize the strategy variables
            current_position = None  # "buy" or "sell"
            cash = BackTester.init_cash  # Starting cash
            sats = 0  # Starting BTC

            # Strategy logging
            trades_df = pd.DataFrame()
            strat_sats = []
            strat_usd = []

            # Position management
            stop_price = 0
            orig_stop_price = 0
            streak = 0
            idle = 0
            
            # Trade logging 
            trade_trigger = []

            # Iterate over the rows of the dataframe
            for index, row in df.iterrows():
                
                ####################################
                # Set BUY and SELL triggers
                ####################################
                
                BUY_trigger =  row[MA1] > (row[MA2] + (mult1 * row[ATR1])) if streak >= streaklim else row[MA1] > row[MA2]
                SELL_trigger =  row[MA3] < (row[MA4] - (mult2 * row[ATR2])) if streak >= streaklim else row[MA3] < row[MA4] 
                
                
                #######################
                # Position management
                #######################
                
                # Trailing stop loss
                if trailing:
                    new_stop = round((1-stoploss) * row['Close'], 2)
                    if stop_price == orig_stop_price:
                        if new_stop > (stop_price * (1+stoploss)): stop_price = new_stop
                    else:
                        if new_stop > (stop_price * (1+0.01)): stop_price = new_stop
                
                # Check stop loss trigger
                if row['Close'] < stop_price and current_position == "buy":
                    
                    # Update streak
                    if stop_price == orig_stop_price:
                        streak += 1
                    else: 
                        streak = 0
                    
                    # Update position
                    current_position = "sell"
                    cash = round(sats * row['Close'], 2)
                    cash = (1-BackTester.fees) * cash 
                    sats = 0
                    # row_usd = cash

                    # Log trade
                    trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                    trade_trigger.append('STOP')
                    
                    

                ###############
                # BUY signal
                ###############
                
                # Check if the MA1 is higher than the MA2
                if BUY_trigger:
                    # If we're not currently holding any BTC, buy BTC
                    if current_position != "buy":
                        
                        # Update position
                        current_position = "buy"
                        cash = (1-BackTester.fees) * cash
                        sats = round(cash / row['Close'], 8)
                        cash = 0
                        # row_sats = sats
                        
                        # Position management
                        orig_stop_price = round((1-stoploss) * row['Close'], 2)
                        stop_price = round((1-stoploss) * row['Close'], 2)
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                        trade_trigger.append('BUY')
                
                
                ###############
                # SELL signal  
                ###############
                        
                # Check if the MA3 is lower than the MA4
                elif SELL_trigger:
                    # If we're currently holding BTC, sell
                    if current_position == "buy":
                        
                        # Update position
                        current_position = "sell"
                        cash = round(sats * row['Close'], 2)
                        cash = (1-BackTester.fees) * cash
                        sats = 0
                        # row_usd = cash
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                        trade_trigger.append('SELL')
                        
                        streak = 0
                        
                
                # Record row
                row_sats = sats
                row_usd = cash
                strat_sats.append(row_sats) 
                row_usd = (row_sats * row['Close']) + (row_usd)
                strat_usd.append(row_usd)

            df['maeve_sats'] = strat_sats
            df['maeve_usd'] = strat_usd
            
            trades_df['trade_trigger'] = trade_trigger
            
            trades[timeframename] = trades_df
            
            summary_df = self.strategy_summary(df)
            summary[timeframename] = summary_df
            
            if len(backtest_df) == 0:
                backtest_df = self.log_backtest_maeve2_t3(combo, timeframename, summary_df)
            else:
                backtest_df = pd.concat([backtest_df, self.log_backtest_maeve2_t3(combo, timeframename, summary_df)])
            
            backtest_df = backtest_df.reset_index(drop=True)
            backtest_df.drop_duplicates(inplace=True)
           
            fig = self.plot_strategy_comparison(df)
            figs[timeframename] = fig
        
        result = float(summary['alltime']['maeve_usd'][-1][:-1])
            
        logging.info(f"{combo} Completed | Profit/Loss: {result}")
        
        return backtest_df, trades, figs, summary
    
    
    ################################
    # Backtest Optimizer functions
    ################################    
    
    def maeve2_t1_backtest_obj(self, trial):
        
        params = {
                        "MA1": trial.suggest_categorical("MA1", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
                        "MA2": trial.suggest_categorical("MA2", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
                        "MA3": trial.suggest_categorical("MA3", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
                        "MA4": trial.suggest_categorical("MA4", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
                        "stoploss": trial.suggest_float("stoploss", 0.01, 0.05, step=0.01),
                        "streaklim": trial.suggest_int("streaklim", 1, 6, 1),
                        "cooldown": trial.suggest_int("cooldown", 6, 49, 1),
                        "trailing": trial.suggest_categorical("trailing", [True, False]),
                        }
            
        MA1 = params['MA1']
        MA2 = params['MA2']
        MA3 = params['MA3']
        MA4 = params['MA4']
        stoploss = params['stoploss']
        streaklim = params['streaklim']
        cooldown = params['cooldown']
        trailing = params['trailing']
        
        if MA1 == MA2 or MA3 == MA4:
            return -100
        
        if len(self.backtest_tracker) > 0:
            if (MA1,MA2,MA3,MA4,stoploss,streaklim,cooldown,trailing) in self.backtest_tracker.keys():
                return self.backtest_tracker[(MA1,MA2,MA3,MA4,stoploss,streaklim,cooldown,trailing)]
        
        
            
    
        # columns=['strategy_id','strategy_type','timeframe','MA1', 'MA2', 'stoploss', 'streaklim', 'cooldown', 'profit/loss']
        backtest_df = pd.DataFrame()
        figs = {}
        figs_strat = {}
        summary = {}
        trades = {}

        for timeframe, timeframename in zip(self.timeframes, self.timeframenames):
            
            if timeframename != "alltime":
                continue
            
            df = self.btc_df[timeframe].reset_index(drop=True)
            
            # Calculate HODL / DCA Performance
            df = self.hodl_dca_perf(df, init_cash=BackTester.init_cash)
            
            # Initialize the strategy variables
            current_position = None  # "buy" or "sell"
            cash = BackTester.init_cash  # Starting cash
            sats = 0  # Starting BTC

            # Strategy logging
            trades_df = pd.DataFrame()
            strat_sats = []
            strat_usd = []

            # Position management
            stop_price = 0
            orig_stop_price = 0
            streak = 0
            idle = 0

            # Iterate over the rows of the dataframe
            for index, row in df.iterrows():
                
                ############
                # Cooldown
                ############
                
                if streak >= streaklim:
                    
                    idle +=1
                    strat_sats.append(row_sats)
                    strat_usd.append(row_usd)
                    
                    if idle >= cooldown:
                        streak = 0
                        idle = 0
                        
                    continue
                
                
                #######################
                # Position management
                #######################
                
                # Trailing stop loss
                if trailing:
                    new_stop = round((1-stoploss) * row['Close'], 2)
                    if stop_price == orig_stop_price:
                        if new_stop > (stop_price * (1+stoploss)): stop_price = new_stop
                    else:
                        if new_stop > (stop_price * (1+0.01)): stop_price = new_stop
                
                # Check stop loss trigger
                if row['Close'] < stop_price and current_position == "buy":
                    
                    # Update streak
                    if stop_price == orig_stop_price:
                        streak += 1
                    else: 
                        streak = 0
                    
                    # Update position
                    current_position = "sell"
                    cash = round(sats * row['Close'], 2)
                    cash = (1-BackTester.fees) * cash 
                    sats = 0
                    # row_usd = cash

                    # Log trade
                    trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                    
                    

                ###############
                # BUY signal
                ###############
                
                # Check if the MA1 is higher than the MA2
                if row[MA1] > row[MA2]:
                    # If we're not currently holding any BTC, buy BTC
                    if current_position != "buy":
                        
                        # Update position
                        current_position = "buy"
                        cash = (1-BackTester.fees) * cash
                        sats = round(cash / row['Close'], 8)
                        cash = 0
                        # row_sats = sats
                        
                        # Position management
                        orig_stop_price = round((1-stoploss) * row['Close'], 2)
                        stop_price = round((1-stoploss) * row['Close'], 2)
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                
                
                ###############
                # SELL signal  
                ###############
                        
                # Check if the MA3 is lower than the MA4
                elif row[MA3] < row[MA4]:
                    # If we're currently holding BTC, sell
                    if current_position == "buy":
                        
                        # Update position
                        current_position = "sell"
                        cash = round(sats * row['Close'], 2)
                        cash = (1-BackTester.fees) * cash
                        sats = 0
                        # row_usd = cash
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                        
                        streak = 0
                        
                
                # Record row
                row_sats = sats
                row_usd = cash
                strat_sats.append(row_sats) 
                row_usd = (row_sats * row['Close']) + (row_usd)
                strat_usd.append(row_usd)

            df['maeve_sats'] = strat_sats
            df['maeve_usd'] = strat_usd
            
            

            summary_df = self.strategy_summary(df)
            summary[timeframename] = summary_df
            
            combo = (MA1,MA2,MA3,MA4,stoploss,streaklim,cooldown,trailing)
            
            if len(backtest_df) == 0:
                backtest_df = self.log_backtest_maeve2_t1(combo, timeframename, summary_df)
            else:
                backtest_df = pd.concat([backtest_df, self.log_backtest_maeve2_t1(combo, timeframename, summary_df)])
            
            backtest_df = backtest_df.reset_index(drop=True)
            backtest_df.drop_duplicates(inplace=True)
           
            fig = self.plot_strategy_comparison(df)
            figs[timeframename] = fig
        
        result = float(summary['alltime']['maeve_usd'][-1][:-1])
            
        logging.info(f"{combo} Completed | Profit/Loss: {result}")
        
        self.backtest_tracker[(MA1,MA2,MA3,MA4,stoploss,streaklim,cooldown,trailing)] = result
        return result


    def maeve2_t2_backtest_obj(self, trial):
        
        params = {
                    "MA1": trial.suggest_categorical("MA1", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
                    "MA2": trial.suggest_categorical("MA2", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
                    "MA3": trial.suggest_categorical("MA3", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
                    "MA4": trial.suggest_categorical("MA4", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
                    "stoploss": trial.suggest_float("stoploss", 0.01, 0.05, step=0.01),
                    "streaklim": trial.suggest_int("streaklim", 0, 6, 1),
                    "mult": trial.suggest_float("mult", 0.1, 5, step=0.1),
                    "ATR": trial.suggest_categorical("ATR", ['ATR5','ATR7','ATR10','ATR14','ATR15','ATR20','ATR21','ATR25','ATR28','ATR30','ATR35','ATR40','ATR42',
                                                             'ATR45','ATR49','ATR50','ATR56','ATR63','ATR70']),
                    "trailing": trial.suggest_categorical("trailing", [True, False]),
                    }
            
        MA1 = params['MA1']
        MA2 = params['MA2']
        MA3 = params['MA3']
        MA4 = params['MA4']
        stoploss = params['stoploss']
        streaklim = params['streaklim']
        mult = params['mult']
        ATR = params['ATR']
        trailing = params['trailing']
        
        if MA1 == MA2 or MA3 == MA4:
            return -100
        
        if len(self.backtest_tracker) > 0:
            if (MA1,MA2,MA3,MA4,stoploss,streaklim,mult,ATR,trailing) in self.backtest_tracker.keys():
                return self.backtest_tracker[(MA1,MA2,MA3,MA4,stoploss,streaklim,mult,ATR,trailing)]
        
        
            
    
        # columns=['strategy_id','strategy_type','timeframe','MA1','MA2','MA3','MA4','stoploss','streaklim','mult','ATR','trailing','profit/loss']
        backtest_df = pd.DataFrame()
        figs = {}
        figs_strat = {}
        summary = {}
        trades = {}

        for timeframe, timeframename in zip(self.timeframes, self.timeframenames):
            
            if timeframename != "alltime":
                continue
            
            df = self.btc_df[timeframe].reset_index(drop=True)
            
            # Calculate HODL / DCA Performance
            df = self.hodl_dca_perf(df, init_cash=BackTester.init_cash)
            
            # Initialize the strategy variables
            current_position = None  # "buy" or "sell"
            cash = BackTester.init_cash  # Starting cash
            sats = 0  # Starting BTC

            # Strategy logging
            trades_df = pd.DataFrame()
            strat_sats = []
            strat_usd = []

            # Position management
            stop_price = 0
            orig_stop_price = 0
            streak = 0
            idle = 0

            # Iterate over the rows of the dataframe
            for index, row in df.iterrows():
                
                ####################################
                # Set BUY and SELL triggers
                ####################################
                
                BUY_trigger =  row[MA1] > (row[MA2] + (mult * row[ATR])) if streak >= streaklim else row[MA1] > row[MA2]
                SELL_trigger =  row[MA1] < (row[MA2] - (mult * row[ATR])) if streak >= streaklim else row[MA1] < row[MA2] 
                
                
                #######################
                # Position management
                #######################
                
                # Trailing stop loss
                if trailing:
                    new_stop = round((1-stoploss) * row['Close'], 2)
                    if stop_price == orig_stop_price:
                        if new_stop > (stop_price * (1+stoploss)): stop_price = new_stop
                    else:
                        if new_stop > (stop_price * (1+0.01)): stop_price = new_stop
                
                # Check stop loss trigger
                if row['Close'] < stop_price and current_position == "buy":
                    
                    # Update streak
                    if stop_price == orig_stop_price:
                        streak += 1
                    else: 
                        streak = 0
                    
                    # Update position
                    current_position = "sell"
                    cash = round(sats * row['Close'], 2)
                    cash = (1-BackTester.fees) * cash 
                    sats = 0
                    # row_usd = cash

                    # Log trade
                    trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                    
                    

                ###############
                # BUY signal
                ###############
                
                # Check if the MA1 is higher than the MA2
                if BUY_trigger:
                    # If we're not currently holding any BTC, buy BTC
                    if current_position != "buy":
                        
                        # Update position
                        current_position = "buy"
                        cash = (1-BackTester.fees) * cash
                        sats = round(cash / row['Close'], 8)
                        cash = 0
                        # row_sats = sats
                        
                        # Position management
                        orig_stop_price = round((1-stoploss) * row['Close'], 2)
                        stop_price = round((1-stoploss) * row['Close'], 2)
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                
                
                ###############
                # SELL signal  
                ###############
                        
                # Check if the MA3 is lower than the MA4
                elif SELL_trigger:
                    # If we're currently holding BTC, sell
                    if current_position == "buy":
                        
                        # Update position
                        current_position = "sell"
                        cash = round(sats * row['Close'], 2)
                        cash = (1-BackTester.fees) * cash
                        sats = 0
                        # row_usd = cash
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                        
                        streak = 0
                        
                
                # Record row
                row_sats = sats
                row_usd = cash
                strat_sats.append(row_sats) 
                row_usd = (row_sats * row['Close']) + (row_usd)
                strat_usd.append(row_usd)

            df['maeve_sats'] = strat_sats
            df['maeve_usd'] = strat_usd
            
            

            summary_df = self.strategy_summary(df)
            summary[timeframename] = summary_df
            
            combo = (MA1,MA2,MA3,MA4,stoploss,streaklim,mult,ATR,trailing)
            
            if len(backtest_df) == 0:
                backtest_df = self.log_backtest_maeve2_t2(combo, timeframename, summary_df)
            else:
                backtest_df = pd.concat([backtest_df, self.log_backtest_maeve2_t2(combo, timeframename, summary_df)])
            
            backtest_df = backtest_df.reset_index(drop=True)
            backtest_df.drop_duplicates(inplace=True)
           
            fig = self.plot_strategy_comparison(df)
            figs[timeframename] = fig
        
        result = float(summary['alltime']['maeve_usd'][-1][:-1])
            
        logging.info(f"{combo} Completed | Profit/Loss: {result}")
        
        self.backtest_tracker[(MA1,MA2,MA3,MA4,stoploss,streaklim,mult,ATR,trailing)] = result
        return result


    def maeve2_t3_backtest_obj(self, trial):
        
        # 1
        # params = {
        #             # BUY signal
        #             "MA1": trial.suggest_categorical("MA1", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
        #             "MA2": trial.suggest_categorical("MA2", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
        #             "mult1": trial.suggest_float("mult1", 0, 5.1, step=0.1),
        #             "ATR1": trial.suggest_categorical("ATR1", ['ATR5','ATR7','ATR10','ATR14','ATR15','ATR20','ATR21','ATR25','ATR28','ATR30','ATR35','ATR40','ATR42',
        #                                                      'ATR45','ATR49','ATR50','ATR56','ATR63','ATR70']),
                    
        #             # SELL signal
        #             "MA3": trial.suggest_categorical("MA3", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
        #             "MA4": trial.suggest_categorical("MA4", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60', 'MA100', 'MA200']),
        #             "mult2": trial.suggest_float("mult2", 0, 5.1, step=0.1),
        #             "ATR2": trial.suggest_categorical("ATR2", ['ATR5','ATR7','ATR10','ATR14','ATR15','ATR20','ATR21','ATR25','ATR28','ATR30','ATR35','ATR40','ATR42',
        #                                                      'ATR45','ATR49','ATR50','ATR56','ATR63','ATR70']),
                    
        #             # Position management
        #             "stoploss": trial.suggest_float("stoploss", 0.01, 0.05, step=0.01),
        #             "streaklim": trial.suggest_int("streaklim", 0, 6, 1),
        #             "trailing": trial.suggest_categorical("trailing", [True, False]),
        #             }
        
        
        # 2
        # params = {
        #             # BUY signal
        #             "MA1": trial.suggest_categorical("MA1", ['MA8', 'MA12', 'MA20', 'MA21']),
        #             "MA2": trial.suggest_categorical("MA2", ['MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60']),
        #             "mult1": trial.suggest_float("mult1", 0, 5, step=0.1),
        #             "ATR1": trial.suggest_categorical("ATR1", ['ATR30','ATR35','ATR40','ATR42',
        #                                                      'ATR45','ATR49','ATR50','ATR56']),
                    
        #             # SELL signal
        #             "MA3": trial.suggest_categorical("MA3", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60']),
        #             "MA4": trial.suggest_categorical("MA4", ['MA8', 'MA12', 'MA20', 'MA21', 'MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60']),
        #             "mult2": trial.suggest_float("mult2", 0, 2.5, step=0.1),
        #             "ATR2": trial.suggest_categorical("ATR2", ['ATR14','ATR21','ATR28','ATR35','ATR42',
        #                                                      'ATR49','ATR56']),
                    
        #             # Position management
        #             "stoploss": trial.suggest_float("stoploss", 0.03, 0.05, step=0.01),
        #             "streaklim": trial.suggest_int("streaklim", 0, 3, 1),
        #             "trailing": trial.suggest_categorical("trailing", [True]),
        #             }
        
        # 3
        params = {
                    # BUY signal
                    "MA1": trial.suggest_categorical("MA1", ['MA8', 'MA12', 'MA20', 'MA21']),
                    "MA2": trial.suggest_categorical("MA2", ['MA24', 'MA30', 'MA40', 'MA48']),
                    "mult1": trial.suggest_float("mult1", 2, 4, step=0.1),
                    "ATR1": trial.suggest_categorical("ATR1", ['ATR30','ATR35','ATR40','ATR42',
                                                             'ATR45','ATR49','ATR50','ATR56']),
                    
                    # SELL signal
                    "MA3": trial.suggest_categorical("MA3", ['MA24', 'MA30', 'MA40', 'MA48', 'MA50', 'MA60']),
                    "MA4": trial.suggest_categorical("MA4", ['MA30', 'MA40', 'MA48', 'MA50', 'MA60']),
                    "mult2": trial.suggest_float("mult2", 0, 2.5, step=0.1),
                    "ATR2": trial.suggest_categorical("ATR2", ['ATR14','ATR21','ATR28','ATR35','ATR42',
                                                             'ATR49','ATR56']),
                    
                    # Position management
                    "stoploss": trial.suggest_float("stoploss", 0.04, 0.05, step=0.01),
                    "streaklim": trial.suggest_int("streaklim", 0, 1, 1),
                    "trailing": trial.suggest_categorical("trailing", [True]),
                    }
        
        
        # BUY    
        MA1 = params['MA1']
        MA2 = params['MA2']
        mult1 = params['mult1']
        ATR1 = params['ATR1']
        
        # SELL
        MA3 = params['MA3']
        MA4 = params['MA4']
        mult2 = params['mult2']
        ATR2 = params['ATR2']
        
        # Position management
        trailing = params['trailing']
        stoploss = params['stoploss']
        streaklim = params['streaklim']
        
        # Parameter combo
        combo = (MA1,MA2,mult1,ATR1,MA3,MA4,mult2,ATR2,stoploss,streaklim,trailing)
        
        
        if MA1 == MA2 or MA3 == MA4:
            return -100
        
        if len(self.backtest_tracker) > 0:
            if combo in self.backtest_tracker.keys():
                return self.backtest_tracker[combo]
        
        
            
    
        backtest_df = pd.DataFrame()
        figs = {}
        figs_strat = {}
        summary = {}
        trades = {}

        for timeframe, timeframename in zip(self.timeframes, self.timeframenames):
            
            if timeframename != "alltime":
                continue
            
            df = self.btc_df[timeframe].reset_index(drop=True)
            
            # Calculate HODL / DCA Performance
            df = self.hodl_dca_perf(df, init_cash=BackTester.init_cash)
            
            # Initialize the strategy variables
            current_position = None  # "buy" or "sell"
            cash = BackTester.init_cash  # Starting cash
            sats = 0  # Starting BTC

            # Strategy logging
            trades_df = pd.DataFrame()
            strat_sats = []
            strat_usd = []

            # Position management
            stop_price = 0
            orig_stop_price = 0
            streak = 0
            idle = 0

            # Iterate over the rows of the dataframe
            for index, row in df.iterrows():
                
                ####################################
                # BUY and SELL triggers
                ####################################
                
                BUY_trigger =  row[MA1] > (row[MA2] + (mult1 * row[ATR1])) if streak >= streaklim else row[MA1] > row[MA2]
                SELL_trigger =  row[MA3] < (row[MA4] - (mult2 * row[ATR2])) if streak >= streaklim else row[MA3] < row[MA4]
                
                
                #######################
                # Position management
                #######################
                
                # Trailing stop loss
                if trailing:
                    new_stop = round((1-stoploss) * row['Close'], 2)
                    if stop_price == orig_stop_price:
                        if new_stop > (stop_price * (1+stoploss)): stop_price = new_stop
                    else:
                        if new_stop > (stop_price * (1+0.01)): stop_price = new_stop
                
                # Check stop loss trigger
                if row['Close'] < stop_price and current_position == "buy":
                    
                    # Update streak
                    if stop_price == orig_stop_price:
                        streak += 1
                    else: 
                        streak = 0
                    
                    # Update position
                    current_position = "sell"
                    cash = round(sats * row['Close'], 2)
                    cash = (1-BackTester.fees) * cash 
                    sats = 0
                    # row_usd = cash

                    # Log trade
                    trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                    
                    

                ###############
                # BUY signal
                ###############
                
                # Check if the MA1 is higher than the MA2
                if BUY_trigger:
                    # If we're not currently holding any BTC, buy BTC
                    if current_position != "buy":
                        
                        # Update position
                        current_position = "buy"
                        cash = (1-BackTester.fees) * cash
                        sats = round(cash / row['Close'], 8)
                        cash = 0
                        # row_sats = sats
                        
                        # Position management
                        orig_stop_price = round((1-stoploss) * row['Close'], 2)
                        stop_price = round((1-stoploss) * row['Close'], 2)
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                
                
                ###############
                # SELL signal  
                ###############
                        
                # Check if the MA3 is lower than the MA4
                elif SELL_trigger:
                    # If we're currently holding BTC, sell
                    if current_position == "buy":
                        
                        # Update position
                        current_position = "sell"
                        cash = round(sats * row['Close'], 2)
                        cash = (1-BackTester.fees) * cash
                        sats = 0
                        # row_usd = cash
                        
                        # Log trade
                        trades_df = pd.concat([trades_df, self.log_trade(row, current_position, cash, sats)])
                        
                        streak = 0
                        
                
                # Record row
                row_sats = sats
                row_usd = cash
                strat_sats.append(row_sats) 
                row_usd = (row_sats * row['Close']) + (row_usd)
                strat_usd.append(row_usd)

            df['maeve_sats'] = strat_sats
            df['maeve_usd'] = strat_usd
            
            

            summary_df = self.strategy_summary(df)
            summary[timeframename] = summary_df
            
            if len(backtest_df) == 0:
                backtest_df = self.log_backtest_maeve2_t3(combo, timeframename, summary_df)
            else:
                backtest_df = pd.concat([backtest_df, self.log_backtest_maeve2_t3(combo, timeframename, summary_df)])
            
            backtest_df = backtest_df.reset_index(drop=True)
            backtest_df.drop_duplicates(inplace=True)
           
            fig = self.plot_strategy_comparison(df)
            figs[timeframename] = fig
        
        result = float(summary['alltime']['maeve_usd'][-1][:-1])
            
        logging.info(f"{combo} Completed | Profit/Loss: {result}")
        
        self.backtest_tracker[combo] = result
        return result

     
    #######################
    # Run Backtest study
    #######################   
    
    def run_maeve_backtest_opt(self, params):
        
        logging.info("######################")
        logging.info(f"{params['func'].lstrip('self.').rstrip('_obj').upper()}")
        logging.info("######################")
        
        params['func'] = eval(params['func'])
        
        study = optuna.create_study(direction='maximize')
        study.optimize(**params)
        return study
    
    
    



  