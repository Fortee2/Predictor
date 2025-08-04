import os
import time
import random
import pandas as pd
from datetime import datetime, timedelta, date

from data import rsi_calculations as rsi_calc
from data import ticker_dao
from data import utility
import yfinance as yf
from dotenv import load_dotenv

from data.portfolio_dao import PortfolioDAO
from data.watch_list_dao import WatchListDAO
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
        self.watch_list_dao = WatchListDAO(db_user, db_password, db_host, db_name)
        self.watch_list_dao.open_connection()
        self.fundamental_dao = FundamentalDataDAO(db_user, db_password, db_host, db_name)
        self.fundamental_dao.open_connection()
        self.sentiment_analyzer = NewsSentimentAnalyzer(db_user, db_password, db_host, db_name)
        
        # Enhanced configurations for rate limiting
        self.requests_per_batch = 1  # Process only one ticker at a time
        self.batch_pause_time = 300  # 5-minute pause between tickers
        self.error_pause_time = 600  # 10-minute pause after errors
        self.max_retries = 3  # Number of times to retry a failed request
        self.jitter_max = 60  # Larger random jitter to avoid pattern detection
        
        # Add an initial random delay before the first request
        initial_delay = random.randint(5, 30)
        print(f"Adding initial delay of {initial_delay} seconds...")
        time.sleep(initial_delay)

    def _apply_rate_limiting(self, count, is_error=False):
        """Apply rate limiting based on count and error status"""
        if is_error:
            # On error, take a longer pause
            pause_time = self.error_pause_time + random.randint(1, self.jitter_max)
            print(f"Taking error pause for {pause_time} seconds...")
            time.sleep(pause_time)
            return 0
        elif count >= self.requests_per_batch:
            # After processing a batch, take a standard pause
            pause_time = self.batch_pause_time + random.randint(1, self.jitter_max)
            print(f"Taking batch pause for {pause_time} seconds...")
            time.sleep(pause_time)
            return 0
        else:
            return count

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

    def update_symbol_data(self, symbol):
        """Updates symbol data with retry mechanism for rate limiting"""
        for attempt in range(self.max_retries):
            try:
                # Different delay strategy for retries
                if attempt > 0:
                    retry_delay = (attempt * 2 * 60) + random.randint(10, 30)  # Progressive backoff
                    print(f"Retry attempt {attempt+1}/{self.max_retries} for {symbol} after {retry_delay} seconds...")
                    time.sleep(retry_delay)
                
                # First check if industry or sector are missing
                ticker_id = self.dao.get_ticker_id(symbol)
                if ticker_id:
                    ticker_data = self.dao.get_ticker_data(ticker_id)
                    
                    # Only proceed with update if industry or sector are missing/unknown
                    should_update = (not ticker_data or 
                                   ticker_data['industry'] is None or 
                                   ticker_data['industry'] == "Unknown" or
                                   ticker_data['sector'] is None or 
                                   ticker_data['sector'] == "Unknown")
                    if should_update:
                        time.sleep(random.randint(1, 3))  # Small delay before API call
                        ticker = yf.Ticker(symbol)
                        
                        # Try to use fast_info first for better performance
                        try:
                            # We still need to get industry and sector from regular info
                            # as they're not available in fast_info
                            time.sleep(random.randint(1, 3))  # Small delay before API call
                            info = ticker.info if hasattr(ticker, 'info') else {}
                            
                            if not info:
                                print(f"Warning: No info available for {symbol}")
                                info = {}
                            
                            # Update basic ticker info with safe defaults for None values
                            name = info.get("shortName") or info.get("longName") or symbol
                            industry = info.get("industry") or "Unknown"
                            sector = info.get("sector") or "Unknown"
                            
                            # Update the database
                            self.dao.update_stock(symbol, name, industry, sector)
                            print(f"Updated basic info for {symbol}")
                        except Exception as e:
                            if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                                print(f"Rate limit hit when accessing fast_info. Will retry.")
                                continue
                            
                            print(f"Error accessing fast_info for {symbol}: {str(e)}")
                            # Fallback to traditional method
                            try:
                                time.sleep(random.randint(1, 3))  # Small delay before API call
                                info = ticker.info if hasattr(ticker, 'info') else {}
                                if not info:
                                    print(f"Warning: No info available for {symbol}")
                                    info = {}
                                name = info.get("shortName") or info.get("longName") or symbol
                                industry = info.get("industry") or "Unknown"
                                sector = info.get("sector") or "Unknown"
                                
                                # Update the database
                                self.dao.update_stock(symbol, name, industry, sector)
                                print(f"Updated basic info for {symbol}")
                            except Exception as e:
                                if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                                    print(f"Rate limit hit when accessing info. Will retry.")
                                    continue
                                print(f"Error updating basic info for {symbol}: {str(e)}")
                                return False
                    else:
                        print(f"Skipping basic info update for {symbol} - industry and sector already present")
                
                # Always retrieve ticker for other operations, if not already done above
                if 'ticker' not in locals():
                    time.sleep(random.randint(1, 3))  # Small delay before API call
                    ticker = yf.Ticker(symbol)
                    info = ticker.info if hasattr(ticker, 'info') else {}
                    
                    if not info:
                        print(f"Warning: No info available for {symbol}")
                        info = {}
                
                # Update fundamental data
                try:
                    if self.update_fundamental_data(ticker, symbol):
                        print(f"Updated fundamental data for {symbol}")
                    else:
                        print(f"Failed to update fundamental data for {symbol}")
                except Exception as e:
                    print(f"Error updating fundamental data for {symbol}: {str(e)}")
                    if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                        continue
                
                # Update news sentiment
                try:
                    ticker_id = self.dao.get_ticker_id(symbol)
                    if ticker_id:
                        self.sentiment_analyzer.fetch_and_analyze_news(ticker_id, symbol)
                        print(f"Updated news sentiment for {symbol}")
                except Exception as e:
                    print(f"Error updating news sentiment for {symbol}: {str(e)}")
                    if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                        continue
                
                return True
                    
            except Exception as e:
                print(f"Error in update_symbol_data attempt {attempt+1} for {symbol}: {str(e)}")
                if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                    continue
                if attempt == self.max_retries - 1:
                    # This was the last retry attempt
                    return False
        
        # Should never reach here, but just in case
        return False

    def update_fundamental_data(self, ticker, symbol):
        """Updates fundamental data for a given ticker with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                # Different delay strategy for retries
                if attempt > 0:
                    retry_delay = (attempt * 30) + random.randint(5, 15)  # Shorter backoff for fundamental data
                    print(f"Retry attempt {attempt+1}/{self.max_retries} for {symbol} fundamentals after {retry_delay} seconds...")
                    time.sleep(retry_delay)
                
                # Try using fast_info where available
                fast_info = None
                info = {}
                market_cap = None
                
                try:
                    time.sleep(random.randint(1, 3))  # Small delay before API call
                    fast_info = ticker.fast_info
                    # Market cap is available in fast_info
                    market_cap = getattr(fast_info, 'market_cap', None)
                    print(f"Using fast_info for {symbol} market cap: {market_cap}")
                except Exception as e:
                    if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                        print("Rate limit hit when accessing fast_info for fundamentals. Will retry.")
                        continue
                    print(f"Error accessing fast_info for {symbol} fundamentals: {str(e)}")
                
                # Get regular info for other metrics not in fast_info
                try:
                    time.sleep(random.randint(1, 3))  # Small delay before API call
                    info = ticker.info if hasattr(ticker, 'info') else {}
                    if not info and not fast_info:
                        print(f"Warning: No fundamental data available for {symbol}")
                        return False
                except Exception as e:
                    if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                        print(f"Rate limit hit when accessing info for fundamentals. Will retry.")
                        continue
                    print(f"Error accessing info for {symbol}: {str(e)}")
                    if not fast_info:
                        return False
                
                ticker_id = self.dao.get_ticker_id(symbol)
                if not ticker_id:
                    print(f"Error: Could not find ticker ID for {symbol}")
                    return False
                
                # Convert None values to appropriate defaults
                try:
                    # Extract fundamental data with safe type conversion
                    # Use market_cap from fast_info if available, otherwise from regular info
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
                        market_cap=market_cap if market_cap is not None else (float(info.get('marketCap')) if info.get('marketCap') is not None else None)
                    )
                    return True
                except (ValueError, TypeError) as e:
                    print(f"Error converting fundamental data for {symbol}: {str(e)}")
                    return False
                
            except Exception as e:
                print(f"Error in update_fundamental_data attempt {attempt+1} for {symbol}: {str(e)}")
                if attempt == self.max_retries - 1:
                    # This was the last retry attempt
                    return False
        
        # Should never reach here, but just in case
        return False

    def update_ticker_history(self, symbol, ticker_id):
        """Updates ticker history with retry mechanism for rate limiting"""
        for attempt in range(self.max_retries):
            try:
                # Different delay strategy for retries
                if attempt > 0:
                    retry_delay = (attempt * 2 * 60) + random.randint(10, 30)  # Progressive backoff
                    print(f"Retry attempt {attempt+1}/{self.max_retries} for {symbol} after {retry_delay} seconds...")
                    time.sleep(retry_delay)
                
                time.sleep(random.randint(1, 3))  # Small delay before API call
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
                        # For new tickers, use 6 months of history to reduce initial data load
                        period = 'max'
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
        """Log dividend transactions in the portfolio"""
        portfolio_ids = self.portfolio_dao.get_portfolios_with_ticker(ticker_id)
        for portfolio_id in portfolio_ids:
            security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
            self.portfolio_transactions_dao.insert_transaction(portfolio_id, security_id, 'dividend', activity_date, amount=amount)

    def retrieve_ticker_history(self, ticker_id):
        """Retrieve ticker history from the database"""
        return self.dao.retrieve_ticker_activity(ticker_id=ticker_id)

    def update_stock_activity(self):
        """Update stock activity for all tickers in portfolios with rate limiting"""
        try:
            portfolio_tickers = self.portfolio_dao.get_all_tickers_in_portfolios()
            watchlist_tickers = self.watch_list_dao.get_all_watchlist_tickers()

            portfolio_tickers.extend(watchlist_tickers)
            portfolio_tickers = list(set(portfolio_tickers))  # Remove duplicates
            
            if not portfolio_tickers:
                print("No tickers found in portfolios")
                return
            
            print("Found tickers:", portfolio_tickers)
            count = 0
            error_count = 0
            max_consecutive_errors = 3
            
            # Add some randomization to the ticker order
            random.shuffle(portfolio_tickers)

            for ticker_id, symbol in portfolio_tickers:
                try:
                   

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
