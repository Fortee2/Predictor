from datetime import date
import mysql.connector
from mysql.connector import errorcode
import pandas as pd

class ticker_dao:

    def __init__(self, user, password, host, database):
        self.db_user = user
        self.db_password = password
        self.db_host = host
        self.db_name = database

        self.current_connection = None
    
    def open_connection(self):
        self.currenct_connection = mysql.connector.connect(user=self.db_user, 
                      password=self.db_password,
                      host=self.db_host,
                      database=self.db_name)

    def close_connection(self):
       self.currenct_connection.close()

    def retrieveTickerList(self):
        try:
            cursor = self.currenct_connection.cursor()
            
            query = 'SELECT ticker, ticker_name, tick.id, industry, sector FROM investing.tickers tick left join (select ticker_id, max(activity_date) as maxDate from investing.activity group by ticker_id) act on tick.id = act.ticker_id order by in_portfolio desc, maxDate;'

            cursor.execute(query)
            df_ticks = pd.DataFrame(cursor.fetchall())
        
            self.currenct_connection.commit()
            cursor.close()
            
            return df_ticks
        except mysql.connector.Error as err:
            print(err)
   
    def insertStock(self, ticker, ticker_name):
        try:
            cursor = self.currenct_connection.cursor()
            
            query = 'INSERT INTO tickers (ticker, ticker_name, trend, close, in_portfolio) values (%s,%s,%s,%s,%s)'
            cursor.execute(query, (ticker, ticker_name,'unknown', 0, False))

            self.currenct_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def updateStockTrend(self,trend, close, ticker):
        try:
            cursor = self.currenct_connection.cursor()
            
            query = 'UPDATE tickers SET trend = %s, close =%s WHERE ticker = %s'
            cursor.execute(query, (trend, float(close), ticker))

            self.currenct_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def updateStock(self, symbol, name, industry, sector):
        try:
            cursor = self.currenct_connection.cursor()
            
            query = 'UPDATE tickers SET ticker_name = %s, industry =%s, sector=%s WHERE ticker = %s'
            cursor.execute(query, (name, industry, sector, symbol))

            self.currenct_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def updateTradeHistory(self, ticker_id, activity_date, open, close, volume, high, low):
        try:
            rsi_state = '' #going to leave it blank if there is no change in price
            
            if(open > close):
                rsi_state = 'down'
            elif(close > open):
                rsi_state =  'up'
            
            #check to see if the record already exists
            df = self.retrieve_ticker_activity_by_day(ticker_id, activity_date);
            
            if(df.empty):
                cursor = self.currenct_connection.cursor(prepared=True)
            
                query = 'INSERT INTO investing.activity (ticker_id,activity_date,open,close,volume,updown, high, low) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
                cursor.execute(query, (int(ticker_id), str(activity_date), float(open), float(close), float(volume), rsi_state,  float(high), float(low)))
            
                self.currenct_connection.commit()
                cursor.close()
                
        except mysql.connector.Error as err:
            print(err)

    def retrieveTickerActivity(self,ticker_id):
        try:
            cursor = self.currenct_connection.cursor()
            
            query = "SELECT ticker_id, activity_date, open, close, volume, updown, high, low FROM investing.activity  WHERE ticker_id = %s order by activity_date asc"
            
            cursor.execute(query,(int(ticker_id),))
            df = pd.DataFrame(cursor.fetchall(), columns= ['ticker_id', 'activity_date', 'open', 'close', 'volume', 'updown' ,'high', 'low'])
            df = df.set_index('activity_date')

            cursor.close()
            
            return df
        except mysql.connector.Error as err:
            print(err)
            
    def retrieve_ticker_activity_by_day(self,ticker_id, activity_date):
        try:
            cursor = self.currenct_connection.cursor()
            
            query = "SELECT ticker_id, activity_date, open, close, volume, updown, high, low FROM investing.activity  WHERE ticker_id = %s and activity_date = %s order by activity_date asc"
            
            cursor.execute(query,(int(ticker_id), date(activity_date)))
            df = pd.DataFrame(cursor.fetchall(), columns= ['ticker_id', 'activity_date', 'open', 'close', 'volume', 'updown' ,'high', 'low'])
            df = df.set_index('activity_date')

            cursor.close()
            
            return df
        except mysql.connector.Error as err:
            print(err)

    def retrieveLastActivityDate(self,ticker_id):
        try:
            cursor = self.currenct_connection.cursor()
            
            query = "SELECT max(activity_date) FROM investing.activity  WHERE ticker_id = %s order by activity_date desc limit 1"
            
            cursor.execute(query,(int(ticker_id),))
            df_last = pd.DataFrame(cursor.fetchall())
        
            self.currenct_connection.commit()
            cursor.close()
            
            return df_last
        except mysql.connector.Error as err:
            print(err)

    def retrieveLastRSI(self,ticker_id):
        try:
            cursor = self.currenct_connection.cursor()
            
            query = "SELECT activity_date, rsi FROM investing.rsi  WHERE ticker_id = %s order by activity_date desc limit 10"
            
            cursor.execute(query,(int(ticker_id),))
            df_last = pd.DataFrame(cursor.fetchall(), columns=['activity_date','rsi'])
        
            cursor.close()
            
            return df_last
        except mysql.connector.Error as err:
            print(err)