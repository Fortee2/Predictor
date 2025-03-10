import mysql.connector
from mysql.connector import errorcode
from datetime import datetime
import pandas as pd

class NewsSentimentDAO:
    def __init__(self, user, password, host, database):
        self.db_user = user
        self.db_password = password
        self.db_host = host
        self.db_name = database
        self.current_connection = None

    def open_connection(self):
        """Opens a connection to the database"""
        self.current_connection = mysql.connector.connect(
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            database=self.db_name
        )

    def close_connection(self):
        """Closes the database connection"""
        if self.current_connection:
            self.current_connection.close()

    def save_sentiment(self, ticker_id, headline, publisher, publish_date, sentiment_score, confidence, article_link):
        """
        Saves news sentiment data for a ticker to the database
        """
        try:
            cursor = self.current_connection.cursor()
            
            sql = """
            INSERT INTO news_sentiment (
                ticker_id, headline, publisher, publish_date,
                sentiment_score, confidence, article_link
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            values = (
                ticker_id,
                headline,
                publisher,
                publish_date,
                sentiment_score,
                confidence,
                article_link
            )
            
            cursor.execute(sql, values)
            self.current_connection.commit()
            cursor.close()
            
            return True
            
        except mysql.connector.Error as err:
            print(f"Error saving news sentiment: {err}")
            return False

    def get_latest_sentiment(self, ticker_id, limit=10):
        """
        Retrieves the latest sentiment data for a ticker
        """
        try:
            cursor = self.current_connection.cursor(dictionary=True)
            
            sql = """
            SELECT 
                headline, publisher, publish_date,
                sentiment_score, confidence, article_link
            FROM news_sentiment
            WHERE ticker_id = %s
            ORDER BY publish_date DESC
            LIMIT %s
            """
            
            cursor.execute(sql, (ticker_id, limit))
            results = cursor.fetchall()
            cursor.close()
            
            return results
            
        except mysql.connector.Error as err:
            print(f"Error retrieving sentiment data: {err}")
            return None

    def get_sentiment_history(self, ticker_id, days=30):
        """
        Retrieves historical sentiment data for a ticker
        """
        try:
            cursor = self.current_connection.cursor()
            
            sql = """
            SELECT 
                DATE(publish_date) as date,
                AVG(sentiment_score) as avg_sentiment,
                COUNT(*) as article_count
            FROM news_sentiment
            WHERE ticker_id = %s
            AND publish_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(publish_date)
            ORDER BY date DESC
            """
            
            cursor.execute(sql, (ticker_id, days))
            columns = ['date', 'avg_sentiment', 'article_count']
            df = pd.DataFrame(cursor.fetchall(), columns=columns)
            cursor.close()
            
            if not df.empty:
                df.set_index('date', inplace=True)
                return df
            return None
            
        except mysql.connector.Error as err:
            print(f"Error retrieving sentiment history: {err}")
            return None
