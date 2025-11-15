#!/usr/bin/env python3
"""
Cash Management Test Script

This script provides a quick way to test all cash management functionality
to ensure it's working properly. It can be run after any code changes
to verify that cash management still functions correctly.
"""

import unittest

from dotenv import load_dotenv

# Add proper imports for portfolio functionality
from data.portfolio_dao import PortfolioDAO
from portfolio_cli import PortfolioCLI


class CashManagementTests(unittest.TestCase):
    """Tests for cash management functionality"""

    @classmethod
    def setUpClass(cls):
        """Setup test environment once before all tests"""
        load_dotenv()


        # Initialize DAOs and CLI
        cls.portfolio_dao = PortfolioDAO(
            cls.db_user, cls.db_password, cls.db_host, cls.db_name
        )
        cls.portfolio_dao.open_connection()
        cls.cli = PortfolioCLI()

        # Create a test portfolio for all tests to use
        cls.test_portfolio_id = cls._create_test_portfolio()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests have run"""
        cls._delete_test_portfolio(cls.test_portfolio_id)
        cls.portfolio_dao.close_connection()

    @classmethod
    def _create_test_portfolio(cls):
        """Create a test portfolio and return its ID"""
        cursor = cls.portfolio_dao.connection.cursor()

        # First check if our test portfolio already exists
        query = "SELECT id FROM portfolio WHERE name = 'CashManagementTest'"
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            # If it exists, delete it first to start fresh
            portfolio_id = result[0]
            cls._delete_test_portfolio(portfolio_id)

        # Create a new test portfolio
        portfolio_id = cls.portfolio_dao.create_portfolio(
            "CashManagementTest",
            "Test portfolio for cash management tests",
            1000.00,  # Initial cash balance
        )

        cursor.close()
        return portfolio_id

    @classmethod
    def _delete_test_portfolio(cls, portfolio_id):
        """Delete the test portfolio"""
        # First delete related records
        cursor = cls.portfolio_dao.connection.cursor()

        # Delete cash transaction history
        try:
            query = "DELETE FROM cash_balance_history WHERE portfolio_id = %s"
            cursor.execute(query, (portfolio_id,))
        except Exception:
            pass  # Table might not exist

        # Delete portfolio transactions
        query = "SELECT id FROM portfolio_securities WHERE portfolio_id = %s"
        cursor.execute(query, (portfolio_id,))
        security_ids = [row[0] for row in cursor.fetchall()]

        for security_id in security_ids:
            query = "DELETE FROM portfolio_transactions WHERE security_id = %s"
            cursor.execute(query, (security_id,))

        # Delete portfolio securities
        query = "DELETE FROM portfolio_securities WHERE portfolio_id = %s"
        cursor.execute(query, (portfolio_id,))

        # Delete portfolio itself
        query = "DELETE FROM portfolio WHERE id = %s"
        cursor.execute(query, (portfolio_id,))

        cls.portfolio_dao.connection.commit()
        cursor.close()

    def setUp(self):
        """Setup before each test - reset the cash balance"""
        # Reset cash balance to 1000.00 before each test
        self.portfolio_dao.update_cash_balance(self.test_portfolio_id, 1000.00)

    def test_get_cash_balance(self):
        """Test retrieving cash balance"""
        balance = self.portfolio_dao.get_cash_balance(self.test_portfolio_id)
        self.assertEqual(balance, 1000.0)
        print(f"✅ get_cash_balance test passed. Initial balance: ${balance:.2f}")

    def test_add_cash(self):
        """Test adding cash to portfolio"""
        initial = self.portfolio_dao.get_cash_balance(self.test_portfolio_id)
        amount = 500.0
        new_balance = self.portfolio_dao.add_cash(self.test_portfolio_id, amount)

        # Check if new balance matches expected value
        expected = initial + amount
        self.assertEqual(new_balance, expected)

        # Verify by getting balance again
        current = self.portfolio_dao.get_cash_balance(self.test_portfolio_id)
        self.assertEqual(current, expected)

        print(
            f"✅ add_cash test passed. Added ${amount:.2f}, New balance: ${current:.2f}"
        )

    def test_withdraw_cash(self):
        """Test withdrawing cash from portfolio"""
        initial = self.portfolio_dao.get_cash_balance(self.test_portfolio_id)
        amount = 200.0
        new_balance = self.portfolio_dao.withdraw_cash(self.test_portfolio_id, amount)

        # Check if new balance matches expected value
        expected = initial - amount
        self.assertEqual(new_balance, expected)

        # Verify by getting balance again
        current = self.portfolio_dao.get_cash_balance(self.test_portfolio_id)
        self.assertEqual(current, expected)

        print(
            f"✅ withdraw_cash test passed. Withdrew ${amount:.2f}, New balance: ${current:.2f}"
        )

    def test_log_cash_transaction(self):
        """Test logging a cash transaction"""
        initial = self.portfolio_dao.get_cash_balance(self.test_portfolio_id)
        amount = 150.0

        # Add a cash transaction
        new_balance = self.portfolio_dao.log_cash_transaction(
            self.test_portfolio_id, amount, "deposit", "Test deposit transaction"
        )

        # Check if new balance matches expected value
        expected = initial + amount
        self.assertEqual(new_balance, expected)

        # Get transaction history and check if our transaction is recorded
        history = self.portfolio_dao.get_cash_transaction_history(
            self.test_portfolio_id
        )

        # Latest transaction should be our test deposit
        if history:
            latest = history[0]
            self.assertEqual(float(latest["amount"]), amount)
            self.assertEqual(latest["transaction_type"], "deposit")
            self.assertEqual(latest["description"], "Test deposit transaction")
            self.assertEqual(float(latest["balance_after"]), expected)
            print(
                "✅ log_cash_transaction test passed. Transaction logged successfully."
            )
        else:
            self.fail("No transaction history found")

    def test_negative_scenarios(self):
        """Test negative scenarios for cash management"""

        # Test withdrawing more than available balance
        initial = self.portfolio_dao.get_cash_balance(self.test_portfolio_id)
        excessive_amount = initial + 1000.0  # More than we have

        # Withdraw should give a warning but still allow the withdrawal
        self.portfolio_dao.withdraw_cash(
            self.test_portfolio_id, excessive_amount
        )

        # If the implementation allows overdrafts, the balance should be negative
        # But if it prevents withdrawing more than available, the balance should stay the same
        # Let's check which implementation is used
        current_balance = self.portfolio_dao.get_cash_balance(self.test_portfolio_id)

        if current_balance < 0:
            # Implementation allows overdrafts
            expected = initial - excessive_amount
            self.assertEqual(current_balance, expected)
            print(
                f"✅ Negative balance scenario test passed. Balance correctly updated to: ${current_balance:.2f}"
            )
        else:
            # Implementation prevents excessive withdrawals
            self.assertEqual(current_balance, initial)
            print(
                f"✅ Excessive withdrawal prevention test passed. Balance remained at: ${current_balance:.2f}"
            )


def main():
    # Run the tests
    unittest.main(argv=["first-arg-is-ignored"], exit=False)


if __name__ == "__main__":
    main()
