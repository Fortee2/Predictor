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
        Returns a dictionary mapping ticker_id to shares held.
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT 
                    s.ticker_id, 
                    tk.ticker as symbol,
                    SUM(CASE WHEN t.transaction_type = 'buy' THEN t.shares ELSE 0 END) as total_bought,
                    SUM(CASE WHEN t.transaction_type = 'sell' THEN t.shares ELSE 0 END) as total_sold
                FROM portfolio_transactions t
                JOIN portfolio_securities s ON t.security_id = s.id
                JOIN tickers tk ON s.ticker_id = tk.id
                WHERE t.portfolio_id = %s
                GROUP BY s.ticker_id, tk.ticker
            """
            cursor.execute(query, (portfolio_id,))
            results = cursor.fetchall()
            
            positions = {}
            for row in results:
                shares_held = (row['total_bought'] or 0) - (row['total_sold'] or 0)
                # Only include positions with positive shares
                if shares_held > 0:
                    positions[row['ticker_id']] = {
                        'symbol': row['symbol'],
                        'shares': shares_held
                    }
                    
            return positions
        except mysql.connector.Error as e:
            print(f"Error calculating current positions: {e}")
            return {}
