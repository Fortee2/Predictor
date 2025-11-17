import argparse
import datetime
import decimal
import os

from data.bollinger_bands import BollingerBandAnalyzer
from data.config import Config
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
from data.utility import DatabaseConnectionPool
from data.watch_list_dao import WatchListDAO


class PortfolioCLI:
    def __init__(self):
        # Initialize configuration
        self.config = Config()
        db_config = self.config.get_database_config()

        # Initialize connection pool ONCE - NEW PATTERN
        self.db_pool = DatabaseConnectionPool(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            database=db_config["database"],
            pool_size=20,  # Optional, already defaults to 20
        )

        # Initialize ticker_dao first since it's needed by BollingerBandAnalyzer
        self.ticker_dao = TickerDao(self.db_pool)

        # Initialize DAOs with database credentials
        self.portfolio_dao = PortfolioDAO(pool=self.db_pool)
        self.transactions_dao = PortfolioTransactionsDAO(pool=self.db_pool)
        self.rsi_calc = rsi_calculations(pool=self.db_pool)
        self.moving_avg = moving_averages(pool=self.db_pool)
        self.bb_analyzer = BollingerBandAnalyzer(
            self.ticker_dao
        )  # Pass ticker_dao instance
        self.fundamental_dao = FundamentalDataDAO(pool=self.db_pool)
        self.macd_analyzer = MACD(pool=self.db_pool)
        self.news_analyzer = NewsSentimentAnalyzer(pool=self.db_pool)
        self.data_retrieval = DataRetrieval(pool=self.db_pool)
        self.value_calculator = PortfolioValueCalculator(pool=self.db_pool)
        self.value_service = PortfolioValueService(pool=self.db_pool)
        self.options_analyzer = OptionsData(pool=self.db_pool)
        self.trend_analyzer = TrendAnalyzer(pool=self.db_pool)
        self.watch_list_dao = WatchListDAO(pool=self.db_pool)
        self.stochastic_analyzer = StochasticOscillator(pool=self.db_pool)

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

    def create_portfolio(self, name, description):
        try:
            portfolio_id = self.portfolio_dao.create_portfolio(name, description)
            print("\nSuccessfully created new portfolio:")
            print(f"Portfolio ID: {portfolio_id}")
            print(f"Name: {name}")
            print(f"Description: {description}")
            return portfolio_id
        except Exception as e:
            print(f"Error creating portfolio: {str(e)}")
            return None

    def view_portfolio(self, portfolio_id):
        try:
            portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
            if not portfolio:
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            print("\nPortfolio Details:")
            print("--------------------------------------------------")
            print(f"Portfolio ID:  {portfolio['id']}")
            print(f"Name:         {portfolio['name']}")
            print(f"Description:  {portfolio['description']}")
            print(f"Status:       {'Active' if portfolio['active'] else 'Inactive'}")
            print(f"Date Added:   {portfolio['date_added'].strftime('%Y-%m-%d')}")

            # Display cash balance
            cash_balance = self.portfolio_dao.get_cash_balance(portfolio_id)
            print(f"Cash Balance: ${cash_balance:.2f}")

            tickers = self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            if tickers:
                print("\nTickers in Portfolio:")
                print("--------------------------------------------------")
                for symbol in tickers:
                    print(f"Symbol: {symbol}")
            else:
                print("\nNo tickers in portfolio.")

        except Exception as e:
            print(f"Error viewing portfolio: {str(e)}")

    def add_tickers(self, portfolio_id, ticker_symbols):
        try:
            # Verify portfolio exists
            if not self.portfolio_dao.read_portfolio(portfolio_id):
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Add tickers
            added_tickers = []
            for symbol in ticker_symbols:
                try:
                    self.portfolio_dao.add_tickers_to_portfolio(portfolio_id, [symbol])
                    ticker_id = self.ticker_dao.get_ticker_id(symbol)
                    if ticker_id:
                        # Process news sentiment for newly added ticker
                        self.news_analyzer.fetch_and_analyze_news(ticker_id, symbol)
                    added_tickers.append(symbol)
                except Exception as e:
                    print(f"Error adding ticker {symbol}: {str(e)}")

            if added_tickers:
                print(
                    f"\nSuccessfully added {len(added_tickers)} ticker(s) to portfolio {portfolio_id}"
                )
                print("\nAdded tickers:")
                for symbol in added_tickers:
                    print(f"- {symbol}")
            else:
                print("No tickers were added to the portfolio.")

        except Exception as e:
            print(f"Error adding tickers: {str(e)}")

    def remove_tickers(self, portfolio_id, ticker_symbols):
        try:
            # Verify portfolio exists
            if not self.portfolio_dao.read_portfolio(portfolio_id):
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Remove tickers
            removed_tickers = []
            for symbol in ticker_symbols:
                try:
                    self.portfolio_dao.remove_tickers_from_portfolio(
                        portfolio_id, [symbol]
                    )
                    removed_tickers.append(symbol)
                except Exception as e:
                    print(f"Error removing ticker {symbol}: {str(e)}")

            if removed_tickers:
                print(
                    f"\nSuccessfully removed {len(removed_tickers)} ticker(s) from portfolio {portfolio_id}"
                )
                print("\nRemoved tickers:")
                for symbol in removed_tickers:
                    print(f"- {symbol}")
            else:
                print("No tickers were removed from the portfolio.")

        except Exception as e:
            print(f"Error removing tickers: {str(e)}")

    def analyze_portfolio(self, portfolio_id, ticker_symbol=None, analysis_date=None):
        try:
            # Verify portfolio exists
            portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
            if not portfolio:
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Parse analysis date if provided
            if analysis_date:
                try:
                    if isinstance(analysis_date, str):
                        analysis_date = datetime.datetime.strptime(
                            analysis_date, "%Y-%m-%d"
                        ).date()
                    elif isinstance(analysis_date, datetime.datetime):
                        analysis_date = analysis_date.date()
                    # If it's already a date object, use it as-is
                except ValueError:
                    print("Error: Invalid date format. Please use YYYY-MM-DD format.")
                    return
            else:
                analysis_date = datetime.date.today()

            # Get positions for the specified date using the value service
            portfolio_value_result = self.value_service.calculate_portfolio_value(
                portfolio_id,
                calculation_date=analysis_date,
                include_cash=True,
                include_dividends=False,  # Don't include dividends in analysis positions
                use_current_prices=(analysis_date == datetime.date.today()),
            )

            current_positions = portfolio_value_result["positions"]

            # If no positions are held, notify the user
            if not current_positions and not ticker_symbol:
                date_str = analysis_date.strftime("%Y-%m-%d")
                print(
                    f"Portfolio {portfolio_id} had no held positions to analyze on {date_str}."
                )
                return

            # If specific ticker was provided, verify it exists
            if ticker_symbol:
                ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
                if not ticker_id:
                    print(f"Error: Ticker symbol {ticker_symbol} not found.")
                    return

                # Check if this ticker was held in the portfolio on the analysis date
                if ticker_id not in current_positions:
                    date_str = analysis_date.strftime("%Y-%m-%d")
                    print(
                        f"Note: {ticker_symbol} was not held in portfolio {portfolio_id} on {date_str}."
                    )
                    # Still analyze it since the user specifically requested it

                tickers = [(ticker_id, ticker_symbol)]
            else:
                # Only analyze tickers that were held on the analysis date
                tickers = [
                    (ticker_id, position["symbol"])
                    for ticker_id, position in current_positions.items()
                ]

            if not tickers:
                print("No tickers to analyze.")
                return

            date_str = analysis_date.strftime("%Y-%m-%d")
            if analysis_date == datetime.date.today():
                print(f"\nTechnical Analysis Results (as of {date_str}):")
            else:
                print(f"\nPortfolio Analysis Results (as of {date_str}):")
                print(
                    "Note: Position data reflects the specified date, but technical indicators show current values"
                )
            print("════════════════════════════════════════════════════════════════")

            for ticker_id, symbol in tickers:
                try:
                    # Show shares held if this is a held position
                    shares_info = ""
                    position_data = None
                    if ticker_id in current_positions:
                        position = current_positions[ticker_id]
                        shares = position["shares"]
                        shares_info = f" ({shares} shares)"

                        # Prepare position data for portfolio metrics
                        position_data = {
                            "shares": shares,
                            "avg_price": position["avg_price"],
                            "current_price": position["current_price"],
                        }

                    # Get comprehensive analysis using shared metrics
                    # Note: The shared metrics will use current data, but we show the position info from the historical date
                    analysis = self.shared_metrics.get_comprehensive_analysis(
                        ticker_id,
                        symbol,
                        include_options=True,
                        ma_period=20,
                        position_data=position_data,
                    )

                    # Format and display the analysis
                    formatted_output = self.shared_metrics.format_analysis_output(
                        analysis, shares_info=shares_info
                    )
                    print(formatted_output)

                except (
                    ZeroDivisionError,
                    decimal.DivisionUndefined,
                    decimal.InvalidOperation,
                ):
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
            print(f"Error analyzing portfolio: {str(e)}")

    def log_transaction(
        self,
        portfolio_id,
        transaction_type,
        date_str,
        ticker_symbol,
        shares=None,
        price=None,
        amount=None,
    ):
        try:
            # Validate portfolio
            if not self.portfolio_dao.read_portfolio(portfolio_id):
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Parse date
            try:
                date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                print("Error: Invalid date format. Please use YYYY-MM-DD format.")
                return

            # Handle cash transactions first - use the new cash_balance_history method
            if transaction_type == "cash":
                if amount is None:
                    print("Error: cash transactions require amount parameter.")
                    return

                # Use the new log_cash_transaction method which handles both the cash balance and history
                cash_action = "deposit" if amount > 0 else "withdrawal"
                description = f"Cash {cash_action}"

                # Log to cash history and update the balance in one operation
                new_balance = self.portfolio_dao.log_cash_transaction(
                    portfolio_id, amount, cash_action, description, date
                )

                print("\nSuccessfully logged cash transaction:")
                if amount > 0:
                    print(f"${amount:.2f} deposit")
                else:
                    print(f"${abs(amount):.2f} withdrawal")
                return

            # For non-cash transactions, we need ticker and security info
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id and transaction_type in ["buy", "sell", "dividend"]:
                print(f"Error: Ticker symbol {ticker_symbol} not found.")
                return

            security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
            if not security_id and transaction_type in ["buy", "sell", "dividend"]:
                try:
                    self.portfolio_dao.add_tickers_to_portfolio(
                        portfolio_id, [ticker_symbol]
                    )
                    security_id = self.portfolio_dao.get_security_id(
                        portfolio_id, ticker_id
                    )
                except Exception as e:
                    print(
                        "Error adding %s to portfolio %d: %s "
                        % (ticker_symbol, portfolio_id, str(e))
                    )
                    return

            get_transaction = self.transactions_dao.get_transaction_id(
                portfolio_id, security_id, transaction_type, date, shares, price, amount
            )

            if get_transaction:
                print(
                    "A matching transaction already exists. Duplicate entries are not allowed."
                )
                return

            # Validate transaction type and parameters
            if transaction_type in ["buy", "sell"]:
                if shares is None or price is None:
                    print(
                        f"Error: {transaction_type} transactions require both shares and price parameters."
                    )
                    return
                amount = None  # Ensure amount is None for buy/sell

                # Calculate the cash impact
                total_cost = shares * price

                # Prepare description for cash history
                description = f"{transaction_type.title()} {shares} shares of {ticker_symbol} at ${price:.2f}"

                if transaction_type == "buy":
                    # Check if there's enough cash for the purchase
                    cash_balance = self.portfolio_dao.get_cash_balance(portfolio_id)
                    if cash_balance < total_cost:
                        print(
                            f"Warning: Insufficient cash balance for purchase. Required: ${total_cost:.2f}, Available: ${cash_balance:.2f}"
                        )

                    # Log the cash withdrawal for the purchase
                    new_balance = self.portfolio_dao.log_cash_transaction(
                        portfolio_id,
                        -total_cost,  # Negative amount for buy
                        "buy",
                        description,
                        date,
                    )
                    print(f"Cash balance updated: ${new_balance:.2f} (after purchase)")

                elif transaction_type == "sell":
                    # Log the cash deposit from the sale
                    new_balance = self.portfolio_dao.log_cash_transaction(
                        portfolio_id,
                        total_cost,  # Positive amount for sell
                        "sell",
                        description,
                        date,
                    )
                    print(f"Cash balance updated: ${new_balance:.2f} (after sale)")

            elif transaction_type == "dividend":
                if amount is None:
                    print("Error: dividend transactions require amount parameter.")
                    return
                shares = price = None  # Ensure shares and price are None for dividend

                # Log the cash deposit from dividend
                description = f"Dividend from {ticker_symbol}"
                new_balance = self.portfolio_dao.log_cash_transaction(
                    portfolio_id,
                    amount,  # Positive amount for dividend
                    "dividend",
                    description,
                    date,
                )
                print(f"Cash balance updated: ${new_balance:.2f} (after dividend)")

            else:
                print(
                    "Error: Invalid transaction type. Must be 'buy', 'sell', 'dividend', or 'cash'."
                )
                return

            # Log transaction to portfolio_transactions table for all non-cash transactions
            self.transactions_dao.get_transaction_id(
                portfolio_id, security_id, transaction_type, date, shares, price, amount
            )

            self.transactions_dao.insert_transaction(
                portfolio_id=portfolio_id,
                transaction_type=transaction_type,
                transaction_date=date,
                security_id=security_id,
                shares=shares,
                price=price,
                amount=amount,
            )

            # Print confirmation
            print(f"\nSuccessfully logged {transaction_type} transaction:")
            print(f"- {ticker_symbol}: ", end="")
            if transaction_type in ["buy", "sell"]:
                print(f"{shares} shares at ${price:.2f} each")
            elif transaction_type == "dividend":
                print(f"${amount:.2f} dividend")

        except Exception as e:
            print(f"Error logging transaction: {str(e)}")

    def view_transactions(self, portfolio_id, ticker_symbol=None):
        try:
            # Validate portfolio
            portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
            if not portfolio:
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Convert symbol to ID if provided
            security_id = None
            if ticker_symbol:
                security_id = self.ticker_dao.get_ticker_id(ticker_symbol)
                if not security_id:
                    print(f"Error: Ticker symbol {ticker_symbol} not found.")
                    return

            # Get transactions
            transactions = self.transactions_dao.get_transaction_history(
                portfolio_id, security_id
            )
            if not transactions:
                print("No transactions found.")
                return

            # Print transactions
            print("\nTransaction History:")
            print(
                "--------------------------------------------------------------------------------"
            )
            print("Date         Type       Symbol   Shares    Price      Amount    ")
            print(
                "--------------------------------------------------------------------------------"
            )

            for t in transactions:
                date = t["transaction_date"].strftime("%Y-%m-%d")
                type_str = t["transaction_type"].ljust(10)
                symbol = t["symbol"].ljust(8)

                if t["transaction_type"] in ["buy", "sell"]:
                    shares = str(t["shares"]).rjust(8)
                    price = f"${t['price']:.2f}".rjust(10)
                    amount = "N/A".rjust(10)
                else:  # dividend
                    shares = "N/A".rjust(8)
                    price = "N/A".rjust(10)
                    amount = f"${t['amount']:.2f}".rjust(10)

                print(f"{date}   {type_str}{symbol}{shares}{price}{amount}")

        except Exception as e:
            print(f"Error viewing transactions: {str(e)}")

    def update_data(self):
        """Updates all data for securities in portfolios including price history, fundamentals, and news sentiment."""
        try:
            print("Updating data for all securities in portfolios...")
            self.data_retrieval.update_stock_activity()

            print("Data update complete.")
        except Exception as e:
            print(f"Error updating data: {str(e)}")

    def recalculate_portfolio_history(self, portfolio_id, from_date=None):
        """
        Recalculate portfolio historical values after adding/modifying historical transactions.

        This method will delete all portfolio value entries from the from_date forward
        and recalculate them based on the current transaction data.

        Args:
            portfolio_id (int): The portfolio ID
            from_date (str, optional): Date in YYYY-MM-DD format to start recalculation from.
                                      If not provided, will use earliest transaction date.
        """
        try:
            # Verify portfolio exists
            portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
            if not portfolio:
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            print(
                f"\nRecalculating historical values for portfolio: {portfolio['name']}"
            )
            if from_date:
                print(f"Starting from: {from_date}")
            else:
                print("Starting from earliest transaction date")

            # Call the recalculate method
            result = self.value_calculator.recalculate_historical_values(
                portfolio_id, from_date
            )

            if result:
                print(
                    "\nPortfolio historical values have been successfully recalculated."
                )
            else:
                print("\nFailed to recalculate portfolio historical values.")

        except Exception as e:
            print(f"Error recalculating portfolio history: {str(e)}")

    def view_portfolio_performance(
        self,
        portfolio_id,
        days=30,
        start_date=None,
        end_date=None,
        generate_chart=False,
    ):
        """
        Display portfolio performance over time.

        Args:
            portfolio_id (int): The portfolio ID
            days (int): Number of days of historical data to show/generate
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
            generate_chart (bool): Whether to generate a performance chart
        """
        try:
            # Verify portfolio exists
            portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
            if not portfolio:
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            print(f"\nPerformance for Portfolio: {portfolio['name']}")
            print("--------------------------------------------------")

            # If no performance data exists yet, generate it
            # First check if any records exist
            cursor = self.value_calculator.current_connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM portfolio_value WHERE portfolio_id = %s",
                (portfolio_id,),
            )
            count = cursor.fetchone()[0]

            if count == 0:
                print(f"Generating {days} days of performance history...")
                self.value_calculator.update_portfolio_value_history(portfolio_id, days)
                print("Performance history generation complete.")

            # Get performance metrics
            metrics = self.value_calculator.calculate_performance_metrics(
                portfolio_id, start_date, end_date
            )

            if metrics["initial_value"] is None:
                print("No performance data available for the specified period.")
                return

            # Display performance metrics
            print("\nPerformance Metrics:")
            print(f"Initial Value: ${metrics['initial_value']:.2f}")
            print(f"Final Value: ${metrics['final_value']:.2f}")
            print(f"Total Return: {metrics['total_return']:.2f}%")

            if metrics["annualized_return"] is not None:
                print(f"Annualized Return: {metrics['annualized_return']:.2f}%")

            print(f"Period: {metrics['period_days']} days")

            # Get and display performance data
            df = self.value_calculator.get_portfolio_performance(
                portfolio_id, start_date, end_date
            )
            if not df.empty:
                print("\nPortfolio Value History:")
                print("--------------------------------------------------")
                for date, row in df.iterrows():
                    print(f"{date.strftime('%Y-%m-%d')}: ${row['value']:.2f}")

            # Generate chart if requested
            if generate_chart:
                chart_path = self.value_calculator.generate_performance_chart(
                    portfolio_id, start_date, end_date
                )
                if chart_path:
                    print(f"\nPerformance chart saved to: {chart_path}")
                    # Try to open the chart with the default image viewer if on a desktop system
                    try:
                        import platform

                        system = platform.system()
                        if system == "Darwin":  # macOS
                            os.system(f"open {chart_path}")
                        elif system == "Windows":
                            os.system(f"start {chart_path}")
                        elif system == "Linux":
                            os.system(f"xdg-open {chart_path}")
                    except Exception as e:
                        print(f"Note: Could not automatically open the chart: {e}")

        except Exception as e:
            print(f"Error viewing portfolio performance: {str(e)}")

    def manage_cash(self, portfolio_id, action, amount=None):
        """
        Manage cash balance for a portfolio.

        Args:
            portfolio_id (int): The portfolio ID
            action (str): 'view', 'deposit', or 'withdraw'
            amount (float, optional): Amount to deposit or withdraw
        """
        try:
            # Verify portfolio exists
            portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
            if not portfolio:
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Get current cash balance
            current_balance = self.portfolio_dao.get_cash_balance(portfolio_id)

            if action == "view":
                print(f"\nCash Balance for Portfolio: {portfolio['name']}")
                print(f"Available Cash: ${current_balance:.2f}")
                return

            # Validate amount for deposit/withdraw actions
            if action in ["deposit", "withdraw"] and amount is None:
                print(f"Error: {action} action requires an amount parameter.")
                return

            # Process deposit/withdraw
            if action == "deposit":
                new_balance = self.portfolio_dao.add_cash(portfolio_id, amount)
                print(f"\nDeposited ${amount:.2f} to portfolio {portfolio['name']}")
                print(f"New Cash Balance: ${new_balance:.2f}")
            elif action == "withdraw":
                if current_balance < amount:
                    print(
                        f"Warning: Insufficient funds. Available: ${current_balance:.2f}, Requested: ${amount:.2f}"
                    )
                    proceed = (
                        input("Do you want to proceed with withdrawal anyway? (y/n): ")
                        .lower()
                        .strip()
                    )
                    if proceed != "y":
                        print("Withdrawal cancelled.")
                        return

                new_balance = self.portfolio_dao.withdraw_cash(portfolio_id, amount)
                print(f"\nWithdrew ${amount:.2f} from portfolio {portfolio['name']}")
                print(f"New Cash Balance: ${new_balance:.2f}")

        except Exception as e:
            print(f"Error managing cash: {str(e)}")

    def recalculating_portfolio_history(self, portfolio_id, from_date=None):
        """
        Recalculate historical values for a portfolio.

        This method will delete all existing historical values from the specified date
        and recalculate them based on current transactions.

        Args:
            portfolio_id (int): The portfolio ID
            from_date (str, optional): Date in YYYY-MM-DD format to start recalculation from.
                                       If not provided, will use earliest transaction date.
        """
        try:
            # Verify portfolio exists
            portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
            if not portfolio:
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            print(
                f"\nRecalculating historical values for portfolio: {portfolio['name']}"
            )
            if from_date:
                print(f"Starting from: {from_date}")
            else:
                print("Starting from earliest transaction date")

            # Call the recalculate method
            result = self.value_calculator.recalculate_historical_values(
                portfolio_id, from_date
            )

            if result:
                print(
                    "\nPortfolio historical values have been successfully recalculated."
                )
            else:
                print("\nFailed to recalculate portfolio historical values.")

        except Exception as e:
            print(f"Error recalculating portfolio history: {str(e)}")

    # Watchlist methods required by Enhanced CLI
    def create_watch_list(self, name, description=None):
        """Create a new watch list"""
        try:
            watch_list_id = self.watch_list_dao.create_watch_list(name, description)
            return watch_list_id
        except Exception as e:
            print(f"Error creating watch list: {str(e)}")
            return None

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

            return added_count > 0
        except Exception as e:
            print(f"Error adding ticker(s) to watch list: {str(e)}")
            return False

    def remove_watch_list_ticker(self, watch_list_id, ticker_symbols):
        """Remove ticker(s) from a watch list"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return False

            # Remove tickers
            removed_count = 0
            for symbol in ticker_symbols:
                if self.watch_list_dao.remove_ticker_from_watch_list(
                    watch_list_id, symbol
                ):
                    removed_count += 1

            return removed_count > 0
        except Exception as e:
            print(f"Error removing ticker(s) from watch list: {str(e)}")
            return False

    def update_watch_list_ticker_notes(self, watch_list_id, ticker_symbol, notes):
        """Update notes for a ticker in a watch list"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return False

            # Update notes
            return self.watch_list_dao.update_ticker_notes(
                watch_list_id, ticker_symbol, notes
            )
        except Exception as e:
            print(f"Error updating ticker notes: {str(e)}")
            return False

    def delete_watch_list(self, watch_list_id):
        """Delete a watch list"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return False

            # Delete watch list
            return self.watch_list_dao.delete_watch_list(watch_list_id)
        except Exception as e:
            print(f"Error deleting watch list: {str(e)}")
            return False

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

                    # Use shared analysis metrics for comprehensive analysis
                    self.shared_metrics.get_comprehensive_analysis(ticker_id, symbol)

                except Exception as e:
                    print(f"║ Error analyzing {symbol}: {str(e):<42}║")

            print("════════════════════════════════════════════════════════════════")
        except Exception as e:
            print(f"Error analyzing watch list: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Portfolio Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create Portfolio
    create_portfolio_parser = subparsers.add_parser(
        "create-portfolio", help="Create a new portfolio"
    )
    create_portfolio_parser.add_argument("name", help="Portfolio name")
    create_portfolio_parser.add_argument("description", help="Portfolio description")
    create_portfolio_parser.add_argument(
        "--initial_cash", type=float, default=0.0, help="Initial cash balance"
    )

    # View Portfolio
    view_parser = subparsers.add_parser("view-portfolio", help="View portfolio details")
    view_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")

    # Cash Management Commands
    cash_parser = subparsers.add_parser(
        "manage-cash", help="Manage portfolio cash balance"
    )
    cash_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")
    cash_parser.add_argument(
        "action", choices=["view", "deposit", "withdraw"], help="Cash management action"
    )
    cash_parser.add_argument(
        "--amount", type=float, help="Amount to deposit or withdraw"
    )

    # Add Tickers
    add_parser = subparsers.add_parser("add-tickers", help="Add tickers to portfolio")
    add_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")
    add_parser.add_argument(
        "ticker_symbols", nargs="+", help="Ticker symbols to add (e.g., AAPL GOOGL)"
    )

    # Remove Tickers
    remove_parser = subparsers.add_parser(
        "remove-tickers", help="Remove tickers from portfolio"
    )
    remove_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")
    remove_parser.add_argument(
        "ticker_symbols", nargs="+", help="Ticker symbols to remove"
    )

    # Log Transaction
    log_parser = subparsers.add_parser("log-transaction", help="Log a transaction")
    log_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")
    log_parser.add_argument(
        "type", choices=["buy", "sell", "dividend", "cash"], help="Transaction type"
    )
    log_parser.add_argument("date", help="Transaction date (YYYY-MM-DD)")
    log_parser.add_argument(
        "ticker_symbol",
        nargs="?",
        help="Ticker symbol (not required for cash transactions)",
    )
    log_parser.add_argument(
        "--shares", type=float, help="Number of shares (for buy/sell)"
    )
    log_parser.add_argument(
        "--price", type=float, help="Price per share (for buy/sell)"
    )
    log_parser.add_argument(
        "--amount",
        type=float,
        help="Amount for dividend or cash transactions. For cash: positive = deposit, negative = withdrawal",
    )

    # View Transactions
    trans_parser = subparsers.add_parser(
        "view-transactions", help="View transaction history"
    )
    trans_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")
    trans_parser.add_argument("--ticker_symbol", help="Filter by ticker symbol")

    # Analyze Portfolio
    analyze_parser = subparsers.add_parser(
        "analyze-portfolio", help="Analyze portfolio"
    )
    analyze_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")
    analyze_parser.add_argument("--ticker_symbol", help="Analyze specific ticker")
    analyze_parser.add_argument(
        "--date", help="Analysis date in YYYY-MM-DD format (default: today)"
    )
    analyze_parser.add_argument(
        "--ma_period",
        type=int,
        default=20,
        help="Moving average period for analysis (default: 20)",
    )
    analyze_parser.add_argument(
        "--lookback_days",
        type=int,
        default=5,
        help="Number of days to look back for trend analysis (default: 5)",
    )

    # Update Data
    update_parser = subparsers.add_parser(
        "update-data", help="Update data for all securities in portfolios"
    )

    # View Portfolio Performance
    performance_parser = subparsers.add_parser(
        "view-performance", help="View portfolio performance over time"
    )
    performance_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")
    performance_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of history to generate if none exists",
    )
    performance_parser.add_argument(
        "--start_date", help="Start date in YYYY-MM-DD format"
    )
    performance_parser.add_argument("--end_date", help="End date in YYYY-MM-DD format")
    performance_parser.add_argument(
        "--chart", action="store_true", help="Generate performance chart"
    )

    # Recalculate Portfolio History
    recalc_parser = subparsers.add_parser(
        "recalculate-history", help="Recalculate portfolio historical values"
    )
    recalc_parser.add_argument("portfolio_id", type=int, help="Portfolio ID")
    recalc_parser.add_argument(
        "--from_date", help="Date from which to start recalculation (YYYY-MM-DD format)"
    )

    # Watch List Commands

    # Create Watch List
    create_wl_parser = subparsers.add_parser(
        "create-watchlist", help="Create a new watch list"
    )
    create_wl_parser.add_argument("name", help="Watch list name")
    create_wl_parser.add_argument("--description", help="Watch list description")

    # View Watch Lists
    subparsers.add_parser(
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
    cli = PortfolioCLI()

    if args.command == "create-portfolio":
        cli.create_portfolio(args.name, args.description)
    elif args.command == "view-portfolio":
        cli.view_portfolio(args.portfolio_id)
    elif args.command == "add-tickers":
        cli.add_tickers(args.portfolio_id, args.ticker_symbols)
    elif args.command == "remove-tickers":
        cli.remove_tickers(args.portfolio_id, args.ticker_symbols)
    elif args.command == "log-transaction":
        cli.log_transaction(
            args.portfolio_id,
            args.type,
            args.date,
            args.ticker_symbol,
            args.shares,
            args.price,
            args.amount,
        )
    elif args.command == "view-transactions":
        cli.view_transactions(args.portfolio_id, args.ticker_symbol)
    elif args.command == "analyze-portfolio":
        cli.analyze_portfolio(args.portfolio_id, args.ticker_symbol, args.date)
    elif args.command == "update-data":
        cli.update_data()
    elif args.command == "view-performance":
        cli.view_portfolio_performance(
            args.portfolio_id, args.days, args.start_date, args.end_date, args.chart
        )
    elif args.command == "recalculate-history":
        cli.recalculate_portfolio_history(args.portfolio_id, args.from_date)
    elif args.command == "manage-cash":
        cli.manage_cash(args.portfolio_id, args.action, args.amount)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
