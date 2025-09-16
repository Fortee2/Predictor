import argparse
import datetime
import decimal
import os

from dotenv import load_dotenv

from data.bollinger_bands import BollingerBandAnalyzer
from data.data_retrieval_consolidated import DataRetrieval
from data.fundamental_data_dao import FundamentalDataDAO
from data.macd import MACD
from data.moving_averages import moving_averages
from data.news_sentiment_analyzer import NewsSentimentAnalyzer
from data.options_data import OptionsData
from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.portfolio_value_calculator import PortfolioValueCalculator
from data.portfolio_value_service import PortfolioValueService
from data.rsi_calculations import rsi_calculations
from data.shared_analysis_metrics import SharedAnalysisMetrics
from data.stochastic_oscillator import StochasticOscillator
from data.ticker_dao import TickerDao
from data.trend_analyzer import TrendAnalyzer
from data.watch_list_dao import WatchListDAO


class WatchListCLI:
    def __init__(self):
        load_dotenv()

        # Get database credentials from environment variables
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_name = os.getenv("DB_NAME")

        # Initialize ticker_dao first since it's needed by BollingerBandAnalyzer
        self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)

        # Initialize DAOs with database credentials
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.transactions_dao = PortfolioTransactionsDAO(
            db_user, db_password, db_host, db_name
        )
        self.rsi_calc = rsi_calculations(db_user, db_password, db_host, db_name)
        self.moving_avg = moving_averages(db_user, db_password, db_host, db_name)
        self.bb_analyzer = BollingerBandAnalyzer(
            self.ticker_dao
        )  # Pass ticker_dao instance
        self.fundamental_dao = FundamentalDataDAO(
            db_user, db_password, db_host, db_name
        )
        self.macd_analyzer = MACD(db_user, db_password, db_host, db_name)
        self.news_analyzer = NewsSentimentAnalyzer(
            db_user, db_password, db_host, db_name
        )
        self.data_retrieval = DataRetrieval(db_user, db_password, db_host, db_name)
        self.value_calculator = PortfolioValueCalculator(
            db_user, db_password, db_host, db_name
        )
        self.value_service = PortfolioValueService(
            db_user, db_password, db_host, db_name
        )
        self.options_analyzer = OptionsData(db_user, db_password, db_host, db_name)
        self.trend_analyzer = TrendAnalyzer(db_user, db_password, db_host, db_name)
        self.watch_list_dao = WatchListDAO(db_user, db_password, db_host, db_name)
        self.stochastic_analyzer = StochasticOscillator(
            db_user, db_password, db_host, db_name
        )

        # Open database connections for classes that need it
        self.portfolio_dao.open_connection()
        self.transactions_dao.open_connection()
        self.ticker_dao.open_connection()
        self.rsi_calc.open_connection()
        self.moving_avg.open_connection()
        self.fundamental_dao.open_connection()
        self.value_calculator.open_connection()
        self.macd_analyzer.open_connection()
        self.trend_analyzer.open_connection()
        self.watch_list_dao.open_connection()
        self.stochastic_analyzer.open_connection()

        # Initialize shared analysis metrics with stochastic support
        self.shared_metrics = SharedAnalysisMetrics(
            self.rsi_calc,
            self.moving_avg,
            self.bb_analyzer,
            self.macd_analyzer,
            self.fundamental_dao,
            self.news_analyzer,
            self.options_analyzer,
            self.trend_analyzer,
            stochastic_analyzer=self.stochastic_analyzer,
        )

    # Watch List Methods
    def create_watch_list(self, name, description=None):
        """Create a new watch list"""
        try:
            watch_list_id = self.watch_list_dao.create_watch_list(name, description)
            if watch_list_id:
                print("\nSuccessfully created new watch list:")
                print(f"ID: {watch_list_id}")
                print(f"Name: {name}")
                if description:
                    print(f"Description: {description}")
                return watch_list_id
            else:
                print("Failed to create watch list.")
        except Exception as e:
            print(f"Error creating watch list: {str(e)}")

    def view_watch_lists(self):
        """View all watch lists"""
        try:
            watch_lists = self.watch_list_dao.get_watch_list()
            if not watch_lists:
                print("No watch lists found.")
                return

            print("\nWatch Lists:")
            print("--------------------------------------------------")
            for wl in watch_lists:
                print(f"ID: {wl['id']}")
                print(f"Name: {wl['name']}")
                if wl["description"]:
                    print(f"Description: {wl['description']}")
                print(f"Created: {wl['date_created'].strftime('%Y-%m-%d')}")
                print("--------------------------------------------------")
        except Exception as e:
            print(f"Error viewing watch lists: {str(e)}")

    def view_watch_list(self, watch_list_id):
        """View details of a specific watch list including its tickers"""
        try:
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return

            print("\nWatch List Details:")
            print("--------------------------------------------------")
            print(f"ID: {watch_list['id']}")
            print(f"Name: {watch_list['name']}")
            if watch_list["description"]:
                print(f"Description: {watch_list['description']}")
            print(f"Created: {watch_list['date_created'].strftime('%Y-%m-%d')}")

            tickers = self.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
            if tickers:
                print("\nTickers in Watch List:")
                print("--------------------------------------------------")
                for ticker in tickers:
                    print(f"Symbol: {ticker['symbol']} - {ticker['name']}")
                    if ticker["notes"]:
                        print(f"  Notes: {ticker['notes']}")
                    print(f"  Added: {ticker['date_added'].strftime('%Y-%m-%d')}")
            else:
                print("\nNo tickers in watch list.")
        except Exception as e:
            print(f"Error viewing watch list: {str(e)}")

    def add_watch_list_ticker(self, watch_list_id, ticker_symbols, notes=None):
        """Add ticker(s) to a watch list"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return

            # Add tickers
            added_count = 0
            for symbol in ticker_symbols:
                if self.watch_list_dao.add_ticker_to_watch_list(
                    watch_list_id, symbol, notes
                ):
                    added_count += 1

            if added_count > 0:
                print(
                    f"\nSuccessfully added {added_count} ticker(s) to watch list \"{watch_list['name']}\""
                )
        except Exception as e:
            print(f"Error adding ticker(s) to watch list: {str(e)}")

    def remove_watch_list_ticker(self, watch_list_id, ticker_symbols):
        """Remove ticker(s) from a watch list"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return

            # Remove tickers
            removed_count = 0
            for symbol in ticker_symbols:
                if self.watch_list_dao.remove_ticker_from_watch_list(
                    watch_list_id, symbol
                ):
                    removed_count += 1

            if removed_count > 0:
                print(
                    f"\nSuccessfully removed {removed_count} ticker(s) from watch list \"{watch_list['name']}\""
                )
        except Exception as e:
            print(f"Error removing ticker(s) from watch list: {str(e)}")

    def update_watch_list_ticker_notes(self, watch_list_id, ticker_symbol, notes):
        """Update notes for a ticker in a watch list"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return

            # Update notes
            if self.watch_list_dao.update_ticker_notes(
                watch_list_id, ticker_symbol, notes
            ):
                print(
                    f"\nSuccessfully updated notes for {ticker_symbol} in watch list \"{watch_list['name']}\""
                )
            else:
                print(
                    f"Failed to update notes. Check if {ticker_symbol} is in the watch list."
                )
        except Exception as e:
            print(f"Error updating ticker notes: {str(e)}")

    def delete_watch_list(self, watch_list_id):
        """Delete a watch list"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return

            # Delete watch list
            if self.watch_list_dao.delete_watch_list(watch_list_id):
                print(f"\nSuccessfully deleted watch list \"{watch_list['name']}\"")
            else:
                print(f"Failed to delete watch list.")
        except Exception as e:
            print(f"Error deleting watch list: {str(e)}")

    def analyze_watch_list(self, watch_list_id, ticker_symbol=None):
        """Analyze tickers in a watch list with comprehensive technical analysis"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return

            # Get tickers in watch list
            if ticker_symbol:
                # Check if ticker is in watch list
                if not self.watch_list_dao.is_ticker_in_watch_list(
                    watch_list_id, ticker_symbol
                ):
                    print(
                        f"Error: {ticker_symbol} is not in watch list {watch_list_id}."
                    )
                    return
                ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
                if not ticker_id:
                    print(f"Error: Ticker symbol {ticker_symbol} not found.")
                    return
                tickers = [(ticker_id, ticker_symbol)]
            else:
                # Get all tickers in watch list
                ticker_data = self.watch_list_dao.get_tickers_in_watch_list(
                    watch_list_id
                )
                if not ticker_data:
                    print(f"Watch list {watch_list_id} has no tickers to analyze.")
                    return
                tickers = [(t["ticker_id"], t["symbol"]) for t in ticker_data]

            print(f"\nComprehensive Watch List Analysis: {watch_list['name']}")
            print("════════════════════════════════════════════════════════════════")

            for ticker_id, symbol in tickers:
                try:
                    print(f"║ {symbol:<56}║")
                    print(
                        "║──────────────────────────────────────────────────────────║"
                    )

                    # RSI Analysis
                    try:
                        self.rsi_calc.calculateRSI(ticker_id)  # Calculate latest RSI
                        rsi_result = self.rsi_calc.retrievePrices(
                            1, ticker_id
                        )  # Get the calculated RSI
                        if not rsi_result.empty:
                            latest_rsi = rsi_result.iloc[-1]
                            rsi_value = latest_rsi["rsi"]
                            rsi_date = rsi_result.index[-1]
                            rsi_status = (
                                "Overbought"
                                if rsi_value > 70
                                else "Oversold" if rsi_value < 30 else "Neutral"
                            )
                            print(
                                f"║ RSI ({rsi_date.strftime('%Y-%m-%d')}): {rsi_value:.2f} - {rsi_status:<45}║"
                            )
                    except Exception as e:
                        print(
                            f"║ RSI: Unable to calculate (Error: {str(e)})             ║"
                        )

                    # Moving Average with Trend Analysis
                    try:
                        ma_data = self.moving_avg.update_moving_averages(ticker_id, 20)
                        if not ma_data.empty:
                            latest_ma = ma_data.iloc[-1]
                            # Parse date string from index
                            date_str = str(ma_data.index[-1]).split()[0]
                            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                            print(
                                f"║ 20-day MA ({dt.strftime('%Y-%m-%d')}): {latest_ma.iloc[0]:.2f}{' ' * 45}║"
                            )

                            # Get MA trend analysis
                            try:
                                ma_trend = self.trend_analyzer.analyze_ma_trend(
                                    ticker_id, 20
                                )
                                direction_emoji = (
                                    "↗️"
                                    if ma_trend["direction"] == "UP"
                                    else "↘️" if ma_trend["direction"] == "DOWN" else "➡️"
                                )
                                print(
                                    f"║ MA Trend: {direction_emoji} {ma_trend['direction']} ({ma_trend['strength']}){' ' * 34}║"
                                )
                                if ma_trend["percent_change"] is not None:
                                    print(
                                        f"║   Rate of Change: {ma_trend['percent_change']:.2f}%{' ' * 39}║"
                                    )
                            except Exception:
                                print(
                                    f"║ MA Trend: Unable to analyze                                 ║"
                                )

                            # Get price vs MA analysis
                            try:
                                price_vs_ma = self.trend_analyzer.analyze_price_vs_ma(
                                    ticker_id, 20
                                )
                                if price_vs_ma["position"] != "UNKNOWN":
                                    position_text = (
                                        "Above MA"
                                        if price_vs_ma["position"] == "ABOVE_MA"
                                        else (
                                            "Below MA"
                                            if price_vs_ma["position"] == "BELOW_MA"
                                            else "At MA"
                                        )
                                    )
                                    distance_formatted = (
                                        f"{price_vs_ma['distance_percent']:.2f}"
                                    )
                                    print(
                                        f"║ Price Position: {position_text} ({distance_formatted}% from MA){' ' * (29 - len(distance_formatted))}║"
                                    )
                            except Exception as e:
                                print(
                                    f"║ Price Position: Unable to analyze                           ║"
                                )
                    except Exception as e:
                        print(
                            f"║ Moving Average: Unable to calculate                          ║"
                        )

                    # Bollinger Bands
                    try:
                        bb_data = self.bb_analyzer.generate_bollinger_band_data(
                            ticker_id
                        )
                        if bb_data:
                            bb_mean = bb_data["bollinger_bands"]["mean"]
                            bb_stddev = bb_data["bollinger_bands"]["stddev"]
                            print(
                                f"║ Bollinger Bands:                                             ║"
                            )
                            print(f"║   Mean: {bb_mean:.2f}{' ' * 49}║")
                            print(f"║   StdDev: {bb_stddev:.2f}{' ' * 47}║")
                    except Exception as e:
                        print(
                            f"║ Bollinger Bands: Unable to calculate                         ║"
                        )

                    # MACD Analysis
                    try:
                        # Calculate MACD data once and reuse it
                        macd_data = self.macd_analyzer.calculate_macd(ticker_id)
                        if (macd_data is not None) and (not macd_data.empty):
                            latest_macd = macd_data.iloc[-1]
                            macd_date = macd_data.index[-1]
                            print(
                                f"║ MACD ({macd_date.strftime('%Y-%m-%d')}):                                ║"
                            )
                            print(
                                f"║   MACD Line: {latest_macd['macd']:.2f}{' ' * 44}║"
                            )
                            print(
                                f"║   Signal Line: {latest_macd['signal_line']:.2f}{' ' * 42}║"
                            )
                            print(
                                f"║   Histogram: {latest_macd['histogram']:.2f}{' ' * 44}║"
                            )

                            # Determine current MACD signal based on latest values (same date as MACD data)
                            if latest_macd["macd"] > latest_macd["signal_line"]:
                                current_signal = "BUY"
                                signal_strength = (
                                    "Strong"
                                    if latest_macd["histogram"] > 0.1
                                    else "Weak"
                                )
                            else:
                                current_signal = "SELL"
                                signal_strength = (
                                    "Strong"
                                    if latest_macd["histogram"] < -0.1
                                    else "Weak"
                                )

                            # Show current MACD signal for the same date as the data
                            print(
                                f"║ Current MACD Signal ({macd_date.strftime('%Y-%m-%d')}): {current_signal} ({signal_strength}){' ' * (25 - len(signal_strength))}║"
                            )

                            # Show trend direction based on histogram
                            if latest_macd["histogram"] > 0:
                                trend_direction = (
                                    "Strengthening"
                                    if len(macd_data) > 1
                                    and latest_macd["histogram"]
                                    > macd_data.iloc[-2]["histogram"]
                                    else "Weakening"
                                )
                            else:
                                trend_direction = (
                                    "Strengthening"
                                    if len(macd_data) > 1
                                    and latest_macd["histogram"]
                                    > macd_data.iloc[-2]["histogram"]
                                    else "Weakening"
                                )

                            print(
                                f"║ MACD Momentum: {trend_direction}{' ' * (47 - len(trend_direction))}║"
                            )
                    except Exception as e:
                        print(
                            f"║ MACD: Unable to calculate                                    ║"
                        )

                    # Fundamental Data
                    try:
                        fundamental_data = (
                            self.fundamental_dao.get_latest_fundamental_data(ticker_id)
                        )
                        if fundamental_data:
                            print(
                                "║ Fundamental Data:                                            ║"
                            )
                            if fundamental_data.get("pe_ratio") is not None:
                                print(
                                    f"║   P/E Ratio: {fundamental_data['pe_ratio']:.2f}{' ' * 44}║"
                                )
                            if fundamental_data.get("market_cap") is not None:
                                market_cap_str = (
                                    f"{fundamental_data['market_cap']:,.2f}"
                                )
                                print(
                                    f"║   Market Cap: ${market_cap_str}{' ' * (42 - len(market_cap_str))}║"
                                )
                            if fundamental_data.get("dividend_yield"):
                                print(
                                    f"║   Dividend Yield: {fundamental_data['dividend_yield']:.2f}%{' ' * 40}║"
                                )
                    except Exception as e:
                        print(
                            f"║ Fundamental Data: Unable to retrieve                          ║"
                        )

                    # News Sentiment
                    try:
                        sentiment_data = self.news_analyzer.get_sentiment_summary(
                            ticker_id, symbol
                        )
                        if (
                            sentiment_data
                            and sentiment_data["status"]
                            != "No sentiment data available"
                        ):
                            print(f"║ News Sentiment: {sentiment_data['status']:<47}║")
                            print(
                                f"║   Average Score: {sentiment_data['average_sentiment']:.2f}{' ' * 41}║"
                            )
                            print(
                                f"║   Articles Analyzed: {sentiment_data['article_count']}{' ' * 39}║"
                            )
                        else:
                            print(
                                "║ News Sentiment: No data available                              ║"
                            )
                    except Exception as e:
                        print(
                            f"║ News Sentiment: Unable to analyze                             ║"
                        )

                    print(
                        "════════════════════════════════════════════════════════════════"
                    )

                    # Options Data
                    try:
                        options_summary = self.options_analyzer.get_options_summary(
                            symbol
                        )
                        if options_summary:
                            print(
                                "║ Options Data:                                                  ║"
                            )
                            print(
                                f"║   Available Expirations: {options_summary['num_expirations']}{' ' * 37}║"
                            )
                            print(
                                f"║   Nearest Expiry: {options_summary['nearest_expiration']}{' ' * 35}║"
                            )
                            if "calls_volume" in options_summary:
                                calls_volume = options_summary["calls_volume"]
                                puts_volume = options_summary["puts_volume"]
                                put_call_ratio = 0
                                try:
                                    if calls_volume > 0:
                                        put_call_ratio = puts_volume / calls_volume
                                except (ZeroDivisionError, decimal.DivisionUndefined):
                                    put_call_ratio = 0

                                print(
                                    f"║   Total Calls Volume: {calls_volume:,}{' ' * (37 - len(str(calls_volume)))}║"
                                )
                                print(
                                    f"║   Total Puts Volume: {puts_volume:,}{' ' * (38 - len(str(puts_volume)))}║"
                                )
                                print(
                                    f"║   Put/Call Ratio: {put_call_ratio:.2f}{' ' * 42}║"
                                )
                                sentiment = (
                                    "Bearish"
                                    if put_call_ratio > 1
                                    else "Bullish" if put_call_ratio < 1 else "Neutral"
                                )
                                print(
                                    f"║   Volume Sentiment: {sentiment}{' ' * (42 - len(sentiment))}║"
                                )

                                print(
                                    "║   Implied Volatility Range:                                  ║"
                                )
                                print(
                                    f"║     Calls: {options_summary['calls_iv_range']['min']:.2%} - {options_summary['calls_iv_range']['max']:.2%}{' ' * 35}║"
                                )
                                print(
                                    f"║     Puts: {options_summary['puts_iv_range']['min']:.2%} - {options_summary['puts_iv_range']['max']:.2%}{' ' * 36}║"
                                )

                                avg_call_iv = (
                                    options_summary["calls_iv_range"]["min"]
                                    + options_summary["calls_iv_range"]["max"]
                                ) / 2
                                print(
                                    f"║   Market Expectation: {'High Volatility' if avg_call_iv > 0.5 else 'Moderate Volatility' if avg_call_iv > 0.2 else 'Low Volatility':<42}║"
                                )
                        else:
                            print(
                                "║ Options Data: Not available                                   ║"
                            )
                    except Exception as e:
                        print(
                            f"║ Options Data: Unable to analyze                               ║"
                        )

                    # Show notes if available
                    notes = None
                    for t in self.watch_list_dao.get_tickers_in_watch_list(
                        watch_list_id
                    ):
                        if t["symbol"] == symbol and t["notes"]:
                            notes = t["notes"]
                    if notes:
                        print(
                            "════════════════════════════════════════════════════════════════"
                        )
                        print(
                            f"║ Notes: {notes[:50]}{' ' * (51 - min(50, len(notes)))}║"
                        )
                        if len(notes) > 50:
                            print(
                                f"║   {notes[50:100]}{' ' * (57 - min(50, len(notes) - 50))}║"
                            )

                    print(
                        "════════════════════════════════════════════════════════════════"
                    )
                except (
                    ZeroDivisionError,
                    decimal.DivisionUndefined,
                    decimal.InvalidOperation,
                ) as div_err:
                    print(
                        f"║ Error analyzing {symbol}: Division error                        ║"
                    )
                    print(
                        "════════════════════════════════════════════════════════════════"
                    )
                except Exception as ticker_err:
                    print(
                        f"║ Error analyzing {symbol}: {str(ticker_err)[:40]}               ║"
                    )
                    print(
                        "════════════════════════════════════════════════════════════════"
                    )

        except Exception as e:
            print(f"Error analyzing watch list: {str(e)}")
            import traceback

            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Watch List Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Watch List Commands

    # Create Watch List
    create_wl_parser = subparsers.add_parser(
        "create-watchlist", help="Create a new watch list"
    )
    create_wl_parser.add_argument("name", help="Watch list name")
    create_wl_parser.add_argument("--description", help="Watch list description")

    # View Watch Lists
    view_wl_parser = subparsers.add_parser(
        "view-watchlists", help="View all watch lists"
    )

    # View Watch List
    view_wl_details_parser = subparsers.add_parser(
        "view-watchlist", help="View watch list details and tickers"
    )
    view_wl_details_parser.add_argument("watch_list_id", type=int, help="Watch list ID")

    # Add Ticker to Watch List
    add_wl_ticker_parser = subparsers.add_parser(
        "add-watchlist-ticker", help="Add ticker(s) to watch list"
    )
    add_wl_ticker_parser.add_argument("watch_list_id", type=int, help="Watch list ID")
    add_wl_ticker_parser.add_argument(
        "ticker_symbols", nargs="+", help="Ticker symbols to add"
    )
    add_wl_ticker_parser.add_argument("--notes", help="Notes for the ticker")

    # Remove Ticker from Watch List
    remove_wl_ticker_parser = subparsers.add_parser(
        "remove-watchlist-ticker", help="Remove ticker(s) from watch list"
    )
    remove_wl_ticker_parser.add_argument(
        "watch_list_id", type=int, help="Watch list ID"
    )
    remove_wl_ticker_parser.add_argument(
        "ticker_symbols", nargs="+", help="Ticker symbols to remove"
    )

    # Update Watch List Ticker Notes
    update_wl_notes_parser = subparsers.add_parser(
        "update-watchlist-notes", help="Update notes for a ticker in watch list"
    )
    update_wl_notes_parser.add_argument("watch_list_id", type=int, help="Watch list ID")
    update_wl_notes_parser.add_argument("ticker_symbol", help="Ticker symbol")
    update_wl_notes_parser.add_argument("notes", help="Notes for the ticker")

    # Delete Watch List
    delete_wl_parser = subparsers.add_parser(
        "delete-watchlist", help="Delete a watch list"
    )
    delete_wl_parser.add_argument("watch_list_id", type=int, help="Watch list ID")

    # Analyze Watch List
    analyze_wl_parser = subparsers.add_parser(
        "analyze-watchlist", help="Analyze tickers in a watch list"
    )
    analyze_wl_parser.add_argument("watch_list_id", type=int, help="Watch list ID")
    analyze_wl_parser.add_argument("--ticker_symbol", help="Analyze specific ticker")

    args = parser.parse_args()
    cli = WatchListCLI()

    if args.command == "create-watchlist":
        cli.create_watch_list(args.name, args.description)
    elif args.command == "view-watchlists":
        cli.view_watch_lists()
    elif args.command == "view-watchlist":
        cli.view_watch_list(args.watch_list_id)
    elif args.command == "add-watchlist-ticker":
        cli.add_watch_list_ticker(args.watch_list_id, args.ticker_symbols, args.notes)
    elif args.command == "remove-watchlist-ticker":
        cli.remove_watch_list_ticker(args.watch_list_id, args.ticker_symbols)
    elif args.command == "update-watchlist-notes":
        cli.update_watch_list_ticker_notes(
            args.watch_list_id, args.ticker_symbol, args.notes
        )
    elif args.command == "delete-watchlist":
        cli.delete_watch_list(args.watch_list_id)
    elif args.command == "analyze-watchlist":
        cli.analyze_watch_list(args.watch_list_id, args.ticker_symbol)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
