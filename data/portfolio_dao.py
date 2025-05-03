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
            print(f"User: {self.db_user}, Password: {self.db_password}, Host: {self.db_host}, Database: {self.db_name}")
            
    def close_connection(self):
        if self.connection:
            self.connection.close()
            self.transactions_dao.close_connection()
            self.ticker_dao.close_connection()
            
    def create_portfolio(self, name, description, initial_cash=0.0):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO portfolio (name, description, date_added, cash_balance) VALUES (%s, %s, NOW(), %s)"
            values = (name, description, initial_cash)
            cursor.execute(query, values)
            self.connection.commit()
            portfolio_id = cursor.lastrowid
            print(f"Created new portfolio with ID {portfolio_id}")
            return portfolio_id
        except mysql.connector.Error as e:
            print(f"Error creating portfolio: {e}")
            return None
            
    # Cash management methods
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
    
    def add_cash(self, portfolio_id, amount):
        """
        Add cash to a portfolio.
        
        Args:
            portfolio_id (int): The portfolio ID
            amount (float): The amount to add
            
        Returns:
            float: The new cash balance
        """
        try:
            current_balance = self.get_cash_balance(portfolio_id)
            new_balance = current_balance + amount
            if self.update_cash_balance(portfolio_id, new_balance):
                return new_balance
            return current_balance
        except Exception as e:
            print(f"Error adding cash: {e}")
            return self.get_cash_balance(portfolio_id)
    
    def withdraw_cash(self, portfolio_id, amount):
        """
        Withdraw cash from a portfolio.
        
        Args:
            portfolio_id (int): The portfolio ID
            amount (float): The amount to withdraw
            
        Returns:
            float: The new cash balance
        """
        try:
            current_balance = self.get_cash_balance(portfolio_id)
            if current_balance < amount:
                print(f"Warning: Insufficient cash balance. Available: ${current_balance:.2f}, Requested: ${amount:.2f}")
                return current_balance
                
            new_balance = current_balance - amount
            if self.update_cash_balance(portfolio_id, new_balance):
                return new_balance
            return current_balance
        except Exception as e:
            print(f"Error withdrawing cash: {e}")
            return self.get_cash_balance(portfolio_id)
    
    def read_portfolio(self, portfolio_id=None):
        try:
            cursor = self.connection.cursor(dictionary=True)  # Return results as dictionaries
            if (portfolio_id):
                query = "SELECT * FROM portfolio WHERE id = %s"
                values = (portfolio_id,)
            else:
                query = "SELECT * FROM portfolio"
                values = None
            cursor.execute(query, values)
            if portfolio_id:
                return cursor.fetchone()  # Return single portfolio as dict
            return cursor.fetchall()  # Return list of portfolio dicts
        except mysql.connector.Error as e:
            print(f"Error reading portfolio: {e}")
            
    def update_portfolio(self, portfolio_id, name=None, description=None, active=None):
        try:
            cursor = self.connection.cursor()
            query = "UPDATE portfolio SET "
            values = []
            if name:
                query += "name = %s, "
                values.append(name)
            if description:
                query += "description = %s, "
                values.append(description)
            if active is not None:
                query += "active = %s, "
                values.append(active)
            query = query.rstrip(", ") + " WHERE id = %s"
            values.append(portfolio_id)
            cursor.execute(query, values)
            self.connection.commit()
            print(f"Updated portfolio {portfolio_id}")
        except mysql.connector.Error as e:
            print(f"Error updating portfolio: {e}")
            
    def delete_portfolio(self, portfolio_id):
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM portfolio WHERE id = %s"
            values = (portfolio_id,)
            cursor.execute(query, values)
            self.connection.commit()
            print(f"Deleted portfolio {portfolio_id}")
        except mysql.connector.Error as e:
            print(f"Error deleting portfolio: {e}")
            
    def add_tickers_to_portfolio(self, portfolio_id, ticker_symbols):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO portfolio_securities (portfolio_id, ticker_id, date_added) VALUES (%s, %s, NOW())"
            added_count = 0
            for symbol in ticker_symbols:
                ticker_id = self.ticker_dao.get_ticker_id(symbol)
                if ticker_id:
                    values = (portfolio_id, ticker_id)
                    cursor.execute(query, values)
                    self.transactions_dao.insert_transaction(portfolio_id, None, 'buy', datetime.date.today())
                    added_count += 1
                else:
                    print(f"Warning: Ticker symbol {symbol} not found")
            self.connection.commit()
            print(f"Added {added_count} tickers to portfolio {portfolio_id}")
        except mysql.connector.Error as e:
            print(f"Error adding tickers to portfolio: {e}")
            
    def remove_tickers_from_portfolio(self, portfolio_id, ticker_symbols):
        try:
            cursor = self.connection.cursor()
            removed_count = 0
            for symbol in ticker_symbols:
                ticker_id = self.ticker_dao.get_ticker_id(symbol)
                if ticker_id:
                    # First get the security_id
                    security_id = self.get_security_id(portfolio_id, ticker_id)
                    if security_id:
                        # Delete related transactions first
                        self.transactions_dao.delete_transactions_for_security(portfolio_id, security_id)
                        
                        # Then delete the security entry
                        query = "DELETE FROM portfolio_securities WHERE portfolio_id = %s AND ticker_id = %s"
                        values = (portfolio_id, ticker_id)
                        cursor.execute(query, values)
                        removed_count += 1
                    else:
                        print(f"Warning: Ticker {symbol} not found in portfolio {portfolio_id}")
                else:
                    print(f"Warning: Ticker symbol {symbol} not found")
                    
            self.connection.commit()
            print(f"Removed {removed_count} tickers from portfolio {portfolio_id}")
        except mysql.connector.Error as e:
            print(f"Error removing tickers from portfolio: {e}")
            self.connection.rollback()
            
    def get_tickers_in_portfolio(self, portfolio_id):
        try:
            cursor = self.connection.cursor()
            query = "SELECT ticker_id FROM portfolio_securities WHERE portfolio_id = %s"
            values = (portfolio_id,)
            cursor.execute(query, values)
            ticker_ids = [row[0] for row in cursor.fetchall()]
            return [self.ticker_dao.get_ticker_symbol(tid) for tid in ticker_ids if self.ticker_dao.get_ticker_symbol(tid)]
        except mysql.connector.Error as e:
            print(f"Error retrieving tickers in portfolio: {e}")
            return []
            
    def is_ticker_in_portfolio(self, portfolio_id, ticker_symbol):
        try:
            cursor = self.connection.cursor()
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                return False
            query = "SELECT COUNT(*) FROM portfolio_securities WHERE portfolio_id = %s AND ticker_id = %s"
            values = (portfolio_id, ticker_id)
            cursor.execute(query, values)
            count = cursor.fetchone()[0]
            return count > 0
        except mysql.connector.Error as e:
            print(f"Error checking if ticker is in portfolio: {e}")
            return False
            
    def get_portfolios_with_ticker(self, ticker_symbol):
        try:
            cursor = self.connection.cursor()
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                return []
            query = "SELECT portfolio_id FROM portfolio_securities WHERE ticker_id = %s"
            values = (ticker_id,)
            cursor.execute(query, values)
            return [row[0] for row in cursor.fetchall()]
        except mysql.connector.Error as e:
            print(f"Error retrieving portfolios with ticker: {e}")
            return []
            
    def get_security_id(self, portfolio_id, ticker_id):
        try:
            cursor = self.connection.cursor()
            query = "SELECT id FROM portfolio_securities WHERE portfolio_id = %s AND ticker_id = %s"
            values = (portfolio_id, ticker_id)
            cursor.execute(query, values)
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except mysql.connector.Error as e:
            print(f"Error retrieving security ID: {e}")
            return None
            
    def get_all_tickers_in_portfolios(self):
        try:
            cursor = self.connection.cursor()
            query = "SELECT DISTINCT ticker_id FROM portfolio_securities"
            cursor.execute(query)
            ticker_ids = [row[0] for row in cursor.fetchall()]
            return [self.ticker_dao.get_ticker_symbol(tid) for tid in ticker_ids if self.ticker_dao.get_ticker_symbol(tid)]
        except mysql.connector.Error as e:
            print(f"Error retrieving all tickers in portfolios: {e}")
            return []
            
    def log_transaction(self, portfolio_id, security_id, transaction_type, transaction_date, shares=None, price=None, amount=None):
        self.transactions_dao.insert_transaction(portfolio_id, security_id, transaction_type, transaction_date, shares, price, amount)
        print(f"Logged {transaction_type} transaction for portfolio {portfolio_id} and security {security_id} on {transaction_date}")
        
    # Cash history management methods
    def log_cash_transaction(self, portfolio_id, amount, transaction_type, description=None, transaction_date=None):
        """
        Log a cash transaction to the cash_balance_history table and update portfolio cash balance.
        
        Args:
            portfolio_id (int): The portfolio ID
            amount (float): The transaction amount (positive for deposits, negative for withdrawals)
            transaction_type (str): The type of transaction ('deposit', 'withdrawal', 'buy', 'sell', 'dividend', etc.)
            description (str, optional): A description of the transaction
            transaction_date (datetime, optional): The transaction date (defaults to current datetime)
            
        Returns:
            float: The new cash balance after the transaction
        """
        try:
            # Default to current date/time if not specified
            if transaction_date is None:
                transaction_date = datetime.datetime.now()
                
            cursor = self.connection.cursor(dictionary=True)
            
            # First check if the cash_balance_history table exists
            check_table_query = """
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'cash_balance_history'
            """
            cursor.execute(check_table_query)
            table_exists = cursor.fetchone()['count'] > 0
            
            if not table_exists:
                # Create the table if it doesn't exist
                create_table_query = """
                    CREATE TABLE cash_balance_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        portfolio_id INT NOT NULL,
                        transaction_date DATETIME NOT NULL,
                        amount DECIMAL(10,2) NOT NULL,
                        transaction_type VARCHAR(20) NOT NULL,
                        description VARCHAR(255),
                        balance_after DECIMAL(10,2) NOT NULL,
                        FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
                    )
                """
                cursor.execute(create_table_query)
                self.connection.commit()
            
            # Get the current balance
            current_balance = self.get_cash_balance(portfolio_id)
            
            # Calculate the new balance
            new_balance = current_balance + amount
            
            # Insert the transaction into history
            insert_query = """
                INSERT INTO cash_balance_history 
                (portfolio_id, transaction_date, amount, transaction_type, description, balance_after)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            insert_values = (
                portfolio_id,
                transaction_date,
                amount,
                transaction_type,
                description,
                new_balance
            )
            cursor.execute(insert_query, insert_values)
            
            # Update the portfolio cash_balance
            self.update_cash_balance(portfolio_id, new_balance)
            
            self.connection.commit()
            return new_balance
            
        except mysql.connector.Error as e:
            print(f"Error logging cash transaction: {e}")
            self.connection.rollback()
            return self.get_cash_balance(portfolio_id)
            
    def get_cash_transaction_history(self, portfolio_id):
        """
        Get all cash transactions for a portfolio.
        
        Args:
            portfolio_id (int): The portfolio ID
            
        Returns:
            list: A list of cash transaction dictionaries
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Check if the cash_balance_history table exists
            check_table_query = """
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'cash_balance_history'
            """
            cursor.execute(check_table_query)
            table_exists = cursor.fetchone()['count'] > 0
            
            if not table_exists:
                # Create the table if it doesn't exist
                create_table_query = """
                    CREATE TABLE cash_balance_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        portfolio_id INT NOT NULL,
                        transaction_date DATETIME NOT NULL,
                        amount DECIMAL(10,2) NOT NULL,
                        transaction_type VARCHAR(20) NOT NULL,
                        description VARCHAR(255),
                        balance_after DECIMAL(10,2) NOT NULL,
                        FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
                    )
                """
                cursor.execute(create_table_query)
                self.connection.commit()
                return []
            
            # Get all cash transactions
            query = """
                SELECT * FROM cash_balance_history
                WHERE portfolio_id = %s
                ORDER BY transaction_date DESC, id DESC
            """
            cursor.execute(query, (portfolio_id,))
            return cursor.fetchall()
            
        except mysql.connector.Error as e:
            print(f"Error retrieving cash transaction history: {e}")
            return []
            
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
                
            # Get the most recent balance
            query = """
                SELECT balance_after
                FROM cash_balance_history
                WHERE portfolio_id = %s
                ORDER BY transaction_date DESC, id DESC
                LIMIT 1
            """
            cursor.execute(query, (portfolio_id,))
            result = cursor.fetchone()
            
            if result and result[0] is not None:
                balance = float(result[0])
                # Update the portfolio cash_balance to match
                self.update_cash_balance(portfolio_id, balance)
                return balance
            else:
                return self.get_cash_balance(portfolio_id)
                
        except mysql.connector.Error as e:
            print(f"Error recalculating cash balance: {e}")
            return self.get_cash_balance(portfolio_id)
