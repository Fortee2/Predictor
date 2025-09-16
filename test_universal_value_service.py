#!/usr/bin/env python3
"""
Test script for the Universal Portfolio Value Service

This script tests the new universal value calculation function to ensure
it provides consistent results and resolves the discrepancy between
View Portfolio and View Performance calculations.
"""

import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.portfolio_value_service import PortfolioValueService


def test_universal_value_service():
    """Test the universal portfolio value service."""

    print("Testing Universal Portfolio Value Service")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    # Get database credentials
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")

    if not all([db_user, db_password, db_host, db_name]):
        print("Error: Missing database credentials in environment variables")
        return False

    try:
        # Initialize services
        value_service = PortfolioValueService(db_user, db_password, db_host, db_name)
        portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        transactions_dao = PortfolioTransactionsDAO(
            db_user, db_password, db_host, db_name
        )

        portfolio_dao.open_connection()
        transactions_dao.open_connection()

        # Get the first available portfolio for testing
        portfolios = portfolio_dao.read_portfolio()
        if not portfolios:
            print("No portfolios found for testing")
            return False

        portfolio_id = portfolios[0]["id"]
        portfolio_name = portfolios[0]["name"]

        print(f"Testing with Portfolio: {portfolio_name} (ID: {portfolio_id})")
        print("-" * 50)

        # Test 1: Current portfolio value (like View Portfolio)
        print("Test 1: Current Portfolio Value (View Portfolio style)")
        current_result = value_service.calculate_portfolio_value(
            portfolio_id,
            include_cash=True,
            include_dividends=False,  # View Portfolio doesn't include dividends
            use_current_prices=True,
        )

        print(f"Stock Value: ${current_result['stock_value']:,.2f}")
        print(f"Cash Balance: ${current_result['cash_balance']:,.2f}")
        print(f"Total Value: ${current_result['total_value']:,.2f}")
        print(f"Positions: {len(current_result['positions'])}")
        print()

        # Test 2: Performance view style (with dividends)
        print("Test 2: Performance Portfolio Value (View Performance style)")
        performance_result = value_service.calculate_portfolio_value(
            portfolio_id,
            include_cash=True,
            include_dividends=True,  # View Performance includes dividends
            use_current_prices=True,
        )

        print(f"Stock Value: ${performance_result['stock_value']:,.2f}")
        print(f"Cash Balance: ${performance_result['cash_balance']:,.2f}")
        print(f"Dividend Value: ${performance_result['dividend_value']:,.2f}")
        print(f"Total Value: ${performance_result['total_value']:,.2f}")
        print(f"Positions: {len(performance_result['positions'])}")
        print()

        # Test 3: Historical value (30 days ago)
        print("Test 3: Historical Portfolio Value (30 days ago)")
        historical_date = date.today() - timedelta(days=30)
        historical_result = value_service.calculate_portfolio_value(
            portfolio_id,
            calculation_date=historical_date,
            include_cash=True,
            include_dividends=True,
            use_current_prices=False,
        )

        print(f"Date: {historical_date}")
        print(f"Stock Value: ${historical_result['stock_value']:,.2f}")
        print(f"Cash Balance: ${historical_result['cash_balance']:,.2f}")
        print(f"Dividend Value: ${historical_result['dividend_value']:,.2f}")
        print(f"Total Value: ${historical_result['total_value']:,.2f}")
        print()

        # Test 4: Compare old vs new method for current positions
        print("Test 4: Comparison with Legacy Method")
        legacy_positions = transactions_dao.get_current_positions(portfolio_id)
        universal_positions = current_result["positions"]

        print(f"Legacy method positions: {len(legacy_positions)}")
        print(f"Universal method positions: {len(universal_positions)}")

        # Compare position details
        if legacy_positions and universal_positions:
            print("\nPosition Comparison:")
            for ticker_id, legacy_pos in legacy_positions.items():
                if ticker_id in universal_positions:
                    universal_pos = universal_positions[ticker_id]
                    print(f"  {legacy_pos['symbol']}:")
                    print(f"    Legacy shares: {legacy_pos['shares']:.4f}")
                    print(f"    Universal shares: {universal_pos['shares']:.4f}")
                    print(f"    Legacy avg price: ${legacy_pos['avg_price']:.2f}")
                    print(f"    Universal avg price: ${universal_pos['avg_price']:.2f}")

                    # Check for discrepancies
                    shares_match = (
                        abs(legacy_pos["shares"] - universal_pos["shares"]) < 0.0001
                    )
                    price_match = (
                        abs(legacy_pos["avg_price"] - universal_pos["avg_price"]) < 0.01
                    )

                    if not shares_match or not price_match:
                        print(f"    ⚠️  DISCREPANCY DETECTED!")
                    else:
                        print(f"    ✅ Match")

        # Test 5: Summary comparison
        print("\nTest 5: Summary Comparison")
        print(
            f"Difference with dividends: ${performance_result['total_value'] - current_result['total_value']:,.2f}"
        )
        print(
            f"This difference should equal dividend value: ${performance_result['dividend_value']:,.2f}"
        )

        dividend_diff_matches = (
            abs(
                (performance_result["total_value"] - current_result["total_value"])
                - performance_result["dividend_value"]
            )
            < 0.01
        )

        if dividend_diff_matches:
            print("✅ Dividend calculation is consistent")
        else:
            print("⚠️  Dividend calculation discrepancy detected")

        print("\n" + "=" * 50)
        print("Universal Value Service Test Complete")

        # Clean up
        value_service.close_connection()
        portfolio_dao.close_connection()
        transactions_dao.close_connection()

        return True

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_universal_value_service()
    sys.exit(0 if success else 1)
