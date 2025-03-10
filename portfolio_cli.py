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
import datetime
from dotenv import load_dotenv

class PortfolioCLI:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.portfolio_dao.open_connection()
        self.portfolio_transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        self.portfolio_transactions_dao.open_connection()
        self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)
        self.ticker_dao.open_connection()
        
        # Initialize technical analysis tools
        self.rsi_calculator = rsi_calculations(db_user, db_password, db_host, db_name)
        self.rsi_calculator.open_connection()
        self.moving_avg = moving_averages(db_user, db_password, db_host, db_name)
        self.moving_avg.open_connection()
        self.bollinger = BollingerBandAnalyzer(self.ticker_dao)
        self.fundamental_dao = FundamentalDataDAO(db_user, db_password, db_host, db_name)
        self.fundamental_dao.open_connection()
        self.sentiment_analyzer = NewsSentimentAnalyzer(db_user, db_password, db_host, db_name)
        
    def create_portfolio(self, args):
        try:
            portfolio_id = self.portfolio_dao.create_portfolio(args.name, args.description)
            if portfolio_id:
                print(f"\nSuccessfully created new portfolio:")
                print(f"Portfolio ID: {portfolio_id}")
                print(f"Name: {args.name}")
                print(f"Description: {args.description}")
            else:
                print("Failed to create portfolio")
        except Exception as e:
            print(f"Error creating portfolio: {str(e)}")

    def add_tickers(self, args):
        try:
            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(args.portfolio_id):
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return

            # Validate and filter ticker IDs
            valid_tickers = []
            invalid_tickers = []
            for ticker_id in args.ticker_ids:
                if self.ticker_dao.get_ticker_symbol(ticker_id):
                    valid_tickers.append(ticker_id)
                else:
                    invalid_tickers.append(ticker_id)

            if valid_tickers:
                self.portfolio_dao.add_tickers_to_portfolio(args.portfolio_id, valid_tickers)
                print(f"\nSuccessfully added {len(valid_tickers)} ticker(s) to portfolio {args.portfolio_id}")
                print("\nAdded tickers:")
                for ticker_id in valid_tickers:
                    symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                    print(f"- {symbol} (ID: {ticker_id})")

            if invalid_tickers:
                print("\nWarning: The following ticker IDs were not found and were skipped:")
                for ticker_id in invalid_tickers:
                    print(f"- Ticker ID {ticker_id}")

        except Exception as e:
            print(f"Error adding tickers: {str(e)}")

    def remove_tickers(self, args):
        try:
            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(args.portfolio_id):
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return

            # Validate tickers are in portfolio
            not_in_portfolio = []
            to_remove = []
            for ticker_id in args.ticker_ids:
                if self.portfolio_dao.is_ticker_in_portfolio(args.portfolio_id, ticker_id):
                    to_remove.append(ticker_id)
                else:
                    not_in_portfolio.append(ticker_id)

            if to_remove:
                self.portfolio_dao.remove_tickers_from_portfolio(args.portfolio_id, to_remove)
                print(f"\nSuccessfully removed {len(to_remove)} ticker(s) from portfolio {args.portfolio_id}")
                print("\nRemoved tickers:")
                for ticker_id in to_remove:
                    symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                    print(f"- {symbol} (ID: {ticker_id})")

            if not_in_portfolio:
                print("\nWarning: The following tickers were not found in the portfolio:")
                for ticker_id in not_in_portfolio:
                    print(f"- Ticker ID {ticker_id}")

        except Exception as e:
            print(f"Error removing tickers: {str(e)}")

    def log_transaction(self, args):
        try:
            transaction_date = datetime.datetime.strptime(args.transaction_date, '%Y-%m-%d').date()
            portfolio_id = args.portfolio_id
            transaction_type = args.transaction_type
            shares = args.shares
            price = args.price
            amount = args.amount

            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(portfolio_id):
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Validate transaction parameters
            if transaction_type in ['buy', 'sell'] and (shares is None or price is None):
                print(f"Error: {transaction_type} transactions require both shares and price parameters.")
                return
            elif transaction_type == 'dividend' and amount is None:
                print("Error: Dividend transactions require the amount parameter.")
                return

            # Process transactions
            failed_tickers = []
            successful_tickers = []
            for ticker_id in args.ticker_ids:
                security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
                if not security_id:
                    failed_tickers.append(ticker_id)
                    continue

                if transaction_type in ['buy', 'sell']:
                    self.portfolio_dao.log_transaction(portfolio_id, security_id, transaction_type, transaction_date, shares, price)
                else:  # dividend
                    self.portfolio_dao.log_transaction(portfolio_id, security_id, transaction_type, transaction_date, amount=amount)
                successful_tickers.append(ticker_id)

            if successful_tickers:
                print(f"\nSuccessfully logged {transaction_type} transactions:")
                for ticker_id in successful_tickers:
                    symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                    if transaction_type in ['buy', 'sell']:
                        print(f"- {symbol}: {shares} shares at ${price:.2f} each")
                    else:
                        print(f"- {symbol}: ${amount:.2f} dividend")

            if failed_tickers:
                print(f"\nWarning: The following tickers are not associated with portfolio {portfolio_id} and were skipped:")
                for ticker_id in failed_tickers:
                    print(f"- Ticker ID {ticker_id}")

        except ValueError as e:
            print(f"Error: Invalid date format. Please use YYYY-MM-DD format. ({str(e)})")
        except Exception as e:
            print(f"Error processing transaction: {str(e)}")

    def view_transactions(self, args):
        try:
            portfolio_id = args.portfolio_id
            security_id = args.security_id

            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(portfolio_id):
                print(f"Error: Portfolio {portfolio_id} does not exist.")
                return

            # Get transactions
            transactions = self.portfolio_transactions_dao.get_transaction_history(portfolio_id, security_id)
            
            if not transactions:
                print(f"No transactions found for portfolio {portfolio_id}" + 
                      (f" and security {security_id}" if security_id else ""))
                return

            # Print header
            print("\nTransaction History:")
            print("-" * 80)
            print(f"{'Date':<12} {'Type':<10} {'Symbol':<8} {'Shares':<8} {'Price':<10} {'Amount':<10}")
            print("-" * 80)

            # Print transactions in a formatted table
            for transaction in transactions:
                date = transaction[3].strftime('%Y-%m-%d')
                trans_type = transaction[2]
                security_id = transaction[1]
                symbol = self.ticker_dao.get_ticker_symbol(security_id) if security_id else 'N/A'
                shares = f"{transaction[4]}" if transaction[4] else 'N/A'
                price = f"${transaction[5]:.2f}" if transaction[5] else 'N/A'
                amount = f"${transaction[6]:.2f}" if transaction[6] else 'N/A'
                
                print(f"{date:<12} {trans_type:<10} {symbol:<8} {shares:<8} {price:<10} {amount:<10}")

        except Exception as e:
            print(f"Error viewing transactions: {str(e)}")

    def view_portfolio(self, args):
        try:
            portfolio_details = self.portfolio_dao.read_portfolio(args.portfolio_id)
            
            if not portfolio_details:
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return
                
            portfolio_details = portfolio_details[0]
            portfolio_id, name, description, active, date_added = portfolio_details
            
            print("\nPortfolio Details:")
            print("-" * 50)
            print(f"Portfolio ID:  {portfolio_id}")
            print(f"Name:         {name}")
            print(f"Description:  {description}")
            print(f"Status:       {'Active' if active else 'Inactive'}")
            print(f"Date Added:   {date_added.strftime('%Y-%m-%d')}")
            
            tickers = self.portfolio_dao.get_tickers_in_portfolio(args.portfolio_id)
            
            if tickers:
                print("\nTickers in Portfolio:")
                print("-" * 50)
                for ticker in tickers:
                    symbol = self.ticker_dao.get_ticker_symbol(ticker)
                    print(f"Symbol: {symbol:<6} (ID: {ticker})")
            else:
                print("\nNo tickers currently in portfolio.")

        except Exception as e:
            print(f"Error viewing portfolio: {str(e)}")

    def close_connection(self):
        self.portfolio_dao.close_connection()
        self.portfolio_transactions_dao.close_connection()
        self.ticker_dao.close_connection()
        self.rsi_calculator.close_connection()
        self.moving_avg.close_connection()
        self.fundamental_dao.close_connection()
        self.sentiment_analyzer.close_connection()

    def analyze_news_sentiment(self, args):
        """Analyze news sentiment for specified portfolio/ticker"""
        try:
            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(args.portfolio_id):
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return

            # Get tickers to analyze
            if args.ticker_id:
                if not self.portfolio_dao.is_ticker_in_portfolio(args.portfolio_id, args.ticker_id):
                    print(f"Error: Ticker ID {args.ticker_id} not found in portfolio {args.portfolio_id}")
                    return
                tickers = [args.ticker_id]
            else:
                tickers = self.portfolio_dao.get_tickers_in_portfolio(args.portfolio_id)

            # Analyze each ticker
            for ticker_id in tickers:
                symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                
                # Fetch and analyze latest news if requested
                if args.update:
                    print(f"\nFetching latest news for {symbol}...")
                    self.sentiment_analyzer.fetch_and_analyze_news(ticker_id, symbol)
                
                # Get sentiment summary
                summary = self.sentiment_analyzer.get_sentiment_summary(ticker_id, symbol)
                
                if summary:
                    print(f"\nNews Sentiment Analysis for {summary['symbol']}:")
                    print("-" * 50)
                    print(f"Overall Sentiment: {summary['status']}")
                    print(f"Average Score: {summary['average_sentiment']:.4f}")
                    print(f"Articles Analyzed: {summary['article_count']}")
                    
                    if summary['articles']:
                        print("\nRecent Headlines:")
                        for article in summary['articles'][:5]:  # Show 5 most recent
                            print(f"\n{article['headline']}")
                            print(f"Publisher: {article['publisher']}")
                            print(f"Date: {article['date']}")
                            print(f"Sentiment: {article['sentiment']:.4f} (Confidence: {article['confidence']:.4f})")
                            print(f"Link: {article['link']}")
                else:
                    print(f"\nNo sentiment data available for {symbol}")

        except Exception as e:
            print(f"Error analyzing news sentiment: {str(e)}")

    def view_fundamentals(self, args):
        """View fundamental data for specified portfolio/ticker"""
        try:
            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(args.portfolio_id):
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return

            # Get tickers to analyze
            if args.ticker_id:
                if not self.portfolio_dao.is_ticker_in_portfolio(args.portfolio_id, args.ticker_id):
                    print(f"Error: Ticker ID {args.ticker_id} not found in portfolio {args.portfolio_id}")
                    return
                tickers = [args.ticker_id]
            else:
                tickers = self.portfolio_dao.get_tickers_in_portfolio(args.portfolio_id)

            # Analyze each ticker
            for ticker_id in tickers:
                symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                print(f"\nFundamental Analysis for {symbol} (ID: {ticker_id}):")
                print("-" * 50)
                
                data = self.fundamental_dao.get_latest_fundamental_data(ticker_id)
                if data:
                    print(f"Data as of: {data['date'].strftime('%Y-%m-%d')}")
                    print("\nValuation Metrics:")
                    print(f"P/E Ratio:      {data['pe_ratio'] or 'N/A'}")
                    print(f"Forward P/E:     {data['forward_pe'] or 'N/A'}")
                    print(f"PEG Ratio:       {data['peg_ratio'] or 'N/A'}")
                    print(f"Price/Book:      {data['price_to_book'] or 'N/A'}")
                    
                    print("\nDividend Information:")
                    print(f"Dividend Yield:  {(data['dividend_yield']*100 if data['dividend_yield'] else 'N/A')}%")
                    print(f"Dividend Rate:   ${data['dividend_rate'] or 'N/A'}")
                    
                    print("\nGrowth & Profitability:")
                    print(f"EPS (TTM):       ${data['eps_ttm'] or 'N/A'}")
                    print(f"EPS Growth:      {(data['eps_growth']*100 if data['eps_growth'] else 'N/A')}%")
                    print(f"Revenue Growth:  {(data['revenue_growth']*100 if data['revenue_growth'] else 'N/A')}%")
                    print(f"Profit Margin:   {(data['profit_margin']*100 if data['profit_margin'] else 'N/A')}%")
                    
                    print("\nFinancial Health:")
                    print(f"Debt/Equity:     {data['debt_to_equity'] or 'N/A'}")
                    print(f"Market Cap:      ${data['market_cap']:,.2f}" if data['market_cap'] else "Market Cap:      N/A")
                else:
                    print("No fundamental data available")

        except Exception as e:
            print(f"Error viewing fundamental data: {str(e)}")

    def analyze_rsi(self, args):
        """Analyze RSI for specified portfolio/ticker"""
        try:
            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(args.portfolio_id):
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return

            # Get tickers to analyze
            if args.ticker_id:
                if not self.portfolio_dao.is_ticker_in_portfolio(args.portfolio_id, args.ticker_id):
                    print(f"Error: Ticker ID {args.ticker_id} not found in portfolio {args.portfolio_id}")
                    return
                tickers = [args.ticker_id]
            else:
                tickers = self.portfolio_dao.get_tickers_in_portfolio(args.portfolio_id)

            # Analyze each ticker
            for ticker_id in tickers:
                symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                print(f"\nRSI Analysis for {symbol} (ID: {ticker_id}):")
                print("-" * 50)
                
                # Calculate RSI
                self.rsi_calculator.calculateRSI(ticker_id)
                
                # Get latest RSI value
                cursor = self.rsi_calculator.current_connection.cursor()
                cursor.execute("""
                    SELECT r.rsi, r.activity_date 
                    FROM investing.rsi r 
                    WHERE r.ticker_id = %s 
                    ORDER BY r.activity_date DESC 
                    LIMIT 1
                """, (ticker_id,))
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    rsi_value, date = result
                    print(f"Latest RSI ({date.strftime('%Y-%m-%d')}): {rsi_value}")
                    
                    # Interpret RSI
                    if rsi_value > 70:
                        print("Status: Overbought - Consider taking profits")
                    elif rsi_value < 30:
                        print("Status: Oversold - Consider buying opportunity")
                    else:
                        print("Status: Neutral")
                else:
                    print("No RSI data available")

        except Exception as e:
            print(f"Error analyzing RSI: {str(e)}")

    def analyze_ma(self, args):
        """Analyze Moving Averages for specified portfolio/ticker"""
        try:
            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(args.portfolio_id):
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return

            # Get tickers to analyze
            if args.ticker_id:
                if not self.portfolio_dao.is_ticker_in_portfolio(args.portfolio_id, args.ticker_id):
                    print(f"Error: Ticker ID {args.ticker_id} not found in portfolio {args.portfolio_id}")
                    return
                tickers = [args.ticker_id]
            else:
                tickers = self.portfolio_dao.get_tickers_in_portfolio(args.portfolio_id)

            period = args.period if args.period else 20  # Default to 20-day MA

            # Analyze each ticker
            for ticker_id in tickers:
                symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                print(f"\nMoving Average Analysis for {symbol} (ID: {ticker_id}):")
                print("-" * 50)
                
                # Calculate and get moving averages
                ma_data = self.moving_avg.update_moving_averages(ticker_id, period)
                
                if not ma_data.empty:
                    latest_ma = ma_data.iloc[-1]
                    print(f"{period}-day Moving Average ({ma_data.index[-1].strftime('%Y-%m-%d')}): {latest_ma[0]:.2f}")
                else:
                    print("No moving average data available")

        except Exception as e:
            print(f"Error analyzing Moving Averages: {str(e)}")

    def display_dashboard(self, args):
        """Display a comprehensive dashboard for the portfolio"""
        try:
            # Validate portfolio exists and get details
            portfolio_details = self.portfolio_dao.read_portfolio(args.portfolio_id)
            if not portfolio_details:
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return
                
            portfolio_details = portfolio_details[0]
            portfolio_id, name, description, active, date_added = portfolio_details
            
            # Get all tickers in portfolio
            tickers = self.portfolio_dao.get_tickers_in_portfolio(args.portfolio_id)
            if not tickers:
                print("\nNo tickers in portfolio to display.")
                return

            # Print dashboard header
            print("\n" + "=" * 80)
            print(f"{'Portfolio Dashboard':^80}")
            print("=" * 80)
            print(f"\nPortfolio: {name} (ID: {portfolio_id})")
            print(f"Status: {'Active' if active else 'Inactive'}")
            print("-" * 80)

            # Process each ticker
            for ticker_id in tickers:
                symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                print(f"\n{'╔' + '═' * 78 + '╗'}")
                print(f"║{f' {symbol} Analysis ':^78}║")
                print(f"{'╠' + '═' * 78 + '╣'}")

                # Technical Indicators Section
                print(f"║{' Technical Indicators ':^78}║")
                print(f"{'╟' + '─' * 78 + '╢'}")
                
                # RSI
                cursor = self.rsi_calculator.current_connection.cursor()
                cursor.execute("""
                    SELECT r.rsi, r.activity_date 
                    FROM investing.rsi r 
                    WHERE r.ticker_id = %s 
                    ORDER BY r.activity_date DESC 
                    LIMIT 1
                """, (ticker_id,))
                rsi_result = cursor.fetchone()
                cursor.close()
                
                if rsi_result:
                    rsi_value, rsi_date = rsi_result
                    rsi_status = "Overbought" if rsi_value > 70 else "Oversold" if rsi_value < 30 else "Neutral"
                    print(f"║ RSI ({rsi_date.strftime('%Y-%m-%d')}): {rsi_value:.2f} - {rsi_status:<45}║")

                # Moving Average
                ma_data = self.moving_avg.update_moving_averages(ticker_id, 20)
                if not ma_data.empty:
                    latest_ma = ma_data.iloc[-1]
                    print(f"║ 20-day MA: {latest_ma[0]:.2f}{' ' * 57}║")

                # Fundamental Data Section
                print(f"{'╟' + '─' * 78 + '╢'}")
                print(f"║{' Fundamental Data ':^78}║")
                print(f"{'╟' + '─' * 78 + '╢'}")
                
                fund_data = self.fundamental_dao.get_latest_fundamental_data(ticker_id)
                if fund_data:
                    print(f"║ P/E Ratio: {fund_data['pe_ratio'] or 'N/A':<20} "
                          f"Market Cap: ${fund_data['market_cap']:,.0f if fund_data['market_cap'] else 'N/A':<15}║")
                    print(f"║ Dividend Yield: {(fund_data['dividend_yield']*100 if fund_data['dividend_yield'] else 'N/A'):<16} "
                          f"EPS (TTM): ${fund_data['eps_ttm'] or 'N/A':<20}║")

                # News Sentiment Section
                print(f"{'╟' + '─' * 78 + '╢'}")
                print(f"║{' Recent News Sentiment ':^78}║")
                print(f"{'╟' + '─' * 78 + '╢'}")
                
                summary = self.sentiment_analyzer.get_sentiment_summary(ticker_id, symbol)
                if summary:
                    print(f"║ Overall: {summary['status']:<20} "
                          f"Score: {summary['average_sentiment']:.4f}{' ' * 35}║")
                    if summary['articles']:
                        latest = summary['articles'][0]
                        print(f"║ Latest: {latest['headline'][:65]:<65} ║")
                
                print(f"{'╚' + '═' * 78 + '╝'}")

        except Exception as e:
            print(f"Error displaying dashboard: {str(e)}")

    def analyze_bb(self, args):
        """Analyze Bollinger Bands for specified portfolio/ticker"""
        try:
            # Validate portfolio exists
            if not self.portfolio_dao.read_portfolio(args.portfolio_id):
                print(f"Error: Portfolio {args.portfolio_id} does not exist.")
                return

            # Get tickers to analyze
            if args.ticker_id:
                if not self.portfolio_dao.is_ticker_in_portfolio(args.portfolio_id, args.ticker_id):
                    print(f"Error: Ticker ID {args.ticker_id} not found in portfolio {args.portfolio_id}")
                    return
                tickers = [args.ticker_id]
            else:
                tickers = self.portfolio_dao.get_tickers_in_portfolio(args.portfolio_id)

            # Analyze each ticker
            for ticker_id in tickers:
                symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
                print(f"\nBollinger Bands Analysis for {symbol} (ID: {ticker_id}):")
                print("-" * 50)
                
                self.bollinger.generate_interpretation(symbol)

        except Exception as e:
            print(f"Error analyzing Bollinger Bands: {str(e)}")

def main():
    load_dotenv()
    portfolio_tool = PortfolioCLI(os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME'))
    
    parser = argparse.ArgumentParser(description='Portfolio Management CLI')
    subparsers = parser.add_subparsers(dest='command')

    create_parser = subparsers.add_parser('create-portfolio', help='Create a new portfolio')
    create_parser.add_argument('name', help='Name of the new portfolio')
    create_parser.add_argument('description', help='Description of the new portfolio')

    add_parser = subparsers.add_parser('add-tickers', help='Add tickers to a portfolio')
    add_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    add_parser.add_argument('ticker_ids', nargs='+', type=int, help='Ticker IDs to add')

    remove_parser = subparsers.add_parser('remove-tickers', help='Remove tickers from a portfolio')
    remove_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    remove_parser.add_argument('ticker_ids', nargs='+', type=int, help='Ticker IDs to remove')

    log_parser = subparsers.add_parser('log-transaction', help='Log a transaction for a portfolio')
    log_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    log_parser.add_argument('transaction_type', choices=['buy', 'sell', 'dividend'], help='Transaction type')
    log_parser.add_argument('transaction_date', help='Transaction date (YYYY-MM-DD)')
    log_parser.add_argument('ticker_ids', nargs='+', type=int, help='Ticker IDs for the transaction')
    log_parser.add_argument('--shares', type=int, help='Number of shares (for buy/sell transactions)')
    log_parser.add_argument('--price', type=float, help='Price per share (for buy/sell transactions)')
    log_parser.add_argument('--amount', type=float, help='Amount (for dividend transactions)')

    view_parser = subparsers.add_parser('view-transactions', help='View transaction history for a portfolio')
    view_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    view_parser.add_argument('--security_id', type=int, help='Security ID (optional)')

    view_portfolio_parser = subparsers.add_parser('view-portfolio', help='View details of a portfolio')
    view_portfolio_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')

    # Add technical analysis parsers
    rsi_parser = subparsers.add_parser('analyze-rsi', help='Analyze RSI for portfolio/ticker')
    rsi_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    rsi_parser.add_argument('--ticker_id', type=int, help='Ticker ID (optional)')

    ma_parser = subparsers.add_parser('analyze-ma', help='Analyze Moving Averages for portfolio/ticker')
    ma_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    ma_parser.add_argument('--ticker_id', type=int, help='Ticker ID (optional)')
    ma_parser.add_argument('--period', type=int, help='MA period (optional, default: 20)')

    bb_parser = subparsers.add_parser('analyze-bb', help='Analyze Bollinger Bands for portfolio/ticker')
    bb_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    bb_parser.add_argument('--ticker_id', type=int, help='Ticker ID (optional)')

    # Add fundamental data parser
    fundamental_parser = subparsers.add_parser('view-fundamentals', help='View fundamental data for portfolio/ticker')
    fundamental_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    fundamental_parser.add_argument('--ticker_id', type=int, help='Ticker ID (optional)')

    # Add news sentiment parser
    sentiment_parser = subparsers.add_parser('analyze-news', help='Analyze news sentiment for portfolio/ticker')
    sentiment_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')
    sentiment_parser.add_argument('--ticker_id', type=int, help='Ticker ID (optional)')
    sentiment_parser.add_argument('--update', action='store_true', help='Fetch and analyze latest news before showing results')

    # Add dashboard parser
    dashboard_parser = subparsers.add_parser('dashboard', help='Display portfolio dashboard')
    dashboard_parser.add_argument('portfolio_id', type=int, help='Portfolio ID')

    args = parser.parse_args()

    if args.command == 'dashboard':
        portfolio_tool.display_dashboard(args)
    elif args.command == 'create-portfolio':
        portfolio_tool.create_portfolio(args)
    elif args.command == 'add-tickers':
        portfolio_tool.add_tickers(args)
    elif args.command == 'remove-tickers':
        portfolio_tool.remove_tickers(args)
    elif args.command == 'log-transaction':
        portfolio_tool.log_transaction(args)
    elif args.command == 'view-transactions':
        portfolio_tool.view_transactions(args)
    elif args.command == 'view-portfolio':
        portfolio_tool.view_portfolio(args)
    elif args.command == 'analyze-rsi':
        portfolio_tool.analyze_rsi(args)
    elif args.command == 'analyze-ma':
        portfolio_tool.analyze_ma(args)
    elif args.command == 'analyze-bb':
        portfolio_tool.analyze_bb(args)
    elif args.command == 'view-fundamentals':
        portfolio_tool.view_fundamentals(args)
    elif args.command == 'analyze-news':
        portfolio_tool.analyze_news_sentiment(args)
    else:
        parser.print_help()
        
    portfolio_tool.close_connection()

if __name__ == '__main__':
    main()
