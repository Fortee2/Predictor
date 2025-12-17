#!/usr/bin/env python3
"""
Test script for get_transaction_history_by_date LLM tool

This script tests the newly implemented get_transaction_history_by_date
tool through the LLM Portfolio Analyzer.
"""

import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from data.llm_portfolio_analyzer import LLMPortfolioAnalyzer
from data.utility import DatabaseConnectionPool

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_transaction_history_by_date():
    """Test the get_transaction_history_by_date tool"""

    # Load environment
    load_dotenv()

    # Setup database connection
    db_pool = DatabaseConnectionPool(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
    )

    # Initialize LLM Portfolio Analyzer
    analyzer = LLMPortfolioAnalyzer(pool=db_pool)

    # Test portfolio ID - CHANGE THIS TO YOUR TEST PORTFOLIO ID
    test_portfolio_id = 1

    print("=" * 80)
    print("Testing get_transaction_history_by_date LLM tool")
    print("=" * 80)

    # Test 1: Direct tool execution with specific date range
    print("\n[Test 1] Direct tool execution - Last 30 days")
    print("-" * 80)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    tool_input = {
        "portfolio_id": test_portfolio_id,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }

    result = analyzer._execute_tool("get_transaction_history_by_date", tool_input)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        transactions = result.get("transactions", [])
        print(f"✅ Found {len(transactions)} transactions")
        if transactions:
            print("\nSample transactions:")
            for t in transactions[:5]:  # Show first 5
                print(f"  - {t['transaction_date']}: {t['symbol']} - {t['transaction_type']}")
                if 'shares' in t and t['shares']:
                    print(f"    Shares: {t['shares']}, Price: ${t.get('price', 0):.2f}")
        else:
            print("  No transactions found in this date range")

    # Test 2: Tool execution with no dates (defaults to last 365 days)
    print("\n[Test 2] Direct tool execution - Default range (last 365 days)")
    print("-" * 80)

    tool_input = {
        "portfolio_id": test_portfolio_id
    }

    result = analyzer._execute_tool("get_transaction_history_by_date", tool_input)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        transactions = result.get("transactions", [])
        print(f"✅ Found {len(transactions)} transactions in the last 365 days")

    # Test 3: Test through LLM chat interface
    print("\n[Test 3] Through LLM chat interface")
    print("-" * 80)
    print("Asking LLM: 'Show me all transactions from the last 30 days'")

    # Reset conversation to start fresh
    analyzer.reset_conversation()

    # Note: This will actually call AWS Bedrock, so it requires AWS credentials
    # and will incur API costs. Comment out if you don't want to test this.
    try:
        response = analyzer.chat(
            "Show me all transactions from the last 30 days",
            portfolio_id=test_portfolio_id
        )
        print("\nLLM Response:")
        print(response)
    except Exception as e:
        print(f"⚠️  LLM chat test skipped or failed: {e}")
        print("   (This is expected if AWS credentials are not configured)")

    # Test 4: Specific date range
    print("\n[Test 4] Direct tool execution - Specific date range (2024)")
    print("-" * 80)

    tool_input = {
        "portfolio_id": test_portfolio_id,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }

    result = analyzer._execute_tool("get_transaction_history_by_date", tool_input)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        transactions = result.get("transactions", [])
        print(f"✅ Found {len(transactions)} transactions in 2024")

        # Show transaction type breakdown
        if transactions:
            buy_count = sum(1 for t in transactions if t['transaction_type'] == 'buy')
            sell_count = sum(1 for t in transactions if t['transaction_type'] == 'sell')
            dividend_count = sum(1 for t in transactions if t['transaction_type'] == 'dividend')

            print(f"\nTransaction breakdown:")
            print(f"  - Buys: {buy_count}")
            print(f"  - Sells: {sell_count}")
            print(f"  - Dividends: {dividend_count}")

    print("\n" + "=" * 80)
    print("Testing complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_transaction_history_by_date()