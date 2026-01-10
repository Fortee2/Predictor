import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict

import mysql.connector
import numpy as np
import pandas as pd
import yfinance as yf

from .base_dao import BaseDAO
from .utility import DatabaseConnectionPool


class MultiTimeframeAnalyzer(BaseDAO):
    """
    Analyzes portfolio performance across multiple timeframes with advanced metrics.
    Supports 1M, 3M, 6M, 1Y, 2Y, 5Y, and MAX timeframes.
    """

    TIMEFRAMES = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "2Y": 730, "5Y": 1825}

    RISK_FREE_RATE = 0.02  # 2% annual risk-free rate (can be made configurable)

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__(pool)

        self.sp500_ticker_id = 504  # S&P 500 ticker ID from the system

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_portfolio_value_history(self, portfolio_id: int, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Retrieve portfolio value history for the specified date range.

        Args:
            portfolio_id: Portfolio ID
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            DataFrame with dates and portfolio values
        """
        cursor = None
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT calculation_date as date, value 
                    FROM portfolio_value 
                    WHERE portfolio_id = %s 
                    AND calculation_date BETWEEN %s AND %s
                    ORDER BY calculation_date ASC
                """
                cursor.execute(query, (portfolio_id, start_date, end_date))
                results = cursor.fetchall()

                cursor.close()

                if not results:
                    return pd.DataFrame(columns=["date", "value"])

                df = pd.DataFrame(results)
                df["date"] = pd.to_datetime(df["date"])
                df["value"] = df["value"].astype(float)
                df.set_index("date", inplace=True)

                return df

        except mysql.connector.Error as e:
            self.logger.error("Error retrieving portfolio value history: %s", e)
            return pd.DataFrame(columns=["date", "value"])
        finally:
            if cursor:
                cursor.close()

    def get_benchmark_data(self, ticker_id: int, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Retrieve benchmark price data for the specified date range.

        Args:
            ticker_id: Ticker ID for the benchmark
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            DataFrame with dates and closing prices
        """
        cursor = None
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                # Get ticker symbol
                cursor.execute("SELECT ticker FROM tickers WHERE id = %s", (ticker_id,))
                result = cursor.fetchone()
                if not result:
                    self.logger.error("Ticker ID %s not found", ticker_id)
                    cursor.close()
                    return pd.DataFrame(columns=["date", "close"])

                symbol = result["ticker"]

                # Try to get data from database first
                query = """
                    SELECT activity_date as date, close 
                    FROM activity 
                    WHERE ticker_id = %s 
                    AND activity_date BETWEEN %s AND %s
                    ORDER BY activity_date ASC
                """
                cursor.execute(query, (ticker_id, start_date, end_date))
                results = cursor.fetchall()

                if results:
                    df = pd.DataFrame(results)
                    df["date"] = pd.to_datetime(df["date"])
                    df["close"] = df["close"].astype(float)
                    df.set_index("date", inplace=True)
                    cursor.close()
                    return df

                cursor.close()

                # Fallback to yfinance if no database data
                self.logger.info("No database data for %s, fetching from yfinance", symbol)
                try:
                    ticker = yf.Ticker(symbol)
                    hist_data = ticker.history(start=start_date, end=end_date + timedelta(days=1))

                    if hist_data.empty:
                        return pd.DataFrame(columns=["date", "close"])

                    df = pd.DataFrame()
                    df["close"] = hist_data["Close"]
                    df.index = hist_data.index.tz_localize(None)  # Remove timezone info
                    return df

                except Exception as e:
                    self.logger.error("Error fetching yfinance data for {symbol}: %s", e)
                    return pd.DataFrame(columns=["date", "close"])

        except mysql.connector.Error as e:
            self.logger.error("Error retrieving benchmark data: %s", e)
            return pd.DataFrame(columns=["date", "close"])
        finally:
            if cursor:
                cursor.close()

    def calculate_returns(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate daily returns from price data.

        Args:
            price_data: DataFrame with price data (indexed by date)

        Returns:
            DataFrame with daily returns
        """
        if price_data.empty:
            return pd.DataFrame()

        # Use the first column if multiple columns exist
        price_column = price_data.columns[0] if len(price_data.columns) > 0 else "value"
        returns = price_data[price_column].pct_change().dropna()
        return pd.DataFrame({price_column: returns})

    def calculate_performance_metrics(self, returns: pd.Series, benchmark_returns: pd.Series = None) -> Dict:
        """
        Calculate comprehensive performance metrics.

        Args:
            returns: Series of daily returns
            benchmark_returns: Series of benchmark daily returns (optional)

        Returns:
            Dictionary containing performance metrics
        """
        if returns.empty:
            return {}

        # Basic return metrics
        total_return = (1 + returns).prod() - 1

        # Annualized return
        trading_days = len(returns)
        years = trading_days / 252  # Assuming 252 trading days per year
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)

        # Sharpe ratio
        excess_returns = returns - (self.RISK_FREE_RATE / 252)  # Daily risk-free rate
        sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

        # Maximum drawdown
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()

        metrics = {
            "total_return_pct": total_return * 100,
            "annualized_return_pct": annualized_return * 100,
            "volatility_pct": volatility * 100,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown_pct": max_drawdown * 100,
        }

        # Add benchmark-relative metrics if benchmark data is provided
        if benchmark_returns is not None and not benchmark_returns.empty:
            # Align the series by date
            aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join="inner")

            if len(aligned_returns) > 1 and len(aligned_benchmark) > 1:
                # Beta calculation
                covariance = np.cov(aligned_returns, aligned_benchmark)[0, 1]
                benchmark_variance = np.var(aligned_benchmark)
                beta = covariance / benchmark_variance if benchmark_variance > 0 else 0

                # Alpha calculation (Jensen's alpha)
                benchmark_total_return = (1 + aligned_benchmark).prod() - 1
                benchmark_annualized = (1 + benchmark_total_return) ** (1 / years) - 1 if years > 0 else 0
                alpha = annualized_return - (self.RISK_FREE_RATE + beta * (benchmark_annualized - self.RISK_FREE_RATE))

                # Up/Down capture ratios
                up_periods = aligned_benchmark > 0
                down_periods = aligned_benchmark < 0

                up_capture = (
                    (aligned_returns[up_periods].mean() / aligned_benchmark[up_periods].mean())
                    if up_periods.sum() > 0 and aligned_benchmark[up_periods].mean() != 0
                    else 0
                )
                down_capture = (
                    (aligned_returns[down_periods].mean() / aligned_benchmark[down_periods].mean())
                    if down_periods.sum() > 0 and aligned_benchmark[down_periods].mean() != 0
                    else 0
                )

                # Excess return
                excess_return = total_return - benchmark_total_return

                metrics.update(
                    {
                        "alpha": alpha * 100,
                        "beta": beta,
                        "up_capture_ratio": up_capture,
                        "down_capture_ratio": down_capture,
                        "benchmark_return_pct": benchmark_total_return * 100,
                        "excess_return_pct": excess_return * 100,
                    }
                )

        return metrics

    def analyze_portfolio_timeframes(self, portfolio_id: int, calculation_date: date = None) -> Dict:
        """
        Analyze portfolio performance across all timeframes.

        Args:
            portfolio_id: Portfolio ID to analyze
            calculation_date: Date for analysis (defaults to today)

        Returns:
            Dictionary with performance metrics for each timeframe
        """
        if calculation_date is None:
            calculation_date = date.today()

        results = {}

        # Get the earliest transaction date to determine MAX timeframe
        cursor = None
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT MIN(transaction_date) as earliest_date
                    FROM portfolio_transactions
                    WHERE portfolio_id = %s
                """,
                    (portfolio_id,),
                )
                result = cursor.fetchone()
                earliest_date = result["earliest_date"] if result and result.get("earliest_date") else calculation_date - timedelta(days=365)
                cursor.close()
        except mysql.connector.Error as e:
            self.logger.error("Error retrieving earliest transaction date: %s", e)
            earliest_date = calculation_date - timedelta(days=365)
            if cursor:
                cursor.close()

        # Analyze each timeframe
        for timeframe, days in self.TIMEFRAMES.items():
            start_date = calculation_date - timedelta(days=days)

            # Skip if start_date is before earliest transaction
            if start_date < earliest_date:
                continue

            self.logger.info("Analyzing {timeframe} timeframe for portfolio %s", portfolio_id)

            # Get portfolio value history
            portfolio_data = self.get_portfolio_value_history(portfolio_id, start_date, calculation_date)
            if portfolio_data.empty:
                self.logger.warning("No portfolio data for %s timeframe", timeframe)
                continue

            # Calculate portfolio returns
            portfolio_returns = self.calculate_returns(portfolio_data)
            if portfolio_returns.empty:
                continue

            # Get S&P 500 benchmark data
            benchmark_data = self.get_benchmark_data(self.sp500_ticker_id, start_date, calculation_date)
            benchmark_returns = None
            if not benchmark_data.empty:
                benchmark_returns_df = self.calculate_returns(benchmark_data)
                if not benchmark_returns_df.empty:
                    benchmark_returns = benchmark_returns_df.iloc[:, 0]

            # Calculate metrics
            portfolio_returns_series = portfolio_returns.iloc[:, 0]
            metrics = self.calculate_performance_metrics(portfolio_returns_series, benchmark_returns)

            if metrics:
                results[timeframe] = metrics

        # Add MAX timeframe (from earliest date to calculation_date)
        if earliest_date < calculation_date:
            self.logger.info("Analyzing MAX timeframe for portfolio %s", portfolio_id)
            portfolio_data = self.get_portfolio_value_history(portfolio_id, earliest_date, calculation_date)
            if not portfolio_data.empty:
                portfolio_returns = self.calculate_returns(portfolio_data)
                if not portfolio_returns.empty:
                    benchmark_data = self.get_benchmark_data(self.sp500_ticker_id, earliest_date, calculation_date)
                    benchmark_returns = None
                    if not benchmark_data.empty:
                        benchmark_returns_df = self.calculate_returns(benchmark_data)
                        if not benchmark_returns_df.empty:
                            benchmark_returns = benchmark_returns_df.iloc[:, 0]

                    portfolio_returns_series = portfolio_returns.iloc[:, 0]
                    metrics = self.calculate_performance_metrics(portfolio_returns_series, benchmark_returns)
                    if metrics:
                        results["MAX"] = metrics

        return results

    def save_portfolio_metrics(
        self,
        portfolio_id: int,
        metrics_by_timeframe: Dict,
        calculation_date: date = None,
    ):
        """
        Save calculated portfolio metrics to the database.

        Args:
            portfolio_id: Portfolio ID
            metrics_by_timeframe: Dictionary of metrics by timeframe
            calculation_date: Date for the metrics (defaults to today)
        """
        if calculation_date is None:
            calculation_date = date.today()

        cursor = None
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                for timeframe, metrics in metrics_by_timeframe.items():
                    # Convert metrics to Decimal for database storage
                    db_metrics = {}
                    for key, value in metrics.items():
                        if value is not None and not np.isnan(value) and not np.isinf(value):
                            db_metrics[key] = Decimal(str(round(float(value), 4)))
                        else:
                            db_metrics[key] = None

                    # Insert or update portfolio performance metrics
                    query = """
                        INSERT INTO portfolio_performance_metrics 
                        (portfolio_id, calculation_date, timeframe, total_return_pct, annualized_return_pct, 
                        volatility_pct, sharpe_ratio, max_drawdown_pct, alpha, beta, up_capture_ratio, 
                        down_capture_ratio, benchmark_return_pct, excess_return_pct)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        total_return_pct = VALUES(total_return_pct),
                        annualized_return_pct = VALUES(annualized_return_pct),
                        volatility_pct = VALUES(volatility_pct),
                        sharpe_ratio = VALUES(sharpe_ratio),
                        max_drawdown_pct = VALUES(max_drawdown_pct),
                        alpha = VALUES(alpha),
                        beta = VALUES(beta),
                        up_capture_ratio = VALUES(up_capture_ratio),
                        down_capture_ratio = VALUES(down_capture_ratio),
                        benchmark_return_pct = VALUES(benchmark_return_pct),
                        excess_return_pct = VALUES(excess_return_pct)
                    """

                    values = (
                        portfolio_id,
                        calculation_date,
                        timeframe,
                        db_metrics.get("total_return_pct"),
                        db_metrics.get("annualized_return_pct"),
                        db_metrics.get("volatility_pct"),
                        db_metrics.get("sharpe_ratio"),
                        db_metrics.get("max_drawdown_pct"),
                        db_metrics.get("alpha"),
                        db_metrics.get("beta"),
                        db_metrics.get("up_capture_ratio"),
                        db_metrics.get("down_capture_ratio"),
                        db_metrics.get("benchmark_return_pct"),
                        db_metrics.get("excess_return_pct"),
                    )

                    cursor.execute(query, values)

                cursor.close()
                self.logger.info("Saved performance metrics for portfolio %s", portfolio_id)

        except mysql.connector.Error as e:
            self.logger.error("Error saving portfolio metrics: %s", e)
            raise
        finally:
            if cursor:
                cursor.close()

    def get_portfolio_metrics(self, portfolio_id: int, calculation_date: date = None) -> Dict:
        """
        Retrieve saved portfolio metrics from the database.

        Args:
            portfolio_id: Portfolio ID
            calculation_date: Date for the metrics (defaults to today)

        Returns:
            Dictionary of metrics by timeframe
        """
        if calculation_date is None:
            calculation_date = date.today()

        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT * FROM portfolio_performance_metrics
                    WHERE portfolio_id = %s AND calculation_date = %s
                    ORDER BY FIELD(timeframe, '1M', '3M', '6M', '1Y', '2Y', '5Y', 'MAX')
                """
                cursor.execute(query, (portfolio_id, calculation_date))
                results = cursor.fetchall()

                metrics_by_timeframe = {}
                for row in results:
                    timeframe = row["timeframe"]
                    metrics = {
                        k: float(v) if v is not None else None
                        for k, v in row.items()
                        if k
                        not in [
                            "id",
                            "portfolio_id",
                            "calculation_date",
                            "timeframe",
                            "created_at",
                        ]
                    }
                    metrics_by_timeframe[timeframe] = metrics

                return metrics_by_timeframe

        except mysql.connector.Error as e:
            self.logger.error("Error retrieving portfolio metrics: %s", e)
            return {}
        finally:
            cursor.close()

    def update_sp500_data(self, days_back: int = 30):
        """
        Update S&P 500 data to ensure benchmark comparisons are current.

        Args:
            days_back: Number of days back to update data for
        """
        try:
            from data.data_retrieval_consolidated import DataRetrieval

            # Initialize data retrieval
            data_retrieval = DataRetrieval(self.pool)

            # Update S&P 500 data
            self.logger.info("Updating S&P 500 benchmark data...")
            data_retrieval.update_symbol_data("^GSPC")

            self.logger.info("S&P 500 data update completed")

        except Exception as e:
            self.logger.error("Error updating S&P 500 data: %s", e)
