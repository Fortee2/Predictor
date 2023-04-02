import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date
from datetime import timedelta
from dotenv import load_dotenv
import os
import time

#import sys  
#sys.path.insert(0, 'finance')

import ticker_dao
#import rsi_calculations as rsi_calc

class StockActivity:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.dao = ticker_dao.ticker_dao(db_user, db_password, db_host, db_name)
        self.dao.open_connection()

    def update_ticker_data(self,symbol):
        ticker = yf.Ticker(symbol)
        self.dao.updateStock(symbol, ticker.get('shortName'), ticker.get('industry'), ticker.get('sector'))
    
    def update_ticker_history(self, symbol, id):
        ticker = yf.Ticker(symbol)

        df_last_date = self.dao.retrieveLastActivityDate(id)
        start = date.today() - timedelta(weeks=520)  #create window with enough room for 50 day moving average

        if df_last_date.iloc[0,0] != None:
            start = df_last_date.iloc[0,0] + timedelta(days=1)
        
        end = date.today() + timedelta(days=1) 
        try:
            hist = ticker.history(interval="1d",start=start,end=end)
            print(hist)

            for i in range(len(hist)):    
                idx = hist.index[i]

                self.dao.updateTradeHistory(id, idx, hist.loc[idx,'Open'], hist.loc[idx,'Close'], hist.loc[idx,'Volume'], hist.loc[idx,'High'], hist.loc[idx,'Low'])
        except Exception as e:
            print(e)
            time.sleep(120)
            print('Sleeping from failure')
        
    def retrieve_ticker_history(self, id):    
        return self.dao.retrieve_ticker_activity(ticker_id=id)

    def update_stock_activity(self):
        df_ticker_list = self.dao.retrieve_ticker_list()
        print(df_ticker_list)
        count = 0

        for i in range(len(df_ticker_list)):
            stock_ticker = df_ticker_list.loc[i,0]
            ticker_name = df_ticker_list.loc[i,1]
            ticker_id = df_ticker_list.loc[i,2]
            industry= df_ticker_list.loc[i,3]
            sector = df_ticker_list.loc[i,4]

            print(stock_ticker)
            print(industry)
            
            if industry == None:
                self.update_ticker_data(stock_ticker)
            
            self.update_ticker_history(stock_ticker,ticker_id)
            count = count + 1
            
            if count == 3:
                time.sleep(120)
                print('Sleeping')
                count = 0
        # rsi.calculateRSI(ticker_id)
       
def main():
    load_dotenv()
    
    stock_activity = StockActivity(os.getenv('DB_USER'), os.getenv('DB_PASS'), os.getenv('DB_HOST'), os.getenv('DB_NAME'))
    stock_activity.update_stock_activity()
    
if __name__ == "__main__":
    main()