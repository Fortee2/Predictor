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
        self.current_connection = mysql.connector.connect(user=self.db_user, 
                      password=self.db_password,
                      host=self.db_host,
                      database=self.db_name)

    def close_connection(self):
       self.current_connection.close()

    def retrieve_ticker_list(self):
        try:
            cursor = self.current_connection.cursor()
            
            query = 'SELECT ticker, ticker_name, tick.id, industry, sector FROM investing.tickers tick INNER JOIN investing.portfolio port on port.ticker_id = tick.id left join (select ticker_id, max(activity_date) as maxDate from investing.activity group by ticker_id) act on tick.id = act.ticker_id  where port.active = 1 order by maxDate;'

            cursor.execute(query)
            df_ticks = pd.DataFrame(cursor.fetchall())
        
            self.current_connection.commit()
            cursor.close()
            
            return df_ticks
        except mysql.connector.Error as err:
            print(err)
   
    def insert_stock(self, ticker, ticker_name):
        try:
            cursor = self.current_connection.cursor()
            
            query = 'INSERT INTO tickers (ticker, ticker_name, trend, close) values (%s,%s,%s,%s)'
            cursor.execute(query, (ticker, ticker_name,'unknown', 0))

            self.current_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def update_stock_trend(self,trend, close, ticker):
        try:
            cursor = self.current_connection.cursor()
            
            query = 'UPDATE tickers SET trend = %s, close =%s WHERE ticker = %s'
            cursor.execute(query, (trend, float(close), ticker))

            self.current_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def ticker_delisted(self, ticker):
        """_summary_
        Set a ticker to inactive in the database
        Args:
            ticker (_type_): _description_
        """
        try:
            cursor = self.current_connection.cursor()
            
            query = 'UPDATE tickers SET active = 0 WHERE ticker = %s'
            cursor.execute(query, (ticker))

            self.current_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def update_stock(self, symbol, name, industry, sector):
        try:
            cursor = self.current_connection.cursor()
            
            query = 'UPDATE tickers SET ticker_name = %s, industry =%s, sector=%s WHERE ticker = %s'
            cursor.execute(query, (name, industry, sector, symbol))

            self.current_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def get_ticker_id(self, symbol):
        try:
            cursor = self.current_connection.cursor()
            query = "SELECT id FROM tickers WHERE ticker = %s"
            cursor.execute(query, (symbol,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result[0]
            else:
                return None
        except mysql.connector.Error as err:
            print(err)
            return None

    def get_ticker_symbol(self, ticker_id):
        try:
            cursor = self.current_connection.cursor()
            query = "SELECT ticker FROM tickers WHERE id = %s"
            cursor.execute(query, (ticker_id,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result[0]
            else:
                return None
        except mysql.connector.Error as err:
            print(err)
            return None

    def get_ticker_industry(self, ticker_id):
        try:
            cursor = self.current_connection.cursor()
            query = "SELECT industry FROM tickers WHERE id = %s"
            cursor.execute(query, (ticker_id,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result[0]
            else:
                return None
        except mysql.connector.Error as err:
            print(err)
            return None

    def update_trade_history(self, ticker_id, activity_date, open, close, volume, high, low):
        try:
            rsi_state = '' #going to leave it blank if there is no change in price
            
            if(open > close):
                rsi_state = 'down'
            elif(close > open):
                rsi_state =  'up'
            
            #check to see if the record already exists
            df = self.retrieve_ticker_activity_by_day(ticker_id, activity_date);
            
            if(df.empty):
                cursor = self.current_connection.cursor(prepared=True)
            
                query = 'INSERT INTO investing.activity (ticker_id,activity_date,open,close,volume,updown, high, low) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
                cursor.execute(query, (int(ticker_id), str(activity_date), float(open), float(close), float(volume), rsi_state,  float(high), float(low)))
            
                self.current_connection.commit()
                cursor.close()
                
        except mysql.connector.Error as err:
            print(err)

    def retrieve_ticker_activity(self,ticker_id):
        try:
            cursor = self.current_connection.cursor()
            
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
            cursor = self.current_connection.cursor()
            
            query = "SELECT ticker_id, activity_date, open, close, volume, updown, high, low FROM investing.activity  WHERE ticker_id = %s and activity_date = %s order by activity_date asc"
            
            cursor.execute(query,(int(ticker_id),  activity_date.strftime('%Y-%m-%d')))
            df = pd.DataFrame(cursor.fetchall(), columns= ['ticker_id', 'activity_date', 'open', 'close', 'volume', 'updown' ,'high', 'low'])
            df = df.set_index('activity_date')

            cursor.close()
            
            return df
        except mysql.connector.Error as err:
            print(err)

    def retrieve_last_activity_date(self,ticker_id):
        try:
            cursor = self.current_connection.cursor()
            
            query = "SELECT max(activity_date) FROM investing.activity  WHERE ticker_id = %s order by activity_date desc limit 1"
            
            cursor.execute(query,(int(ticker_id),))
            df_last = pd.DataFrame(cursor.fetchall())
        
            self.current_connection.commit()
            cursor.close()
            
            return df_last
        except mysql.connector.Error as err:
            print(err)

    def retrieve_last_rsi(self,ticker_id):
        try:
            cursor = self.current_connection.cursor()
            
            query = "SELECT activity_date, rsi FROM investing.rsi  WHERE ticker_id = %s order by activity_date desc limit 10"
            
            cursor.execute(query,(int(ticker_id),))
            df_last = pd.DataFrame(cursor.fetchall(), columns=['activity_date','rsi'])
        
            cursor.close()
            
            return df_last
        except mysql.connector.Error as err:
            print(err)
