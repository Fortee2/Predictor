import concurrent.futures
import random
import time
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

from data import rsi_calculations as rsi_calc
from data import ticker_dao, utility

from .base_dao import BaseDAO
from .bollinger_bands import BollingerBandAnalyzer
from .fundamental_data_dao import FundamentalDataDAO
from .macd import MACD
from .moving_averages import moving_averages
from .news_sentiment_analyzer import NewsSentimentAnalyzer
from .portfolio_dao import PortfolioDAO
from .portfolio_transactions_dao import PortfolioTransactionsDAO
from .stochastic_oscillator import StochasticOscillator
from .utility import DatabaseConnectionPool
from .watch_list_dao import WatchListDAO


class DataRetrieval(BaseDAO):
    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__(pool)
        self.dao = ticker_dao.TickerDao(pool=self.pool)
        self.utility = utility.utility()
        self.rsi = rsi_calc.rsi_calculations(pool=self.pool)
        self.portfolio_dao = PortfolioDAO(pool=self.pool)
        self.portfolio_transactions_dao = PortfolioTransactionsDAO(pool=self.pool)
        self.watch_list_dao = WatchListDAO(pool=self.pool)
        self.fundamental_dao = FundamentalDataDAO(pool=self.pool)
        self.sentiment_analyzer = NewsSentimentAnalyzer(pool=self.pool)

        # Initialize technical indicator calculators
        self.macd_analyzer = MACD(pool=self.pool)
        self.moving_avg = moving_averages(pool=self.pool)
        self.bb_analyzer = BollingerBandAnalyzer(self.dao)
        self.stochastic_analyzer = StochasticOscillator(pool=self.pool)

        # Enhanced configurations for rate limiting
        self.requests_per_batch = 10  # Process multiple tickers in a batch
        self.batch_pause_time = 2  # Short pause between batches
        self.error_pause_time = 60  # 1-minute pause after errors
        self.max_retries = 3  # Number of times to retry a failed request
        self.jitter_max = 5  # Small random jitter

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
                    print(f"Retry attempt {attempt + 1}/{self.max_retries} for {symbol} after {retry_delay} seconds...")
                    time.sleep(retry_delay)

                # First check if industry or sector are missing
                ticker_id = self.dao.get_ticker_id(symbol)
                if ticker_id:
                    ticker_data = self.dao.get_ticker_data(ticker_id)

                    # Only proceed with update if industry or sector are missing/unknown
                    should_update = (
                        not ticker_data
                        or ticker_data["industry"] is None
                        or ticker_data["industry"] == "Unknown"
                        or ticker_data["sector"] is None
                        or ticker_data["sector"] == "Unknown"
                    )

                    if should_update:
                        time.sleep(random.randint(1, 3))  # Small delay before API call
                        ticker = yf.Ticker(symbol)

                        # Try to use fast_info first for better performance
                        try:
                            # We still need to get industry and sector from regular info
                            # as they're not available in fast_info
                            time.sleep(random.randint(1, 3))  # Small delay before API call
                            info = ticker.info if hasattr(ticker, "info") else {}

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
                                print("Rate limit hit when accessing fast_info. Will retry.")
                                continue

                            print(f"Error accessing fast_info for {symbol}: {str(e)}")
                            # Fallback to traditional method
                            try:
                                time.sleep(random.randint(1, 3))  # Small delay before API call
                                info = ticker.info if hasattr(ticker, "info") else {}
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
                                    print("Rate limit hit when accessing info. Will retry.")
                                    continue
                                print(f"Error updating basic info for {symbol}: {str(e)}")
                                return False
                    else:
                        print(f"Skipping basic info update for {symbol} - industry and sector already present")

                # Always retrieve ticker for other operations, if not already done above
                if "ticker" not in locals():
                    time.sleep(random.randint(1, 3))  # Small delay before API call
                    ticker = yf.Ticker(symbol)
                    info = ticker.info if hasattr(ticker, "info") else {}

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
                print(f"Error in update_symbol_data attempt {attempt + 1} for {symbol}: {str(e)}")
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
                    print(
                        f"Retry attempt {attempt + 1}/{self.max_retries} for {symbol} fundamentals after {retry_delay} seconds..."
                    )
                    time.sleep(retry_delay)

                # Try using fast_info where available
                fast_info = None
                info = {}
                market_cap = None

                try:
                    time.sleep(random.randint(1, 3))  # Small delay before API call
                    fast_info = ticker.fast_info
                    # Market cap is available in fast_info
                    market_cap = getattr(fast_info, "market_cap", None)
                    print(f"Using fast_info for {symbol} market cap: {market_cap}")
                except Exception as e:
                    if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                        print("Rate limit hit when accessing fast_info for fundamentals. Will retry.")
                        continue
                    print(f"Error accessing fast_info for {symbol} fundamentals: {str(e)}")

                # Get regular info for other metrics not in fast_info
                try:
                    time.sleep(random.randint(1, 3))  # Small delay before API call
                    info = ticker.info if hasattr(ticker, "info") else {}
                    if not info and not fast_info:
                        print(f"Warning: No fundamental data available for {symbol}")
                        return False
                except Exception as e:
                    if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                        print("Rate limit hit when accessing info for fundamentals. Will retry.")
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
                        pe_ratio=(float(info.get("trailingPE")) if info.get("trailingPE") is not None else None),
                        forward_pe=(float(info.get("forwardPE")) if info.get("forwardPE") is not None else None),
                        peg_ratio=(float(info.get("pegRatio")) if info.get("pegRatio") is not None else None),
                        price_to_book=(float(info.get("priceToBook")) if info.get("priceToBook") is not None else None),
                        dividend_yield=(
                            float(info.get("dividendYield")) if info.get("dividendYield") is not None else None
                        ),
                        dividend_rate=(
                            float(info.get("dividendRate")) if info.get("dividendRate") is not None else None
                        ),
                        eps_ttm=(float(info.get("trailingEps")) if info.get("trailingEps") is not None else None),
                        eps_growth=(
                            float(info.get("earningsGrowth")) if info.get("earningsGrowth") is not None else None
                        ),
                        revenue_growth=(
                            float(info.get("revenueGrowth")) if info.get("revenueGrowth") is not None else None
                        ),
                        profit_margin=(
                            float(info.get("profitMargins")) if info.get("profitMargins") is not None else None
                        ),
                        debt_to_equity=(
                            float(info.get("debtToEquity")) if info.get("debtToEquity") is not None else None
                        ),
                        market_cap=(
                            market_cap
                            if market_cap is not None
                            else (float(info.get("marketCap")) if info.get("marketCap") is not None else None)
                        ),
                    )
                    return True
                except (ValueError, TypeError) as e:
                    print(f"Error converting fundamental data for {symbol}: {str(e)}")
                    return False

            except Exception as e:
                print(f"Error in update_fundamental_data attempt {attempt + 1} for {symbol}: {str(e)}")
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
                    print(f"Retry attempt {attempt + 1}/{self.max_retries} for {symbol} after {retry_delay} seconds...")
                    time.sleep(retry_delay)

                ticker = yf.Ticker(symbol)

                # Try to use fast_info first to check if the ticker is valid
                is_delisted = False
                try:
                    fast_info = ticker.fast_info
                    # If we can get the last price, the stock is likely active
                    last_price = getattr(fast_info, "last_price", None)
                    if last_price is None or last_price == 0:
                        print(f"{symbol} might be delisted or not available (fast_info check).")
                        is_delisted = True
                except Exception as e:
                    if "Too Many Requests" in str(e) and attempt < self.max_retries - 1:
                        print("Rate limit hit when checking fast_info. Will retry.")
                        continue

                    print(f"Error accessing fast_info for {symbol} history check: {str(e)}")
                    # Fall back to traditional method
                    try:
                        info = ticker.info if hasattr(ticker, "info") else {}

                        if not info:
                            print(f"Warning: No info available for {symbol}")
                            info = {}

                        # Check if ticker is delisted or unavailable
                        if not info.get("regularMarketPrice") and not info.get("financialCurrency"):
                            print(f"{symbol} might be delisted or not available.")
                            is_delisted = True
                    except Exception as info_e:
                        if "Too Many Requests" in str(info_e) and attempt < self.max_retries - 1:
                            print("Rate limit hit when checking info. Will retry.")
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
                                    chunk = ticker.history(
                                        interval="1d",
                                        start=current_start,
                                        end=current_end,
                                    )
                                    if not chunk.empty:
                                        hist_parts.append(chunk)
                                except Exception as inner_e:
                                    if "Too Many Requests" in str(inner_e) and attempt < self.max_retries - 1:
                                        print(
                                            "Rate limit hit during chunked history request. Will restart with a new retry."
                                        )
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
                        period = "max"
                        print(f"No previous data for {symbol}. Getting {period} of history.")
                        hist = ticker.history(period=period)

                except Exception as hist_e:
                    if "Too Many Requests" in str(hist_e) and attempt < self.max_retries - 1:
                        print("Rate limit hit when retrieving history. Will retry.")
                        continue
                    else:
                        print(f"Error retrieving history data: {str(hist_e)}")
                        return False

                if hist is None or hist.empty:
                    print(f"No historical data available for {symbol}")
                    return True  # Return true as this is not a failure condition

                # Process the historical data
                try:
                    # Prepare batch data
                    activity_records = []
                    
                    for idx, row in hist.iterrows():
                        try:
                            activity_records.append((
                                ticker_id,
                                idx,
                                float(row["Open"]),
                                float(row["Close"]),
                                float(row["Volume"]),
                                float(row["High"]),
                                float(row["Low"])
                            ))

                            # Check if the stock paid dividends on this date
                            if row["Dividends"] > 0:
                                self.log_dividend_transactions(
                                    ticker_id,
                                    idx,
                                    float(row["Dividends"]),
                                )
                        except Exception as e:
                            print(f"Error preparing activity record for {symbol} on {idx}: {str(e)}")
                            continue
                            
                    # Batch insert/update
                    if activity_records:
                        self.dao.batch_update_activity(activity_records)

                    # Successfully processed all data
                    return True

                except Exception as processing_e:
                    print(f"Error processing historical data: {str(processing_e)}")
                    return False

            except Exception as e:
                print(f"Error in update_ticker_history attempt {attempt + 1} for {symbol}: {str(e)}")
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
            self.portfolio_transactions_dao.get_transaction_id(
                portfolio_id, security_id, "dividend", activity_date, amount=amount
            )

    def retrieve_ticker_history(self, ticker_id):
        """Retrieve ticker history from the database"""
        return self.dao.retrieve_ticker_activity(ticker_id=ticker_id)

    def _find_last_trading_day(self) -> datetime:
        trading_day = datetime.today()
        is_weekday = trading_day.weekday() < 5  # 0-4 are weekdays, 5-6 are weekend

        while not is_weekday:
            trading_day += timedelta(days=-1)
            is_weekday = trading_day.weekday() < 5

        print(f"Last trading day determined to be: {trading_day.date()}")
        return trading_day

    def _already_updated_today(self, last_update_date, trading_day_date):
        if last_update_date is None:
            last_update_date = date.today() - timedelta(days=365 * 5)  # Set to 5 years ago if never updated
        if last_update_date >= trading_day_date:
            return True

        return False

    def process_ticker(self, ticker_info, trading_day_date):
        """
        Process a single ticker update.
        
        Args:
            ticker_info (tuple): (ticker_id, symbol, last_update)
            trading_day_date (date): The last trading day date
            
        Returns:
            bool: True if successful, False otherwise
        """
        ticker_id, symbol, last_update = ticker_info
        
        try:
            if self._already_updated_today(last_update, trading_day_date):
                print(f"Skipping {symbol} (ID: {ticker_id}) - already updated ({last_update})")
                return True

            print(f"\nProcessing {symbol} (ID: {ticker_id})")

            # Add a small random delay to avoid synchronized API hits
            time.sleep(random.uniform(0.5, 2.0))

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

            # Recalculate indicators even if data update failed, as we might have partial data
            # or just need to refresh indicators
            
            try:
                self.rsi.calculateRSI(ticker_id)
                print(f"Updated RSI for {symbol}")
            except Exception as e:
                print(f"Error calculating RSI for {symbol}: {str(e)}")
                success = False

            # Calculate MACD
            try:
                self.macd_analyzer.calculate_macd(ticker_id)
                print(f"Updated MACD for {symbol}")
            except Exception as e:
                print(f"Error calculating MACD for {symbol}: {str(e)}")
                success = False

            # Calculate Moving Averages (multiple periods)
            try:
                for period in [20, 50, 200]:  # Calculate common MA periods
                    self.moving_avg.update_moving_averages(ticker_id, period)
                print(f"Updated Moving Averages for {symbol}")
            except Exception as e:
                print(f"Error calculating Moving Averages for {symbol}: {str(e)}")
                success = False

            # Calculate Stochastic Oscillator
            try:
                self.stochastic_analyzer.calculate_stochastic(ticker_id)
                print(f"Updated Stochastic Oscillator for {symbol}")
            except Exception as e:
                print(f"Error calculating Stochastic for {symbol}: {str(e)}")
                success = False

            return success

        except Exception as e:
            print(f"Error processing ticker_id {ticker_id}: {str(e)}")
            return False

    def update_stock_activity(self, update_watch_list=True):
        """Update stock activity for all tickers in portfolios with parallel processing"""
        try:
            trading_day = self._find_last_trading_day()
            # Get all tickers from all portfolios
            raw_portfolio_tickers = self.portfolio_dao.get_all_tickers_in_portfolios()
            # Normalize to 3-tuples (id, symbol, last_update)
            portfolio_tickers = [(t[0], t[1], t[2]) for t in raw_portfolio_tickers]

            # Also include tickers that have open positions but might be missing from portfolio_securities table
            try:
                portfolios = self.portfolio_dao.get_portfolio_list()
                existing_ticker_ids = {t[0] for t in portfolio_tickers}

                for portfolio in portfolios:
                    positions = self.portfolio_transactions_dao.get_current_positions(portfolio['id'])
                    for ticker_id, position_data in positions.items():
                        if ticker_id not in existing_ticker_ids:
                            symbol = position_data['symbol']
                            new_entry = (ticker_id, symbol, None)
                            portfolio_tickers.append(new_entry)
                            existing_ticker_ids.add(ticker_id)
                            print(f"Added {symbol} (ID: {ticker_id}) from transactions (was missing from portfolio list)")
            except Exception as e:
                print(f"Warning: Error fetching additional positions: {str(e)}")

            if update_watch_list:
                watch_list_tickers = self.watch_list_dao.get_all_watchlist_tickers()
                portfolio_tickers.extend(watch_list_tickers)

            portfolio_tickers = list(set(portfolio_tickers))  # Remove duplicates

            if not portfolio_tickers:
                print("No tickers found in portfolios")
                return

            print(f"Found {len(portfolio_tickers)} tickers to process")
            
            # Use ThreadPoolExecutor for parallel processing
            # Limit max_workers to avoid overwhelming the database connection pool or API
            max_workers = min(10, len(portfolio_tickers))
            
            print(f"Starting parallel update with {max_workers} workers...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Create a partial function or lambda to pass the trading day
                futures = {
                    executor.submit(self.process_ticker, ticker_info, trading_day.date()): ticker_info 
                    for ticker_info in portfolio_tickers
                }
                
                for future in concurrent.futures.as_completed(futures):
                    ticker_info = futures[future]
                    symbol = ticker_info[1]
                    try:
                        success = future.result()
                        status = "Success" if success else "Failed"
                        print(f"Completed {symbol}: {status}")
                    except Exception as exc:
                        print(f"Generated an exception for {symbol}: {exc}")

        except Exception as e:
            print(f"Error in update_stock_activity: {str(e)}")
            raise
