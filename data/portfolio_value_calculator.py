import mysql.connector
import yfinance as yf
from datetime import date, timedelta

class PortfolioValueCalculator:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.connection = None
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

    def calculate_portfolio_value(self, portfolio_id, calculation_date):
        try:
            cursor = self.connection.cursor()

            # Retrieve transaction history for the portfolio
            query = "SELECT pt.transaction_type, pt.transaction_date, pt.shares, pt.price, pt.amount, t.id AS ticker_id " \
                    "FROM portfolio_transactions pt " \
                    "JOIN portfolio p ON pt.portfolio_id = p.id " \
                    "JOIN ticker t ON pt.ticker_id = t.id " \
                    "WHERE p.id = %s AND pt.transaction_date <= %s"
            values = (portfolio_id, calculation_date)
            cursor.execute(query, values)
            transactions = cursor.fetchall()

            # Calculate the number of shares held for each stock
            shares_held = {}
            for transaction in transactions:
                transaction_type, transaction_date, shares, price, amount, ticker_id = transaction
                if transaction_type == 'buy':
                    if ticker_id in shares_held:
                        shares_held[ticker_id] += shares
                    else:
                        shares_held[ticker_id] = shares
                elif transaction_type == 'sell':
                    if ticker_id in shares_held:
                        shares_held[ticker_id] -= shares
                    else:
                        shares_held[ticker_id] = -shares

            # Fetch the latest stock prices
            stock_prices = {}
            for ticker_id in shares_held:
                ticker = self.get_ticker_symbol(ticker_id)
                stock = yf.Ticker(ticker)
                stock_prices[ticker_id] = stock.info['regularMarketPrice']

            # Calculate the portfolio value
            portfolio_value = 0
            for ticker_id, shares in shares_held.items():
                if shares > 0:
                    portfolio_value += shares * stock_prices[ticker_id]

            # Add any dividend amounts received
            query = "SELECT SUM(amount) AS total_dividends " \
                    "FROM portfolio_transactions pt " \
                    "JOIN portfolio p ON pt.portfolio_id = p.id " \
                    "WHERE p.id = %s AND pt.transaction_type = 'dividend' AND pt.transaction_date <= %s"
            values = (portfolio_id, calculation_date)
            cursor.execute(query, values)
            result = cursor.fetchone()
            total_dividends = result[0] if result[0] else 0
            portfolio_value += total_dividends

            # Store the calculated portfolio value in the database
            query = "INSERT INTO portfolio_value (portfolio_id, calculation_date, value) VALUES (%s, %s, %s)"
            values = (portfolio_id, calculation_date, portfolio_value)
            cursor.execute(query, values)
            self.connection.commit()

            return portfolio_value

        except mysql.connector.Error as e:
            print(f"Error calculating portfolio value: {e}")
            return None

    def get_ticker_symbol(self, ticker_id):
        try:
            cursor = self.connection.cursor()
            query = "SELECT symbol FROM ticker WHERE id = %s"
            values = (ticker_id,)
            cursor.execute(query, values)
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except mysql.connector.Error as e:
            print(f"Error retrieving ticker symbol: {e}")
            return None
