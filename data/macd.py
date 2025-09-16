from datetime import datetime, timedelta

import mysql.connector
import numpy as np
import pandas as pd
from mysql.connector import errorcode


class MACD:
    def __init__(self, user, password, host, database):
        self.db_user = user
        self.db_password = password
        self.db_host = host
        self.db_name = database
        self.current_connection = None

    def open_connection(self):
        self.current_connection = mysql.connector.connect(
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            database=self.db_name,
        )

    def close_connection(self):
        if self.current_connection:
            self.current_connection.close()

    def calculate_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        multiplier = 2 / (period + 1)
        return data.ewm(span=period, adjust=False).mean()

    def calculate_macd(self, ticker_id):
        """Calculate MACD and Signal Line for a given ticker"""
        if self.current_connection is None:
            self.open_connection()

        cursor = self.current_connection.cursor()

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
        for date, macd_value, signal_value in zip(
            macd_line.index, macd_line, signal_line
        ):
            # Store MACD line
            # Convert date to date object if it's a datetime
            store_date = date.date() if hasattr(date, "date") else date

            cursor.execute(
                """
                INSERT INTO investing.averages (ticker_id, activity_date, average_type, value)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE value = VALUES(value)
            """,
                (ticker_id, store_date, "MACD", float(macd_value)),
            )

            # Store Signal line
            cursor.execute(
                """
                INSERT INTO investing.averages (ticker_id, activity_date, average_type, value)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE value = VALUES(value)
            """,
                (ticker_id, store_date, "MACD_SIGNAL", float(signal_value)),
            )

        self.current_connection.commit()
        cursor.close()

        return self.load_macd_from_db(ticker_id)

    def load_macd_from_db(self, ticker_id):
        """Load MACD and Signal line values from database"""
        if self.current_connection is None:
            self.open_connection()

        cursor = self.current_connection.cursor()

        # Get both MACD and Signal line values
        sql = """
            SELECT a.activity_date, 
                   MAX(CASE WHEN a.average_type = 'MACD' THEN a.value END) as macd,
                   MAX(CASE WHEN a.average_type = 'MACD_SIGNAL' THEN a.value END) as signal_line
            FROM investing.averages a 
            WHERE a.ticker_id = %s 
            AND a.average_type IN ('MACD', 'MACD_SIGNAL')
            AND a.activity_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
            GROUP BY a.activity_date
            ORDER BY a.activity_date ASC
        """

        cursor.execute(sql, (ticker_id,))

        df = pd.DataFrame(
            cursor.fetchall(), columns=["activity_date", "macd", "signal_line"]
        )
        df = df.set_index("activity_date")

        # Calculate histogram (MACD - Signal)
        df["histogram"] = df["macd"] - df["signal_line"]

        cursor.close()
        return df

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
