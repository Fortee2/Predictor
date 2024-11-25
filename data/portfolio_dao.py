import mysql.connector
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
import datetime
import os

class PortfolioDAO:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
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
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")
            print(f"User: {self.db_user}, Password: {self.db_password}, Host: {self.db_host}, Database: {self.db_name}")
            
    def close_connection(self):
        if self.connection:
            self.connection.close()
            self.transactions_dao.close_connection()
            
    def create_portfolio(self, ticker_id):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO portfolio (ticker_id, date_added) VALUES (%s, NOW())"
            values = (ticker_id,)
            cursor.execute(query, values)
            self.connection.commit()
            portfolio_id = cursor.lastrowid
            print(f"Added ticker {ticker_id} to portfolio {portfolio_id}")
            return portfolio_id
        except mysql.connector.Error as e:
            print(f"Error creating portfolio entry: {e}")
            return None
            
    def get_portfolio_id(self, ticker_id):
        try:
            cursor = self.connection.cursor()
            query = "SELECT id FROM portfolio WHERE ticker_id = %s"
            values = (ticker_id,)
            cursor.execute(query, values)
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except mysql.connector.Error as e:
            print(f"Error retrieving portfolio ID: {e}")
            return None
            
    def read_portfolio(self, ticker_id=None):
        try:
            cursor = self.connection.cursor()
            if ticker_id:
                query = "SELECT * FROM portfolio WHERE ticker_id = %s"
                values = (ticker_id,)
            else:
                query = "SELECT * FROM portfolio"
                values = None
            cursor.execute(query, values)
            return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Error reading portfolio: {e}")
            
    def update_portfolio(self, id, active):
        try:
            cursor = self.connection.cursor()
            query = "UPDATE portfolio SET active = %s WHERE id = %s"
            values = (active, id)
            cursor.execute(query, values)
            self.connection.commit()
            print(f"Updated portfolio entry {id} to active={active}")
        except mysql.connector.Error as e:
            print(f"Error updating portfolio: {e}")
            
    def delete_portfolio(self, id):
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM portfolio WHERE id = %s"
            values = (id,)
            cursor.execute(query, values)
            self.connection.commit()
            print(f"Removed entry {id} from portfolio")
        except mysql.connector.Error as e:
            print(f"Error deleting from portfolio: {e}")
            
    def add_tickers_to_portfolio(self, portfolio_id, ticker_ids):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO portfolio (ticker_id, date_added) VALUES (%s, NOW())"
            for ticker_id in ticker_ids:
                values = (ticker_id,)
                cursor.execute(query, values)
                self.transactions_dao.insert_transaction(portfolio_id, 'buy', datetime.date.today())
            self.connection.commit()
            print(f"Added {len(ticker_ids)} tickers to portfolio {portfolio_id}")
        except mysql.connector.Error as e:
            print(f"Error adding tickers to portfolio: {e}")
            
    def remove_tickers_from_portfolio(self, portfolio_id, ticker_ids):
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM portfolio WHERE id = %s"
            for ticker_id in ticker_ids:
                portfolio_entry_id = self.get_portfolio_id(ticker_id)
                if portfolio_entry_id:
                    values = (portfolio_entry_id,)
                    cursor.execute(query, values)
                    self.transactions_dao.insert_transaction(portfolio_id, 'sell', datetime.date.today())
            self.connection.commit()
            print(f"Removed {len(ticker_ids)} tickers from portfolio {portfolio_id}")
        except mysql.connector.Error as e:
            print(f"Error removing tickers from portfolio: {e}")
            
    def log_transaction(self, portfolio_id, transaction_type, transaction_date, shares=None, price=None, amount=None):
        self.transactions_dao.insert_transaction(portfolio_id, transaction_type, transaction_date, shares, price, amount)
        print(f"Logged {transaction_type} transaction for portfolio {portfolio_id} on {transaction_date}")
