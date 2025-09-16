import decimal
import os
from datetime import date

import mysql.connector
import pandas as pd
from dotenv import load_dotenv
from mysql.connector import errorcode

from data.ticker_dao import TickerDao


class BollingerBandAnalyzer:

    def __init__(self, ticker_dao):
        self.ticker_dao = ticker_dao
        self.tickers = {}
        self.data_points = {}

    def generate_bollinger_band_data(self, ticker_id):
        """Generate data points for a Bollinger Band chart"""

        try:
            # Get symbol for the ticker_id
            symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
            if not symbol:
                return None

            # Retrieve historical price data
            df = self.ticker_dao.retrieve_ticker_activity(ticker_id)
            if df.empty:
                return None

            # Calculate 20-day moving average and standard deviation
            window = 20
            df["sma"] = df["close"].rolling(window=window).mean()
            df["stddev"] = df["close"].rolling(window=window).std()

            # Get the latest values
            latest = df.iloc[-1]

            # Convert to float and handle any potential NaN values
            sma_value = float(latest["sma"]) if not pd.isna(latest["sma"]) else 0.0
            stddev_value = (
                float(latest["stddev"]) if not pd.isna(latest["stddev"]) else 0.0
            )

            return {"bollinger_bands": {"mean": sma_value, "stddev": stddev_value}}
        except (
            ZeroDivisionError,
            decimal.DivisionUndefined,
            decimal.InvalidOperation,
        ) as e:
            # Return reasonable default values in case of division errors
            return {"bollinger_bands": {"mean": 0.0, "stddev": 0.0}}
        except Exception as e:
            print(f"Error generating Bollinger Band data: {str(e)}")
            return None

    def generate_interpretation(self, ticker_id):
        """Generate an interpretation of the Bollinger Band"""

        try:
            # Get symbol for the ticker_id
            symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
            if not symbol:
                print(f"No data available for ticker ID {ticker_id}")
                return

            bollinger_band = self.generate_bollinger_band_data(ticker_id)
            if not bollinger_band:
                return

            mean = bollinger_band["bollinger_bands"]["mean"]
            stddev = bollinger_band["bollinger_bands"]["stddev"]

            # Get the latest close price
            latest_close = self.ticker_dao.retrieve_last_activity_date(ticker_id)
            if latest_close.empty:
                return
            close_price = float(latest_close.iloc[0]["close"])

            # Calculate upper and lower bands (typically 2 standard deviations)
            upper_band = mean + (2 * stddev)
            lower_band = mean - (2 * stddev)

            # Interpret the Bollinger Band
            if close_price > upper_band:
                print(
                    f"{symbol} is trading above the upper Bollinger Band (${upper_band:.2f}), suggesting overbought conditions."
                )
            elif close_price < lower_band:
                print(
                    f"{symbol} is trading below the lower Bollinger Band (${lower_band:.2f}), suggesting oversold conditions."
                )
            else:
                print(
                    f"{symbol} is trading within the Bollinger Bands (${lower_band:.2f} - ${upper_band:.2f})."
                )

            if stddev == 0:
                print(
                    "Warning: Standard deviation is 0, indicating insufficient price variation in the calculation period."
                )
            elif mean > 0 and (stddev / mean) < 0.01:  # Less than 1% of mean
                print(
                    f"The Bollinger Bands are narrow (stddev: ${stddev:.2f}), indicating low volatility."
                )
            elif mean > 0 and (stddev / mean) > 0.04:  # More than 4% of mean
                print(
                    f"The Bollinger Bands are wide (stddev: ${stddev:.2f}), indicating high volatility."
                )
            else:
                print(
                    f"The Bollinger Bands show normal volatility (stddev: ${stddev:.2f})."
                )
        except (
            ZeroDivisionError,
            decimal.DivisionUndefined,
            decimal.InvalidOperation,
        ) as e:
            print(f"Unable to generate Bollinger Bands interpretation: {str(e)}")
        except Exception as e:
            print(f"Error interpreting Bollinger Bands: {str(e)}")


if __name__ == "__main__":
    load_dotenv()

    analyzer = BollingerBandAnalyzer(
        ticker_dao=TickerDao(
            os.getenv("DB_USER"),
            os.getenv("DB_PASSWORD"),
            os.getenv("DB_HOST"),
            os.getenv("DB_NAME"),
        )
    )
    data_points = analyzer.generate_bollinger_band_data("AAPL")
    print(data_points)

    analyzer.generate_interpretation("AAPL")
