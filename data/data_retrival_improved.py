Marketimport os
import time
import random
from datetime import datetime, timedelta, date

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
        
        # Enhanced configurations for rate limiting - much stricter than before
        self.requests_per_batch = 1  # Process only one ticker at a time
        self.batch_pause_time = 300  # 5-minute pause between tickers
        self.error_pause_time = 600  # 10-minute pause after errors
        self.max_retries = 3  # Number of times to retry a failed request
        self.jitter_max = 60  # Larger random jitter to avoid pattern detection
        
        # Add an initial random delay before the first request
        initial_delay = random.randint(5, 30)
        print(f"Adding initial delay of {initial_delay} seconds...")
        time.sleep(initial_delay)

    def _ensure_datetime(self, input_date):
        """
        Convert input to datetime, handling various input types
        """
        if isinstance(input_date, datetime):
            return input_date
        elif isinstance(input_date, date):
            return datetime.combine(input_date, datetime.min.time())
        else:
            try:
                # Try parsing string or other convertible types
                return datetime.fromisoformat(str(input_date))
            except Exception as e:
                print(f"Could not convert {input_date} to datetime: {e}")
                return datetime.now()  # Fallback to current datetime

    def update_ticker_history(self, symbol, ticker_id):
        """Updates ticker history with retry mechanism for rate limiting"""
        # Import pandas for concat operations
        import pandas as pd
        
        for attempt in range(self.max_retries):
            try:
                # Different delay strategy for retries
                if attempt > 0:
                    retry_delay = (attempt * 2 * 60) + random.randint(10, 30)  # Progressive backoff
                    print(f"Retry attempt {attempt+1}/{self.max_retries} for {symbol} after {retry_delay} seconds...")
                    time.sleep(retry_delay)
                
                ticker = yf.Ticker(symbol)
                
                # Try to use fast_info first to check if the ticker is valid
                is_delisted = False
                try:
                    # Add small delay before accessing fast_info
                    time.sleep(random.randint(1, 3))
                    
                    fast_info = ticker.fast_info
                    # If we can get the last price, the stock is likely active
                    last_price = getattr(fast_info, 'last_price', None)
                    if last_price is None or last_price == 0:
                        print(f"{symbol} might be delisted or not available (fast_info check).")
                        is_delisted = True
                except Exception as e:
                    if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                        print(f"Rate limit hit when checking fast_info. Will retry.")
                        continue
                        
                    print(f"Error accessing fast_info for {symbol} history check: {str(e)}")
                    # Fall back to traditional method
                    try:
                        # Add small delay before accessing info
                        time.sleep(random.randint(1, 3))
                        
                        info = ticker.info if hasattr(ticker, 'info') else {}
                        
                        if not info:
                            print(f"Warning: No info available for {symbol}")
                            info = {}
    
                        # Check if ticker is delisted or unavailable
                        if not info.get('regularMarketPrice') and not info.get('financialCurrency'):
                            print(f"{symbol} might be delisted or not available.")
                            is_delisted = True
                    except Exception as info_e:
                        if "Too Many Requests" in str(info_e) and attempt < self.max_retries - 1:
                            print(f"Rate limit hit when checking info. Will retry.")
                            continue
                        print(f"Error accessing info for {symbol}: {str(info_e)}")
                
                # Handle delisted ticker
                if is_delisted:
                    try:
                        self.dao.ticker_delisted(symbol)
                    except Exception as e:
                        print(f"Error handling delisted ticker {symbol}: {str(e)}")
                    return True  # Return true because we handled this case appropriately
                
                # Get the historical data
                df_last_date = self.dao.retrieve_last_activity_date(ticker_id)
                hist = None
                
                try:
                    # Add small delay before getting history
                    time.sleep(random.randint(1, 3))
                    
                    if df_last_date is not None and not df_last_date.empty and df_last_date.iloc[0, 0] is not None:
                        # If we have previous data, just get data since last update
                        # Add buffer days to avoid hitting exact boundaries which might cause rate limiting
                        last_date = df_last_date.iloc[0, 0]
                        
                        # Robust datetime conversion
                        last_date = self._ensure_datetime(last_date)
                        
                        start = last_date + timedelta(days=1)
                        end = datetime.today() + timedelta(days=1)
                        
                        # Debug logging
                        print(f"Last date type: {type(last_date)}")
                        print(f"Start date type: {type(start)}")
                        print(f"End date type: {type(end)}")
                        
                        print(f"Getting history for {symbol} from {start} to {end}")
                        
                        # For incremental updates, use a smaller chunk size
                        days_difference = (end - start).days
                        if days_difference > 30:
                            # If getting more than a month of data, split into multiple requests
                            print(f"Getting history in chunks (incremental update for {days_difference} days)")
                            hist_parts = []
                            current_start = start
                            while current_start < end:
                                current_end = min(current_start + timedelta(days=30), end)
                                print(f"Getting chunk from {current_start} to {current_end}")
                                try:
                                    chunk = ticker.history(interval="1d", start=current_start, end=current_end)
                                    if not chunk.empty:
                                        hist_parts.append(chunk)
                                except Exception as inner_e:
                                    if "Too Many Requests" in str(inner_e) and attempt < self.max_retries - 1:
                                        print("Rate limit hit during chunked history request. Will restart with a new retry.")
                                        raise inner_e  # This will be caught by the outer try/except
                                    else:
                                        print(f"Error during chunk request: {str(inner_e)}")
                                
                                time.sleep(random.randint(5, 10))  # Wait between chunk requests
                                current_start = current_end
                            
                            if hist_parts:
                                hist = pd.concat(hist_parts)
                            else:
                                hist = pd.DataFrame()
                        else:
                            # Use longer interval to reduce number of data points requested
                            hist = ticker.history(interval="1d", start=start, end=end)
                    else:
                        # Instead of 1 year of history, use 6 months to reduce initial data load
                        period = '6mo'
                        print(f"No previous data for {symbol}. Getting {period} of history.")
                        hist = ticker.history(period=period)
                
                except Exception as hist_e:
                    if "Too Many Requests" in str(hist_e) and attempt < self.max_retries - 1:
                        print(f"Rate limit hit when retrieving history. Will retry.")
                        continue
                    else:
                        print(f"Error retrieving history data: {str(hist_e)}")
                        return False

                if hist is None or hist.empty:
                    print(f"No historical data available for {symbol}")
                    return True  # Return true as this is not a failure condition
                
                # Process the historical data
                try:
                    # Break up large data processing into smaller chunks
                    chunk_size = 50  # Process 50 days at a time
                    for i in range(0, len(hist), chunk_size):
                        chunk = hist.iloc[i:i+chunk_size]
                        for j in range(len(chunk)):
                            try:
                                idx = chunk.index[j]
                                self.dao.update_activity(
                                    ticker_id, 
                                    idx,
                                    float(chunk.loc[idx, 'Open']),
                                    float(chunk.loc[idx, 'Close']),
                                    float(chunk.loc[idx, 'Volume']),
                                    float(chunk.loc[idx, 'High']),
                                    float(chunk.loc[idx, 'Low'])
                                )

                                # Check if the stock paid dividends on this date
                                if chunk.loc[idx, 'Dividends'] > 0:
                                    self.log_dividend_transactions(ticker_id, idx, float(chunk.loc[idx, 'Dividends']))
                            except Exception as e:
                                print(f"Error updating activity for {symbol} on {idx}: {str(e)}")
                                continue
                        
                        # Add a small pause between chunks to avoid overwhelming the database
                        if i + chunk_size < len(hist):
                            time.sleep(1)
                            
                    # Successfully processed all data
                    return True
                    
                except Exception as processing_e:
                    print(f"Error processing historical data: {str(processing_e)}")
                    return False
                
            except Exception as e:
                print(f"Error in update_ticker_history attempt {attempt+1} for {symbol}: {str(e)}")
                if attempt == self.max_retries - 1:
                    # This was the last retry attempt
                    return False
        
                        
                        info = ticker.info if hasattr(ticker, 'info') else {}
                        
                        if not info:
                            print(f"Warning: No info available for {symbol}")
                            info = {}
    
                        # Check if ticker is delisted or unavailable
                        if not info.get('regularMarketPrice') and not info.get('financialCurrency'):
                            print(f"{symbol} might be delisted or not available.")
                            is_delisted = True
                    except Exception as info_e:
                        if "Too Many Requests" in str(info_e) and attempt < self.max_retries - 1:
                            print(f"Rate limit hit when checking info. Will retry.")
                            continue
                        print(f"Error accessing info for {symbol}: {str(info_e)}")
                
                # Handle delisted ticker
                if is_delisted:
                    try:
                        self.dao.ticker_delisted(symbol)
                    except Exception as e:
                        print(f"Error handling delisted ticker {symbol}: {str(e)}")
                    return True  # Return true because we handled this case appropriately
                
                # Get the historical data
                df_last_date = self.dao.retrieve_last_activity_date(ticker_id)
                hist = None
                
                try:
                    # Add small delay before getting history
                    time.sleep(random.randint(1, 3))
                    
                    if df_last_date is not None and not df_last_date.empty and df_last_date.iloc[0, 0] is not None:
                        # If we have previous data, just get data since last update
                        # Add buffer days to avoid hitting exact boundaries which might cause rate limiting
                        last_date = df_last_date.iloc[0, 0]
                        # Explicitly convert to datetime if it's a date
                        if hasattr(last_date, 'date'):
                            last_date = datetime.combine(last_date, datetime.min.time())
                        start = last_date + timedelta(days=1)
                        end = datetime.today() + timedelta(days=1)
                        print(f"Getting history for {symbol} from {start} to {end}")
                        
                        # For incremental updates, use a smaller chunk size
                        days_difference = (end - start).days
                        if days_difference > 30:
                            # If getting more than a month of data, split into multiple requests
                            print(f"Getting history in chunks (incremental update for {days_difference} days)")
                            hist_parts = []
                            current_start = start
                            while current_start < end:
                                current_end = min(current_start + timedelta(days=30), end)
                                print(f"Getting chunk from {current_start} to {current_end}")
                                try:
                                    chunk = ticker.history(interval="1d", start=current_start, end=current_end)
                                    if not chunk.empty:
                                        hist_parts.append(chunk)
                                except Exception as inner_e:
                                    if "Too Many Requests" in str(inner_e) and attempt < self.max_retries - 1:
                                        print("Rate limit hit during chunked history request. Will restart with a new retry.")
                                        raise inner_e  # This will be caught by the outer try/except
                                    else:
                                        print(f"Error during chunk request: {str(inner_e)}")
                                
                                time.sleep(random.randint(5, 10))  # Wait between chunk requests
                                current_start = current_end
                            
                            if hist_parts:
                                hist = pd.concat(hist_parts)
                            else:
                                hist = pd.DataFrame()
                        else:
                            # Use longer interval to reduce number of data points requested
                            hist = ticker.history(interval="1d", start=start, end=end)
                    else:
                        # Instead of 1 year of history, use 6 months to reduce initial data load
                        period = '6mo'
                        print(f"No previous data for {symbol}. Getting {period} of history.")
                        hist = ticker.history(period=period)
                
                except Exception as hist_e:
                    if "Too Many Requests" in str(hist_e) and attempt < self.max_retries - 1:
                        print(f"Rate limit hit when retrieving history. Will retry.")
                        continue
                    else:
                        print(f"Error retrieving history data: {str(hist_e)}")
                        return False

                if hist is None or hist.empty:
                    print(f"No historical data available for {symbol}")
                    return True  # Return true as this is not a failure condition
                
                # Process the historical data
                try:
                    # Break up large data processing into smaller chunks
                    chunk_size = 50  # Process 50 days at a time
                    for i in range(0, len(hist), chunk_size):
                        chunk = hist.iloc[i:i+chunk_size]
                        for j in range(len(chunk)):
                            try:
                                idx = chunk.index[j]
                                self.dao.update_activity(
                                    ticker_id, 
                                    idx,
                                    float(chunk.loc[idx, 'Open']),
                                    float(chunk.loc[idx, 'Close']),
                                    float(chunk.loc[idx, 'Volume']),
                                    float(chunk.loc[idx, 'High']),
                                    float(chunk.loc[idx, 'Low'])
                                )

                                # Check if the stock paid dividends on this date
                                if chunk.loc[idx, 'Dividends'] > 0:
                                    self.log_dividend_transactions(ticker_id, idx, float(chunk.loc[idx, 'Dividends']))
                            except Exception as e:
                                print(f"Error updating activity for {symbol} on {idx}: {str(e)}")
                                continue
                        
                        # Add a small pause between chunks to avoid overwhelming the database
                        if i + chunk_size < len(hist):
                            time.sleep(1)
                            
                    # Successfully processed all data
                    return True
                    
                except Exception as processing_e:
                    print(f"Error processing historical data: {str(processing_e)}")
                    return False
                
            except Exception as e:
                print(f"Error in update_ticker_history attempt {attempt+1} for {symbol}: {str(e)}")
                if attempt == self.max_retries - 1:
                    # This was the last retry attempt
                    return False
        
        # Should never reach here, but just in case
        return False

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
            error_count = 0
            max_consecutive_errors = 3
            
            # Add some randomization to the ticker order
            random.shuffle(portfolio_tickers)

            for symbol in portfolio_tickers:
                try:
                    ticker_id = self.dao.get_ticker_id(symbol)
                    if not ticker_id:
                        print(f"Error: Could not get ticker_id for symbol {symbol}")
                        continue

                    print(f"\nProcessing {symbol} (ID: {ticker_id})")
                    
                    # Add a small random delay between requests to avoid pattern detection
                    if count > 0:
                        jitter = random.randint(1, 5)
                        time.sleep(jitter)
                    
                    success = True
                    
                    try:
                        if not self.update_symbol_data(symbol):
                            success = False
                        else:
                            print(f"Updated ticker data for {symbol}")
                    except Exception as e:
                        print(f"Error updating ticker data for {symbol}: {str(e)}")
                        success = False
                    
                    try:
                        if not self.update_ticker_history(symbol, ticker_id):
                            success = False
                        else:
                            print(f"Updated ticker history for {symbol}")
                    except Exception as e:
                        print(f"Error updating ticker history for {symbol}: {str(e)}")
                        success = False
                    
                    try:
                        self.rsi.calculateRSI(ticker_id)
                        print(f"Updated RSI for {symbol}")
                    except Exception as e:
                        print(f"Error calculating RSI for {symbol}: {str(e)}")
                        success = False

                    # Handle success or error cases
                    if success:
                        # If successful, increment counter and reset error count
                        count += 1
                        error_count = 0
                        # Apply standard rate limiting
                        count = self._apply_rate_limiting(count)
                    else:
                        # If failed, increment error count
                        error_count += 1
                        # Take extended break if too many consecutive errors
                        if error_count >= max_consecutive_errors:
                            print(f"Too many consecutive errors ({error_count}). Taking a longer break...")
                            time.sleep(self.error_pause_time * 2)
                            error_count = 0
                        # Apply error-based rate limiting
                        count = self._apply_rate_limiting(count, is_error=True)

                except Exception as e:
                    print(f"Error processing ticker_id {ticker_id}: {str(e)}")
                    error_count += 1
                    count = self._apply_rate_limiting(count, is_error=True)
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
