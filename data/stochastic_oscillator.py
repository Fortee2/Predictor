import logging
from contextlib import contextmanager
from decimal import DivisionUndefined

import mysql.connector
import pandas as pd

from .base_dao import BaseDAO
from .utility import DatabaseConnectionPool

# Set up logging - consistent with existing pattern
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("stochastic_oscillator.log")],
)
logger = logging.getLogger("stochastic_oscillator")

# Ensure no console output
for handler in logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
        logger.removeHandler(handler)


class StochasticOscillator(BaseDAO):
    """
    Stochastic Oscillator implementation following DRY principles.
    Reuses existing database patterns, connection management, and analysis structure.
    """

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__(pool)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections - reusing existing pattern."""
        connection = None
        try:
            if self.current_connection is not None and self.current_connection.is_connected():
                connection = self.current_connection
                yield connection
            else:
                connection = self.pool.get_connection()
                self.current_connection = connection
                yield connection
        except mysql.connector.Error as e:
            logger.error("Database connection error: %s", str(e))
            raise
        finally:
            pass

    def calculate_stochastic(self, ticker_id, k_period=14, d_period=3):
        """
        Calculate Stochastic Oscillator %K and %D values.

        Args:
            ticker_id (int): Ticker ID to calculate for
            k_period (int): Period for %K calculation (default: 14)
            d_period (int): Period for %D smoothing (default: 3)

        Returns:
            pd.DataFrame: DataFrame with stochastic values
        """
        logger.info(
            "Calculating Stochastic Oscillator for ticker %s, K period: %s, D period: %s", ticker_id, k_period, d_period
        )

        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Get the last date for which stochastic was calculated - reusing existing pattern
                cursor.execute(
                    """
                    SELECT MAX(activity_date) 
                    FROM investing.averages 
                    WHERE ticker_id = %s AND average_type = %s
                """,
                    (ticker_id, f"STOCH_K_{k_period}"),
                )
                result = cursor.fetchone()
                last_date = result[0] if result else None

                # Set calculation start date - reusing existing logic
                if last_date is None:
                    last_date = "1900-01-01"
                    logger.debug("No previous stochastic data found for ticker %s, calculating all", ticker_id)
                else:
                    # Go back enough days to ensure we have sufficient data for calculation
                    from datetime import timedelta

                    last_date = last_date - timedelta(days=k_period + d_period)
                    logger.debug("Last stochastic date for ticker %s: %s", ticker_id, last_date)

                # Retrieve price data - reusing existing query pattern
                cursor.execute(
                    """
                    SELECT activity_date, high, low, close 
                    FROM investing.activity 
                    WHERE ticker_id = %s AND activity_date > %s
                    ORDER BY activity_date ASC
                """,
                    (ticker_id, last_date),
                )

                # Convert to DataFrame - consistent with existing pattern
                new_data = pd.DataFrame(cursor.fetchall(), columns=["activity_date", "high", "low", "close"])

                if not new_data.empty:
                    logger.info("Found %s new data points to calculate stochastic", len(new_data))

                    new_data["activity_date"] = pd.to_datetime(new_data["activity_date"])
                    new_data = new_data.set_index("activity_date")

                    # Calculate %K - core stochastic formula
                    new_data["lowest_low"] = new_data["low"].rolling(window=k_period, min_periods=k_period).min()
                    new_data["highest_high"] = new_data["high"].rolling(window=k_period, min_periods=k_period).max()

                    # Handle division by zero - consistent with existing error handling
                    def safe_stochastic_k(row):
                        try:
                            # Convert to float to handle Decimal/float arithmetic - consistent with existing patterns
                            close = float(row["close"])
                            highest_high = float(row["highest_high"])
                            lowest_low = float(row["lowest_low"])

                            denominator = highest_high - lowest_low
                            if abs(denominator) < 0.0001:
                                return 50.0  # Neutral value when no price movement
                            return ((close - lowest_low) / denominator) * 100
                        except (
                            ZeroDivisionError,
                            DivisionUndefined,
                            ValueError,
                            TypeError,
                        ):
                            return 50.0

                    new_data["stoch_k"] = new_data.apply(safe_stochastic_k, axis=1)

                    # Calculate %D (smoothed %K) - reusing rolling calculation pattern
                    new_data["stoch_d"] = new_data["stoch_k"].rolling(window=d_period, min_periods=d_period).mean()

                    # Remove rows where calculations couldn't be completed
                    complete_data = new_data.dropna(subset=["stoch_k", "stoch_d"])

                    if not complete_data.empty:
                        # Store in database - reusing existing storage pattern
                        rows_updated = 0
                        for index, row in complete_data.iterrows():
                            # Store %K
                            cursor.execute(
                                """
                                INSERT INTO investing.averages (ticker_id, activity_date, average_type, value)
                                VALUES (%s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE value = VALUES(value)
                            """,
                                (
                                    ticker_id,
                                    index.date(),
                                    f"STOCH_K_{k_period}",
                                    float(row["stoch_k"]),
                                ),
                            )

                            # Store %D
                            cursor.execute(
                                """
                                INSERT INTO investing.averages (ticker_id, activity_date, average_type, value)
                                VALUES (%s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE value = VALUES(value)
                            """,
                                (
                                    ticker_id,
                                    index.date(),
                                    f"STOCH_D_{k_period}_{d_period}",
                                    float(row["stoch_d"]),
                                ),
                            )

                            rows_updated += cursor.rowcount

                        connection.commit()
                        logger.info("Updated %s stochastic values for ticker %s", rows_updated, ticker_id)
                    else:
                        logger.info("No complete stochastic data could be calculated for ticker %s", ticker_id)
                else:
                    logger.info("No new data found for ticker %s since %s", ticker_id, last_date)

                cursor.close()

                # Return the updated stochastic data - reusing existing return pattern
                return self.load_stochastic_from_db(ticker_id, k_period, d_period)

        except mysql.connector.Error as e:
            logger.error("Database error calculating stochastic: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error calculating stochastic: %s", str(e))
            raise

    def load_stochastic_from_db(self, ticker_id, k_period=14, d_period=3):
        """
        Load stochastic data from database - reusing existing load pattern.

        Args:
            ticker_id (int): Ticker ID
            k_period (int): K period used in calculation
            d_period (int): D period used in calculation

        Returns:
            pd.DataFrame: Stochastic data
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Load both %K and %D - reusing existing query pattern
                sql = """
                    SELECT a.activity_date, 
                           MAX(CASE WHEN a.average_type = %s THEN a.value END) as stoch_k,
                           MAX(CASE WHEN a.average_type = %s THEN a.value END) as stoch_d
                    FROM investing.averages a 
                    WHERE a.ticker_id = %s 
                    AND a.average_type IN (%s, %s)
                    AND a.activity_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
                    GROUP BY a.activity_date
                    ORDER BY a.activity_date ASC
                """

                k_type = f"STOCH_K_{k_period}"
                d_type = f"STOCH_D_{k_period}_{d_period}"

                cursor.execute(sql, (k_type, d_type, ticker_id, k_type, d_type))

                df = pd.DataFrame(cursor.fetchall(), columns=["activity_date", "stoch_k", "stoch_d"])
                df = df.set_index("activity_date")

                cursor.close()

                logger.debug("Loaded %s stochastic data points for ticker %s", len(df), ticker_id)
                return df

        except mysql.connector.Error as e:
            logger.error("Database error loading stochastic data: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error loading stochastic data: %s", str(e))
            raise

    def get_stochastic_signals(self, ticker_id, k_period=14, d_period=3, overbought=80, oversold=20):
        """
        Generate trading signals based on stochastic levels - reusing existing signal pattern.

        Args:
            ticker_id (int): Ticker ID
            k_period (int): K period
            d_period (int): D period
            overbought (float): Overbought threshold (default: 80)
            oversold (float): Oversold threshold (default: 20)

        Returns:
            dict: Current signal analysis
        """
        try:
            # Ensure data is up to date
            stoch_data = self.calculate_stochastic(ticker_id, k_period, d_period)

            if stoch_data is None or stoch_data.empty:
                return {"success": False, "error": "No stochastic data available"}

            # Get latest values - reusing existing pattern
            latest = stoch_data.iloc[-1]
            latest_date = stoch_data.index[-1]

            stoch_k = float(latest["stoch_k"]) if not pd.isna(latest["stoch_k"]) else None
            stoch_d = float(latest["stoch_d"]) if not pd.isna(latest["stoch_d"]) else None

            if stoch_k is None or stoch_d is None:
                return {"success": False, "error": "Invalid stochastic values"}

            # Determine signal - reusing existing signal logic patterns
            if stoch_k >= overbought and stoch_d >= overbought:
                signal = "OVERBOUGHT"
                signal_strength = "Strong" if min(stoch_k, stoch_d) > 85 else "Moderate"
            elif stoch_k <= oversold and stoch_d <= oversold:
                signal = "OVERSOLD"
                signal_strength = "Strong" if max(stoch_k, stoch_d) < 15 else "Moderate"
            else:
                signal = "NEUTRAL"
                signal_strength = "N/A"

            # Check for crossover signals if we have enough data
            crossover_signal = None
            if len(stoch_data) >= 2:
                prev = stoch_data.iloc[-2]
                prev_k = float(prev["stoch_k"]) if not pd.isna(prev["stoch_k"]) else None
                prev_d = float(prev["stoch_d"]) if not pd.isna(prev["stoch_d"]) else None

                if prev_k is not None and prev_d is not None:
                    # Bullish crossover (%K crosses above %D)
                    if stoch_k > stoch_d and prev_k <= prev_d:
                        crossover_signal = "BULLISH_CROSSOVER"
                    # Bearish crossover (%K crosses below %D)
                    elif stoch_k < stoch_d and prev_k >= prev_d:
                        crossover_signal = "BEARISH_CROSSOVER"

            return {
                "success": True,
                "stoch_k": stoch_k,
                "stoch_d": stoch_d,
                "date": latest_date,
                "signal": signal,
                "signal_strength": signal_strength,
                "crossover_signal": crossover_signal,
                "overbought_threshold": overbought,
                "oversold_threshold": oversold,
                "display_text": f"Stochastic ({latest_date.strftime('%Y-%m-%d')}): %K={stoch_k:.1f}, %D={stoch_d:.1f} - {signal}",
            }

        except Exception as e:
            logger.error("Error generating stochastic signals: %s", str(e))
            return {
                "success": False,
                "error": f"Unable to generate stochastic signals: {str(e)}",
            }

    def analyze_divergence(self, ticker_id, k_period=14, d_period=3, lookback_days=20):
        """
        Analyze price vs stochastic divergence - reusing existing analysis patterns.

        Args:
            ticker_id (int): Ticker ID
            k_period (int): K period
            d_period (int): D period
            lookback_days (int): Days to look back for divergence analysis

        Returns:
            dict: Divergence analysis results
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Get recent price data
                cursor.execute(
                    """
                    SELECT activity_date, close 
                    FROM investing.activity 
                    WHERE ticker_id = %s 
                    ORDER BY activity_date DESC 
                    LIMIT %s
                """,
                    (ticker_id, lookback_days),
                )

                price_data = pd.DataFrame(cursor.fetchall(), columns=["activity_date", "close"])
                cursor.close()

                if price_data.empty:
                    return {"success": False, "error": "No price data available"}

                price_data = price_data.set_index("activity_date")
                price_data = price_data.sort_index()

                # Get stochastic data for same period
                stoch_data = self.load_stochastic_from_db(ticker_id, k_period, d_period)

                if stoch_data.empty:
                    return {"success": False, "error": "No stochastic data available"}

                # Merge data - reusing existing data merge patterns
                combined = price_data.join(stoch_data, how="inner")

                if len(combined) < 10:  # Need sufficient data for divergence analysis
                    return {
                        "success": False,
                        "error": "Insufficient data for divergence analysis",
                    }

                # Simple divergence detection - can be enhanced later
                recent_data = combined.tail(10)

                price_trend = "UP" if recent_data["close"].iloc[-1] > recent_data["close"].iloc[0] else "DOWN"
                stoch_trend = "UP" if recent_data["stoch_k"].iloc[-1] > recent_data["stoch_k"].iloc[0] else "DOWN"

                divergence = None
                if price_trend == "UP" and stoch_trend == "DOWN":
                    divergence = "BEARISH_DIVERGENCE"
                elif price_trend == "DOWN" and stoch_trend == "UP":
                    divergence = "BULLISH_DIVERGENCE"

                return {
                    "success": True,
                    "divergence": divergence,
                    "price_trend": price_trend,
                    "stoch_trend": stoch_trend,
                    "display_text": f"Divergence Analysis: {divergence if divergence else 'No divergence detected'}",
                }

        except Exception as e:
            logger.error("Error analyzing divergence: %s", str(e))
            return {
                "success": False,
                "error": f"Unable to analyze divergence: {str(e)}",
            }
