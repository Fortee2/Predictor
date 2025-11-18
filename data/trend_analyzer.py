import decimal
from enum import Enum

import numpy as np
import pandas as pd

from .base_dao import BaseDAO


class TrendDirection(Enum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


class TrendStrength(Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"


class TrendAnalyzer(BaseDAO):
    """Class for analyzing trend direction and strength of various indicators."""

    def analyze_ma_trend(self, ticker_id, period=20, lookback_days=5):
        """
        Analyzes the moving average trend for a given ticker and period.

        Args:
            ticker_id (int): Ticker ID to analyze
            period (int): MA period (e.g., 20 for 20-day MA)
            lookback_days (int): Number of days to look back for trend analysis

        Returns:
            dict: A dictionary containing trend direction, strength, and angle
        """
        with self.get_connection() as connection:
            cursor = connection.cursor()

            # Retrieve MA values for the last {lookback_days} days
            cursor.execute(
                """
                SELECT activity_date, value 
                FROM investing.averages
                WHERE ticker_id = %s 
                AND average_type = %s
                ORDER BY activity_date DESC
                LIMIT %s
            """,
                (ticker_id, period, lookback_days),
            )

            result = cursor.fetchall()

            # Handle case where not enough MA data is available - try to generate it
            if len(result) < 2:
                cursor.close()
                # Try to generate missing moving averages from activity data
                if self._generate_missing_moving_averages(ticker_id, period):
                    # Retry the query after generating MAs
                    cursor = self.current_connection.cursor()
                    cursor.execute(
                        """
                        SELECT activity_date, value 
                        FROM investing.averages
                        WHERE ticker_id = %s 
                        AND average_type = %s
                        ORDER BY activity_date DESC
                        LIMIT %s
                    """,
                        (ticker_id, period, lookback_days),
                    )
                    result = cursor.fetchall()
                    cursor.close()

                    # If still insufficient data after generation attempt
                    if len(result) < 2:
                        return {
                            "direction": TrendDirection.UNKNOWN.value,
                            "strength": TrendStrength.UNKNOWN.value,
                            "angle": None,
                            "percent_change": None,
                            "values": [],
                        }
                else:
                    # Could not generate MAs, return unknown
                    return {
                        "direction": TrendDirection.UNKNOWN.value,
                        "strength": TrendStrength.UNKNOWN.value,
                        "angle": None,
                        "percent_change": None,
                        "values": [],
                    }
            else:
                cursor.close()

            # Convert to dataframe and sort by date
            df = pd.DataFrame(result, columns=["date", "value"])
            df = df.sort_values("date")

            # Calculate the slope (direction and strength)
            latest_value = float(df.iloc[-1]["value"])
            previous_value = float(df.iloc[-2]["value"])

            # Calculate the percentage change rate
            # Additional checks for division by zero or very small values
            try:
                if abs(previous_value) < 0.0001:
                    percent_change = 0
                else:
                    percent_change = (latest_value - previous_value) / previous_value * 100
            except (ZeroDivisionError, decimal.DivisionUndefined):
                percent_change = 0

            # Calculate angle of the trend
            if len(df) >= 3:
                # Fit a line to the data points
                x = np.arange(len(df))
                # Ensure all values are converted to float for numpy operations
                y = np.array([float(val) for val in df["value"].values])
                z = np.polyfit(x, y, 1)
                slope = float(z[0])

                # Calculate the angle in degrees
                angle = float(np.degrees(np.arctan(slope)))
            else:
                angle = None

            # Determine direction
            if latest_value > previous_value:
                direction = TrendDirection.UP.value
            elif latest_value < previous_value:
                direction = TrendDirection.DOWN.value
            else:
                direction = TrendDirection.FLAT.value

            # Determine strength based on percentage change
            abs_percent_change = abs(percent_change)

            if abs_percent_change > 1.0:
                strength = TrendStrength.STRONG.value
            elif abs_percent_change > 0.5:
                strength = TrendStrength.MODERATE.value
            else:
                strength = TrendStrength.WEAK.value

            # Convert the MA values to a list for return
            values = df["value"].tolist()

            return {
                "direction": direction,
                "strength": strength,
                "angle": angle,
                "percent_change": percent_change,
                "values": values,
            }

    def analyze_price_vs_ma(self, ticker_id, ma_period=20):
        """
        Analyzes the relationship between price and its moving average.

        Args:
            ticker_id (int): Ticker ID to analyze
            ma_period (int): Moving average period

        Returns:
            dict: A dictionary describing the price location relative to MA
        """
        with self.get_connection() as connection:
            cursor = connection.cursor()

            # Get latest price
            cursor.execute(
                """
                SELECT close FROM investing.activity
                WHERE ticker_id = %s
                ORDER BY activity_date DESC
                LIMIT 1
            """,
                (ticker_id,),
            )

            price_result = cursor.fetchone()

            # Get latest MA
            cursor.execute(
                """
                SELECT value FROM investing.averages
                WHERE ticker_id = %s AND average_type = %s
                ORDER BY activity_date DESC
                LIMIT 1
            """,
                (ticker_id, ma_period),
            )

            ma_result = cursor.fetchone()
            cursor.close()

            if not price_result or not ma_result:
                return {
                    "position": "UNKNOWN",
                    "distance_percent": None,
                    "price": None,
                    "ma_value": None,
                }

            # Use explicit float conversion to avoid decimal/float mixing
            price = float(price_result[0])
            ma_value = float(ma_result[0])

            # Calculate percentage distance from MA
            # Additional checks for division by zero or very small values
            try:
                if abs(ma_value) < 0.0001:
                    distance_percent = 0
                else:
                    distance_percent = (price - ma_value) / ma_value * 100
            except (ZeroDivisionError, decimal.DivisionUndefined):
                distance_percent = 0

            # Determine position relative to MA
            if price > ma_value:
                position = "ABOVE_MA"
            elif price < ma_value:
                position = "BELOW_MA"
            else:
                position = "AT_MA"

            return {
                "position": position,
                "distance_percent": distance_percent,
                "price": price,
                "ma_value": ma_value,
            }

    def _generate_missing_moving_averages(self, ticker_id, period):
        """
        Generate missing moving averages for a ticker if sufficient activity data exists.

        Args:
            ticker_id (int): Ticker ID to generate MAs for
            period (int): MA period (e.g., 20 for 20-day MA)

        Returns:
            bool: True if MAs were successfully generated, False otherwise
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Check if we have sufficient activity data to calculate moving averages
                cursor.execute(
                    """
                    SELECT COUNT(*) 
                    FROM investing.activity 
                    WHERE ticker_id = %s
                """,
                    (ticker_id,),
                )

                activity_count = cursor.fetchone()[0]

                # Need at least the period number of days to calculate meaningful MAs
                if activity_count < period:
                    cursor.close()
                    return False

                # Get activity data for MA calculation
                cursor.execute(
                    """
                    SELECT activity_date, close 
                    FROM investing.activity 
                    WHERE ticker_id = %s
                    ORDER BY activity_date ASC
                """,
                    (ticker_id,),
                )

                activity_data = cursor.fetchall()

                if len(activity_data) < period:
                    cursor.close()
                    return False

                # Convert to DataFrame for easier calculation
                df = pd.DataFrame(activity_data, columns=["activity_date", "close"])
                df["activity_date"] = pd.to_datetime(df["activity_date"])
                df = df.set_index("activity_date")

                # Calculate moving averages
                df["moving_average"] = (
                    df["close"].rolling(window=period, min_periods=period).mean()
                )

                # Remove rows where MA couldn't be calculated (first period-1 rows)
                df_with_ma = df.dropna()

                if df_with_ma.empty:
                    cursor.close()
                    return False

                # Insert calculated MAs into the averages table
                rows_inserted = 0
                for index, row in df_with_ma.iterrows():
                    cursor.execute(
                        """
                        INSERT INTO investing.averages (ticker_id, activity_date, average_type, value)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE value = VALUES(value)
                    """,
                        (ticker_id, index.date(), period, float(row["moving_average"])),
                    )
                    rows_inserted += cursor.rowcount

                # Commit the changes
                self.current_connection.commit()
                cursor.close()

                return rows_inserted > 0

        except Exception as e:
            # Log error but don't crash the analysis
            print(f"Error generating moving averages for ticker {ticker_id}: {str(e)}")
            if cursor:
                cursor.close()
            return False