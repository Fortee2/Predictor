"""
Universal Portfolio Value Service

This module provides a centralized, consistent method for calculating portfolio values
that can be used throughout the application to ensure consistency between different views.
"""

import logging
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any, Dict, Optional

import mysql.connector
import pandas as pd
import yfinance as yf

from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class PortfolioValueService:
    """
    Universal service for calculating portfolio values consistently across the application.
    """

    def __init__(self, pool: DatabaseConnectionPool):
        """
        Initialize DAO with a shared database connection pool.

        Args:
            pool: DatabaseConnectionPool instance shared across all DAOs
        """
        self.pool = pool
        self.current_connection = None

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        connection = None
        try:
            if self.current_connection is not None and self.current_connection.is_connected():
                connection = self.current_connection
                yield connection
            else:
                connection = self.pool.get_connection()
                self.current_connection = connection
                yield connection
        except mysql.connector.Error as e:
            logger.error("Database connection error: %s", str(e))
            raise
        finally:
            pass

    def calculate_portfolio_value(
        self,
        portfolio_id: int,
        calculation_date: Optional[date] = None,
        include_cash: bool = True,
        include_dividends: bool = True,
        use_current_prices: bool = False,
    ) -> Dict[str, Any]:
        """
        Universal portfolio value calculation method.

        Args:
            portfolio_id (int): The portfolio ID
            calculation_date (date, optional): Date for calculation. Defaults to today.
            include_cash (bool): Whether to include cash balance. Defaults to True.
            include_dividends (bool): Whether to include dividend payments. Defaults to True.
            use_current_prices (bool, optional): Force use of current prices vs historical.
                                               If None, automatically determined based on calculation_date.

        Returns:
            Dict containing:
                - total_value (float): Total portfolio value
                - stock_value (float): Value of stock positions
                - cash_balance (float): Cash balance (if included)
                - dividend_value (float): Cumulative dividends (if included)
                - positions (dict): Individual position details
                - calculation_date (date): Date used for calculation
                - metadata (dict): Additional calculation metadata
        """
        try:
            if calculation_date is None:
                calculation_date = date.today()

            # Determine if we should use current prices
            if use_current_prices is None:
                use_current_prices = calculation_date == date.today()

            # Get current positions using the existing FIFO method
            positions = self._get_current_positions(portfolio_id, calculation_date)

            # Calculate stock values
            stock_value = 0.0
            position_details = {}

            for ticker_id, position in positions.items():
                symbol = position["symbol"]
                shares = float(position["shares"])
                avg_price = float(position["avg_price"])

                # Get current price for this ticker
                current_price = self._get_ticker_price(ticker_id, symbol, calculation_date)

                if current_price is not None:
                    position_value = shares * current_price
                    stock_value += position_value

                    # Calculate gain/loss
                    cost_basis = shares * avg_price
                    gain_loss = position_value - cost_basis
                    gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0

                    position_details[ticker_id] = {
                        "symbol": symbol,
                        "shares": shares,
                        "avg_price": avg_price,
                        "current_price": current_price,
                        "position_value": position_value,
                        "cost_basis": cost_basis,
                        "gain_loss": gain_loss,
                        "gain_loss_pct": gain_loss_pct,
                        "weight_pct": 0,  # Will be calculated after total is known
                        "core_holding": position.get("core_holding", 0),
                    }

            # Get cash balance
            cash_balance = 0.0
            if include_cash:
                cash_balance = self._get_cash_balance(portfolio_id, calculation_date)

            # Get dividend value
            dividend_value = 0.0
            if include_dividends:
                dividend_value = self._get_cumulative_dividends(portfolio_id, calculation_date)

            # Calculate total value
            total_value = stock_value + cash_balance + dividend_value

            # Calculate position weights
            if total_value > 0:
                for position in position_details.values():
                    position["weight_pct"] = (position["position_value"] / total_value) * 100

            return {
                "total_value": round(total_value, 2),
                "stock_value": round(stock_value, 2),
                "cash_balance": round(cash_balance, 2),
                "dividend_value": round(dividend_value, 2),
                "positions": position_details,
                "calculation_date": calculation_date,
                "metadata": {
                    "include_cash": include_cash,
                    "include_dividends": include_dividends,
                    "use_current_prices": use_current_prices,
                    "position_count": len(position_details),
                },
            }

        except Exception as e:
            logger.error("Error calculating portfolio value: %s", e, exc_info=True)
            return {
                "total_value": 0.0,
                "stock_value": 0.0,
                "cash_balance": 0.0,
                "dividend_value": 0.0,
                "positions": {},
                "calculation_date": calculation_date,
                "metadata": {"error": str(e)},
            }

    def _get_current_positions(self, portfolio_id: int, calculation_date: date) -> Dict[int, Dict[str, Any]]:
        """
        Get current positions for a portfolio as of a specific date.
        Uses FIFO method for cost basis calculation.
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                # Get all buy/sell transactions up to the calculation date
                query = """
                    SELECT
                        s.ticker_id,
                        s.id as security_id,
                        tk.ticker as symbol,
                        t.transaction_type,
                        t.transaction_date,
                        t.shares,
                        t.price,
                        s.core_holding
                    FROM portfolio_transactions t
                    JOIN portfolio_securities s ON t.security_id = s.id
                    JOIN tickers tk ON s.ticker_id = tk.id
                    WHERE t.portfolio_id = %s
                    AND t.transaction_date <= %s
                    AND t.transaction_type IN ('buy', 'sell')
                    ORDER BY s.ticker_id, t.transaction_date ASC, t.id ASC
                """
                cursor.execute(query, (portfolio_id, calculation_date))
                transactions = cursor.fetchall()

                # Process transactions using FIFO method
                positions = {}
                current_ticker = None
                buy_queue = []
                symbol: str = ""
                core_holding: int = 0

                for transaction in transactions:
                    ticker_id = transaction["ticker_id"]
                    trans_type = transaction["transaction_type"]

                    # If we're starting a new ticker, finalize the previous one
                    if current_ticker is not None and current_ticker != ticker_id:
                        if buy_queue:
                            positions[current_ticker] = self._calculate_position_from_queue(buy_queue, symbol, core_holding)
                        buy_queue = []

                    current_ticker = ticker_id
                    symbol = transaction["symbol"]
                    core_holding = transaction["core_holding"]

                    shares = float(transaction["shares"] or 0)
                    price = float(transaction["price"] or 0)

                    if shares <= 0 or price <= 0:
                        continue

                    if trans_type == "buy":
                        buy_queue.append((shares, price))
                    elif trans_type == "sell":
                        self._process_fifo_sell(buy_queue, shares)

                # Process the last ticker
                if current_ticker is not None and buy_queue:
                    positions[current_ticker] = self._calculate_position_from_queue(buy_queue, symbol, core_holding)

                return positions

        except Exception as e:
            logger.error("Error getting current positions: %s", e, exc_info=True)
            return {}

    def _calculate_position_from_queue(self, buy_queue: list, symbol: str, core_holding: int = 0) -> Dict[str, Any] | None:
        """Calculate position details from a buy queue."""
        total_shares = sum(shares for shares, _ in buy_queue)
        total_cost = sum(shares * price for shares, price in buy_queue)

        if total_shares > 0:
            return {
                "symbol": symbol,
                "shares": round(total_shares, 4),
                "avg_price": round(total_cost / total_shares, 2),
                "core_holding": core_holding,
            }
        return None

    def _process_fifo_sell(self, buy_queue: list, shares_to_sell: float):
        """Process a sell transaction using FIFO method."""
        while shares_to_sell > 0 and buy_queue:
            buy_shares, buy_price = buy_queue[0]

            if buy_shares <= shares_to_sell:
                buy_queue.pop(0)
                shares_to_sell -= buy_shares
            else:
                buy_queue[0] = (buy_shares - shares_to_sell, buy_price)
                shares_to_sell = 0

    def _get_ticker_price(self, ticker_id: int, symbol: str, calculation_date: date) -> Optional[float]:
        """
        Get ticker price for a specific date.

        Priority:
        1. If use_current=True, get latest price from ticker table
        2. Get historical price from investing.activity table
        3. Fall back to yfinance historical data
        4. Use last transaction price as final fallback
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Try to get historical price from database
                try:
                    hist_query = """
                        SELECT close
                        FROM investing.activity
                        WHERE ticker_id = %s AND activity_date <= %s
                        ORDER BY activity_date DESC
                        LIMIT 1
                    """
                    cursor.execute(hist_query, (ticker_id, calculation_date))
                    result = cursor.fetchone()
                    if result and result[0]:
                        return float(result[0])
                except mysql.connector.Error:
                    # investing.activity table might not exist
                    pass

                # Try yfinance for historical data
                try:
                    stock = yf.Ticker(symbol)
                    start_date = (calculation_date - timedelta(days=5)).strftime("%Y-%m-%d")
                    end_date = (calculation_date + timedelta(days=1)).strftime("%Y-%m-%d")
                    hist_data = stock.history(start=start_date, end=end_date)

                    if not hist_data.empty:
                        # Remove timezone information from the index if present
                        try:
                            # Try to remove timezone (works if index is timezone-aware)
                            hist_data.index = hist_data.index.tz_localize(None)
                        except (TypeError, AttributeError):
                            # Index is already timezone-naive or doesn't support tz operations
                            pass

                        calc_timestamp = pd.Timestamp(calculation_date)
                        valid_dates = hist_data.index[hist_data.index <= calc_timestamp]
                        if len(valid_dates) > 0:
                            closest_date = valid_dates[-1]
                            return float(hist_data.loc[closest_date, "Close"])
                except Exception:
                    pass

                # Final fallback: get last transaction price
                cursor.execute(
                    """
                    SELECT price FROM portfolio_transactions pt
                    JOIN portfolio_securities ps ON pt.security_id = ps.id
                    WHERE ps.ticker_id = %s AND pt.price IS NOT NULL
                    ORDER BY pt.transaction_date DESC, pt.id DESC
                    LIMIT 1
                    """,
                    (ticker_id,),
                )
                result = cursor.fetchone()
                if result and result[0]:
                    return float(result[0])

                return None

        except Exception as e:
            logger.error("Error getting ticker price for %s: %s", symbol, e)
            return None

    def _get_cash_balance(self, portfolio_id: int, calculation_date: date | None = None) -> float:
        """Get cash balance for portfolio, optionally for a specific date."""
        try:
            # Import here to avoid circular imports
            from .portfolio_dao import PortfolioDAO

            # Create a temporary DAO instance to use the historical cash balance method
            portfolio_dao = PortfolioDAO(self.pool)
            portfolio_dao.current_connection = self.current_connection  # Reuse existing connection

            return portfolio_dao.get_cash_balance(portfolio_id, calculation_date)

        except Exception as e:
            logger.error("Error getting cash balance: %s", e)
            return 0.0

    def _get_cumulative_dividends(self, portfolio_id: int, calculation_date: date) -> float:
        """Get cumulative dividends received up to calculation date."""
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = """
                    SELECT SUM(amount) as total_dividends
                    FROM portfolio_transactions
                    WHERE portfolio_id = %s
                    AND transaction_type = 'dividend'
                    AND transaction_date <= %s
                """
                cursor.execute(query, (portfolio_id, calculation_date))
                result = cursor.fetchone()
                if result and result[0]:
                    return float(result[0])
                return 0.0
        except Exception as e:
            logger.error("Error getting cumulative dividends: %s", e)
            return 0.0

    def get_portfolio_summary(self, portfolio_id: int, **kwargs) -> str:
        """
        Get a formatted summary of portfolio value calculation.

        Args:
            portfolio_id (int): Portfolio ID
            **kwargs: Arguments passed to calculate_portfolio_value

        Returns:
            str: Formatted portfolio summary
        """
        result = self.calculate_portfolio_value(portfolio_id, **kwargs)

        summary = []
        summary.append(f"Portfolio Value Summary (as of {result['calculation_date']})")
        summary.append("=" * 50)
        summary.append(f"Stock Value:     ${result['stock_value']:>12,.2f}")

        if result["metadata"].get("include_cash", True):
            summary.append(f"Cash Balance:    ${result['cash_balance']:>12,.2f}")

        if result["metadata"].get("include_dividends", True):
            summary.append(f"Dividends:       ${result['dividend_value']:>12,.2f}")

        summary.append("-" * 50)
        summary.append(f"Total Value:     ${result['total_value']:>12,.2f}")
        summary.append("")

        if result["positions"]:
            summary.append("Individual Positions:")
            summary.append("-" * 50)
            for position in result["positions"].values():
                gain_loss_sign = "+" if position["gain_loss"] >= 0 else ""
                summary.append(
                    f"{position['symbol']:<8} {position['shares']:>8.2f} shares @ "
                    f"${position['current_price']:>7.2f} = ${position['position_value']:>10,.2f} "
                    f"({gain_loss_sign}{position['gain_loss_pct']:>6.2f}%)"
                )

        return "\n".join(summary)
