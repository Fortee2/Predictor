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
