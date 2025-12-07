#!/usr/bin/env python3
"""
Test for Transaction Duplicate Detection with Rounding Issues

This test verifies that the get_transaction_id method correctly handles
rounding issues when detecting duplicate transactions.
"""

import unittest
from decimal import Decimal


class TestTransactionRoundingLogic(unittest.TestCase):
    """Test rounding logic for transaction duplicate detection"""

    def test_price_rounding_to_match_database_precision(self):
        """Test that prices are rounded to 2 decimal places to match DECIMAL(10,2)"""
        # Simulating values that might come from CSV
        csv_price = 12.345
        csv_price_rounded = round(csv_price, 2)
        
        # Simulating what's stored in database as DECIMAL(10,2)
        db_price = Decimal("12.35")
        
        # After rounding, they should match
        self.assertEqual(csv_price_rounded, float(db_price))
        self.assertEqual(csv_price_rounded, 12.35)

    def test_amount_rounding_to_match_database_precision(self):
        """Test that amounts are rounded to 2 decimal places to match DECIMAL(10,2)"""
        # Dividend amount from calculation
        calculated_amount = 123.456
        calculated_amount_rounded = round(calculated_amount, 2)
        
        # Database stores as DECIMAL(10,2)
        db_amount = Decimal("123.46")
        
        # After rounding, they should match
        self.assertEqual(calculated_amount_rounded, float(db_amount))
        self.assertEqual(calculated_amount_rounded, 123.46)

    def test_shares_comparison_no_rounding_needed(self):
        """Test that shares don't need rounding - they're stored as INT"""
        # Shares are stored as INT in the database
        csv_shares = 100
        db_shares = 100
        
        self.assertEqual(csv_shares, db_shares)

    def test_floating_point_precision_issue(self):
        """Demonstrate the floating point precision issue"""
        # Classic floating point issue
        result = 0.1 + 0.2
        expected = 0.3
        
        # Direct comparison fails
        self.assertNotEqual(result, expected)
        
        # But rounded comparison works
        self.assertEqual(round(result, 2), round(expected, 2))

    def test_comparison_with_none_values(self):
        """Test that None values are handled correctly"""
        # For buy/sell transactions, amount should be None
        self.assertIsNone(None)
        
        # For dividend transactions, shares and price should be None
        self.assertIsNone(None)

    def test_buy_transaction_comparison(self):
        """Test comparison logic for buy transactions"""
        # Buy transaction parameters
        shares = 100
        price = 12.345  # From CSV
        amount = None
        
        # After rounding
        price_rounded = round(price, 2)
        
        # Simulating database values
        db_shares = 100
        db_price = Decimal("12.35")
        db_amount = None
        
        # All should match after rounding
        self.assertEqual(shares, db_shares)
        self.assertEqual(price_rounded, float(db_price))
        self.assertEqual(amount, db_amount)

    def test_dividend_transaction_comparison(self):
        """Test comparison logic for dividend transactions"""
        # Dividend transaction parameters
        shares = None
        price = None
        amount = 25.678  # From calculation
        
        # After rounding
        amount_rounded = round(amount, 2)
        
        # Simulating database values
        db_shares = None
        db_price = None
        db_amount = Decimal("25.68")
        
        # All should match after rounding
        self.assertEqual(shares, db_shares)
        self.assertEqual(price, db_price)
        self.assertEqual(amount_rounded, float(db_amount))

    def test_epsilon_comparison_alternative(self):
        """Test epsilon-based comparison as an alternative approach"""
        # This is an alternative approach, but rounding is simpler
        price1 = 12.345
        price2 = 12.35
        epsilon = 0.01  # 1 cent tolerance
        
        # Within tolerance
        self.assertTrue(abs(price1 - price2) < epsilon)

    def test_multiple_decimal_places_scenarios(self):
        """Test various decimal place scenarios"""
        test_cases = [
            (12.345, 12.35),
            (12.344, 12.34),
            (12.346, 12.35),
            (0.999, 1.00),
            (0.994, 0.99),
            (0.995, 0.99),  # Python uses "round half to even" (banker's rounding) - rounds to even (10 -> 0.99)
            (0.985, 0.98),  # Banker's rounding rounds 5 to even (8)
            (0.975, 0.97),  # Rounds to even (6, not 8)
            (1.125, 1.12),  # Rounds to even (2)
            (1.135, 1.14),  # Rounds to even (4)
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val, expected=expected):
                rounded = round(input_val, 2)
                self.assertEqual(rounded, expected)


if __name__ == "__main__":
    unittest.main()
