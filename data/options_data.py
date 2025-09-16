from datetime import datetime

import mysql.connector
import pandas as pd
import yfinance as yf


class OptionsData:
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

    def get_options_chain(self, symbol):
        """
        Retrieves the options chain for a given symbol.
        Returns a dictionary with calls and puts data for all available expiration dates.
        """
        try:
            ticker = yf.Ticker(symbol)

            # Get all available expiration dates
            expirations = ticker.options

            if not expirations:
                print(f"No options data available for {symbol}")
                return None

            options_data = {"calls": [], "puts": []}

            for expiration in expirations:
                # Get option chain for this expiration
                opt = ticker.option_chain(expiration)

                # Process calls
                calls = opt.calls.copy()
                calls["expirationDate"] = expiration
                calls["optionType"] = "CALL"
                options_data["calls"].append(calls)

                # Process puts
                puts = opt.puts.copy()
                puts["expirationDate"] = expiration
                puts["optionType"] = "PUT"
                options_data["puts"].append(puts)

            # Combine all data
            all_calls = (
                pd.concat(options_data["calls"])
                if options_data["calls"]
                else pd.DataFrame()
            )
            all_puts = (
                pd.concat(options_data["puts"])
                if options_data["puts"]
                else pd.DataFrame()
            )

            return {
                "calls": all_calls,
                "puts": all_puts,
                "expirations": expirations,
                "underlying_price": ticker.info.get("regularMarketPrice", None),
            }

        except Exception as e:
            print(f"Error retrieving options data for {symbol}: {str(e)}")
            return None

    def get_options_summary(self, symbol):
        """
        Returns a summary of options data including:
        - Number of available expiration dates
        - Nearest expiration date
        - Most active strikes
        - Implied volatility range
        """
        try:
            options_data = self.get_options_chain(symbol)
            if not options_data:
                return None

            summary = {
                "symbol": symbol,
                "underlying_price": options_data["underlying_price"],
                "num_expirations": len(options_data["expirations"]),
                "nearest_expiration": min(options_data["expirations"]),
                "furthest_expiration": max(options_data["expirations"]),
            }

            # Process calls
            if not options_data["calls"].empty:
                calls = options_data["calls"]
                summary.update(
                    {
                        "calls_volume": calls["volume"].sum(),
                        "calls_open_interest": calls["openInterest"].sum(),
                        "calls_iv_range": {
                            "min": calls["impliedVolatility"].min(),
                            "max": calls["impliedVolatility"].max(),
                        },
                    }
                )

            # Process puts
            if not options_data["puts"].empty:
                puts = options_data["puts"]
                summary.update(
                    {
                        "puts_volume": puts["volume"].sum(),
                        "puts_open_interest": puts["openInterest"].sum(),
                        "puts_iv_range": {
                            "min": puts["impliedVolatility"].min(),
                            "max": puts["impliedVolatility"].max(),
                        },
                    }
                )

            return summary

        except Exception as e:
            print(f"Error creating options summary for {symbol}: {str(e)}")
            return None

    def get_nearest_expiry_options(self, symbol):
        """
        Returns the options chain for the nearest expiration date.
        """
        try:
            options_data = self.get_options_chain(symbol)
            if not options_data or not options_data["expirations"]:
                return None

            nearest_expiry = min(options_data["expirations"])

            # Filter for nearest expiration
            nearest_calls = options_data["calls"][
                options_data["calls"]["expirationDate"] == nearest_expiry
            ]
            nearest_puts = options_data["puts"][
                options_data["puts"]["expirationDate"] == nearest_expiry
            ]

            return {
                "expiration": nearest_expiry,
                "underlying_price": options_data["underlying_price"],
                "calls": nearest_calls,
                "puts": nearest_puts,
            }

        except Exception as e:
            print(f"Error retrieving nearest expiry options for {symbol}: {str(e)}")
            return None
