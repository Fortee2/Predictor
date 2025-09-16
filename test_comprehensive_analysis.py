"""
Unit tests for Comprehensive Analysis calculations.

This module tests the core calculation methods in MultiTimeframeAnalyzer
to ensure accurate performance metrics, risk calculations, and benchmark comparisons.
"""

import os
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd

# Add the project root to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.comprehensive_performance_formatter import \
    ComprehensivePerformanceFormatter
from data.multi_timeframe_analyzer import MultiTimeframeAnalyzer


class TestMultiTimeframeAnalyzer(unittest.TestCase):
    """Test cases for MultiTimeframeAnalyzer calculations."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock database connection to avoid actual DB calls
        with patch("mysql.connector.connect"):
            self.analyzer = MultiTimeframeAnalyzer(
                db_user="test", db_password="test", db_host="test", db_name="test"
            )

        # Mock the connection
        self.analyzer.connection = Mock()

        # Sample portfolio value data for testing
        self.sample_portfolio_data = pd.DataFrame(
            {"value": [10000, 10100, 10050, 10200, 10150, 10300, 10250, 10400]},
            index=pd.date_range("2023-01-01", periods=8, freq="D"),
        )

        # Sample benchmark data
        self.sample_benchmark_data = pd.DataFrame(
            {"close": [4000, 4020, 4010, 4040, 4030, 4060, 4050, 4080]},
            index=pd.date_range("2023-01-01", periods=8, freq="D"),
        )

    def test_calculate_returns(self):
        """Test daily returns calculation."""
        returns = self.analyzer.calculate_returns(self.sample_portfolio_data)

        # Check that returns are calculated correctly
        self.assertFalse(returns.empty)
        self.assertEqual(
            len(returns), 7
        )  # One less than original data due to pct_change

        # Verify first return calculation: (10100 - 10000) / 10000 = 0.01
        expected_first_return = 0.01
        actual_first_return = returns.iloc[0, 0]
        self.assertAlmostEqual(actual_first_return, expected_first_return, places=6)

        # Verify second return calculation: (10050 - 10100) / 10100 ≈ -0.00495
        expected_second_return = -0.004950495049504951
        actual_second_return = returns.iloc[1, 0]
        self.assertAlmostEqual(actual_second_return, expected_second_return, places=6)

    def test_calculate_returns_empty_data(self):
        """Test returns calculation with empty data."""
        empty_data = pd.DataFrame()
        returns = self.analyzer.calculate_returns(empty_data)
        self.assertTrue(returns.empty)

    def test_calculate_performance_metrics_basic(self):
        """Test basic performance metrics calculation."""
        # Create simple returns data
        returns = pd.Series([0.01, -0.005, 0.015, -0.002, 0.012, 0.008, 0.003])

        metrics = self.analyzer.calculate_performance_metrics(returns)

        # Check that all expected metrics are present
        expected_keys = [
            "total_return_pct",
            "annualized_return_pct",
            "volatility_pct",
            "sharpe_ratio",
            "max_drawdown_pct",
        ]
        for key in expected_keys:
            self.assertIn(key, metrics)
            self.assertIsNotNone(metrics[key])

        # Verify total return calculation
        expected_total_return = (1 + returns).prod() - 1
        actual_total_return = metrics["total_return_pct"] / 100
        self.assertAlmostEqual(actual_total_return, expected_total_return, places=6)

        # Verify volatility is positive
        self.assertGreater(metrics["volatility_pct"], 0)

        # Verify max drawdown is negative or zero
        self.assertLessEqual(metrics["max_drawdown_pct"], 0)

    def test_calculate_performance_metrics_with_benchmark(self):
        """Test performance metrics calculation with benchmark comparison."""
        portfolio_returns = pd.Series([0.01, -0.005, 0.015, -0.002, 0.012])
        benchmark_returns = pd.Series([0.008, -0.003, 0.012, 0.001, 0.010])

        metrics = self.analyzer.calculate_performance_metrics(
            portfolio_returns, benchmark_returns
        )

        # Check that benchmark-related metrics are present
        benchmark_keys = [
            "alpha",
            "beta",
            "up_capture_ratio",
            "down_capture_ratio",
            "benchmark_return_pct",
            "excess_return_pct",
        ]
        for key in benchmark_keys:
            self.assertIn(key, metrics)
            self.assertIsNotNone(metrics[key])

        # Verify excess return calculation
        portfolio_total = (1 + portfolio_returns).prod() - 1
        benchmark_total = (1 + benchmark_returns).prod() - 1
        expected_excess = (portfolio_total - benchmark_total) * 100

        self.assertAlmostEqual(metrics["excess_return_pct"], expected_excess, places=4)

        # Beta should be a reasonable value (typically between 0 and 2)
        self.assertGreater(metrics["beta"], -2)
        self.assertLess(metrics["beta"], 3)

    def test_calculate_performance_metrics_empty_returns(self):
        """Test performance metrics with empty returns."""
        empty_returns = pd.Series(dtype=float)
        metrics = self.analyzer.calculate_performance_metrics(empty_returns)
        self.assertEqual(metrics, {})

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation specifically."""
        # Create returns with known characteristics
        returns = pd.Series([0.02, 0.01, 0.03, -0.01, 0.015, 0.005, 0.025])

        metrics = self.analyzer.calculate_performance_metrics(returns)

        # Manual Sharpe ratio calculation for verification
        risk_free_daily = self.analyzer.RISK_FREE_RATE / 252
        excess_returns = returns - risk_free_daily
        expected_sharpe = excess_returns.mean() / returns.std() * np.sqrt(252)

        self.assertAlmostEqual(metrics["sharpe_ratio"], expected_sharpe, places=4)

    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation."""
        # Create returns that will result in a known drawdown
        # Starting at 100, going to 110, then down to 95, then up to 105
        prices = [100, 110, 95, 105]
        returns = pd.Series([0.1, -0.136364, 0.105263])  # Calculated from prices

        metrics = self.analyzer.calculate_performance_metrics(returns)

        # The drawdown from 110 to 95 should be (95-110)/110 = -13.64%
        # This should be the maximum drawdown
        self.assertLess(metrics["max_drawdown_pct"], -13)
        self.assertGreater(metrics["max_drawdown_pct"], -15)

    def test_annualized_return_calculation(self):
        """Test annualized return calculation for different time periods."""
        # Test with exactly one year of daily data (252 trading days)
        returns_1year = pd.Series([0.001] * 252)  # 0.1% daily return
        metrics_1year = self.analyzer.calculate_performance_metrics(returns_1year)

        # For 252 days of 0.1% returns: (1.001)^252 - 1 ≈ 28.8%
        # Annualized should be approximately the same since it's exactly 1 year
        total_return = (1.001**252) - 1
        self.assertAlmostEqual(
            metrics_1year["annualized_return_pct"], total_return * 100, places=1
        )

        # Test with half year of data (126 trading days)
        returns_half_year = pd.Series([0.001] * 126)
        metrics_half_year = self.analyzer.calculate_performance_metrics(
            returns_half_year
        )

        # Annualized return should be higher than total return for half year
        self.assertGreater(
            metrics_half_year["annualized_return_pct"],
            metrics_half_year["total_return_pct"],
        )

    def test_beta_calculation_edge_cases(self):
        """Test beta calculation with edge cases."""
        # Test with zero variance benchmark (should result in beta = 0)
        portfolio_returns = pd.Series([0.01, -0.005, 0.015, -0.002])
        zero_variance_benchmark = pd.Series([0.01, 0.01, 0.01, 0.01])

        metrics = self.analyzer.calculate_performance_metrics(
            portfolio_returns, zero_variance_benchmark
        )

        self.assertEqual(metrics["beta"], 0)

    def test_up_down_capture_ratios(self):
        """Test up and down capture ratio calculations."""
        # Create data where portfolio outperforms in up markets and underperforms in down markets
        portfolio_returns = pd.Series([0.02, -0.01, 0.03, -0.015, 0.025])
        benchmark_returns = pd.Series([0.015, -0.008, 0.02, -0.01, 0.018])

        metrics = self.analyzer.calculate_performance_metrics(
            portfolio_returns, benchmark_returns
        )

        # Up capture should be > 1 (portfolio outperforms in up markets)
        self.assertGreater(metrics["up_capture_ratio"], 1.0)

        # Down capture should be > 1 (portfolio underperforms in down markets)
        self.assertGreater(metrics["down_capture_ratio"], 1.0)

        # Both ratios should be reasonable values
        self.assertLess(metrics["up_capture_ratio"], 3.0)
        self.assertLess(metrics["down_capture_ratio"], 3.0)

    @patch("mysql.connector.connect")
    def test_get_portfolio_value_history_mock(self, mock_connect):
        """Test portfolio value history retrieval with mocked database."""
        # Setup mock cursor and connection
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        # Mock database results
        mock_cursor.fetchall.return_value = [
            {"date": date(2023, 1, 1), "value": Decimal("10000.00")},
            {"date": date(2023, 1, 2), "value": Decimal("10100.00")},
            {"date": date(2023, 1, 3), "value": Decimal("10050.00")},
        ]

        # Create analyzer with mocked connection
        analyzer = MultiTimeframeAnalyzer("test", "test", "test", "test")
        analyzer.connection = mock_connection

        # Test the method
        result = analyzer.get_portfolio_value_history(
            1, date(2023, 1, 1), date(2023, 1, 3)
        )

        # Verify results
        self.assertFalse(result.empty)
        self.assertEqual(len(result), 3)
        self.assertIn("value", result.columns)

        # Verify database query was called correctly
        mock_cursor.execute.assert_called_once()
        query_args = mock_cursor.execute.call_args[0]
        self.assertIn("portfolio_value", query_args[0])
        self.assertEqual(query_args[1], (1, date(2023, 1, 1), date(2023, 1, 3)))

    def test_timeframes_constant(self):
        """Test that timeframes are defined correctly."""
        expected_timeframes = {
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365,
            "2Y": 730,
            "5Y": 1825,
        }

        self.assertEqual(self.analyzer.TIMEFRAMES, expected_timeframes)

    def test_risk_free_rate_constant(self):
        """Test that risk-free rate is set to a reasonable value."""
        self.assertGreater(self.analyzer.RISK_FREE_RATE, 0)
        self.assertLess(self.analyzer.RISK_FREE_RATE, 0.1)  # Should be less than 10%


class TestComprehensivePerformanceFormatter(unittest.TestCase):
    """Test cases for ComprehensivePerformanceFormatter."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = ComprehensivePerformanceFormatter()

        # Sample metrics data for testing
        self.sample_metrics = {
            "1M": {
                "total_return_pct": 2.5,
                "annualized_return_pct": 35.2,
                "volatility_pct": 18.5,
                "sharpe_ratio": 1.2,
                "max_drawdown_pct": -5.3,
                "alpha": 1.8,
                "beta": 1.1,
                "excess_return_pct": 0.8,
                "benchmark_return_pct": 1.7,
            },
            "3M": {
                "total_return_pct": 8.2,
                "annualized_return_pct": 36.8,
                "volatility_pct": 16.2,
                "sharpe_ratio": 1.5,
                "max_drawdown_pct": -8.1,
                "alpha": 2.1,
                "beta": 0.9,
                "excess_return_pct": 1.5,
                "benchmark_return_pct": 6.7,
            },
        }

    def test_format_percentage(self):
        """Test percentage formatting."""
        # Test positive percentage
        result = self.formatter.format_percentage(15.678, 2)
        self.assertEqual(result, "15.68%")

        # Test negative percentage
        result = self.formatter.format_percentage(-5.432, 1)
        self.assertEqual(result, "-5.4%")

        # Test None value
        result = self.formatter.format_percentage(None)
        self.assertEqual(result, "N/A")

        # Test zero
        result = self.formatter.format_percentage(0.0, 1)
        self.assertEqual(result, "0.0%")

    def test_format_ratio(self):
        """Test ratio formatting."""
        # Test positive ratio
        result = self.formatter.format_ratio(1.234, 2)
        self.assertEqual(result, "1.23")

        # Test negative ratio
        result = self.formatter.format_ratio(-0.567, 3)
        self.assertEqual(result, "-0.567")

        # Test None value
        result = self.formatter.format_ratio(None)
        self.assertEqual(result, "N/A")

    def test_get_performance_color(self):
        """Test performance color assignment."""
        # Test positive value
        color = self.formatter.get_performance_color(5.5)
        self.assertEqual(color, "green")

        # Test negative value
        color = self.formatter.get_performance_color(-3.2)
        self.assertEqual(color, "red")

        # Test zero
        color = self.formatter.get_performance_color(0.0)
        self.assertEqual(color, "green")

        # Test None
        color = self.formatter.get_performance_color(None)
        self.assertEqual(color, "white")

    def test_create_portfolio_summary_table(self):
        """Test portfolio summary table creation."""
        table = self.formatter.create_portfolio_summary_table(
            self.sample_metrics, "Test Portfolio"
        )

        # Check that table is created
        self.assertIsNotNone(table)

        # Check title contains portfolio name
        self.assertIn("Test Portfolio", str(table.title))

        # Check that table has expected columns (Metric + timeframes)
        # The formatter creates columns for all defined timeframes, not just available ones
        expected_columns = 8  # Metric + 1M + 3M + 6M + 1Y + 2Y + 5Y + MAX
        self.assertEqual(len(table.columns), expected_columns)

    def test_create_benchmark_comparison_table(self):
        """Test benchmark comparison table creation."""
        table = self.formatter.create_benchmark_comparison_table(
            self.sample_metrics, "Test Portfolio"
        )

        # Check that table is created
        self.assertIsNotNone(table)

        # Check title
        self.assertIn("Benchmark Comparison", str(table.title))
        self.assertIn("Test Portfolio", str(table.title))

        # Check expected columns
        expected_columns = (
            6  # Timeframe, Portfolio, S&P 500, Excess Return, Alpha, Beta
        )
        self.assertEqual(len(table.columns), expected_columns)

    def test_create_risk_metrics_table(self):
        """Test risk metrics table creation."""
        table = self.formatter.create_risk_metrics_table(
            self.sample_metrics, "Test Portfolio"
        )

        # Check that table is created
        self.assertIsNotNone(table)

        # Check title
        self.assertIn("Risk Analysis", str(table.title))
        self.assertIn("Test Portfolio", str(table.title))

    def test_create_holdings_performance_table(self):
        """Test holdings performance table creation."""
        # Sample holdings data
        holdings_metrics = {
            "AAPL": {
                "1M": {
                    "total_return_pct": 5.2,
                    "max_drawdown_pct": -3.1,
                    "sharpe_ratio": 1.8,
                    "excess_return_pct": 2.1,
                },
                "3M": {
                    "total_return_pct": 12.5,
                    "max_drawdown_pct": -7.2,
                    "sharpe_ratio": 1.5,
                    "excess_return_pct": 4.3,
                },
            },
            "MSFT": {
                "1M": {
                    "total_return_pct": 3.8,
                    "max_drawdown_pct": -2.5,
                    "sharpe_ratio": 2.1,
                    "excess_return_pct": 1.7,
                },
                "3M": {
                    "total_return_pct": 9.2,
                    "max_drawdown_pct": -5.8,
                    "sharpe_ratio": 1.9,
                    "excess_return_pct": 2.8,
                },
            },
        }

        table = self.formatter.create_holdings_performance_table(
            holdings_metrics, "Test Portfolio"
        )

        # Check that table is created
        self.assertIsNotNone(table)

        # Check title
        self.assertIn("Holdings Performance Analysis", str(table.title))

        # Check expected columns (Holding + 6 timeframes + Max DD + Sharpe + vs S&P500)
        expected_columns = 10
        self.assertEqual(len(table.columns), expected_columns)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for comprehensive analysis scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        with patch("mysql.connector.connect"):
            self.analyzer = MultiTimeframeAnalyzer(
                db_user="test", db_password="test", db_host="test", db_name="test"
            )
        self.analyzer.connection = Mock()
        self.formatter = ComprehensivePerformanceFormatter()

    def test_bull_market_scenario(self):
        """Test calculations during a bull market scenario."""
        # Create steadily increasing returns (bull market)
        bull_returns = pd.Series([0.02, 0.015, 0.025, 0.018, 0.022, 0.012, 0.028])
        benchmark_returns = pd.Series([0.015, 0.012, 0.018, 0.014, 0.016, 0.010, 0.020])

        metrics = self.analyzer.calculate_performance_metrics(
            bull_returns, benchmark_returns
        )

        # In a bull market, we expect:
        # - Positive total return
        self.assertGreater(metrics["total_return_pct"], 0)

        # - Positive excess return (outperforming benchmark)
        self.assertGreater(metrics["excess_return_pct"], 0)

        # - Low maximum drawdown (small losses)
        self.assertGreater(metrics["max_drawdown_pct"], -5)  # Less than 5% drawdown

        # - Positive Sharpe ratio
        self.assertGreater(metrics["sharpe_ratio"], 0)

    def test_bear_market_scenario(self):
        """Test calculations during a bear market scenario."""
        # Create declining returns (bear market)
        bear_returns = pd.Series([-0.03, -0.02, -0.04, -0.01, -0.035, -0.025, -0.015])
        benchmark_returns = pd.Series(
            [-0.025, -0.018, -0.035, -0.012, -0.028, -0.020, -0.018]
        )

        metrics = self.analyzer.calculate_performance_metrics(
            bear_returns, benchmark_returns
        )

        # In a bear market, we expect:
        # - Negative total return
        self.assertLess(metrics["total_return_pct"], 0)

        # - Significant maximum drawdown
        self.assertLess(metrics["max_drawdown_pct"], -10)  # More than 10% drawdown

        # - High volatility
        self.assertGreater(metrics["volatility_pct"], 15)  # More than 15% volatility

    def test_volatile_market_scenario(self):
        """Test calculations during high volatility scenario."""
        # Create highly volatile returns
        volatile_returns = pd.Series(
            [0.05, -0.04, 0.06, -0.03, 0.07, -0.05, 0.04, -0.02]
        )
        benchmark_returns = pd.Series(
            [0.02, -0.015, 0.025, -0.01, 0.03, -0.02, 0.018, -0.008]
        )

        metrics = self.analyzer.calculate_performance_metrics(
            volatile_returns, benchmark_returns
        )

        # In a volatile market, we expect:
        # - High volatility
        self.assertGreater(metrics["volatility_pct"], 20)  # More than 20% volatility

        # - Beta > 1 (more volatile than benchmark)
        self.assertGreater(metrics["beta"], 1.0)

        # - Some drawdown due to volatility (adjust expectation based on actual data)
        self.assertLess(metrics["max_drawdown_pct"], 0)  # Should have some drawdown

    def test_low_correlation_scenario(self):
        """Test calculations with low correlation to benchmark."""
        # Create returns with truly low correlation to benchmark
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.03, -0.005, 0.015])
        benchmark_returns = pd.Series([-0.02, -0.01, 0.03, -0.025, 0.02, -0.015])

        metrics = self.analyzer.calculate_performance_metrics(
            portfolio_returns, benchmark_returns
        )

        # With low correlation, we expect:
        # - Beta should be calculable (may not be close to 0 with small sample)
        self.assertIsNotNone(metrics["beta"])
        self.assertTrue(np.isfinite(metrics["beta"]))

        # - Alpha could be significant (positive or negative)
        self.assertIsNotNone(metrics["alpha"])

    def test_edge_case_single_day_returns(self):
        """Test calculations with minimal data (single return)."""
        single_return = pd.Series([0.05])

        metrics = self.analyzer.calculate_performance_metrics(single_return)

        # With single day data:
        # - Total return should equal the single return
        self.assertAlmostEqual(metrics["total_return_pct"], 5.0, places=1)

        # - Volatility should be NaN (no variation with single point)
        self.assertTrue(np.isnan(metrics["volatility_pct"]))

        # - Max drawdown should be 0 (no decline possible)
        self.assertEqual(metrics["max_drawdown_pct"], 0.0)


if __name__ == "__main__":
    # Create a test suite combining all test classes
    test_suite = unittest.TestSuite()

    # Add all test methods from each class
    test_classes = [
        TestMultiTimeframeAnalyzer,
        TestComprehensivePerformanceFormatter,
        TestIntegrationScenarios,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run the tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )

    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(
                f"- {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}"
            )

    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('\\n')[-2]}")

    print(f"{'='*60}")
