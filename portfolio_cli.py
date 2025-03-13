import argparse
import os
from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.ticker_dao import TickerDao
from data.rsi_calculations import rsi_calculations
from data.moving_averages import moving_averages
from data.bollinger_bands import BollingerBandAnalyzer
from data.fundamental_data_dao import FundamentalDataDAO
from data.news_sentiment_analyzer import NewsSentimentAnalyzer
from data.data_retrival import DataRetrieval
from data.portfolio_value_calculator import PortfolioValueCalculator
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
        self.news_analyzer = NewsSentimentAnalyzer(db_user, db_password, db_host, db_name)
        self.data_retrieval = DataRetrieval(db_user, db_password, db_host, db_name)
        self.value_calculator = PortfolioValueCalculator(db_user, db_password, db_host, db_name)
        
        # Open database connections for classes that need it
        self.portfolio_dao.open_connection()
        self.transactions_dao.open_connection()
        self.ticker_dao.open_connection()
        self.rsi_calc.open_connection()
        self.moving_avg.open_connection()
        self.fundamental_dao.open_connection()
        self.value_calculator.open_connection()

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

            # Get tickers to analyze
            if ticker_symbol:
                ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
                if not ticker_id:
                    print(f"Error: Ticker symbol {ticker_symbol} not found.")
                    return
                tickers = [(ticker_id, ticker_symbol)]
            else:
                tickers = [(self.ticker_dao.get_ticker_id(symbol), symbol) 
                          for symbol in self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)]

            if not tickers:
                print("No tickers to analyze.")
                return

            print("\nTechnical Analysis Results:")
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

                # Moving Average
                ma_data = self.moving_avg.update_moving_averages(ticker_id, 20)
                if not ma_data.empty:
                    latest_ma = ma_data.iloc[-1]
                    # Parse date string from index
                    date_str = str(ma_data.index[-1]).split()[0]
                    dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    print(f"║ 20-day MA ({dt.strftime('%Y-%m-%d')}): {latest_ma.iloc[0]:.2f}{' ' * 45}║")

                # Bollinger Bands
                bb_data = self.bb_analyzer.generate_bollinger_band_data(ticker_id)
                if bb_data:
                    bb_mean = bb_data['bollinger_bands']['mean']
                    bb_stddev = bb_data['bollinger_bands']['stddev']
                    print(f"║ Bollinger Bands:                                             ║")
                    print(f"║   Mean: {bb_mean:.2f}{' ' * 49}║")
                    print(f"║   StdDev: {bb_stddev:.2f}{' ' * 47}║")

                # Fundamental Data
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

                # News Sentiment
                sentiment_data = self.news_analyzer.get_sentiment_summary(ticker_id, symbol)
                if sentiment_data and sentiment_data['status'] != 'No sentiment data available':
                    print(f"║ News Sentiment: {sentiment_data['status']:<47}║")
                    print(f"║   Average Score: {sentiment_data['average_sentiment']:.2f}{' ' * 41}║")
                    print(f"║   Articles Analyzed: {sentiment_data['article_count']}{' ' * 39}║")
                else:
                    print("║ News Sentiment: No data available                              ║")

                print("════════════════════════════════════════════════════════════════")

        except Exception as e:
            print(f"Error analyzing portfolio: {str(e)}")

    def log_transaction(self, portfolio_id, transaction_type, date_str, ticker_symbol, shares=None, price=None, amount=None):
        try:
            # Validate portfolio
            if not self.portfolio_dao.read_portfolio(portfolio_id):
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Get ticker_id and security_id
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                print(f"Error: Ticker symbol {ticker_symbol} not found.")
                return
                
            security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
            if not security_id:
                print(f"Error: {ticker_symbol} not found in portfolio {portfolio_id}.")
                return

            # Parse date
            try:
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                print("Error: Invalid date format. Please use YYYY-MM-DD format.")
                return

            # Validate transaction type and parameters
            if transaction_type in ['buy', 'sell']:
                if shares is None or price is None:
                    print(f"Error: {transaction_type} transactions require both shares and price parameters.")
                    return
                amount = None  # Ensure amount is None for buy/sell
            elif transaction_type == 'dividend':
                if amount is None:
                    print("Error: dividend transactions require amount parameter.")
                    return
                shares = price = None  # Ensure shares and price are None for dividend
            else:
                print("Error: Invalid transaction type. Must be 'buy', 'sell', or 'dividend'.")
                return

            # Log transaction
            self.transactions_dao.insert_transaction(
                portfolio_id, security_id, transaction_type, date, shares, price, amount
            )

            # Print confirmation
            print(f"\nSuccessfully logged {transaction_type} transaction:")
            print(f"- {ticker_symbol}: ", end='')
            if transaction_type in ['buy', 'sell']:
                print(f"{shares} shares at ${price:.2f} each")
            else:  # dividend
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

def main():
    parser = argparse.ArgumentParser(description='Portfolio Management CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create Portfolio
    create_parser = subparsers.add_parser('create-portfolio', help='Create a new portfolio')
    create_parser.add_argument('name', help='Portfolio name')
    create_parser.add_argument('description', help='Portfolio description')

    # View Portfolio
    view_parser = subparsers.add_parser('view-portfolio', help='View portfolio details')
    view_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')

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
    log_parser.add_argument('type', choices=['buy', 'sell', 'dividend'], help='Transaction type')
    log_parser.add_argument('date', help='Transaction date (YYYY-MM-DD)')
    log_parser.add_argument('ticker_symbol', help='Ticker symbol')
    log_parser.add_argument('--shares', type=float, help='Number of shares (for buy/sell)')
    log_parser.add_argument('--price', type=float, help='Price per share (for buy/sell)')
    log_parser.add_argument('--amount', type=float, help='Dividend amount')

    # View Transactions
    trans_parser = subparsers.add_parser('view-transactions', help='View transaction history')
    trans_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    trans_parser.add_argument('--ticker_symbol', help='Filter by ticker symbol')

    # Analyze Portfolio
    analyze_parser = subparsers.add_parser('analyze-portfolio', help='Analyze portfolio')
    analyze_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    analyze_parser.add_argument('--ticker_symbol', help='Analyze specific ticker')

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
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
