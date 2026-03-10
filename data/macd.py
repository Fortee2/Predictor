import logging

import mysql.connector
import pandas as pd

from .base_dao import BaseDAO
from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class MACD(BaseDAO):
    def __init__(self, pool: DatabaseConnectionPool):
        """
        Initialize DAO with a shared database connection pool.

        Args:
            pool: DatabaseConnectionPool instance shared across all DAOs
        """
        super().__init__(pool)

    def calculate_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        2 / (period + 1)
        return data.ewm(span=period, adjust=False).mean()

    def calculate_macd(self, ticker_id):
        """Calculate MACD and Signal Line for a given ticker"""
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # 1. Get the date of the latest available price data
                cursor.execute(
                    "SELECT MAX(activity_date) FROM investing.activity WHERE ticker_id = %s",
                    (ticker_id,)
                )
                latest_price_result = cursor.fetchone()
                latest_price_date = latest_price_result[0] if latest_price_result else None

                # 2. Get the date of the latest calculated MACD
                cursor.execute(
                    "SELECT MAX(activity_date) FROM investing.macd_indicators WHERE ticker_id = %s",
                    (ticker_id,)
                )
                latest_macd_result = cursor.fetchone()
                latest_macd_date = latest_macd_result[0] if latest_macd_result else None

                # 3. Check if calculation is needed
                needs_calculation = not (latest_price_date and latest_macd_date and latest_macd_date >= latest_price_date)

                if needs_calculation:
                    # Get price data for the last year
                    cursor.execute(
                        """
                        SELECT activity_date, close 
                        FROM investing.activity 
                        WHERE ticker_id = %s 
                        AND activity_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
                        ORDER BY activity_date ASC
                    """,
                        (ticker_id,),
                    )

                    df = pd.DataFrame(cursor.fetchall(), columns=["activity_date", "close"])
                    if df.empty:
                        cursor.close()
                        return None

                    df = df.set_index("activity_date")

                    # Calculate EMAs
                    ema12 = self.calculate_ema(df["close"], 12)
                    ema26 = self.calculate_ema(df["close"], 26)

                    # Calculate MACD line
                    macd_line = ema12 - ema26

                    # Calculate Signal line (9-day EMA of MACD line)
                    signal_line = self.calculate_ema(macd_line, 9)

                    # Store results in database
                    insert_data = []
                    for date, macd_value, signal_value in zip(macd_line.index, macd_line, signal_line):
                        # Convert date to date object if it's a datetime
                        store_date = date.date() if hasattr(date, "date") else date
                        
                        # Calculate histogram
                        histogram = float(macd_value) - float(signal_value)
                        
                        insert_data.append((
                            ticker_id, 
                            store_date, 
                            float(macd_value), 
                            float(signal_value),
                            histogram
                        ))

                    if insert_data:
                        cursor.executemany(
                            """
                            INSERT INTO investing.macd_indicators (ticker_id, activity_date, macd, `signal`, histogram)
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE 
                                macd = VALUES(macd),
                                `signal` = VALUES(`signal`),
                                histogram = VALUES(histogram)
                            """,
                            insert_data
                        )

                    connection.commit()
                
                cursor.close()

            # Load data after connection is released
            return self.load_macd_from_db(ticker_id)
        except mysql.connector.Error as e:
            logger.error("Error calculating MACD for ticker %s: %s", ticker_id, e)
            return None

    def load_macd_from_db(self, ticker_id):
        """Load MACD and Signal line values from database"""
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Get MACD data from dedicated table
                sql = """
                    SELECT activity_date, macd, `signal`, histogram
                    FROM investing.macd_indicators
                    WHERE ticker_id = %s 
                    AND activity_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
                    ORDER BY activity_date ASC
                """

                cursor.execute(sql, (ticker_id,))

                df = pd.DataFrame(cursor.fetchall(), columns=["activity_date", "macd", "signal_line", "histogram"])
                df = df.set_index("activity_date")

                cursor.close()
                return df
        except mysql.connector.Error as e:
            logger.error("Error loading MACD from database for ticker %s: %s", ticker_id, e)
            return None

    def get_macd_signals(self, ticker_id):
        """Get buy/sell signals based on MACD crossovers"""
        # First, ensure MACD data is up to date
        self.calculate_macd(ticker_id)

        # Load the most recent MACD data
        df = self.load_macd_from_db(ticker_id)
        if df is None or df.empty:
            return None

        # Calculate crossover signals
        df["signal_shift"] = df["signal_line"].shift(1)
        df["macd_shift"] = df["macd"].shift(1)

        signals = []
        for date in df.index[1:]:  # Skip first row due to shift
            # Bullish crossover (MACD crosses above Signal)
            if (
                df.loc[date, "macd"] > df.loc[date, "signal_line"]
                and df.loc[date, "macd_shift"] <= df.loc[date, "signal_shift"]
            ):
                signals.append(
                    {
                        "date": date,
                        "signal": "BUY",
                        "macd": df.loc[date, "macd"],
                        "signal_line": df.loc[date, "signal_line"],
                    }
                )

            # Bearish crossover (MACD crosses below Signal)
            elif (
                df.loc[date, "macd"] < df.loc[date, "signal_line"]
                and df.loc[date, "macd_shift"] >= df.loc[date, "signal_shift"]
            ):
                signals.append(
                    {
                        "date": date,
                        "signal": "SELL",
                        "macd": df.loc[date, "macd"],
                        "signal_line": df.loc[date, "signal_line"],
                    }
                )

        return signals
