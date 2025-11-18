"""
Additional edge case tests for Comprehensive Analysis calculations.

This module focuses on testing edge cases, error conditions, and boundary scenarios
that might not be covered in the main test suite.
"""

import os
import sys
import unittest
from decimal import Decimal
from unittest.mock import Mock

import numpy as np
import pandas as pd

# Add the project root to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.comprehensive_performance_formatter import ComprehensivePerformanceFormatter
from data.multi_timeframe_analyzer import MultiTimeframeAnalyzer


class TestEdgeCasesMultiTimeframeAnalyzer(unittest.TestCase):
    """Test edge cases for MultiTimeframeAnalyzer."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock database connection pool
        mock_pool = Mock()
        mock_connection = Mock()
        mock_pool.get_connection.return_value = mock_connection
        mock_pool.get_connection_context.return_value.__enter__.return_value = mock_connection
        mock_pool.get_connection_context.return_value.__exit__.return_value = None

        # Create analyzer with mocked pool - MultiTimeframeAnalyzer only takes pool parameter
        self.analyzer = MultiTimeframeAnalyzer(pool=mock_pool)

    def test_calculate_performance_metrics_with_nan_values(self):
        """Test performance metrics calculation with NaN values in returns."""
        # Create returns with NaN values
        returns_with_nan = pd.Series([0.01, np.nan, 0.015, -0.002, np.nan, 0.008])

        # Should handle NaN values gracefully
        metrics = self.analyzer.calculate_performance_metrics(returns_with_nan)

        # Check that metrics are still calculated (pandas should handle NaN)
        self.assertIn("total_return_pct", metrics)
        self.assertIn("volatility_pct", metrics)

        # Volatility should still be calculable
        self.assertGreater(metrics["volatility_pct"], 0)

    def test_calculate_performance_metrics_with_infinite_values(self):
        """Test performance metrics calculation with infinite values."""
        # Create returns with infinite values
        returns_with_inf = pd.Series([0.01, np.inf, 0.015, -0.002, 0.008])

        metrics = self.analyzer.calculate_performance_metrics(returns_with_inf)

        # Should handle infinite values (might result in inf metrics)
        self.assertIn("total_return_pct", metrics)
        # Total return might be infinite, but should not crash
        self.assertTrue(np.isinf(metrics["total_return_pct"]) or np.isfinite(metrics["total_return_pct"]))

    def test_calculate_performance_metrics_all_zero_returns(self):
        """Test performance metrics with all zero returns."""
        zero_returns = pd.Series([0.0, 0.0, 0.0, 0.0, 0.0])

        metrics = self.analyzer.calculate_performance_metrics(zero_returns)

        # With zero returns:
        self.assertEqual(metrics["total_return_pct"], 0.0)
        self.assertEqual(metrics["annualized_return_pct"], 0.0)
        self.assertEqual(metrics["volatility_pct"], 0.0)
        self.assertEqual(metrics["max_drawdown_pct"], 0.0)
        # Sharpe ratio should be 0 (0 excess return / 0 volatility handled as 0)
        self.assertEqual(metrics["sharpe_ratio"], 0)

    def test_calculate_performance_metrics_extreme_volatility(self):
        """Test performance metrics with extremely volatile returns."""
        # Create extremely volatile returns (+/- 50%)
        extreme_returns = pd.Series([0.5, -0.5, 0.5, -0.5, 0.5, -0.5])

        metrics = self.analyzer.calculate_performance_metrics(extreme_returns)

        # Should handle extreme volatility
        self.assertGreater(metrics["volatility_pct"], 50)  # Very high volatility
        self.assertLess(metrics["max_drawdown_pct"], -40)  # Significant drawdown

        # Sharpe ratio should be calculable (might be negative due to high volatility)
        self.assertIsNotNone(metrics["sharpe_ratio"])
        self.assertTrue(np.isfinite(metrics["sharpe_ratio"]))

    def test_calculate_performance_metrics_very_small_returns(self):
        """Test performance metrics with very small returns (precision issues)."""
        # Create very small returns (0.0001%)
        tiny_returns = pd.Series([0.000001, -0.0000005, 0.0000015, -0.0000002, 0.0000012])

        metrics = self.analyzer.calculate_performance_metrics(tiny_returns)

        # Should handle tiny returns without precision issues
        self.assertIsNotNone(metrics["total_return_pct"])
        self.assertIsNotNone(metrics["volatility_pct"])
        self.assertIsNotNone(metrics["sharpe_ratio"])

        # All values should be finite
        for key, value in metrics.items():
            if value is not None:
                self.assertTrue(np.isfinite(value), f"{key} should be finite, got {value}")

    def test_benchmark_comparison_mismatched_dates(self):
        """Test benchmark comparison with mismatched date ranges."""
        # Portfolio returns for 5 days
        portfolio_returns = pd.Series([0.01, -0.005, 0.015, -0.002, 0.012])
        portfolio_returns.index = pd.date_range("2023-01-01", periods=5, freq="D")

        # Benchmark returns for different 5 days (offset)
        benchmark_returns = pd.Series([0.008, -0.003, 0.012, 0.001, 0.010])
        benchmark_returns.index = pd.date_range("2023-01-03", periods=5, freq="D")

        metrics = self.analyzer.calculate_performance_metrics(portfolio_returns, benchmark_returns)

        # Should align dates and calculate metrics for overlapping period
        self.assertIn("beta", metrics)
        self.assertIn("alpha", metrics)
        self.assertIn("excess_return_pct", metrics)

        # Beta should be calculable for the overlapping period
        self.assertIsNotNone(metrics["beta"])
        self.assertTrue(np.isfinite(metrics["beta"]))

    def test_benchmark_comparison_no_overlap(self):
        """Test benchmark comparison with no overlapping dates."""
        # Portfolio returns
        portfolio_returns = pd.Series([0.01, -0.005, 0.015])
        portfolio_returns.index = pd.date_range("2023-01-01", periods=3, freq="D")

        # Benchmark returns with no overlap
        benchmark_returns = pd.Series([0.008, -0.003, 0.012])
        benchmark_returns.index = pd.date_range("2023-02-01", periods=3, freq="D")

        metrics = self.analyzer.calculate_performance_metrics(portfolio_returns, benchmark_returns)

        # Should still calculate basic metrics, but benchmark metrics might be None or default
        self.assertIn("total_return_pct", metrics)
        self.assertIn("volatility_pct", metrics)

        # Benchmark-related metrics should handle no overlap gracefully
        if "beta" in metrics:
            # If beta is calculated, it should be finite or None
            beta = metrics["beta"]
            self.assertTrue(beta is None or np.isfinite(beta))

    def test_calculate_returns_single_value(self):
        """Test returns calculation with single data point."""
        single_value_data = pd.DataFrame({"value": [10000]}, index=pd.date_range("2023-01-01", periods=1, freq="D"))

        returns = self.analyzer.calculate_returns(single_value_data)

        # Should return empty DataFrame (no returns can be calculated)
        self.assertTrue(returns.empty)

    def test_calculate_returns_identical_values(self):
        """Test returns calculation with identical values (no change)."""
        identical_data = pd.DataFrame(
            {"value": [10000, 10000, 10000, 10000, 10000]},
            index=pd.date_range("2023-01-01", periods=5, freq="D"),
        )

        returns = self.analyzer.calculate_returns(identical_data)

        # Should return all zero returns
        self.assertFalse(returns.empty)
        self.assertEqual(len(returns), 4)  # 4 returns from 5 values

        # All returns should be zero
        for return_value in returns.iloc[:, 0]:
            self.assertEqual(return_value, 0.0)

    def test_performance_metrics_with_negative_prices(self):
        """Test performance metrics when prices go negative (edge case)."""
        # This is an unusual scenario but could happen with certain instruments
        # Create returns that would result in negative cumulative values
        extreme_negative_returns = pd.Series([-0.9, -0.8, -0.7, 0.5, 0.3])

        metrics = self.analyzer.calculate_performance_metrics(extreme_negative_returns)

        # Should handle extreme negative returns
        self.assertIn("total_return_pct", metrics)
        self.assertIn("max_drawdown_pct", metrics)

        # Max drawdown should be very negative
        self.assertLess(metrics["max_drawdown_pct"], -90)

        # Total return should be very negative
        self.assertLess(metrics["total_return_pct"], -90)


class TestEdgeCasesFormatter(unittest.TestCase):
    """Test edge cases for ComprehensivePerformanceFormatter."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = ComprehensivePerformanceFormatter()

    def test_format_percentage_extreme_values(self):
        """Test percentage formatting with extreme values."""
        # Test very large positive value
        result = self.formatter.format_percentage(999999.999, 1)
        self.assertEqual(result, "1000000.0%")

        # Test very large negative value
        result = self.formatter.format_percentage(-999999.999, 1)
        self.assertEqual(result, "-1000000.0%")

        # Test very small positive value
        result = self.formatter.format_percentage(0.0001, 4)
        self.assertEqual(result, "0.0001%")

        # Test very small negative value
        result = self.formatter.format_percentage(-0.0001, 4)
        self.assertEqual(result, "-0.0001%")

    def test_format_ratio_extreme_values(self):
        """Test ratio formatting with extreme values."""
        # Test very large ratio
        result = self.formatter.format_ratio(1000000.123, 2)
        self.assertEqual(result, "1000000.12")

        # Test very small ratio
        result = self.formatter.format_ratio(0.000001, 6)
        self.assertEqual(result, "0.000001")

        # Test negative ratio
        result = self.formatter.format_ratio(-1000.567, 1)
        self.assertEqual(result, "-1000.6")

    def test_create_tables_with_empty_metrics(self):
        """Test table creation with empty or None metrics."""
        empty_metrics = {}

        # Should handle empty metrics gracefully
        table = self.formatter.create_portfolio_summary_table(empty_metrics, "Empty Portfolio")
        self.assertIsNotNone(table)

        # Table should have at least the metric column
        self.assertGreaterEqual(len(table.columns), 1)

    def test_create_tables_with_partial_metrics(self):
        """Test table creation with partial/incomplete metrics."""
        partial_metrics = {
            "1M": {
                "total_return_pct": 5.0,
                # Missing other metrics
            },
            "3M": {
                "volatility_pct": 15.0,
                "sharpe_ratio": 1.2,
                # Missing other metrics
            },
        }

        # Should handle partial metrics gracefully
        table = self.formatter.create_portfolio_summary_table(partial_metrics, "Partial Portfolio")
        self.assertIsNotNone(table)

        # Should have columns for available timeframes
        self.assertGreaterEqual(len(table.columns), 3)  # Metric + 1M + 3M

    def test_create_tables_with_none_values(self):
        """Test table creation with None values in metrics."""
        metrics_with_none = {
            "1M": {
                "total_return_pct": None,
                "annualized_return_pct": 10.0,
                "volatility_pct": None,
                "sharpe_ratio": 1.5,
                "max_drawdown_pct": -5.0,
            }
        }

        # Should handle None values gracefully
        table = self.formatter.create_portfolio_summary_table(metrics_with_none, "None Portfolio")
        self.assertIsNotNone(table)

    def test_get_performance_color_edge_cases(self):
        """Test performance color with edge cases."""
        # Test exactly zero
        color = self.formatter.get_performance_color(0.0)
        self.assertEqual(color, "green")

        # Test very small positive
        color = self.formatter.get_performance_color(0.0001)
        self.assertEqual(color, "green")

        # Test very small negative
        color = self.formatter.get_performance_color(-0.0001)
        self.assertEqual(color, "red")

        # Test infinity
        color = self.formatter.get_performance_color(float("inf"))
        self.assertEqual(color, "green")

        # Test negative infinity
        color = self.formatter.get_performance_color(float("-inf"))
        self.assertEqual(color, "red")

        # Test NaN - NaN comparisons always return False, so it's treated as negative
        color = self.formatter.get_performance_color(float("nan"))
        self.assertEqual(color, "red")  # NaN comparisons return False, so treated as negative


class TestDataValidationAndSanitization(unittest.TestCase):
    """Test data validation and sanitization in calculations."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock database connection pool
        mock_pool = Mock()
        mock_connection = Mock()
        mock_pool.get_connection.return_value = mock_connection
        mock_pool.get_connection_context.return_value.__enter__.return_value = mock_connection
        mock_pool.get_connection_context.return_value.__exit__.return_value = None

        # Create analyzer with mocked pool - MultiTimeframeAnalyzer only takes pool parameter
        self.analyzer = MultiTimeframeAnalyzer(pool=mock_pool)

    def test_returns_calculation_with_mixed_data_types(self):
        """Test returns calculation with mixed data types."""
        # Create DataFrame with mixed numeric types (all convertible to float)
        mixed_data = pd.DataFrame(
            {
                "value": [
                    10000.0,
                    10100.5,
                    float(Decimal("10050.25")),
                    10200.0,
                    10150.75,
                ]
            },
            index=pd.date_range("2023-01-01", periods=5, freq="D"),
        )

        returns = self.analyzer.calculate_returns(mixed_data)

        # Should handle mixed types and convert to float
        self.assertFalse(returns.empty)
        self.assertEqual(len(returns), 4)

        # All returns should be float type
        for return_value in returns.iloc[:, 0]:
            self.assertIsInstance(return_value, (float, np.floating))

    def test_performance_metrics_input_validation(self):
        """Test that performance metrics handle invalid input gracefully."""
        # Test with string data (should fail gracefully)
        try:
            invalid_returns = pd.Series(["a", "b", "c"])
            metrics = self.analyzer.calculate_performance_metrics(invalid_returns)
            # If it doesn't raise an exception, metrics should be empty or have None values
            if metrics:
                for key, value in metrics.items():
                    self.assertTrue(value is None or np.isnan(value) or np.isinf(value))
        except (TypeError, ValueError):
            # It's acceptable for this to raise an exception
            pass

    def test_timeframe_boundary_conditions(self):
        """Test timeframe calculations at boundary conditions."""
        # Test with exactly the timeframe boundary
        for timeframe, days in self.analyzer.TIMEFRAMES.items():
            # Create returns for exactly the timeframe period
            returns = pd.Series([0.001] * days)  # Small positive returns

            metrics = self.analyzer.calculate_performance_metrics(returns)

            # Should calculate metrics for exact timeframe
            self.assertIn("total_return_pct", metrics)
            self.assertIn("annualized_return_pct", metrics)

            # Annualized return should be reasonable
            self.assertIsNotNone(metrics["annualized_return_pct"])
            self.assertTrue(np.isfinite(metrics["annualized_return_pct"]))


if __name__ == "__main__":
    # Run edge case tests
    unittest.main(verbosity=2)
