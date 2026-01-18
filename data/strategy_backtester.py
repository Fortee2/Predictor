"""
Strategy Backtester - Historical strategy validation engine.

This module backtests trading strategies on historical data to evaluate
their performance and calculate metrics like win rate, returns, and Sharpe ratio.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import Config
from .strategy_evaluator import StrategyEvaluator
from .strategy_performance_dao import StrategyPerformanceDAO
from .ticker_dao import TickerDao
from .trading_strategy_dao import TradingStrategyDAO
from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class StrategyBacktester:
    """
    Backtesting engine for evaluating strategy performance on historical data.
    """

    def __init__(self, pool: DatabaseConnectionPool, config: Optional[Config] = None):
        """
        Initialize the Strategy Backtester.

        Args:
            pool: Database connection pool
            config: Optional configuration object
        """
        self.pool = pool
        self.config = config if config else Config()
        self.evaluator = StrategyEvaluator(pool, config)
        self.performance_dao = StrategyPerformanceDAO(pool)
        self.strategy_dao = TradingStrategyDAO(pool)
        self.ticker_dao = TickerDao(pool)

    def backtest_strategy(
        self,
        strategy_id: int,
        ticker_id: int,
        start_date: date,
        end_date: date,
        initial_capital: float = 10000.0,
    ) -> Dict:
        """
        Run backtest on historical data.

        Args:
            strategy_id: Strategy to backtest
            ticker_id: Ticker to backtest on
            start_date: Start date of backtest
            end_date: End date of backtest
            initial_capital: Starting capital for simulation

        Returns:
            Dict with comprehensive backtest results
        """
        try:
            # Get strategy
            strategy = self.strategy_dao.get_strategy(strategy_id)
            if not strategy:
                return {"success": False, "error": "Strategy not found"}

            # Get ticker symbol
            ticker_symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
            if not ticker_symbol:
                return {"success": False, "error": "Ticker not found"}

            logger.info(
                f"Backtesting strategy '{strategy['name']}' on {ticker_symbol} "
                f"from {start_date} to {end_date}"
            )

            # Get historical price data
            price_data = self._get_historical_prices(ticker_id, start_date, end_date)
            if price_data.empty:
                return {"success": False, "error": "No historical data available"}

            # Initialize simulation state
            cash = initial_capital
            shares = 0
            cost_basis = 0.0
            trades = []
            equity_curve = []
            signals_generated = []

            # Transaction cost from config
            transaction_cost = self.config.config.get("trading_strategies", {}).get(
                "backtest_transaction_cost", 5.0
            )

            # Iterate through each trading day
            for trade_date in pd.date_range(start_date, end_date, freq='D'):
                # Skip if no price data for this date
                if trade_date not in price_data.index:
                    continue

                current_price = price_data.loc[trade_date, 'close']

                # Evaluate strategy for this date
                # Note: In real backtest, we'd need historical indicator values
                # For simplicity, we'll evaluate with data available up to this date
                signal = self._evaluate_strategy_at_date(
                    strategy, ticker_id, ticker_symbol, trade_date
                )

                if signal:
                    signals_generated.append(
                        {
                            "date": trade_date,
                            "signal_type": signal["signal_type"],
                            "confidence": signal["confidence_score"],
                            "price": current_price,
                        }
                    )

                    # Execute trade based on signal
                    if signal["signal_type"] == "BUY" and shares == 0 and cash > 0:
                        # Buy signal - enter position
                        shares_to_buy = int((cash - transaction_cost) / current_price)
                        if shares_to_buy > 0:
                            cost = shares_to_buy * current_price + transaction_cost
                            cash -= cost
                            shares = shares_to_buy
                            cost_basis = current_price

                            trades.append(
                                {
                                    "date": trade_date,
                                    "type": "BUY",
                                    "shares": shares_to_buy,
                                    "price": current_price,
                                    "cost": cost,
                                    "signal_confidence": signal["confidence_score"],
                                }
                            )

                    elif signal["signal_type"] == "SELL" and shares > 0:
                        # Sell signal - exit position
                        proceeds = shares * current_price - transaction_cost
                        cash += proceeds
                        profit_loss = (current_price - cost_basis) * shares - (
                            2 * transaction_cost
                        )
                        profit_loss_pct = (
                            (current_price - cost_basis) / cost_basis * 100
                        )

                        trades.append(
                            {
                                "date": trade_date,
                                "type": "SELL",
                                "shares": shares,
                                "price": current_price,
                                "proceeds": proceeds,
                                "profit_loss": profit_loss,
                                "profit_loss_pct": profit_loss_pct,
                                "signal_confidence": signal["confidence_score"],
                            }
                        )

                        shares = 0
                        cost_basis = 0.0

                # Calculate current portfolio value
                portfolio_value = cash + (shares * current_price if shares > 0 else 0)
                equity_curve.append(
                    {"date": trade_date, "value": portfolio_value, "price": current_price}
                )

            # Close any open position at end date
            if shares > 0:
                final_price = price_data.iloc[-1]['close']
                proceeds = shares * final_price - transaction_cost
                cash += proceeds
                profit_loss = (final_price - cost_basis) * shares - (2 * transaction_cost)
                profit_loss_pct = (final_price - cost_basis) / cost_basis * 100

                trades.append(
                    {
                        "date": end_date,
                        "type": "SELL",
                        "shares": shares,
                        "price": final_price,
                        "proceeds": proceeds,
                        "profit_loss": profit_loss,
                        "profit_loss_pct": profit_loss_pct,
                        "signal_confidence": 0,
                        "note": "Position closed at end of backtest",
                    }
                )

                shares = 0

            final_value = cash
            total_return = final_value - initial_capital
            total_return_pct = (total_return / initial_capital) * 100

            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(
                trades, equity_curve, initial_capital, final_value, start_date, end_date
            )

            # Build result
            result = {
                "success": True,
                "strategy_id": strategy_id,
                "strategy_name": strategy["name"],
                "ticker_id": ticker_id,
                "ticker_symbol": ticker_symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "initial_capital": initial_capital,
                "final_value": final_value,
                "total_return": total_return,
                "total_return_pct": total_return_pct,
                "total_trades": len([t for t in trades if t["type"] == "SELL"]),
                "total_signals": len(signals_generated),
                "trades": trades,
                "signals": signals_generated,
                "equity_curve": equity_curve,
                **metrics,
            }

            logger.info(
                f"Backtest complete: {total_return_pct:.2f}% return, "
                f"{len(trades)} trades, {metrics['win_rate']:.1f}% win rate"
            )

            return result

        except Exception as e:
            logger.error(f"Error during backtest: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _get_historical_prices(
        self, ticker_id: int, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Get historical price data for a ticker.

        Args:
            ticker_id: Ticker ID
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with OHLCV data indexed by date
        """
        try:
            # Query the activity table for historical data
            with self.pool.get_connection() as connection:
                query = """
                    SELECT activity_date, open, high, low, close, volume
                    FROM activity
                    WHERE ticker_id = %s
                    AND activity_date BETWEEN %s AND %s
                    ORDER BY activity_date
                """
                df = pd.read_sql_query(
                    query,
                    connection,
                    params=(ticker_id, start_date, end_date),
                    parse_dates=['activity_date'],
                    index_col='activity_date',
                )
                return df

        except Exception as e:
            logger.error(f"Error fetching historical prices: {e}")
            return pd.DataFrame()

    def _evaluate_strategy_at_date(
        self,
        strategy: Dict,
        ticker_id: int,
        ticker_symbol: str,
        eval_date: datetime,
    ) -> Optional[Dict]:
        """
        Evaluate strategy at a specific historical date.

        Note: This is simplified - in a full implementation, we would
        need to ensure all indicator calculations use only data available
        up to eval_date.

        Args:
            strategy: Strategy configuration
            ticker_id: Ticker ID
            ticker_symbol: Ticker symbol
            eval_date: Date to evaluate at

        Returns:
            Signal dict if conditions met, None otherwise
        """
        try:
            # For backtesting, we evaluate the strategy as if it were that date
            # The indicators should only use data up to eval_date
            # This is a simplified version - full implementation would need
            # date-aware indicator calculations

            signal = self.evaluator.evaluate_strategy(
                strategy, ticker_id, ticker_symbol, portfolio_id=None
            )

            return signal

        except Exception as e:
            logger.debug(f"Error evaluating strategy at {eval_date}: {e}")
            return None

    def _calculate_performance_metrics(
        self,
        trades: List[Dict],
        equity_curve: List[Dict],
        initial_capital: float,
        final_value: float,
        start_date: date,
        end_date: date,
    ) -> Dict:
        """
        Calculate comprehensive performance metrics.

        Args:
            trades: List of executed trades
            equity_curve: Portfolio value over time
            initial_capital: Starting capital
            final_value: Final portfolio value
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            Dict with performance metrics
        """
        metrics = {}

        # Trade analysis
        sell_trades = [t for t in trades if t["type"] == "SELL"]
        if sell_trades:
            winning_trades = [t for t in sell_trades if t.get("profit_loss", 0) > 0]
            losing_trades = [t for t in sell_trades if t.get("profit_loss", 0) < 0]

            metrics["winning_trades"] = len(winning_trades)
            metrics["losing_trades"] = len(losing_trades)
            metrics["win_rate"] = (
                (len(winning_trades) / len(sell_trades)) * 100 if sell_trades else 0
            )

            # Average profit/loss
            if winning_trades:
                metrics["avg_win"] = np.mean([t["profit_loss"] for t in winning_trades])
                metrics["avg_win_pct"] = np.mean(
                    [t["profit_loss_pct"] for t in winning_trades]
                )
            else:
                metrics["avg_win"] = 0
                metrics["avg_win_pct"] = 0

            if losing_trades:
                metrics["avg_loss"] = np.mean([t["profit_loss"] for t in losing_trades])
                metrics["avg_loss_pct"] = np.mean(
                    [t["profit_loss_pct"] for t in losing_trades]
                )
            else:
                metrics["avg_loss"] = 0
                metrics["avg_loss_pct"] = 0

            # Profit factor
            total_wins = sum(t.get("profit_loss", 0) for t in winning_trades)
            total_losses = abs(sum(t.get("profit_loss", 0) for t in losing_trades))
            metrics["profit_factor"] = (
                total_wins / total_losses if total_losses > 0 else 0
            )

        else:
            metrics.update(
                {
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0,
                    "avg_win": 0,
                    "avg_win_pct": 0,
                    "avg_loss": 0,
                    "avg_loss_pct": 0,
                    "profit_factor": 0,
                }
            )

        # Calculate annualized return
        days = (end_date - start_date).days
        if days > 0:
            years = days / 365.25
            total_return_pct = ((final_value - initial_capital) / initial_capital) * 100
            metrics["annualized_return_pct"] = (
                ((final_value / initial_capital) ** (1 / years) - 1) * 100
            )
        else:
            metrics["annualized_return_pct"] = 0

        # Calculate max drawdown
        if equity_curve:
            values = [ec["value"] for ec in equity_curve]
            peak = values[0]
            max_dd = 0
            for value in values:
                if value > peak:
                    peak = value
                drawdown = ((peak - value) / peak) * 100
                if drawdown > max_dd:
                    max_dd = drawdown
            metrics["max_drawdown_pct"] = max_dd
        else:
            metrics["max_drawdown_pct"] = 0

        # Calculate Sharpe ratio (simplified - using daily returns)
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                ret = (
                    (equity_curve[i]["value"] - equity_curve[i - 1]["value"])
                    / equity_curve[i - 1]["value"]
                )
                returns.append(ret)

            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                if std_return > 0:
                    # Annualize (252 trading days, risk-free rate ~2%)
                    risk_free_daily = 0.02 / 252
                    sharpe = ((avg_return - risk_free_daily) / std_return) * np.sqrt(252)
                    metrics["sharpe_ratio"] = sharpe
                else:
                    metrics["sharpe_ratio"] = 0
            else:
                metrics["sharpe_ratio"] = 0
        else:
            metrics["sharpe_ratio"] = 0

        return metrics

    def compare_strategies(
        self,
        strategy_ids: List[int],
        ticker_id: int,
        start_date: date,
        end_date: date,
        initial_capital: float = 10000.0,
    ) -> Dict:
        """
        Compare multiple strategies side-by-side.

        Args:
            strategy_ids: List of strategy IDs to compare
            ticker_id: Ticker to backtest on
            start_date: Start date
            end_date: End date
            initial_capital: Starting capital for each

        Returns:
            Dict with comparison results
        """
        results = []

        for strategy_id in strategy_ids:
            result = self.backtest_strategy(
                strategy_id, ticker_id, start_date, end_date, initial_capital
            )
            if result.get("success"):
                results.append(result)

        if not results:
            return {"success": False, "error": "No successful backtests"}

        # Create comparison summary
        comparison = {
            "success": True,
            "ticker_id": ticker_id,
            "ticker_symbol": results[0]["ticker_symbol"] if results else None,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "initial_capital": initial_capital,
            "strategies": [],
        }

        for result in results:
            comparison["strategies"].append(
                {
                    "strategy_id": result["strategy_id"],
                    "strategy_name": result["strategy_name"],
                    "total_return_pct": result["total_return_pct"],
                    "annualized_return_pct": result["annualized_return_pct"],
                    "win_rate": result["win_rate"],
                    "total_trades": result["total_trades"],
                    "max_drawdown_pct": result["max_drawdown_pct"],
                    "sharpe_ratio": result["sharpe_ratio"],
                    "profit_factor": result.get("profit_factor", 0),
                }
            )

        # Rank by total return
        comparison["strategies"].sort(
            key=lambda x: x["total_return_pct"], reverse=True
        )

        # Identify best strategy by different metrics
        comparison["best_return"] = max(
            comparison["strategies"], key=lambda x: x["total_return_pct"]
        )
        comparison["best_win_rate"] = max(
            comparison["strategies"], key=lambda x: x["win_rate"]
        )
        comparison["best_sharpe"] = max(
            comparison["strategies"], key=lambda x: x["sharpe_ratio"]
        )

        logger.info(f"Compared {len(results)} strategies on {results[0]['ticker_symbol']}")

        return comparison

    def run_walk_forward_analysis(
        self,
        strategy_id: int,
        ticker_id: int,
        start_date: date,
        end_date: date,
        train_window_days: int = 180,
        test_window_days: int = 60,
    ) -> Dict:
        """
        Run walk-forward analysis to test strategy robustness.

        Splits data into training and testing windows, walking forward through time.

        Args:
            strategy_id: Strategy to test
            ticker_id: Ticker to test on
            start_date: Overall start date
            end_date: Overall end date
            train_window_days: Days in training window
            test_window_days: Days in testing window

        Returns:
            Dict with walk-forward results
        """
        results = []
        current_start = start_date

        while current_start < end_date:
            train_end = current_start + timedelta(days=train_window_days)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=test_window_days)

            if test_end > end_date:
                test_end = end_date

            # Run backtest on test period
            result = self.backtest_strategy(
                strategy_id, ticker_id, test_start, test_end
            )

            if result.get("success"):
                results.append(
                    {
                        "train_start": current_start.isoformat(),
                        "train_end": train_end.isoformat(),
                        "test_start": test_start.isoformat(),
                        "test_end": test_end.isoformat(),
                        "return_pct": result["total_return_pct"],
                        "win_rate": result["win_rate"],
                        "trades": result["total_trades"],
                    }
                )

            # Move forward
            current_start = test_end + timedelta(days=1)

        if not results:
            return {"success": False, "error": "No walk-forward results"}

        # Calculate aggregate statistics
        avg_return = np.mean([r["return_pct"] for r in results])
        avg_win_rate = np.mean([r["win_rate"] for r in results])
        consistency = np.std([r["return_pct"] for r in results])

        return {
            "success": True,
            "strategy_id": strategy_id,
            "ticker_id": ticker_id,
            "periods_tested": len(results),
            "avg_return_pct": avg_return,
            "avg_win_rate": avg_win_rate,
            "return_consistency": consistency,
            "periods": results,
        }
