import logging
from functools import lru_cache

import mysql.connector
import pandas as pd

from .base_dao import BaseDAO
from .utility import DatabaseConnectionPool

# Set up logging
logger = logging.getLogger(__name__)


class TickerDao(BaseDAO):
    def __init__(self, pool: DatabaseConnectionPool):
        """
        Initialize TickerDao with a shared database connection pool.
        Inherits proper connection management from BaseDAO.

        Args:
            pool: DatabaseConnectionPool instance shared across all DAOs
        """
        super().__init__(pool)

    def retrieve_ticker_list(self):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "SELECT ticker, ticker_name, id, industry, sector FROM investing.tickers ORDER BY ticker;"
                    cursor.execute(query)
                    results = cursor.fetchall()

                    if not results:
                        return pd.DataFrame()

                    df_ticks = pd.DataFrame(results, columns=["ticker", "ticker_name", "id", "industry", "sector"])
                    return df_ticks
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error retrieving ticker list: %s", err)
            return pd.DataFrame()

    def insert_stock(self, ticker, ticker_name):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = """INSERT INTO investing.tickers 
                            (ticker, ticker_name, industry, sector) 
                            VALUES (%s, %s, %s, %s)"""
                    cursor.execute(query, (ticker, ticker_name, None, None))
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error inserting stock %s: %s", ticker, err)
            raise

    def update_stock_trend(self, trend, close, ticker):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "UPDATE investing.tickers SET trend = %s, close =%s WHERE ticker = %s"
                    cursor.execute(query, (trend, float(close), ticker))
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error updating stock trend for %s: %s", ticker, err)
            raise

    def ticker_delisted(self, ticker):
        """Set a ticker to inactive in the database"""
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "UPDATE investing.tickers SET trend = %s WHERE ticker = %s"
                    cursor.execute(query, ("delisted", ticker))
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error marking ticker %s as delisted: %s", ticker, err)
            raise

    def update_stock(self, symbol, name, industry, sector):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "UPDATE investing.tickers SET ticker_name = %s, industry =%s, sector=%s WHERE ticker = %s"
                    cursor.execute(query, (name, industry, sector, symbol))
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error updating stock %s: %s", symbol, err)
            raise

    @lru_cache(maxsize=128)
    def get_ticker_id(self, symbol):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "SELECT id FROM investing.tickers WHERE ticker = %s"
                    cursor.execute(query, (symbol,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                    else:
                        return None
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error getting ticker ID for %s: %s", symbol, err)
            return None

    @lru_cache(maxsize=128)
    def get_ticker_symbol(self, ticker_id):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "SELECT ticker FROM investing.tickers WHERE id = %s"
                    cursor.execute(query, (ticker_id,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                    else:
                        return None
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error getting ticker symbol for ID %s: %s", ticker_id, err)
            return None

    def get_ticker_industry(self, ticker_id):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "SELECT industry FROM investing.tickers WHERE id = %s"
                    cursor.execute(query, (ticker_id,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                    else:
                        return None
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error getting ticker industry for ID %s: %s", ticker_id, err)
            return None

    def update_activity(self, ticker_id, activity_date, open, close, volume, high, low):
        try:
            rsi_state = ""  # going to leave it blank if there is no change in price

            if open > close:
                rsi_state = "down"
            elif close > open:
                rsi_state = "up"

            # check to see if the record already exists
            df = self.retrieve_ticker_activity_by_day(ticker_id, activity_date)

            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    if df.empty:
                        query = "INSERT INTO investing.activity (ticker_id,activity_date,open,close,volume,updown, high, low) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(
                            query,
                            (
                                int(ticker_id),
                                str(activity_date),
                                float(open),
                                float(close),
                                float(volume),
                                rsi_state,
                                float(high),
                                float(low),
                            ),
                        )
                    else:
                        if df["close"].values[0] != close:
                            query = "UPDATE investing.activity SET open = %s, close = %s, volume = %s, updown = %s, high = %s, low = %s WHERE ticker_id = %s and activity_date = %s"
                            cursor.execute(
                                query,
                                (
                                    float(open),
                                    float(close),
                                    float(volume),
                                    rsi_state,
                                    float(high),
                                    float(low),
                                    int(ticker_id),
                                    str(activity_date),
                                ),
                            )
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error updating activity for ticker %s: %s", ticker_id, err)
            raise

    def retrieve_ticker_activity(self, ticker_id):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "SELECT ticker_id, activity_date, open, close, volume, updown, high, low FROM investing.activity  WHERE ticker_id = %s order by activity_date asc"
                    cursor.execute(query, (int(ticker_id),))
                    df = pd.DataFrame(
                        cursor.fetchall(),
                        columns=[
                            "ticker_id",
                            "activity_date",
                            "open",
                            "close",
                            "volume",
                            "updown",
                            "high",
                            "low",
                        ],
                    )
                    df = df.set_index("activity_date")
                    return df
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error retrieving ticker activity for %s: %s", ticker_id, err)
            return pd.DataFrame()

    def retrieve_ticker_activity_by_day(self, ticker_id, activity_date):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "SELECT ticker_id, activity_date, open, close, volume, updown, high, low FROM investing.activity  WHERE ticker_id = %s and activity_date = %s order by activity_date asc"
                    cursor.execute(query, (int(ticker_id), activity_date.strftime("%Y-%m-%d")))
                    df = pd.DataFrame(
                        cursor.fetchall(),
                        columns=[
                            "ticker_id",
                            "activity_date",
                            "open",
                            "close",
                            "volume",
                            "updown",
                            "high",
                            "low",
                        ],
                    )
                    df = df.set_index("activity_date")
                    return df
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error retrieving ticker activity by day for %s: %s", ticker_id, err)
            return pd.DataFrame()

    def retrieve_last_activity_date(self, ticker_id):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = """
                        SELECT activity_date, open, close, volume, updown, high, low 
                        FROM investing.activity 
                        WHERE ticker_id = %s 
                        ORDER BY activity_date DESC 
                        LIMIT 1
                    """
                    cursor.execute(query, (int(ticker_id),))
                    df_last = pd.DataFrame(
                        cursor.fetchall(),
                        columns=[
                            "activity_date",
                            "open",
                            "close",
                            "volume",
                            "updown",
                            "high",
                            "low",
                        ],
                    )
                    return df_last
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error retrieving last activity date for %s: %s", ticker_id, err)
            return pd.DataFrame()

    def retrieve_last_rsi(self, ticker_id):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                try:
                    query = "SELECT activity_date, rsi FROM investing.rsi  WHERE ticker_id = %s order by activity_date desc limit 10"
                    cursor.execute(query, (int(ticker_id),))
                    df_last = pd.DataFrame(cursor.fetchall(), columns=["activity_date", "rsi"])
                    return df_last
                finally:
                    cursor.close()
        except mysql.connector.Error as err:
            logger.error("Error retrieving last RSI for %s: %s", ticker_id, err)
            return pd.DataFrame()

    def get_ticker_data(self, ticker_id):
        """
        Get comprehensive data for a specific ticker including latest price.

        Args:
            ticker_id (int): The ID of the ticker to retrieve data for

        Returns:
            dict: A dictionary containing ticker data including last_price and other details
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                try:
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
                    ticker_info["trend"] = None

                    # Now try to get the trend column if it exists
                    try:
                        trend_query = "SELECT trend FROM investing.tickers WHERE id = %s"
                        cursor.execute(trend_query, (ticker_id,))
                        trend_result = cursor.fetchone()
                        if trend_result and "trend" in trend_result:
                            ticker_info["trend"] = trend_result["trend"]
                    except mysql.connector.Error as column_err:
                        # If trend column doesn't exist or other error, we already have a default value
                        if column_err.errno != 1054:  # If it's not just an unknown column error
                            logger.warning("Error retrieving trend data: %s", column_err)

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

                    # Combine the data
                    result = ticker_info
                    if latest_activity:
                        result["last_price"] = float(latest_activity["close"])
                        result["last_update"] = latest_activity["activity_date"]
                    else:
                        # Fall back to a default price if no activity data is available
                        result["last_price"] = 0.0
                        result["last_update"] = None

                    return result
                finally:
                    cursor.close()

        except mysql.connector.Error as err:
            logger.error("Database error in get_ticker_data for %s: %s", ticker_id, err)
            return None
        except Exception as e:
            logger.error("Error in get_ticker_data for %s: %s", ticker_id, str(e))
            return None
