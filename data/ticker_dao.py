from datetime import date
import mysql.connector
from mysql.connector import errorcode
import pandas as pd

class TickerDao:

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
            
            query = 'SELECT ticker, ticker_name, id, industry, sector FROM investing.tickers ORDER BY ticker;'

            cursor.execute(query)
            results = cursor.fetchall()
            if not results:
                return pd.DataFrame()
            
            df_ticks = pd.DataFrame(results, columns=['ticker', 'ticker_name', 'id', 'industry', 'sector'])
        
            self.current_connection.commit()
            cursor.close()
            
            return df_ticks
        except mysql.connector.Error as err:
            print(err)
   
    def insert_stock(self, ticker, ticker_name):
        try:
            cursor = self.current_connection.cursor()
            
            query = '''INSERT INTO investing.tickers 
                      (ticker, ticker_name, industry, sector) 
                      VALUES (%s, %s, %s, %s)'''
            cursor.execute(query, (ticker, ticker_name, None, None))

            self.current_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def update_stock_trend(self,trend, close, ticker):
        try:
            cursor = self.current_connection.cursor()
            
            query = 'UPDATE investing.tickers SET trend = %s, close =%s WHERE ticker = %s'
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
            
            query = 'UPDATE investing.tickers SET trend = %s WHERE ticker = %s'
            cursor.execute(query, ('delisted', ticker))

            self.current_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def update_stock(self, symbol, name, industry, sector):
        try:
            cursor = self.current_connection.cursor()
            
            query = 'UPDATE investing.tickers SET ticker_name = %s, industry =%s, sector=%s WHERE ticker = %s'
            cursor.execute(query, (name, industry, sector, symbol))

            self.current_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err)

    def get_ticker_id(self, symbol):
        try:
            cursor = self.current_connection.cursor()
            query = "SELECT id FROM investing.tickers WHERE ticker = %s"
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
            query = "SELECT ticker FROM investing.tickers WHERE id = %s"
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
            query = "SELECT industry FROM investing.tickers WHERE id = %s"
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

    def update_activity(self, ticker_id, activity_date, open, close, volume, high, low):
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
            else:
                if(df['close'].values[0] != close):
                    cursor = self.current_connection.cursor(prepared=True)
            
                    query = 'UPDATE investing.activity SET open = ?, close = ?, volume = ?, updown = ?, high = ?, low = ? WHERE ticker_id = ? and activity_date = ?'
                    cursor.execute(query, (float(open), float(close), float(volume), rsi_state, float(high), float(low), int(ticker_id), str(activity_date)))
            
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
            
            query = """
                SELECT activity_date, open, close, volume, updown, high, low 
                FROM investing.activity 
                WHERE ticker_id = %s 
                ORDER BY activity_date DESC 
                LIMIT 1
            """
            
            cursor.execute(query,(int(ticker_id),))
            df_last = pd.DataFrame(cursor.fetchall(), columns=['activity_date', 'open', 'close', 'volume', 'updown', 'high', 'low'])
        
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
