import argparse
import os
import decimal
from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.ticker_dao import TickerDao
from data.rsi_calculations import rsi_calculations
from data.moving_averages import moving_averages
from data.bollinger_bands import BollingerBandAnalyzer
from data.fundamental_data_dao import FundamentalDataDAO
from data.macd import MACD
from data.news_sentiment_analyzer import NewsSentimentAnalyzer
from data.data_retrival_improved import DataRetrieval
from data.portfolio_value_calculator import PortfolioValueCalculator
from data.options_data import OptionsData
from data.trend_analyzer import TrendAnalyzer
from data.watch_list_dao import WatchListDAO
import datetime
from dotenv import load_dotenv

class PortfolioCLI:
    def __init__(self):
        load_dotenv()
        
        # Get database credentials from environment variables
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_name = os.getenv('DB_NAME')
        
        # Initialize ticker_dao first since it's needed by BollingerBandAnalyzer
        self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)
        
        # Initialize DAOs with database credentials
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        self.rsi_calc = rsi_calculations(db_user, db_password, db_host, db_name)
        self.moving_avg = moving_averages(db_user, db_password, db_host, db_name)
        self.bb_analyzer = BollingerBandAnalyzer(self.ticker_dao)  # Pass ticker_dao instance
        self.fundamental_dao = FundamentalDataDAO(db_user, db_password, db_host, db_name)
        self.macd_analyzer = MACD(db_user, db_password, db_host, db_name)
        self.news_analyzer = NewsSentimentAnalyzer(db_user, db_password, db_host, db_name)
        self.data_retrieval = DataRetrieval(db_user, db_password, db_host, db_name)
        self.value_calculator = PortfolioValueCalculator(db_user, db_password, db_host, db_name)
        self.options_analyzer = OptionsData(db_user, db_password, db_host, db_name)
        self.trend_analyzer = TrendAnalyzer(db_user, db_password, db_host, db_name)
        self.watch_list_dao = WatchListDAO(db_user, db_password, db_host, db_name)
        
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

    def create_portfolio(self, name, description):
        try:
            portfolio_id = self.portfolio_dao.create_portfolio(name, description)
            print(f"\nSuccessfully created new portfolio:")
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
                print(f"\nSuccessfully added {len(added_tickers)} ticker(s) to portfolio {portfolio_id}")
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
                    self.portfolio_dao.remove_tickers_from_portfolio(portfolio_id, [symbol])
                    removed_tickers.append(symbol)
                except Exception as e:
                    print(f"Error removing ticker {symbol}: {str(e)}")

            if removed_tickers:
                print(f"\nSuccessfully removed {len(removed_tickers)} ticker(s) from portfolio {portfolio_id}")
                print("\nRemoved tickers:")
                for symbol in removed_tickers:
                    print(f"- {symbol}")
            else:
                print("No tickers were removed from the portfolio.")

        except Exception as e:
            print(f"Error removing tickers: {str(e)}")

    def analyze_portfolio(self, portfolio_id, ticker_symbol=None):
        try:
            # Verify portfolio exists
            portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
            if not portfolio:
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Get current positions in the portfolio
            current_positions = self.transactions_dao.get_current_positions(portfolio_id)
            
            # If no positions are held, notify the user
            if not current_positions and not ticker_symbol:
                print(f"Portfolio {portfolio_id} has no currently held positions to analyze.")
                return
                
            # If specific ticker was provided, verify it exists and is currently held
            if ticker_symbol:
                ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
                if not ticker_id:
                    print(f"Error: Ticker symbol {ticker_symbol} not found.")
                    return
                    
                # Check if this ticker is currently held in the portfolio
                if ticker_id not in current_positions:
                    print(f"Note: {ticker_symbol} is not currently held in portfolio {portfolio_id}.")
                    # Still analyze it since the user specifically requested it
                tickers = [(ticker_id, ticker_symbol)]
            else:
                # Only analyze tickers that are currently held
                tickers = [(ticker_id, position['symbol']) 
                          for ticker_id, position in current_positions.items()]

            if not tickers:
                print("No tickers to analyze.")
                return

            print("\nTechnical Analysis Results:")
            print("════════════════════════════════════════════════════════════════")
            
            for ticker_id, symbol in tickers:
                try:
                    # Show shares held if this is a held position
                    shares_info = ""
                    if ticker_id in current_positions:
                        shares = current_positions[ticker_id]['shares']
                        shares_info = f" ({shares} shares)"
                    
                    print(f"║ {symbol}{shares_info:<56}║")
                    print("║──────────────────────────────────────────────────────────║")

                    # RSI Analysis
                    try:
                        self.rsi_calc.calculateRSI(ticker_id)  # Calculate latest RSI
                        rsi_result = self.rsi_calc.retrievePrices(1, ticker_id)  # Get the calculated RSI
                        if not rsi_result.empty:
                            latest_rsi = rsi_result.iloc[-1]
                            rsi_value = latest_rsi['rsi']
                            rsi_date = rsi_result.index[-1]
                            rsi_status = "Overbought" if rsi_value > 70 else "Oversold" if rsi_value < 30 else "Neutral"
                            print(f"║ RSI ({rsi_date.strftime('%Y-%m-%d')}): {rsi_value:.2f} - {rsi_status:<45}║")
                    except Exception as e:
                        print(f"║ RSI: Unable to calculate (Error: {str(e)})             ║")

                    # Moving Average with Trend Analysis
                    try:
                        ma_data = self.moving_avg.update_moving_averages(ticker_id, 20)
                        if not ma_data.empty:
                            latest_ma = ma_data.iloc[-1]
                            # Parse date string from index
                            date_str = str(ma_data.index[-1]).split()[0]
                            dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                            print(f"║ 20-day MA ({dt.strftime('%Y-%m-%d')}): {latest_ma.iloc[0]:.2f}{' ' * 45}║")
                            
                            # Get MA trend analysis
                            try:
                                ma_trend = self.trend_analyzer.analyze_ma_trend(ticker_id, 20)
                                direction_emoji = "↗️" if ma_trend["direction"] == "UP" else "↘️" if ma_trend["direction"] == "DOWN" else "➡️"
                                print(f"║ MA Trend: {direction_emoji} {ma_trend['direction']} ({ma_trend['strength']}){' ' * 34}║")
                                if ma_trend["percent_change"] is not None:
                                    print(f"║   Rate of Change: {ma_trend['percent_change']:.2f}%{' ' * 39}║")
                            except Exception as e:
                                print(f"║ MA Trend: Unable to analyze                                 ║")
                            
                            # Get price vs MA analysis
                            try:
                                price_vs_ma = self.trend_analyzer.analyze_price_vs_ma(ticker_id, 20)
                                if price_vs_ma["position"] != "UNKNOWN":
                                    position_text = "Above MA" if price_vs_ma["position"] == "ABOVE_MA" else "Below MA" if price_vs_ma["position"] == "BELOW_MA" else "At MA"
                                    distance_formatted = f"{price_vs_ma['distance_percent']:.2f}"
                                    print(f"║ Price Position: {position_text} ({distance_formatted}% from MA){' ' * (29 - len(distance_formatted))}║")
                            except Exception as e:
                                print(f"║ Price Position: Unable to analyze                           ║")
                    except Exception as e:
                        print(f"║ Moving Average: Unable to calculate                          ║")

                    # Bollinger Bands
                    try:
                        bb_data = self.bb_analyzer.generate_bollinger_band_data(ticker_id)
                        if bb_data:
                            bb_mean = bb_data['bollinger_bands']['mean']
                            bb_stddev = bb_data['bollinger_bands']['stddev']
                            print(f"║ Bollinger Bands:                                             ║")
                            print(f"║   Mean: {bb_mean:.2f}{' ' * 49}║")
                            print(f"║   StdDev: {bb_stddev:.2f}{' ' * 47}║")
                    except Exception as e:
                        print(f"║ Bollinger Bands: Unable to calculate                         ║")

                    # MACD Analysis
                    try:
                        macd_data = self.macd_analyzer.calculate_macd(ticker_id)
                        if (macd_data is not None) and (not macd_data.empty):
                            latest_macd = macd_data.iloc[-1]
                            macd_date = macd_data.index[-1]
                            print(f"║ MACD ({macd_date.strftime('%Y-%m-%d')}):                                ║")
                            print(f"║   MACD Line: {latest_macd['macd']:.2f}{' ' * 44}║")
                            print(f"║   Signal Line: {latest_macd['signal_line']:.2f}{' ' * 42}║")
                            print(f"║   Histogram: {latest_macd['histogram']:.2f}{' ' * 44}║")

                        # Get MACD signals
                        macd_signals = self.macd_analyzer.get_macd_signals(ticker_id)
                        if macd_signals and len(macd_signals) > 0:
                            latest_signal = macd_signals[-1]
                            print(f"║ Latest MACD Signal ({latest_signal['date'].strftime('%Y-%m-%d')}): {latest_signal['signal']:<27}║")
                    except Exception as e:
                        print(f"║ MACD: Unable to calculate                                    ║")

                    # Fundamental Data
                    try:
                        fundamental_data = self.fundamental_dao.get_latest_fundamental_data(ticker_id)
                        if fundamental_data:
                            print("║ Fundamental Data:                                            ║")
                            if fundamental_data.get('pe_ratio') is not None:
                                print(f"║   P/E Ratio: {fundamental_data['pe_ratio']:.2f}{' ' * 44}║")
                            if fundamental_data.get('market_cap') is not None:
                                market_cap_str = f"{fundamental_data['market_cap']:,.2f}"
                                print(f"║   Market Cap: ${market_cap_str}{' ' * (42 - len(market_cap_str))}║")
                            if fundamental_data.get('dividend_yield'):
                                print(f"║   Dividend Yield: {fundamental_data['dividend_yield']:.2f}%{' ' * 40}║")
                    except Exception as e:
                        print(f"║ Fundamental Data: Unable to retrieve                          ║")

                    # News Sentiment
                    try:
                        sentiment_data = self.news_analyzer.get_sentiment_summary(ticker_id, symbol)
                        if sentiment_data and sentiment_data['status'] != 'No sentiment data available':
                            print(f"║ News Sentiment: {sentiment_data['status']:<47}║")
                            print(f"║   Average Score: {sentiment_data['average_sentiment']:.2f}{' ' * 41}║")
                            print(f"║   Articles Analyzed: {sentiment_data['article_count']}{' ' * 39}║")
                        else:
                            print("║ News Sentiment: No data available                              ║")
                    except Exception as e:
                        print(f"║ News Sentiment: Unable to analyze                             ║")

                    print("════════════════════════════════════════════════════════════════")

                    # Options Data
                    try:
                        options_summary = self.options_analyzer.get_options_summary(symbol)
                        if options_summary:
                            print("║ Options Data:                                                  ║")
                            print(f"║   Available Expirations: {options_summary['num_expirations']}{' ' * 37}║")
                            print(f"║   Nearest Expiry: {options_summary['nearest_expiration']}{' ' * 35}║")
                            if 'calls_volume' in options_summary:
                                calls_volume = options_summary['calls_volume']
                                puts_volume = options_summary['puts_volume']
                                put_call_ratio = 0
                                try:
                                    if calls_volume > 0:
                                        put_call_ratio = puts_volume / calls_volume
                                except (ZeroDivisionError, decimal.DivisionUndefined):
                                    put_call_ratio = 0
                                
                                print(f"║   Total Calls Volume: {calls_volume:,}{' ' * (37 - len(str(calls_volume)))}║")
                                print(f"║   Total Puts Volume: {puts_volume:,}{' ' * (38 - len(str(puts_volume)))}║")
                                print(f"║   Put/Call Ratio: {put_call_ratio:.2f}{' ' * 42}║")
                                sentiment = "Bearish" if put_call_ratio > 1 else "Bullish" if put_call_ratio < 1 else "Neutral"
                                print(f"║   Volume Sentiment: {sentiment}{' ' * (42 - len(sentiment))}║")
                                
                                print("║   Implied Volatility Range:                                  ║")
                                print(f"║     Calls: {options_summary['calls_iv_range']['min']:.2%} - {options_summary['calls_iv_range']['max']:.2%}{' ' * 35}║")
                                print(f"║     Puts: {options_summary['puts_iv_range']['min']:.2%} - {options_summary['puts_iv_range']['max']:.2%}{' ' * 36}║")
                                
                                avg_call_iv = (options_summary['calls_iv_range']['min'] + options_summary['calls_iv_range']['max']) / 2
                                print(f"║   Market Expectation: {'High Volatility' if avg_call_iv > 0.5 else 'Moderate Volatility' if avg_call_iv > 0.2 else 'Low Volatility':<42}║")
                        else:
                            print("║ Options Data: Not available                                   ║")
                    except Exception as e:
                        print(f"║ Options Data: Unable to analyze                               ║")

                    print("════════════════════════════════════════════════════════════════")
                except (ZeroDivisionError, decimal.DivisionUndefined, decimal.InvalidOperation) as div_err:
                    print(f"║ Error analyzing {symbol}: Division error                        ║")
                    print("════════════════════════════════════════════════════════════════")
                except Exception as ticker_err:
                    print(f"║ Error analyzing {symbol}: {str(ticker_err)[:40]}               ║")
                    print("════════════════════════════════════════════════════════════════")

        except Exception as e:
            print(f"Error analyzing portfolio: {str(e)}")

    def log_transaction(self, portfolio_id, transaction_type, date_str, ticker_symbol, shares=None, price=None, amount=None):
        try:
            # Validate portfolio
            if not self.portfolio_dao.read_portfolio(portfolio_id):
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Parse date
            try:
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                print("Error: Invalid date format. Please use YYYY-MM-DD format.")
                return

            # Handle cash transactions first - use the new cash_balance_history method
            if transaction_type == 'cash':
                if amount is None:
                    print("Error: cash transactions require amount parameter.")
                    return
                
                # Use the new log_cash_transaction method which handles both the cash balance and history
                cash_action = "deposit" if amount > 0 else "withdrawal"
                description = f"Cash {cash_action}"
                
                # Log to cash history and update the balance in one operation
                new_balance = self.portfolio_dao.log_cash_transaction(
                    portfolio_id, 
                    amount, 
                    cash_action,
                    description, 
                    date
                )
                
                print(f"\nSuccessfully logged cash transaction:")
                if amount > 0:
                    print(f"${amount:.2f} deposit")
                else:
                    print(f"${abs(amount):.2f} withdrawal")
                return
                
            # For non-cash transactions, we need ticker and security info
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id and transaction_type in ['buy', 'sell', 'dividend']:
                print(f"Error: Ticker symbol {ticker_symbol} not found.")
                return
                
            security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
            if not security_id and transaction_type in ['buy', 'sell', 'dividend']:
                print(f"Error: {ticker_symbol} not found in portfolio {portfolio_id}.")
                return

            # Validate transaction type and parameters
            if transaction_type in ['buy', 'sell']:
                if shares is None or price is None:
                    print(f"Error: {transaction_type} transactions require both shares and price parameters.")
                    return
                amount = None  # Ensure amount is None for buy/sell
                
                # Calculate the cash impact
                total_cost = shares * price
                
                # Prepare description for cash history
                description = f"{transaction_type.title()} {shares} shares of {ticker_symbol} at ${price:.2f}"
                
                if transaction_type == 'buy':
                    # Check if there's enough cash for the purchase
                    cash_balance = self.portfolio_dao.get_cash_balance(portfolio_id)
                    if cash_balance < total_cost:
                        print(f"Warning: Insufficient cash balance for purchase. Required: ${total_cost:.2f}, Available: ${cash_balance:.2f}")
                        proceed = input("Do you want to proceed anyway? (y/n): ").lower().strip()
                        if proceed != 'y':
                            print("Transaction cancelled.")
                            return
                    
                    # Log the cash withdrawal for the purchase
                    new_balance = self.portfolio_dao.log_cash_transaction(
                        portfolio_id,
                        -total_cost,  # Negative amount for buy
                        "buy",
                        description,
                        date
                    )
                    print(f"Cash balance updated: ${new_balance:.2f} (after purchase)")
                
                elif transaction_type == 'sell':
                    # Log the cash deposit from the sale
                    new_balance = self.portfolio_dao.log_cash_transaction(
                        portfolio_id,
                        total_cost,  # Positive amount for sell
                        "sell",
                        description,
                        date
                    )
                    print(f"Cash balance updated: ${new_balance:.2f} (after sale)")
            
            elif transaction_type == 'dividend':
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
                    date
                )
                print(f"Cash balance updated: ${new_balance:.2f} (after dividend)")
            
            else:
                print("Error: Invalid transaction type. Must be 'buy', 'sell', 'dividend', or 'cash'.")
                return

            # Log transaction to portfolio_transactions table for all non-cash transactions
            self.transactions_dao.insert_transaction(
                portfolio_id, security_id, transaction_type, date, shares, price, amount
            )

            # Print confirmation
            print(f"\nSuccessfully logged {transaction_type} transaction:")
            print(f"- {ticker_symbol}: ", end='')
            if transaction_type in ['buy', 'sell']:
                print(f"{shares} shares at ${price:.2f} each")
            elif transaction_type == 'dividend':
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
            transactions = self.transactions_dao.get_transaction_history(portfolio_id, security_id)
            if not transactions:
                print("No transactions found.")
                return

            # Print transactions
            print("\nTransaction History:")
            print("--------------------------------------------------------------------------------")
            print("Date         Type       Symbol   Shares    Price      Amount    ")
            print("--------------------------------------------------------------------------------")
            
            for t in transactions:
                date = t['transaction_date'].strftime('%Y-%m-%d')
                type_str = t['transaction_type'].ljust(10)
                symbol = t['symbol'].ljust(8)
                
                if t['transaction_type'] in ['buy', 'sell']:
                    shares = str(t['shares']).rjust(8)
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

            print(f"\nRecalculating historical values for portfolio: {portfolio['name']}")
            if from_date:
                print(f"Starting from: {from_date}")
            else:
                print("Starting from earliest transaction date")

            # Call the recalculate method
            result = self.value_calculator.recalculate_historical_values(portfolio_id, from_date)
            
            if result:
                print("\nPortfolio historical values have been successfully recalculated.")
            else:
                print("\nFailed to recalculate portfolio historical values.")
                
        except Exception as e:
            print(f"Error recalculating portfolio history: {str(e)}")
    
    def view_portfolio_performance(self, portfolio_id, days=30, start_date=None, end_date=None, generate_chart=False):
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
            cursor = self.value_calculator.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM portfolio_value WHERE portfolio_id = %s", (portfolio_id,))
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"Generating {days} days of performance history...")
                self.value_calculator.update_portfolio_value_history(portfolio_id, days)
                print("Performance history generation complete.")
            
            # Get performance metrics
            metrics = self.value_calculator.calculate_performance_metrics(
                portfolio_id, start_date, end_date)
                
            if metrics['initial_value'] is None:
                print("No performance data available for the specified period.")
                return
                
            # Display performance metrics
            print(f"\nPerformance Metrics:")
            print(f"Initial Value: ${metrics['initial_value']:.2f}")
            print(f"Final Value: ${metrics['final_value']:.2f}")
            print(f"Total Return: {metrics['total_return']:.2f}%")
            
            if metrics['annualized_return'] is not None:
                print(f"Annualized Return: {metrics['annualized_return']:.2f}%")
            
            print(f"Period: {metrics['period_days']} days")
            
            # Get and display performance data
            df = self.value_calculator.get_portfolio_performance(portfolio_id, start_date, end_date)
            if not df.empty:
                print("\nPortfolio Value History:")
                print("--------------------------------------------------")
                for date, row in df.iterrows():
                    print(f"{date.strftime('%Y-%m-%d')}: ${row['value']:.2f}")
            
            # Generate chart if requested
            if generate_chart:
                chart_path = self.value_calculator.generate_performance_chart(portfolio_id, start_date, end_date)
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

    # Watch List Methods
    def create_watch_list(self, name, description=None):
        """Create a new watch list"""
        try:
            watch_list_id = self.watch_list_dao.create_watch_list(name, description)
            if watch_list_id:
                print(f"\nSuccessfully created new watch list:")
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
                if wl['description']:
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
            if watch_list['description']:
                print(f"Description: {watch_list['description']}")
            print(f"Created: {watch_list['date_created'].strftime('%Y-%m-%d')}")
            
            tickers = self.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
            if tickers:
                print("\nTickers in Watch List:")
                print("--------------------------------------------------")
                for ticker in tickers:
                    print(f"Symbol: {ticker['symbol']} - {ticker['name']}")
                    if ticker['notes']:
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
                if self.watch_list_dao.add_ticker_to_watch_list(watch_list_id, symbol, notes):
                    added_count += 1
                    
            if added_count > 0:
                print(f"\nSuccessfully added {added_count} ticker(s) to watch list \"{watch_list['name']}\"")
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
                if self.watch_list_dao.remove_ticker_from_watch_list(watch_list_id, symbol):
                    removed_count += 1
                    
            if removed_count > 0:
                print(f"\nSuccessfully removed {removed_count} ticker(s) from watch list \"{watch_list['name']}\"")
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
            if self.watch_list_dao.update_ticker_notes(watch_list_id, ticker_symbol, notes):
                print(f"\nSuccessfully updated notes for {ticker_symbol} in watch list \"{watch_list['name']}\"")
            else:
                print(f"Failed to update notes. Check if {ticker_symbol} is in the watch list.")
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
        """Analyze tickers in a watch list"""
        try:
            # Verify watch list exists
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
            if not watch_list:
                print(f"Error: Watch list {watch_list_id} does not exist.")
                return
                
            # Get tickers in watch list
            if ticker_symbol:
                # Check if ticker is in watch list
                if not self.watch_list_dao.is_ticker_in_watch_list(watch_list_id, ticker_symbol):
                    print(f"Error: {ticker_symbol} is not in watch list {watch_list_id}.")
                    return
                ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
                if not ticker_id:
                    print(f"Error: Ticker symbol {ticker_symbol} not found.")
                    return
                tickers = [(ticker_id, ticker_symbol)]
            else:
                # Get all tickers in watch list
                ticker_data = self.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
                if not ticker_data:
                    print(f"Watch list {watch_list_id} has no tickers to analyze.")
                    return
                tickers = [(t['ticker_id'], t['symbol']) for t in ticker_data]
                
            print(f"\nAnalyzing Watch List: {watch_list['name']}")
            print("════════════════════════════════════════════════════════════════")
            
            for ticker_id, symbol in tickers:
                print(f"║ {symbol:<56}║")
                print("║──────────────────────────────────────────────────────────║")

                # RSI Analysis
                self.rsi_calc.calculateRSI(ticker_id)  # Calculate latest RSI
                rsi_result = self.rsi_calc.retrievePrices(1, ticker_id)  # Get the calculated RSI
                if not rsi_result.empty:
                    latest_rsi = rsi_result.iloc[-1]
                    rsi_value = latest_rsi['rsi']
                    rsi_date = rsi_result.index[-1]
                    rsi_status = "Overbought" if rsi_value > 70 else "Oversold" if rsi_value < 30 else "Neutral"
                    print(f"║ RSI ({rsi_date.strftime('%Y-%m-%d')}): {rsi_value:.2f} - {rsi_status:<45}║")

                # Moving Average with Trend Analysis
                ma_data = self.moving_avg.update_moving_averages(ticker_id, 20)
                if not ma_data.empty:
                    latest_ma = ma_data.iloc[-1]
                    # Parse date string from index
                    date_str = str(ma_data.index[-1]).split()[0]
                    dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    print(f"║ 20-day MA ({dt.strftime('%Y-%m-%d')}): {latest_ma.iloc[0]:.2f}{' ' * 45}║")
                    
                    # Get MA trend analysis
                    ma_trend = self.trend_analyzer.analyze_ma_trend(ticker_id, 20)
                    direction_emoji = "↗️" if ma_trend["direction"] == "UP" else "↘️" if ma_trend["direction"] == "DOWN" else "➡️"
                    print(f"║ MA Trend: {direction_emoji} {ma_trend['direction']} ({ma_trend['strength']}){' ' * 34}║")
                    if ma_trend["percent_change"] is not None:
                        print(f"║   Rate of Change: {ma_trend['percent_change']:.2f}%{' ' * 39}║")
                    
                    # Get price vs MA analysis
                    price_vs_ma = self.trend_analyzer.analyze_price_vs_ma(ticker_id, 20)
                    if price_vs_ma["position"] != "UNKNOWN":
                        position_text = "Above MA" if price_vs_ma["position"] == "ABOVE_MA" else "Below MA" if price_vs_ma["position"] == "BELOW_MA" else "At MA"
                        distance_formatted = f"{price_vs_ma['distance_percent']:.2f}"
                        print(f"║ Price Position: {position_text} ({distance_formatted}% from MA){' ' * (29 - len(distance_formatted))}║")

                # Show notes if available
                notes = None
                for t in self.watch_list_dao.get_tickers_in_watch_list(watch_list_id):
                    if t['symbol'] == symbol and t['notes']:
                        notes = t['notes']
                if notes:
                    print(f"║ Notes: {notes[:50]}{' ' * (51 - min(50, len(notes)))}║")
                    if len(notes) > 50:
                        print(f"║   {notes[50:100]}{' ' * (57 - min(50, len(notes) - 50))}║")

                print("════════════════════════════════════════════════════════════════")
                
        except Exception as e:
            print(f"Error analyzing watch list: {str(e)}")
            import traceback
            traceback.print_exc()

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
            
            if action == 'view':
                print(f"\nCash Balance for Portfolio: {portfolio['name']}")
                print(f"Available Cash: ${current_balance:.2f}")
                return
                
            # Validate amount for deposit/withdraw actions
            if action in ['deposit', 'withdraw'] and amount is None:
                print(f"Error: {action} action requires an amount parameter.")
                return
                
            # Process deposit/withdraw
            if action == 'deposit':
                new_balance = self.portfolio_dao.add_cash(portfolio_id, amount)
                print(f"\nDeposited ${amount:.2f} to portfolio {portfolio['name']}")
                print(f"New Cash Balance: ${new_balance:.2f}")
            elif action == 'withdraw':
                if current_balance < amount:
                    print(f"Warning: Insufficient funds. Available: ${current_balance:.2f}, Requested: ${amount:.2f}")
                    proceed = input("Do you want to proceed with withdrawal anyway? (y/n): ").lower().strip()
                    if proceed != 'y':
                        print("Withdrawal cancelled.")
                        return
                
                new_balance = self.portfolio_dao.withdraw_cash(portfolio_id, amount)
                print(f"\nWithdrew ${amount:.2f} from portfolio {portfolio['name']}")
                print(f"New Cash Balance: ${new_balance:.2f}")
                
        except Exception as e:
            print(f"Error managing cash: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Portfolio Management CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create Portfolio
    create_parser = subparsers.add_parser('create-portfolio', help='Create a new portfolio')
    create_parser.add_argument('name', help='Portfolio name')
    create_parser.add_argument('description', help='Portfolio description')
    create_parser.add_argument('--initial_cash', type=float, default=0.0, help='Initial cash balance')

    # View Portfolio
    view_parser = subparsers.add_parser('view-portfolio', help='View portfolio details')
    view_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')

    # Cash Management Commands
    cash_parser = subparsers.add_parser('manage-cash', help='Manage portfolio cash balance')
    cash_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    cash_parser.add_argument('action', choices=['view', 'deposit', 'withdraw'], help='Cash management action')
    cash_parser.add_argument('--amount', type=float, help='Amount to deposit or withdraw')

    # Add Tickers
    add_parser = subparsers.add_parser('add-tickers', help='Add tickers to portfolio')
    add_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    add_parser.add_argument('ticker_symbols', nargs='+', help='Ticker symbols to add (e.g., AAPL GOOGL)')

    # Remove Tickers
    remove_parser = subparsers.add_parser('remove-tickers', help='Remove tickers from portfolio')
    remove_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    remove_parser.add_argument('ticker_symbols', nargs='+', help='Ticker symbols to remove')

    # Log Transaction
    log_parser = subparsers.add_parser('log-transaction', help='Log a transaction')
    log_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    log_parser.add_argument('type', choices=['buy', 'sell', 'dividend', 'cash'], help='Transaction type')
    log_parser.add_argument('date', help='Transaction date (YYYY-MM-DD)')
    log_parser.add_argument('ticker_symbol', nargs='?', help='Ticker symbol (not required for cash transactions)')
    log_parser.add_argument('--shares', type=float, help='Number of shares (for buy/sell)')
    log_parser.add_argument('--price', type=float, help='Price per share (for buy/sell)')
    log_parser.add_argument('--amount', type=float, help='Amount for dividend or cash transactions. For cash: positive = deposit, negative = withdrawal')

    # View Transactions
    trans_parser = subparsers.add_parser('view-transactions', help='View transaction history')
    trans_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    trans_parser.add_argument('--ticker_symbol', help='Filter by ticker symbol')

    # Analyze Portfolio
    analyze_parser = subparsers.add_parser('analyze-portfolio', help='Analyze portfolio')
    analyze_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    analyze_parser.add_argument('--ticker_symbol', help='Analyze specific ticker')
    analyze_parser.add_argument('--ma_period', type=int, default=20, help='Moving average period for analysis (default: 20)')
    analyze_parser.add_argument('--lookback_days', type=int, default=5, help='Number of days to look back for trend analysis (default: 5)')

    # Update Data
    update_parser = subparsers.add_parser('update-data', help='Update data for all securities in portfolios')
    
    # View Portfolio Performance
    performance_parser = subparsers.add_parser('view-performance', help='View portfolio performance over time')
    performance_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    performance_parser.add_argument('--days', type=int, default=30, help='Number of days of history to generate if none exists')
    performance_parser.add_argument('--start_date', help='Start date in YYYY-MM-DD format')
    performance_parser.add_argument('--end_date', help='End date in YYYY-MM-DD format')
    performance_parser.add_argument('--chart', action='store_true', help='Generate performance chart')
    
    # Recalculate Portfolio History
    recalc_parser = subparsers.add_parser('recalculate-history', help='Recalculate portfolio historical values')
    recalc_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    recalc_parser.add_argument('--from_date', help='Date from which to start recalculation (YYYY-MM-DD format)')

    # Watch List Commands
    
    # Create Watch List
    create_wl_parser = subparsers.add_parser('create-watchlist', help='Create a new watch list')
    create_wl_parser.add_argument('name', help='Watch list name')
    create_wl_parser.add_argument('--description', help='Watch list description')
    
    # View Watch Lists
    view_wl_parser = subparsers.add_parser('view-watchlists', help='View all watch lists')
    
    # View Watch List
    view_wl_details_parser = subparsers.add_parser('view-watchlist', help='View watch list details and tickers')
    view_wl_details_parser.add_argument('watch_list_id', type=int, help='Watch list ID')
    
    # Add Ticker to Watch List
    add_wl_ticker_parser = subparsers.add_parser('add-watchlist-ticker', help='Add ticker(s) to watch list')
    add_wl_ticker_parser.add_argument('watch_list_id', type=int, help='Watch list ID')
    add_wl_ticker_parser.add_argument('ticker_symbols', nargs='+', help='Ticker symbols to add')
    add_wl_ticker_parser.add_argument('--notes', help='Notes for the ticker')
    
    # Remove Ticker from Watch List
    remove_wl_ticker_parser = subparsers.add_parser('remove-watchlist-ticker', help='Remove ticker(s) from watch list')
    remove_wl_ticker_parser.add_argument('watch_list_id', type=int, help='Watch list ID')
    remove_wl_ticker_parser.add_argument('ticker_symbols', nargs='+', help='Ticker symbols to remove')
    
    # Update Watch List Ticker Notes
    update_wl_notes_parser = subparsers.add_parser('update-watchlist-notes', help='Update notes for a ticker in watch list')
    update_wl_notes_parser.add_argument('watch_list_id', type=int, help='Watch list ID')
    update_wl_notes_parser.add_argument('ticker_symbol', help='Ticker symbol')
    update_wl_notes_parser.add_argument('notes', help='Notes for the ticker')
    
    # Delete Watch List
    delete_wl_parser = subparsers.add_parser('delete-watchlist', help='Delete a watch list')
    delete_wl_parser.add_argument('watch_list_id', type=int, help='Watch list ID')
    
    # Analyze Watch List
    analyze_wl_parser = subparsers.add_parser('analyze-watchlist', help='Analyze tickers in a watch list')
    analyze_wl_parser.add_argument('watch_list_id', type=int, help='Watch list ID')
    analyze_wl_parser.add_argument('--ticker_symbol', help='Analyze specific ticker')
    
    args = parser.parse_args()
    cli = PortfolioCLI()

    if args.command == 'create-portfolio':
        cli.create_portfolio(args.name, args.description)
    elif args.command == 'view-portfolio':
        cli.view_portfolio(args.portfolio_id)
    elif args.command == 'add-tickers':
        cli.add_tickers(args.portfolio_id, args.ticker_symbols)
    elif args.command == 'remove-tickers':
        cli.remove_tickers(args.portfolio_id, args.ticker_symbols)
    elif args.command == 'log-transaction':
        cli.log_transaction(
            args.portfolio_id, args.type, args.date, args.ticker_symbol,
            args.shares, args.price, args.amount
        )
    elif args.command == 'view-transactions':
        cli.view_transactions(args.portfolio_id, args.ticker_symbol)
    elif args.command == 'analyze-portfolio':
        cli.analyze_portfolio(args.portfolio_id, args.ticker_symbol)
    elif args.command == 'update-data':
        cli.update_data()
    elif args.command == 'view-performance':
        cli.view_portfolio_performance(
            args.portfolio_id, args.days, args.start_date, args.end_date, args.chart
        )
    elif args.command == 'recalculate-history':
        cli.recalculate_portfolio_history(args.portfolio_id, args.from_date)
    elif args.command == 'create-watchlist':
        cli.create_watch_list(args.name, args.description)
    elif args.command == 'view-watchlists':
        cli.view_watch_lists()
    elif args.command == 'view-watchlist':
        cli.view_watch_list(args.watch_list_id)
    elif args.command == 'add-watchlist-ticker':
        cli.add_watch_list_ticker(args.watch_list_id, args.ticker_symbols, args.notes)
    elif args.command == 'remove-watchlist-ticker':
        cli.remove_watch_list_ticker(args.watch_list_id, args.ticker_symbols)
    elif args.command == 'update-watchlist-notes':
        cli.update_watch_list_ticker_notes(args.watch_list_id, args.ticker_symbol, args.notes)
    elif args.command == 'delete-watchlist':
        cli.delete_watch_list(args.watch_list_id)
    elif args.command == 'analyze-watchlist':
        cli.analyze_watch_list(args.watch_list_id, args.ticker_symbol)
    elif args.command == 'manage-cash':
        cli.manage_cash(args.portfolio_id, args.action, args.amount)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
