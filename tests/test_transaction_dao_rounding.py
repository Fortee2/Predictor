#!/usr/bin/env python3
"""
Integration test for PortfolioTransactionsDAO rounding fix

This test verifies that the rounding logic is correctly applied in the DAO methods.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import date

# Add the parent directory to the path so we can import data modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPortfolioTransactionsDAORounding(unittest.TestCase):
    """Test rounding logic in PortfolioTransactionsDAO methods"""

    @patch('data.portfolio_transactions_dao.BaseDAO.get_connection')
    def test_insert_transaction_rounds_price(self, mock_get_connection):
        """Verify that insert_transaction rounds price to 2 decimal places"""
        from data.portfolio_transactions_dao import PortfolioTransactionsDAO
        
        # Setup mock connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        
        # Create DAO instance with mock pool
        mock_pool = MagicMock()
        dao = PortfolioTransactionsDAO(pool=mock_pool)
        
        # Insert transaction with price that needs rounding
        dao.insert_transaction(
            portfolio_id=1,
            security_id=1,
            transaction_type='buy',
            transaction_date=date(2024, 1, 1),
            shares=100,
            price=12.345,  # Should be rounded to 12.35
            amount=None
        )
        
        # Verify the execute call was made with rounded price
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        values = call_args[1]
        
        # Check that price was rounded to 12.35
        self.assertEqual(values[5], 12.35)  # price is at index 5

    @patch('data.portfolio_transactions_dao.BaseDAO.get_connection')
    def test_insert_transaction_rounds_amount(self, mock_get_connection):
        """Verify that insert_transaction rounds amount to 2 decimal places"""
        from data.portfolio_transactions_dao import PortfolioTransactionsDAO
        
        # Setup mock connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        
        # Create DAO instance with mock pool
        mock_pool = MagicMock()
        dao = PortfolioTransactionsDAO(pool=mock_pool)
        
        # Insert dividend transaction with amount that needs rounding
        dao.insert_transaction(
            portfolio_id=1,
            security_id=1,
            transaction_type='dividend',
            transaction_date=date(2024, 1, 1),
            shares=None,
            price=None,
            amount=123.456  # Should be rounded to 123.46
        )
        
        # Verify the execute call was made with rounded amount
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        values = call_args[1]
        
        # Check that amount was rounded to 123.46
        self.assertEqual(values[6], 123.46)  # amount is at index 6

    @patch('data.portfolio_transactions_dao.BaseDAO.get_connection')
    def test_get_transaction_id_rounds_price_for_buy(self, mock_get_connection):
        """Verify that get_transaction_id rounds price for buy transactions"""
        from data.portfolio_transactions_dao import PortfolioTransactionsDAO
        
        # Setup mock connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [123]  # Simulated transaction ID
        mock_connection.cursor.return_value = mock_cursor
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        
        # Create DAO instance with mock pool
        mock_pool = MagicMock()
        dao = PortfolioTransactionsDAO(pool=mock_pool)
        
        # Get transaction with price that needs rounding
        result = dao.get_transaction_id(
            portfolio_id=1,
            security_id=1,
            transaction_type='buy',
            transaction_date=date(2024, 1, 1),
            shares=100,
            price=12.345,  # Should be rounded to 12.35
            amount=None
        )
        
        # Verify the execute call was made with rounded price
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        query = call_args[0]
        values = call_args[1]
        
        # Check that the query includes shares and price comparison
        self.assertIn('shares = %s', query)
        self.assertIn('price = %s', query)
        self.assertIn('amount IS NULL', query)
        
        # Check that price was rounded to 12.35
        self.assertEqual(values[4], 100)  # shares
        self.assertEqual(values[5], 12.35)  # rounded price

    @patch('data.portfolio_transactions_dao.BaseDAO.get_connection')
    def test_get_transaction_id_rounds_amount_for_dividend(self, mock_get_connection):
        """Verify that get_transaction_id rounds amount for dividend transactions"""
        from data.portfolio_transactions_dao import PortfolioTransactionsDAO
        
        # Setup mock connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [456]  # Simulated transaction ID
        mock_connection.cursor.return_value = mock_cursor
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        
        # Create DAO instance with mock pool
        mock_pool = MagicMock()
        dao = PortfolioTransactionsDAO(pool=mock_pool)
        
        # Get transaction with amount that needs rounding
        result = dao.get_transaction_id(
            portfolio_id=1,
            security_id=1,
            transaction_type='dividend',
            transaction_date=date(2024, 1, 1),
            shares=None,
            price=None,
            amount=123.456  # Should be rounded to 123.46
        )
        
        # Verify the execute call was made with rounded amount
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        query = call_args[0]
        values = call_args[1]
        
        # Check that the query includes amount comparison
        self.assertIn('shares IS NULL', query)
        self.assertIn('price IS NULL', query)
        self.assertIn('amount = %s', query)
        
        # Check that amount was rounded to 123.46
        self.assertEqual(values[4], 123.46)  # rounded amount

    @patch('data.portfolio_transactions_dao.BaseDAO.get_connection')
    def test_get_transaction_id_handles_none_values(self, mock_get_connection):
        """Verify that get_transaction_id handles None values correctly"""
        from data.portfolio_transactions_dao import PortfolioTransactionsDAO
        
        # Setup mock connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No matching transaction
        mock_connection.cursor.return_value = mock_cursor
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        
        # Create DAO instance with mock pool
        mock_pool = MagicMock()
        dao = PortfolioTransactionsDAO(pool=mock_pool)
        
        # Get transaction with None price
        result = dao.get_transaction_id(
            portfolio_id=1,
            security_id=1,
            transaction_type='buy',
            transaction_date=date(2024, 1, 1),
            shares=100,
            price=None,
            amount=None
        )
        
        # Verify the execute call was made
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        values = call_args[1]
        
        # Check that None values are preserved
        self.assertIsNone(values[5])  # price should be None

    @patch('data.portfolio_transactions_dao.BaseDAO.get_connection')
    def test_get_transaction_id_for_sell_transaction(self, mock_get_connection):
        """Verify that get_transaction_id works correctly for sell transactions"""
        from data.portfolio_transactions_dao import PortfolioTransactionsDAO
        
        # Setup mock connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [789]
        mock_connection.cursor.return_value = mock_cursor
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        
        # Create DAO instance with mock pool
        mock_pool = MagicMock()
        dao = PortfolioTransactionsDAO(pool=mock_pool)
        
        # Get sell transaction
        result = dao.get_transaction_id(
            portfolio_id=1,
            security_id=1,
            transaction_type='sell',
            transaction_date=date(2024, 1, 1),
            shares=50,
            price=15.678,  # Should be rounded to 15.68
            amount=None
        )
        
        # Verify the result
        self.assertEqual(result, 789)
        
        # Verify the execute call
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        values = call_args[1]
        
        # Check that price was rounded
        self.assertEqual(values[4], 50)  # shares
        self.assertEqual(values[5], 15.68)  # rounded price


if __name__ == "__main__":
    unittest.main()
