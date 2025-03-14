import os
import time
from datetime import datetime, timedelta

from data import rsi_calculations as rsi_calc
from data import ticker_dao
from data import utility
import yfinance as yf
from dotenv import load_dotenv

from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.fundamental_data_dao import FundamentalDataDAO
from data.news_sentiment_analyzer import NewsSentimentAnalyzer

class DataRetrieval:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.dao = ticker_dao.TickerDao(db_user, db_password, db_host, db_name)
        self.utility = utility.utility()
        self.dao.open_connection()
        self.rsi = rsi_calc.rsi_calculations(db_user, db_password, db_host, db_name)
        self.rsi.open_connection()
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.portfolio_dao.open_connection()
        self.portfolio_transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        self.portfolio_transactions_dao.open_connection()
        self.fundamental_dao = FundamentalDataDAO(db_user, db_password, db_host, db_name)
        self.fundamental_dao.open_connection()
        self.sentiment_analyzer = NewsSentimentAnalyzer(db_user, db_password, db_host, db_name)

    def update_ticker_data(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info if hasattr(ticker, 'info') else {}
            
            if not info:
                print(f"Warning: No info available for {symbol}")
                info = {}
            
            # Update basic ticker info with safe defaults for None values
            try:
                name = info.get("shortName") or info.get("longName") or symbol
                industry = info.get("industry") or "Unknown"
                sector = info.get("sector") or "Unknown"
                self.dao.update_stock(symbol, name, industry, sector)
                print(f"Updated basic info for {symbol}")
            except Exception as e:
                print(f"Error updating basic info for {symbol}: {str(e)}")
            
            # Update fundamental data
            try:
                self.update_fundamental_data(ticker, symbol)
                print(f"Updated fundamental data for {symbol}")
            except Exception as e:
                print(f"Error updating fundamental data for {symbol}: {str(e)}")
            
            # Update news sentiment
            try:
                ticker_id = self.dao.get_ticker_id(symbol)
                if ticker_id:
                    self.sentiment_analyzer.fetch_and_analyze_news(ticker_id, symbol)
                    print(f"Updated news sentiment for {symbol}")
            except Exception as e:
                print(f"Error updating news sentiment for {symbol}: {str(e)}")
                
        except Exception as e:
            print(f"Error in update_ticker_data for {symbol}: {str(e)}")

    def update_fundamental_data(self, ticker, symbol):
        """Updates fundamental data for a given ticker"""
        try:
            info = ticker.info if hasattr(ticker, 'info') else {}
            
            if not info:
                print(f"Warning: No fundamental data available for {symbol}")
                return
            
            ticker_id = self.dao.get_ticker_id(symbol)
            if not ticker_id:
                print(f"Error: Could not find ticker ID for {symbol}")
                return
            
            # Convert None values to appropriate defaults
            try:
                # Extract fundamental data with safe type conversion
                self.fundamental_dao.save_fundamental_data(
                    ticker_id=ticker_id,
                    pe_ratio=float(info.get('trailingPE')) if info.get('trailingPE') is not None else None,
                    forward_pe=float(info.get('forwardPE')) if info.get('forwardPE') is not None else None,
                    peg_ratio=float(info.get('pegRatio')) if info.get('pegRatio') is not None else None,
                    price_to_book=float(info.get('priceToBook')) if info.get('priceToBook') is not None else None,
                    dividend_yield=float(info.get('dividendYield')) if info.get('dividendYield') is not None else None,
                    dividend_rate=float(info.get('dividendRate')) if info.get('dividendRate') is not None else None,
                    eps_ttm=float(info.get('trailingEps')) if info.get('trailingEps') is not None else None,
                    eps_growth=float(info.get('earningsGrowth')) if info.get('earningsGrowth') is not None else None,
                    revenue_growth=float(info.get('revenueGrowth')) if info.get('revenueGrowth') is not None else None,
                    profit_margin=float(info.get('profitMargins')) if info.get('profitMargins') is not None else None,
                    debt_to_equity=float(info.get('debtToEquity')) if info.get('debtToEquity') is not None else None,
                    market_cap=float(info.get('marketCap')) if info.get('marketCap') is not None else None
                )
            except (ValueError, TypeError) as e:
                print(f"Error converting fundamental data for {symbol}: {str(e)}")
            
        except Exception as e:
            print(f"Error updating fundamental data for {symbol}: {str(e)}")

    def update_ticker_history(self, symbol, ticker_id):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info if hasattr(ticker, 'info') else {}
            
            if not info:
                print(f"Warning: No info available for {symbol}")
                info = {}

            # Check if ticker is delisted or unavailable
            if not info.get('regularMarketPrice') and not info.get('financialCurrency'):
                print(f"{symbol} might be delisted or not available.")
                try:
                    self.dao.ticker_delisted(symbol)
                    portfolio_ids = self.portfolio_dao.get_portfolios_with_ticker(ticker_id)
                    for portfolio_id in portfolio_ids:
                        self.portfolio_dao.remove_tickers_from_portfolio(portfolio_id, [ticker_id])
                        self.portfolio_transactions_dao.insert_transaction(portfolio_id, None, 'sell', datetime.today().date())
                    return
                except Exception as e:
                    print(f"Error handling delisted ticker {symbol}: {str(e)}")
                    return

            try:
                df_last_date = self.dao.retrieve_last_activity_date(ticker_id)
                start = datetime.today() - timedelta(weeks=520)  # create window with enough room for 50 day moving average

                if df_last_date is not None and not df_last_date.empty and df_last_date.iloc[0, 0] is not None:
                    start = df_last_date.iloc[0, 0] + timedelta(days=1)

                end = datetime.today() + timedelta(days=1)
                hist = ticker.history(interval="1d", start=start, end=end)

                if hist.empty:
                    print(f"No historical data available for {symbol}")
                    return

                for i in range(len(hist)):
                    try:
                        idx = hist.index[i]
                        self.dao.update_activity(
                            ticker_id, 
                            idx,
                            float(hist.loc[idx, 'Open']),
                            float(hist.loc[idx, 'Close']),
                            float(hist.loc[idx, 'Volume']),
                            float(hist.loc[idx, 'High']),
                            float(hist.loc[idx, 'Low'])
                        )

                        # Check if the stock paid dividends on this date
                        if hist.loc[idx, 'Dividends'] > 0:
                            self.log_dividend_transactions(ticker_id, idx, float(hist.loc[idx, 'Dividends']))
                    except Exception as e:
                        print(f"Error updating activity for {symbol} on {idx}: {str(e)}")
                        continue

            except Exception as e:
                print(f"Error retrieving history for {symbol}: {str(e)}")

        except Exception as e:
            print(f"Error in update_ticker_history for {symbol}: {str(e)}")
            time.sleep(120)  # Sleep on failure to respect rate limits
            print('Sleeping from failure')

    def log_dividend_transactions(self, ticker_id, activity_date, amount):
        portfolio_ids = self.portfolio_dao.get_portfolios_with_ticker(ticker_id)
        for portfolio_id in portfolio_ids:
            security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
            self.portfolio_transactions_dao.insert_transaction(portfolio_id, security_id, 'dividend', activity_date, amount=amount)

    def retrieve_ticker_history(self, ticker_id):
        return self.dao.retrieve_ticker_activity(ticker_id=ticker_id)

    def update_stock_activity(self):
        try:
            portfolio_tickers = self.portfolio_dao.get_all_tickers_in_portfolios()
            if not portfolio_tickers:
                print("No tickers found in portfolios")
                return
            
            print("Found tickers:", portfolio_tickers)
            count = 0

            for symbol in portfolio_tickers:
                try:
                    ticker_id = self.dao.get_ticker_id(symbol)
                    if not ticker_id:
                        print(f"Error: Could not get ticker_id for symbol {symbol}")
                        continue

                    print(f"\nProcessing {symbol} (ID: {ticker_id})")
                    
                    try:
                        self.update_ticker_data(symbol)
                        print(f"Updated ticker data for {symbol}")
                    except Exception as e:
                        print(f"Error updating ticker data for {symbol}: {str(e)}")
                    
                    try:
                        self.update_ticker_history(symbol, ticker_id)
                        print(f"Updated ticker history for {symbol}")
                    except Exception as e:
                        print(f"Error updating ticker history for {symbol}: {str(e)}")
                    
                    try:
                        self.rsi.calculateRSI(ticker_id)
                        print(f"Updated RSI for {symbol}")
                    except Exception as e:
                        print(f"Error calculating RSI for {symbol}: {str(e)}")

                    count += 1
                    if count == 3:
                        print("Pausing for rate limit...")
                        time.sleep(120)
                        count = 0
                        print("Resuming updates")

                except Exception as e:
                    print(f"Error processing ticker_id {ticker_id}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error in update_stock_activity: {str(e)}")
            raise

def main():
    load_dotenv()

    stock_activity = DataRetrieval(os.getenv('DB_USER'), os.getenv('DB_PASSWORD'), os.getenv('DB_HOST'), os.getenv('DB_NAME'))
    stock_activity.update_stock_activity()

if __name__ == "__main__":
    main()
