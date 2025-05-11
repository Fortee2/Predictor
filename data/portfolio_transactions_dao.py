import mysql.connector

class PortfolioTransactionsDAO:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.open_connection()

    def open_connection(self):
        try:
            self.connection = mysql.connector.connect(
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                database=self.db_name
            )
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")

    def close_connection(self):
        if self.connection:
            self.connection.close()

    def get_transaction_history(self, portfolio_id, security_id=None):
        try:
            cursor = self.connection.cursor(dictionary=True)
            if security_id:
                query = """
                    SELECT t.*, s.ticker_id, tk.ticker as symbol 
                    FROM portfolio_transactions t
                    JOIN portfolio_securities s ON t.security_id = s.id
                    JOIN tickers tk ON s.ticker_id = tk.id
                    WHERE t.portfolio_id = %s AND t.security_id = %s
                """
                cursor.execute(query, (portfolio_id, security_id))
            else:
                query = """
                    SELECT t.*, s.ticker_id, tk.ticker as symbol 
                    FROM portfolio_transactions t
                    JOIN portfolio_securities s ON t.security_id = s.id
                    JOIN tickers tk ON s.ticker_id = tk.id
                    WHERE t.portfolio_id = %s
                """
                cursor.execute(query, (portfolio_id,))
            return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Error retrieving transaction history: {e}")
            return []

    def insert_transaction(self, portfolio_id, security_id, transaction_type, transaction_date, shares=None, price=None, amount=None):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO portfolio_transactions (portfolio_id, security_id, transaction_type, transaction_date, shares, price, amount) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            values = (portfolio_id, security_id, transaction_type, transaction_date, shares, price, amount)
            cursor.execute(query, values)
            self.connection.commit()
        except mysql.connector.Error as e:
            print(f"Error inserting transaction: {e}")
            self.connection.rollback()

    def delete_transactions_for_security(self, portfolio_id, security_id):
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM portfolio_transactions WHERE portfolio_id = %s AND security_id = %s"
            values = (portfolio_id, security_id)
            cursor.execute(query, values)
            self.connection.commit()
        except mysql.connector.Error as e:
            print(f"Error deleting transactions: {e}")
            self.connection.rollback()
            
    def get_current_positions(self, portfolio_id):
        """
        Calculate the current positions in a portfolio based on transaction history.
        Returns a dictionary mapping ticker_id to position details including shares held and average price.
        Implements FIFO (First-In-First-Out) method for cost basis calculation.
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Get all transactions for the portfolio in a single query to improve performance
            # Order strictly by transaction_date first, then by ID to ensure proper FIFO ordering
            query = """
                SELECT 
                    s.ticker_id, 
                    s.id as security_id,
                    tk.ticker as symbol,
                    t.transaction_type,
                    t.transaction_date,
                    t.shares,
                    t.price,
                    t.amount
                FROM portfolio_transactions t
                JOIN portfolio_securities s ON t.security_id = s.id
                JOIN tickers tk ON s.ticker_id = tk.id
                WHERE t.portfolio_id = %s
                ORDER BY s.ticker_id, t.transaction_date ASC, t.id ASC
            """
            cursor.execute(query, (portfolio_id,))
            all_transactions = cursor.fetchall()
            
            # Process transactions by ticker_id
            positions = {}
            current_ticker = None
            buy_queue = []  # Store (shares, price) for each buy
            symbol = None
            
            for transaction in all_transactions:
                ticker_id = transaction['ticker_id']
                trans_type = transaction['transaction_type']
                
                # Only process buy/sell transactions for position calculation
                # Other transaction types (dividend, cash) don't affect share positions
                if trans_type not in ('buy', 'sell'):
                    continue
                
                # If we're starting a new ticker, calculate results for the previous one
                if current_ticker is not None and current_ticker != ticker_id and buy_queue:
                    # Calculate and store position for the previous ticker
                    self._store_position_data(positions, current_ticker, buy_queue, symbol)
                
                # Set or update the current ticker and its symbol
                if current_ticker != ticker_id:
                    current_ticker = ticker_id
                    symbol = transaction['symbol']
                    # Clear the buy queue for the new ticker
                    buy_queue = []
                
                # Convert decimal/numeric types to float to avoid type issues
                try:
                    shares = float(transaction['shares'] or 0)
                    price = float(transaction['price'] or 0)
                except (ValueError, TypeError) as e:
                    print(f"Error converting transaction values for {ticker_id}: {e}")
                    continue
                    
                # Skip invalid transactions (missing essential data)
                if shares <= 0 or price <= 0:
                    continue
                    
                # Process the transaction
                if trans_type == 'buy':
                    buy_queue.append((shares, price))
                elif trans_type == 'sell':
                    shares_to_sell = shares
                    
                    # Process FIFO sell
                    while shares_to_sell > 0 and buy_queue:
                        buy_shares, buy_price = buy_queue[0]
                        
                        if buy_shares <= shares_to_sell:
                            # Use all of this buy lot
                            buy_queue.pop(0)
                            shares_to_sell -= buy_shares
                        else:
                            # Use part of this buy lot
                            buy_queue[0] = (buy_shares - shares_to_sell, buy_price)
                            shares_to_sell = 0
                    
                    # Check if we couldn't sell all shares (error condition)
                    if shares_to_sell > 0:
                        print(f"Warning: Attempted to sell more shares of {symbol} than available in portfolio. Shares not covered: {shares_to_sell}")
            
            # Calculate position for the last ticker
            if current_ticker is not None and buy_queue:
                self._store_position_data(positions, current_ticker, buy_queue, symbol)
                    
            return positions
        except mysql.connector.Error as e:
            print(f"Error calculating current positions: {e}")
            return {}
            
    def _store_position_data(self, positions_dict, ticker_id, buy_queue, symbol):
        """Helper method to calculate and store position data from a buy queue."""
        try:
            total_shares = 0
            total_cost = 0
            
            for shares, price in buy_queue:
                total_shares += shares
                total_cost += shares * price
            
            # Only include positions with positive shares and valid cost
            if total_shares > 0:
                positions_dict[ticker_id] = {
                    'symbol': symbol,
                    'shares': round(total_shares, 4),  # Round to 4 decimal places for fractional shares
                    'avg_price': round(total_cost / total_shares, 2) if total_shares > 0 else 0
                }
            return positions_dict
        except Exception as e:
            print(f"Error storing position data for {ticker_id}: {e}")
            return positions_dict

    def add_cash_transaction(self, portfolio_id, transaction_type, amount, transaction_date):
        """
        Add a cash deposit or withdrawal transaction with a specific date.
        
        Args:
            portfolio_id (int): ID of the portfolio
            transaction_type (str): Either 'deposit' or 'withdrawal'
            amount (float): The cash amount (positive value)
            transaction_date (datetime): The date when the cash transaction occurred
            
        Returns:
            bool: True if the transaction was added successfully, False otherwise
        """
        if transaction_type not in ('deposit', 'withdrawal'):
            print(f"Error: Invalid cash transaction type '{transaction_type}'. Must be 'deposit' or 'withdrawal'.")
            return False
            
        if amount <= 0:
            print("Error: Transaction amount must be positive.")
            return False
            
        try:
            cursor = self.connection.cursor()
            
            # Get the current cash balance
            current_balance = self.get_cash_balance(portfolio_id)
            
            # For withdrawals, check if there's enough balance
            if transaction_type == 'withdrawal' and amount > current_balance:
            # Map our transaction type to allowed ENUM values: 'buy' for withdrawals, 'sell' for deposits
            # This is because the database only allows 'buy', 'sell', and 'dividend' as transaction types
            db_transaction_type = 'sell' if transaction_type == 'deposit' else 'buy'
            
            # For cash transactions, we use the cash_security_id and NULL for shares/price
            # The amount field stores the cash value
            query = """
                INSERT INTO portfolio_transactions 
                (portfolio_id, security_id, transaction_type, transaction_date, amount)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            # The amount should always be positive in the database
            # The transaction_type determines if it's a deposit or withdrawal
            values = (portfolio_id, cash_security_id, db_transaction_type, transaction_date, amount)
            cursor.execute(query, values)
            self.connection.commit()
            return True
            
        except mysql.connector.Error as e:
            print(f"Error adding cash {transaction_type}: {e}")
            self.connection.rollback()
            return False
            
    def _get_or_create_cash_security_id(self, portfolio_id):
        """
        Get or create a special security_id for cash transactions.
        This is needed because the database schema requires a valid security_id for all transactions.
        
        Args:
            portfolio_id (int): ID of the portfolio
            
        Returns:
            int: The security_id for cash transactions, or None if there was an error
        """
        try:
            cursor = self.connection.cursor()
            
            # Check if we have a special cash ticker
            cursor.execute("SELECT id FROM tickers WHERE ticker = 'CASH'")
            cash_ticker = cursor.fetchone()
            
            # If not, create it
            if not cash_ticker:
                cursor.execute(
                    "INSERT INTO tickers (ticker, ticker_name) VALUES ('CASH', 'Cash Account')"
                )
                self.connection.commit()
                cash_ticker_id = cursor.lastrowid
            else:
                cash_ticker_id = cash_ticker[0]
                
            # Check if we have a portfolio_securities entry for this cash ticker
            cursor.execute(
                "SELECT id FROM portfolio_securities WHERE portfolio_id = %s AND ticker_id = %s",
                (portfolio_id, cash_ticker_id)
            )
            cash_security = cursor.fetchone()
            
            # If not, create it
            if not cash_security:
                cursor.execute(
                    "INSERT INTO portfolio_securities (portfolio_id, ticker_id, date_added) VALUES (%s, %s, NOW())",
                    (portfolio_id, cash_ticker_id)
                )
                self.connection.commit()
                return cursor.lastrowid
            else:
                return cash_security[0]
                
        except mysql.connector.Error as e:
            print(f"Error setting up cash security: {e}")
            self.connection.rollback()
            return None

    def get_cash_balance(self, portfolio_id):
        """
        Calculate the current cash balance for a portfolio based on deposits and withdrawals.
        
        Args:
            portfolio_id (int): ID of the portfolio
            
        Returns:
            float: The current cash balance
        """
        try:
            cursor = self.connection.cursor()
            
            # Get the cash ticker ID
            cursor.execute("SELECT id FROM tickers WHERE ticker = 'CASH'")
            cash_ticker_result = cursor.fetchone()
            
            if not cash_ticker_result:
                return 0  # No cash ticker found, so no cash transactions
                
            cash_ticker_id = cash_ticker_result[0]
            
            # Get the portfolio security ID for cash
            cursor.execute(
                "SELECT id FROM portfolio_securities WHERE portfolio_id = %s AND ticker_id = %s",
                (portfolio_id, cash_ticker_id)
            )
            cash_security_result = cursor.fetchone()
            
            if not cash_security_result:
                return 0  # No cash security entry, so no cash transactions
                
            cash_security_id = cash_security_result[0]
            
            # Sum the amounts with the correct mapping:
            # 'sell' transactions (deposits) are positive
            # 'buy' transactions (withdrawals) are negative
            query = """
                SELECT 
                    COALESCE(SUM(CASE WHEN transaction_type = 'sell' THEN amount ELSE -amount END), 0) as balance
                FROM portfolio_transactions
                WHERE portfolio_id = %s 
                AND security_id = %s
            """
            
            cursor.execute(query, (portfolio_id, cash_security_id))
            result = cursor.fetchone()
            
            # Return the cash balance (will be 0 if no transactions found)
            return float(result[0]) if result else 0
            
        except mysql.connector.Error as e:
            print(f"Error retrieving cash balance: {e}")
            return 0
