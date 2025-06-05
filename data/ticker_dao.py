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

    def get_ticker_data(self, ticker_id):
        """
        Get comprehensive data for a specific ticker including latest price.
        
        Args:
            ticker_id (int): The ID of the ticker to retrieve data for
            
        Returns:
            dict: A dictionary containing ticker data including last_price and other details
        """
        try:
            # First get basic ticker information
            cursor = self.current_connection.cursor(dictionary=True)
            
            # Start with a basic query that should work regardless of schema changes
            ticker_query = """
                SELECT id, ticker, ticker_name, industry, sector
                FROM investing.tickers 
                WHERE id = %s
            """
            cursor.execute(ticker_query, (ticker_id,))
            ticker_info = cursor.fetchone()
            
            if not ticker_info:
                return None
            
            # Set a default trend value
            ticker_info['trend'] = None
            
            # Now try to get the trend column if it exists
            try:
                trend_query = "SELECT trend FROM investing.tickers WHERE id = %s"
                cursor.execute(trend_query, (ticker_id,))
                trend_result = cursor.fetchone()
                if trend_result and 'trend' in trend_result:
                    ticker_info['trend'] = trend_result['trend']
            except mysql.connector.Error as column_err:
                # If trend column doesn't exist or other error, we already have a default value
                if column_err.errno != 1054:  # If it's not just an unknown column error
                    print(f"Warning: Error retrieving trend data: {column_err}")
                
            # Get the latest activity data
            latest_activity_query = """
                SELECT activity_date, open, close, high, low, volume
                FROM investing.activity 
                WHERE ticker_id = %s 
                ORDER BY activity_date DESC 
                LIMIT 1
            """
            cursor.execute(latest_activity_query, (ticker_id,))
            latest_activity = cursor.fetchone()
            
            cursor.close()
            
            # Combine the data
            result = ticker_info
            if latest_activity:
                result['last_price'] = float(latest_activity['close'])
                result['last_update'] = latest_activity['activity_date']
            else:
                # Fall back to a default price if no activity data is available
                result['last_price'] = 0.0
                result['last_update'] = None
                
            return result
            
        except mysql.connector.Error as err:
            print(f"Database error in get_ticker_data: {err}")
            return None
        except Exception as e:
            print(f"Error in get_ticker_data: {str(e)}")
            return None
