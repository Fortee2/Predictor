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
            
    def create_portfolio(self, name, description):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO portfolio (name, description, date_added) VALUES (%s, %s, NOW())"
            values = (name, description)
            cursor.execute(query, values)
            self.connection.commit()
            portfolio_id = cursor.lastrowid
            print(f"Created new portfolio with ID {portfolio_id}")
            return portfolio_id
        except mysql.connector.Error as e:
            print(f"Error creating portfolio: {e}")
            return None
            
    def read_portfolio(self, portfolio_id=None):
        try:
            cursor = self.connection.cursor(dictionary=True)  # Return results as dictionaries
            if portfolio_id:
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
