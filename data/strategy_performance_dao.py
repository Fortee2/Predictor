"""
Data Access Object for managing strategy performance metrics.

This module provides database operations for calculating, storing, and retrieving
performance metrics for trading strategies.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import mysql.connector

from .base_dao import BaseDAO
from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class StrategyPerformanceDAO(BaseDAO):
    """Data Access Object for strategy performance metrics."""

    def __init__(self, pool: DatabaseConnectionPool):
        """
        Initialize the StrategyPerformanceDAO.

        Args:
            pool: Database connection pool
        """
        super().__init__(pool)

    def calculate_and_save_metrics(
        self,
        strategy_id: int,
        portfolio_id: Optional[int] = None,
        ticker_id: Optional[int] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> bool:
        """
        Calculate and save performance metrics for a strategy.

        This calls the stored procedure calculate_strategy_performance which
        aggregates signal data and calculates metrics.

        Args:
            strategy_id: Strategy to calculate metrics for
            portfolio_id: Optional portfolio filter (None = all)
            ticker_id: Optional ticker filter (None = all)
            period_start: Start of period (None = 30 days ago)
            period_end: End of period (None = today)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Default period: last 30 days
            if period_end is None:
                period_end = date.today()
            if period_start is None:
                period_start = period_end - timedelta(days=30)

            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                # Call the stored procedure
                cursor.callproc(
                    "calculate_strategy_performance",
                    (strategy_id, portfolio_id, ticker_id, period_start, period_end),
                )

                # Fetch the result
                for result in cursor.stored_results():
                    output = result.fetchone()
                    logger.info(
                        f"Calculated metrics for strategy {strategy_id}: {output}"
                    )

                return True

        except mysql.connector.Error as e:
            logger.error(f"Error calculating strategy metrics: {e}")
            return False

    def get_performance_metrics(
        self,
        strategy_id: int,
        portfolio_id: Optional[int] = None,
        ticker_id: Optional[int] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> List[Dict]:
        """
        Retrieve performance metrics for a strategy.

        Args:
            strategy_id: Strategy ID
            portfolio_id: Optional portfolio filter
            ticker_id: Optional ticker filter
            period_start: Optional start date filter
            period_end: Optional end date filter

        Returns:
            List of performance metric dictionaries
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                query = """
                    SELECT * FROM strategy_performance_metrics
                    WHERE strategy_id = %s
                """
                params = [strategy_id]

                if portfolio_id is not None:
                    query += " AND (portfolio_id IS NULL OR portfolio_id = %s)"
                    params.append(portfolio_id)

                if ticker_id is not None:
                    query += " AND (ticker_id IS NULL OR ticker_id = %s)"
                    params.append(ticker_id)

                if period_start is not None:
                    query += " AND period_start >= %s"
                    params.append(period_start)

                if period_end is not None:
                    query += " AND period_end <= %s"
                    params.append(period_end)

                query += " ORDER BY period_end DESC"

                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                return results

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving performance metrics: {e}")
            return []

    def get_latest_metrics(
        self,
        strategy_id: int,
        portfolio_id: Optional[int] = None,
        ticker_id: Optional[int] = None,
    ) -> Optional[Dict]:
        """
        Get the most recent performance metrics for a strategy.

        Args:
            strategy_id: Strategy ID
            portfolio_id: Optional portfolio filter
            ticker_id: Optional ticker filter

        Returns:
            Dict containing latest metrics, or None if not found
        """
        metrics = self.get_performance_metrics(
            strategy_id=strategy_id, portfolio_id=portfolio_id, ticker_id=ticker_id
        )

        return metrics[0] if metrics else None

    def get_strategy_leaderboard(
        self,
        portfolio_id: Optional[int] = None,
        metric: str = "win_rate",
        limit: int = 10,
        min_signals: int = 5,
    ) -> List[Dict]:
        """
        Get top performing strategies ranked by a metric.

        Args:
            portfolio_id: Optional portfolio filter
            metric: Metric to rank by (win_rate, total_profit_loss, sharpe_ratio, avg_confidence)
            limit: Maximum number of results
            min_signals: Minimum signals required to be included

        Returns:
            List of strategy dictionaries with performance data
        """
        try:
            # Validate metric
            valid_metrics = [
                "win_rate",
                "total_profit_loss",
                "sharpe_ratio",
                "avg_confidence",
                "signals_acted_on",
            ]
            if metric not in valid_metrics:
                logger.warning(f"Invalid metric: {metric}, defaulting to win_rate")
                metric = "win_rate"

            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                # Use the view we created
                query = f"""
                    SELECT * FROM v_strategy_leaderboard
                    WHERE total_signals >= %s
                """
                params = [min_signals]

                if portfolio_id is not None:
                    # Need to join back to get portfolio filter
                    query = f"""
                        SELECT l.* FROM v_strategy_leaderboard l
                        INNER JOIN trading_signals sig ON l.strategy_id = sig.strategy_id
                        WHERE l.total_signals >= %s
                        AND (sig.portfolio_id IS NULL OR sig.portfolio_id = %s)
                        GROUP BY l.strategy_id
                    """
                    params.append(portfolio_id)

                # Order by the specified metric (descending, NULL last)
                query += f" ORDER BY {metric} DESC NULLS LAST LIMIT %s"
                params.append(limit)

                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                return results

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving strategy leaderboard: {e}")
            return []

    def get_timeframe_metrics(
        self, strategy_id: int, timeframe: str = "30D"
    ) -> Optional[Dict]:
        """
        Get metrics for a specific timeframe.

        Args:
            strategy_id: Strategy ID
            timeframe: Timeframe string (7D, 30D, 90D, 1Y, ALL)

        Returns:
            Dict containing calculated metrics for the timeframe
        """
        try:
            # Calculate date range based on timeframe
            end_date = date.today()
            timeframe_map = {
                "7D": 7,
                "30D": 30,
                "90D": 90,
                "1Y": 365,
            }

            if timeframe in timeframe_map:
                start_date = end_date - timedelta(days=timeframe_map[timeframe])
            elif timeframe == "ALL":
                start_date = None
            else:
                logger.warning(f"Invalid timeframe: {timeframe}, defaulting to 30D")
                start_date = end_date - timedelta(days=30)

            # Calculate fresh metrics
            self.calculate_and_save_metrics(
                strategy_id=strategy_id,
                period_start=start_date,
                period_end=end_date,
            )

            # Retrieve the metrics
            return self.get_latest_metrics(strategy_id=strategy_id)

        except Exception as e:
            logger.error(f"Error getting timeframe metrics: {e}")
            return None

    def compare_strategies(
        self, strategy_ids: List[int], portfolio_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Compare performance of multiple strategies side-by-side.

        Args:
            strategy_ids: List of strategy IDs to compare
            portfolio_id: Optional portfolio filter

        Returns:
            List of dictionaries with strategy comparison data
        """
        comparison = []

        for strategy_id in strategy_ids:
            metrics = self.get_latest_metrics(
                strategy_id=strategy_id, portfolio_id=portfolio_id
            )

            if metrics:
                comparison.append(
                    {
                        "strategy_id": strategy_id,
                        "metrics": metrics,
                    }
                )

        return comparison

    def get_performance_trend(
        self, strategy_id: int, num_periods: int = 12
    ) -> List[Dict]:
        """
        Get performance trend over time (last N periods).

        Args:
            strategy_id: Strategy ID
            num_periods: Number of periods to retrieve

        Returns:
            List of metrics ordered by period (oldest to newest)
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                query = """
                    SELECT
                        period_start,
                        period_end,
                        total_signals,
                        win_rate,
                        total_profit_loss,
                        avg_confidence
                    FROM strategy_performance_metrics
                    WHERE strategy_id = %s
                    ORDER BY period_end DESC
                    LIMIT %s
                """
                cursor.execute(query, (strategy_id, num_periods))
                results = cursor.fetchall()

                # Reverse to get oldest first (for trend charts)
                return list(reversed(results))

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving performance trend: {e}")
            return []

    def delete_old_metrics(self, days_to_keep: int = 90) -> int:
        """
        Delete old performance metrics to keep database clean.

        Args:
            days_to_keep: Keep metrics from last N days

        Returns:
            int: Number of rows deleted
        """
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)

            with self.get_connection() as connection:
                cursor = connection.cursor()

                query = """
                    DELETE FROM strategy_performance_metrics
                    WHERE period_end < %s
                """
                cursor.execute(query, (cutoff_date,))
                deleted_count = cursor.rowcount

                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} old performance metric records")

                return deleted_count

        except mysql.connector.Error as e:
            logger.error(f"Error deleting old metrics: {e}")
            return 0

    def recalculate_all_metrics(
        self, strategy_id: int, period_days: int = 30
    ) -> bool:
        """
        Recalculate metrics for all timeframes for a strategy.

        Useful after signal outcomes are updated.

        Args:
            strategy_id: Strategy ID
            period_days: Period length in days

        Returns:
            bool: True if successful
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days)

            # Calculate metrics for the period
            success = self.calculate_and_save_metrics(
                strategy_id=strategy_id,
                period_start=start_date,
                period_end=end_date,
            )

            if success:
                logger.info(
                    f"Recalculated all metrics for strategy {strategy_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error recalculating metrics: {e}")
            return False
