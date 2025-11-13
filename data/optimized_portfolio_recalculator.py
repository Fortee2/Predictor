"""
Optimized Portfolio Recalculation Service

This module provides an optimized approach to portfolio recalculation that starts
from the transaction date instead of recalculating the entire history.
"""

from datetime import date, timedelta
from typing import Optional
import mysql.connector

from data.portfolio_value_calculator import PortfolioValueCalculator


class OptimizedPortfolioRecalculator:
    """
    Optimized portfolio recalculation service that minimizes unnecessary calculations
    by starting recalculation from the transaction date.
    """
    
    def __init__(self, db_user, db_password, db_host, db_name):
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.connection = None
        self.calculator = PortfolioValueCalculator(db_user, db_password, db_host, db_name)
        self.open_connection()

    def open_connection(self):
        """Open database connection."""
        try:
            self.connection = mysql.connector.connect(
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                database=self.db_name,
            )
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")

    def close_connection(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
        if self.calculator:
            self.calculator.close_connection()

    def smart_recalculate_from_transaction(
        self, 
        portfolio_id: int, 
        transaction_date: date,
        force_full_recalc: bool = False
    ) -> bool:
        """
        Optimally recalculate portfolio values starting from a transaction date.
        
        This method only recalculates portfolio values from the transaction date forward,
        preserving all valid historical values calculated before that date.
        
        Args:
            portfolio_id (int): The portfolio ID
            transaction_date (date): The date of the transaction that triggered recalculation
            force_full_recalc (bool): If True, forces full recalculation from beginning
            
        Returns:
            bool: True if successful, False otherwise
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            today = date.today()
            
            print("\n🔄 Starting optimized portfolio recalculation...")
            print(f"📅 Transaction Date: {transaction_date}")
            
            # Determine the optimal starting date
            if force_full_recalc:
                # Find earliest transaction date for full recalculation
                query = """
                    SELECT MIN(transaction_date) as earliest_date
                    FROM portfolio_transactions
                    WHERE portfolio_id = %s
                """
                cursor.execute(query, (portfolio_id,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    start_date = result[0]
                    if hasattr(start_date, 'date'):
                        start_date = start_date.date()
                else:
                    start_date = transaction_date
                    
                print(f"🔄 Force full recalculation from: {start_date}")
            else:
                # Use transaction date as starting point (optimal approach)
                start_date = transaction_date
                print(f"⚡ Optimized recalculation from: {start_date}")
                
                # Check if there are any existing portfolio values before this date
                query = """
                    SELECT COUNT(*) as count,
                           MAX(calculation_date) as latest_before
                    FROM portfolio_value
                    WHERE portfolio_id = %s AND calculation_date < %s
                """
                cursor.execute(query, (portfolio_id, start_date))
                result = cursor.fetchone()
                
                if result and result[0] > 0:
                    print(f"💾 Preserving {result[0]} existing portfolio values before {start_date}")
                    print(f"📊 Latest preserved value date: {result[1]}")
            
            # Delete portfolio values from start_date forward
            query = """
                DELETE FROM portfolio_value
                WHERE portfolio_id = %s AND calculation_date >= %s
            """
            cursor.execute(query, (portfolio_id, start_date))
            self.connection.commit()
            deleted_rows = cursor.rowcount
            
            if deleted_rows > 0:
                print(f"🗑️  Deleted {deleted_rows} portfolio value records from {start_date} onward")
            else:
                print(f"ℹ️  No existing values found from {start_date} onward")
            
            # Calculate the number of days to recalculate
            days_to_calculate = (today - start_date).days + 1
            
            print(f"📈 Recalculating {days_to_calculate} days of portfolio values...")
            
            # Limit excessive calculations
            if days_to_calculate > 500:
                print(f"⚠️  Warning: {days_to_calculate} days is excessive. Limiting to 500 days.")
                days_to_calculate = 500
                start_date = today - timedelta(days=499)
            
            # Recalculate for each day
            successful_calculations = 0
            failed_calculations = 0
            
            for i in range(days_to_calculate):
                calc_date = start_date + timedelta(days=i)
                
                try:
                    # Show progress for longer calculations
                    if days_to_calculate > 10 and i % max(1, days_to_calculate // 10) == 0:
                        progress_pct = (i / days_to_calculate) * 100
                        print(f"📊 Progress: {progress_pct:.1f}% - Calculating {calc_date}")
                    
                    result = self.calculator.calculate_portfolio_value(portfolio_id, calc_date)
                    
                    if result is not None:
                        successful_calculations += 1
                    else:
                        failed_calculations += 1
                        
                except Exception as calc_error:
                    failed_calculations += 1
                    print(f"❌ Error calculating value for {calc_date}: {calc_error}")
                    continue
            
            # Summary of results
            print(f"\n✅ Recalculation Complete!")
            print(f"📊 Successful calculations: {successful_calculations}")
            if failed_calculations > 0:
                print(f"❌ Failed calculations: {failed_calculations}")
                
            efficiency_gain = self._calculate_efficiency_gain(
                transaction_date, start_date, force_full_recalc
            )
            if efficiency_gain > 0:
                print(f"⚡ Efficiency Gain: Saved ~{efficiency_gain} days of calculations!")
            
            return successful_calculations > 0
            
        except mysql.connector.Error as db_error:
            print(f"💥 Database error during recalculation: {db_error}")
            if self.connection:
                self.connection.rollback()
            return False
        except Exception as e:
            print(f"💥 Error during optimized recalculation: {e}")
            if self.connection:
                self.connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

    def _calculate_efficiency_gain(
        self, 
        transaction_date: date, 
        actual_start_date: date, 
        was_forced: bool
    ) -> int:
        """
        Calculate how many days of calculation were saved by the optimization.
        
        Args:
            transaction_date (date): The transaction date that triggered recalculation
            actual_start_date (date): The actual start date used for recalculation
            was_forced (bool): Whether full recalculation was forced
            
        Returns:
            int: Number of days saved by optimization
        """
        if was_forced:
            return 0  # No savings if full recalculation was forced
            
        # Calculate what the old system would have done
        cursor = self.connection.cursor()
        try:
            query = """
                SELECT MIN(transaction_date) as earliest_date
                FROM portfolio_transactions
                WHERE portfolio_id IN (SELECT DISTINCT portfolio_id FROM portfolio_transactions)
            """
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result and result[0]:
                earliest_date = result[0]
                if hasattr(earliest_date, 'date'):
                    earliest_date = earliest_date.date()
                    
                # Days saved = difference between old approach and new approach
                days_saved = (transaction_date - earliest_date).days
                return max(0, days_saved)
                
        except Exception:
            pass
        finally:
            cursor.close()
            
        return 0

    def recalculate_from_specific_date(
        self, 
        portfolio_id: int, 
        from_date: date, 
        reason: str = "Manual recalculation"
    ) -> bool:
        """
        Recalculate portfolio values from a specific date (backwards compatibility).
        
        Args:
            portfolio_id (int): The portfolio ID
            from_date (date): The date to start recalculation from
            reason (str): Reason for recalculation (for logging)
            
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"🔄 Manual recalculation requested: {reason}")
        return self.smart_recalculate_from_transaction(
            portfolio_id, 
            from_date, 
            force_full_recalc=True
        )

    def get_recalculation_info(self, portfolio_id: int) -> dict:
        """
        Get information about what recalculation would be needed.
        
        Args:
            portfolio_id (int): The portfolio ID
            
        Returns:
            dict: Information about recalculation scope
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Get date range of existing portfolio values
            query = """
                SELECT 
                    MIN(calculation_date) as earliest_value,
                    MAX(calculation_date) as latest_value,
                    COUNT(*) as value_count
                FROM portfolio_value
                WHERE portfolio_id = %s
            """
            cursor.execute(query, (portfolio_id,))
            value_info = cursor.fetchone()
            
            # Get transaction date range
            query = """
                SELECT 
                    MIN(transaction_date) as earliest_transaction,
                    MAX(transaction_date) as latest_transaction,
                    COUNT(*) as transaction_count
                FROM portfolio_transactions
                WHERE portfolio_id = %s
            """
            cursor.execute(query, (portfolio_id,))
            transaction_info = cursor.fetchone()
            
            return {
                'value_info': value_info,
                'transaction_info': transaction_info,
                'needs_full_recalc': (
                    not value_info or 
                    not value_info['earliest_value'] or
                    value_info['value_count'] == 0
                )
            }
            
        except Exception as e:
            print(f"Error getting recalculation info: {e}")
            return {'error': str(e)}
        finally:
            if 'cursor' in locals():
                cursor.close()
