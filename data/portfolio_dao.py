import mysql.connector
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.ticker_dao import TickerDao
import datetime

class PortfolioDAO:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)
        self.connection = None
        
    def open_connection(self):
        try:
            self.connection = mysql.connector.connect(
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                database=self.db_name
            )
            self.transactions_dao.open_connection()
            self.ticker_dao.open_connection()
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")
            
    def close_connection(self):
        if self.connection:
            self.connection.close()
            self.transactions_dao.close_connection()
            self.ticker_dao.close_connection()
            
    def get_cash_balance(self, portfolio_id):
        """
        Get the current cash balance for a portfolio.
        
        Args:
            portfolio_id (int): The portfolio ID
            
        Returns:
            float: The cash balance
        """
        try:
            cursor = self.connection.cursor()
            query = "SELECT cash_balance FROM portfolio WHERE id = %s"
            cursor.execute(query, (portfolio_id,))
            result = cursor.fetchone()
            if result and result[0] is not None:
                return float(result[0])
            return 0.0
        except mysql.connector.Error as e:
            print(f"Error retrieving cash balance: {e}")
            return 0.0
            
    def update_cash_balance(self, portfolio_id, new_balance):
        """
        Update the cash balance for a portfolio.
        
        Args:
            portfolio_id (int): The portfolio ID
            new_balance (float): The new cash balance
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            query = "UPDATE portfolio SET cash_balance = %s WHERE id = %s"
            cursor.execute(query, (new_balance, portfolio_id))
            self.connection.commit()
            return True
        except mysql.connector.Error as e:
            print(f"Error updating cash balance: {e}")
            self.connection.rollback()
            return False

    def recalculate_cash_balance(self, portfolio_id):
        """
        Recalculate the cash balance from the transaction history.
        
        Args:
            portfolio_id (int): The portfolio ID
            
        Returns:
            float: The recalculated cash balance
        """
        try:
            cursor = self.connection.cursor()
            
            # Check if the cash_balance_history table exists
            check_table_query = """
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'cash_balance_history'
            """
            cursor.execute(check_table_query)
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                return self.get_cash_balance(portfolio_id)
                
            # Get all transactions ordered by date
            query = """
                SELECT id, transaction_date, amount, transaction_type
                FROM cash_balance_history
                WHERE portfolio_id = %s
                ORDER BY transaction_date ASC, id ASC
            """
            cursor.execute(query, (portfolio_id,))
            transactions = cursor.fetchall()
            
            # Start with 0 balance and process transactions in chronological order
            running_balance = 0.0
            
            # Update each transaction's balance_after field
            update_query = """
                UPDATE cash_balance_history
                SET balance_after = %s
                WHERE id = %s
            """
            
            for transaction in transactions:
                transaction_id = transaction[0]
                amount = float(transaction[2])
                running_balance += amount
                
                # Update the balance_after field for this transaction
                cursor.execute(update_query, (running_balance, transaction_id))
            
            # Commit all updates
            self.connection.commit()
            
            # Update the portfolio cash_balance to match
            self.update_cash_balance(portfolio_id, running_balance)
            return running_balance
                
        except mysql.connector.Error as e:
            print(f"Error recalculating cash balance: {e}")
            self.connection.rollback()
            return self.get_cash_balance(portfolio_id)
        finally:
            if cursor:
                cursor.close()
