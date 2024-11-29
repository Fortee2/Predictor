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
            cursor = self.connection.cursor()
            if security_id:
                query = "SELECT * FROM portfolio_transactions WHERE portfolio_id = %s AND security_id = %s"
                cursor.execute(query, (portfolio_id, security_id))
            else:
                query = "SELECT * FROM portfolio_transactions WHERE portfolio_id = %s"
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
