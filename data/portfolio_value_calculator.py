import mysql.connector
import yfinance as yf
from datetime import date, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import os
from io import BytesIO
import base64

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
            query = """
                SELECT pt.transaction_type, pt.transaction_date, pt.shares, pt.price, pt.amount, 
                       t.id AS ticker_id, t.ticker AS symbol
                FROM portfolio_transactions pt 
                JOIN portfolio p ON pt.portfolio_id = p.id 
                JOIN portfolio_securities ps ON ps.id = pt.security_id 
                JOIN tickers t ON t.id = ps.ticker_id 
                WHERE p.id = %s AND pt.transaction_date <= %s
                ORDER BY pt.transaction_date
            """
            values = (portfolio_id, calculation_date)
            cursor.execute(query, values)
            transactions = cursor.fetchall()

            if not transactions:
                print(f"No transactions found for portfolio {portfolio_id} before {calculation_date}")
                return 0.0

            # Calculate the number of shares held for each stock
            shares_held = {}
            ticker_symbols = {}  # Map ticker_id to symbol for easier lookup
            
            # Track cost basis for debugging
            cost_basis = {}
            
            for transaction in transactions:
                transaction_type, transaction_date, shares, price, amount, ticker_id, symbol = transaction
                ticker_symbols[ticker_id] = symbol
                
                # Convert Decimal types to float for calculation
                shares = float(shares) if shares is not None else 0
                price = float(price) if price is not None else 0
                amount = float(amount) if amount is not None else 0
                
                if transaction_type == 'buy':
                    if ticker_id in shares_held:
                        shares_held[ticker_id] += shares
                        cost_basis[ticker_id] += shares * price
                    else:
                        shares_held[ticker_id] = shares
                        cost_basis[ticker_id] = shares * price
                elif transaction_type == 'sell':
                    if ticker_id in shares_held:
                        shares_held[ticker_id] -= shares
                        # Adjust cost basis proportionally (simple average cost method)
                        if shares_held[ticker_id] > 0:
                            cost_basis[ticker_id] = cost_basis[ticker_id] * (1 - (shares / (shares_held[ticker_id] + shares)))
                    else:
                        shares_held[ticker_id] = -shares
                        cost_basis[ticker_id] = 0

            # Format the calculation date for yfinance
            calc_date_str = calculation_date.strftime('%Y-%m-%d')
            # Need to get the next day for yfinance end date (it's exclusive)
            next_day = (calculation_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # For debugging
            print(f"\nCalculating portfolio value as of {calc_date_str}")
            
            # Fetch historical stock prices for the calculation date
            stock_prices = {}
            for ticker_id, symbol in ticker_symbols.items():
                if shares_held[ticker_id] <= 0:
                    continue
                    
                # Try to get data from investing.activity table if it exists
                try:
                    # Try to get historical price from database first
                    hist_query = """
                        SELECT price_date, close_price 
                        FROM investing.activity 
                        WHERE ticker = %s AND price_date <= %s
                        ORDER BY price_date DESC
                        LIMIT 1
                    """
                    cursor.execute(hist_query, (symbol, calculation_date))
                    hist_result = cursor.fetchone()
                    
                    if hist_result:
                        price_date, close_price = hist_result
                        stock_prices[ticker_id] = float(close_price)
                        print(f"  {symbol}: Using price from database ({price_date}): ${close_price:.2f}")
                        continue
                    else:
                        print(f"  {symbol}: No historical price data found in database, trying yfinance")
                except Exception as e:
                    # If the investing.activity table doesn't exist or other error
                    print(f"  Could not query database for historical prices: {e}")
                
                # Try yfinance as primary source or fallback
                try:
                    stock = yf.Ticker(symbol)
                    # Get data for a few days before in case the exact date is a holiday/weekend
                    start_date = (calculation_date - timedelta(days=5)).strftime('%Y-%m-%d')
                    end_date = next_day
                    hist_data = stock.history(start=start_date, end=end_date)
                    
                    if hist_data.empty:
                        print(f"  Warning: No historical data found for {symbol} in yfinance")
                        # Fall back to transaction price if available
                        for transaction in reversed(transactions):
                            if transaction[5] == ticker_id:  # ticker_id
                                # Make sure to convert to float
                                stock_prices[ticker_id] = float(transaction[3])  # price
                                print(f"  Using last transaction price for {symbol}: ${stock_prices[ticker_id]:.2f}")
                                break
                    else:
                        # Convert all timestamps to tz-naive for comparison to avoid timezone issues
                        hist_data.index = hist_data.index.tz_localize(None)
                        calc_timestamp = pd.Timestamp(calculation_date)
                        
                        # Get the closest date on or before calculation_date
                        valid_dates = hist_data.index[hist_data.index <= calc_timestamp]
                        if len(valid_dates) > 0:
                            closest_date = valid_dates[-1]
                            close_price = float(hist_data.loc[closest_date, 'Close'])
                            stock_prices[ticker_id] = close_price
                            print(f"  {symbol}: Using price from {closest_date.date()}: ${close_price:.2f}")
                        else:
                            # Fall back to first available price
                            first_date = hist_data.index[0]
                            close_price = float(hist_data.loc[first_date, 'Close'])
                            stock_prices[ticker_id] = close_price
                            print(f"  {symbol}: No prior data, using earliest available from {first_date.date()}: ${close_price:.2f}")
                except Exception as e:
                    print(f"Error retrieving data for {symbol}: {e}")
                    # Try to use the last known transaction price as a fallback
                    for transaction in reversed(transactions):
                        if transaction[5] == ticker_id:  # ticker_id
                            stock_prices[ticker_id] = transaction[3]  # price
                            print(f"  Using last transaction price for {symbol}: ${stock_prices[ticker_id]:.2f}")
                            break

            # Calculate the portfolio value
            portfolio_value = 0.0  # Initialize as float
            print("\nPortfolio Positions:")
            for ticker_id, shares in shares_held.items():
                if shares > 0 and ticker_id in stock_prices:
                    symbol = ticker_symbols[ticker_id]
                    share_count = float(shares)
                    price = stock_prices[ticker_id]
                    position_value = share_count * price
                    avg_cost = cost_basis[ticker_id] / share_count if share_count > 0 else 0
                    
                    print(f"  {symbol}: {share_count} shares @ ${price:.2f} = ${position_value:.2f} (avg cost: ${avg_cost:.2f})")
                    portfolio_value += position_value

            # Add any dividend amounts received
            query = "SELECT SUM(amount) AS total_dividends " \
                    "FROM portfolio_transactions pt " \
                    "JOIN portfolio p ON pt.portfolio_id = p.id " \
                    "WHERE p.id = %s AND pt.transaction_type = 'dividend' AND pt.transaction_date <= %s"
            values = (portfolio_id, calculation_date)
            cursor.execute(query, values)
            result = cursor.fetchone()
            total_dividends = float(result[0]) if result[0] else 0.0
            if total_dividends > 0:
                print(f"  Dividends: ${total_dividends:.2f}")
            portfolio_value += total_dividends

            print(f"\nTotal portfolio value: ${portfolio_value:.2f}")

            # Check for existing value on this date
            query = "SELECT id FROM portfolio_value WHERE portfolio_id = %s AND calculation_date = %s"
            cursor.execute(query, (portfolio_id, calculation_date))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                query = "UPDATE portfolio_value SET value = %s WHERE portfolio_id = %s AND calculation_date = %s"
                values = (portfolio_value, portfolio_id, calculation_date)
                cursor.execute(query, values)
                print(f"Updated existing value record for {calculation_date}")
            else:
                # Insert new record
                query = "INSERT INTO portfolio_value (portfolio_id, calculation_date, value) VALUES (%s, %s, %s)"
                values = (portfolio_id, calculation_date, portfolio_value)
                cursor.execute(query, values)
                print(f"Created new value record for {calculation_date}")
                
            self.connection.commit()
            return portfolio_value

        except mysql.connector.Error as e:
            print(f"Error calculating portfolio value: {e}")
            return None

    def get_ticker_symbol(self, ticker_id):
        try:
            cursor = self.connection.cursor()
            query = "SELECT ticker FROM tickers WHERE id = %s"
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
            
    def get_portfolio_performance(self, portfolio_id, start_date=None, end_date=None):
        """
        Retrieve portfolio performance data between specified dates.
        If no dates are specified, returns all available data.
        
        Args:
            portfolio_id (int): The ID of the portfolio
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
            
        Returns:
            pandas.DataFrame: DataFrame with dates and portfolio values
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Build query based on provided date parameters
            query = "SELECT calculation_date, value FROM portfolio_value WHERE portfolio_id = %s"
            values = [portfolio_id]
            
            if start_date:
                query += " AND calculation_date >= %s"
                values.append(start_date)
                
            if end_date:
                query += " AND calculation_date <= %s"
                values.append(end_date)
                
            query += " ORDER BY calculation_date ASC"
            
            cursor.execute(query, values)
            results = cursor.fetchall()
            
            if not results:
                return pd.DataFrame(columns=['date', 'value'])
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(results)
            df.rename(columns={'calculation_date': 'date'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
            
        except mysql.connector.Error as e:
            print(f"Error retrieving portfolio performance: {e}")
            return pd.DataFrame(columns=['date', 'value'])
            
    def calculate_performance_metrics(self, portfolio_id, start_date=None, end_date=None):
        """
        Calculate performance metrics for the specified portfolio.
        
        Args:
            portfolio_id (int): The ID of the portfolio
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
            
        Returns:
            dict: Dictionary containing performance metrics
        """
        df = self.get_portfolio_performance(portfolio_id, start_date, end_date)
        
        if df.empty:
            return {
                'total_return': None,
                'annualized_return': None,
                'initial_value': None,
                'final_value': None,
                'period_days': None
            }
            
        initial_value = float(df['value'].iloc[0])
        final_value = float(df['value'].iloc[-1])
        total_return_pct = ((final_value / initial_value) - 1) * 100
        
        # Calculate period in days
        first_date = df.index[0].to_pydatetime().date()
        last_date = df.index[-1].to_pydatetime().date()
        period_days = (last_date - first_date).days
        
        # Calculate annualized return if period is longer than a day
        annualized_return = None
        if period_days > 0:
            annualized_return = ((1 + (total_return_pct/100)) ** (365/period_days) - 1) * 100
                
        return {
            'total_return': total_return_pct,
            'annualized_return': annualized_return,
            'initial_value': initial_value,
            'final_value': final_value,
            'period_days': period_days
        }
        
    def update_portfolio_value_history(self, portfolio_id, days_back=30):
        """
        Update or create portfolio value history for the last X days.
        
        Args:
            portfolio_id (int): The ID of the portfolio
            days_back (int): Number of days back to calculate values for
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            today = date.today()
            
            # For each day in the specified range, calculate and store the portfolio value
            for i in range(days_back, -1, -1):
                calculation_date = today - timedelta(days=i)
                self.calculate_portfolio_value(portfolio_id, calculation_date)
                
            return True
                
        except Exception as e:
            print(f"Error updating portfolio value history: {e}")
            return False
            
    def recalculate_historical_values(self, portfolio_id, from_date=None):
        """
        Recalculate portfolio historical values after adding/modifying historical transactions.
        
        This method will:
        1. If from_date is provided, delete all portfolio value entries from that date forward
        2. If from_date is not provided, find the earliest transaction date and use that
        3. Recalculate portfolio values for each day from the determined date to today
        
        Args:
            portfolio_id (int): The ID of the portfolio
            from_date (str, optional): Date in YYYY-MM-DD format to start recalculation from
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            today = date.today()
            
            # If from_date not provided, find earliest transaction date
            if not from_date:
                query = """
                    SELECT MIN(transaction_date) as earliest_date
                    FROM portfolio_transactions
                    WHERE portfolio_id = %s
                """
                cursor.execute(query, (portfolio_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    from_date = result[0]
                else:
                    # Default to 30 days ago if no transactions found
                    from_date = today - timedelta(days=30)
            
            # Convert string date to date object if necessary
            if isinstance(from_date, str):
                from_date = pd.to_datetime(from_date).date()
                
            print(f"Recalculating portfolio values from {from_date} to {today}")
                
            # Delete existing portfolio values from from_date forward
            query = """
                DELETE FROM portfolio_value
                WHERE portfolio_id = %s AND calculation_date >= %s
            """
            cursor.execute(query, (portfolio_id, from_date))
            self.connection.commit()
            deleted_rows = cursor.rowcount
            print(f"Deleted {deleted_rows} historical portfolio value records")
            
            # Calculate the number of days to recalculate
            days_to_calculate = (today - from_date).days + 1
            
            # Recalculate for each day
            calculation_dates = [from_date + timedelta(days=i) for i in range(days_to_calculate)]
            for calc_date in calculation_dates:
                print(f"Calculating portfolio value for {calc_date}")
                self.calculate_portfolio_value(portfolio_id, calc_date)
                
            return True
                
        except Exception as e:
            print(f"Error recalculating historical portfolio values: {e}")
            self.connection.rollback()
            return False

    def generate_performance_chart(self, portfolio_id, start_date=None, end_date=None):
        """
        Generate a performance chart for the specified portfolio and date range.
        Returns a base64-encoded image that can be displayed in the terminal.
        
        Args:
            portfolio_id (int): The ID of the portfolio
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
            
        Returns:
            str: Base64-encoded PNG image or None if chart generation fails
        """
        try:
            # Get portfolio name
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT name FROM portfolio WHERE id = %s", (portfolio_id,))
            result = cursor.fetchone()
            portfolio_name = result['name'] if result else f"Portfolio {portfolio_id}"
            
            # Get performance data
            df = self.get_portfolio_performance(portfolio_id, start_date, end_date)
            
            if df.empty:
                print("No performance data available for the specified period.")
                return None
                
            # Convert decimal values to float for plotting
            df['value'] = df['value'].astype(float)
            
            # Create the figure and plot
            plt.figure(figsize=(10, 6))
            plt.plot(df.index, df['value'], marker='o', linestyle='-')
            plt.title(f"{portfolio_name} Performance")
            plt.xlabel('Date')
            plt.ylabel('Portfolio Value ($)')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save the plot to a BytesIO object
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            
            # Convert to base64 for terminal display
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            # Save the image to a temporary file in the user's home directory
            home_dir = os.path.expanduser("~")
            file_path = os.path.join(home_dir, f"portfolio_{portfolio_id}_performance.png")
            with open(file_path, 'wb') as f:
                f.write(buffer.getvalue())
            
            return file_path
            
        except Exception as e:
            print(f"Error generating performance chart: {e}")
            return None
