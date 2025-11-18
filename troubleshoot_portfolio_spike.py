#!/usr/bin/env python3
"""
Portfolio Data Spike Troubleshooting Tool

This script helps identify data anomalies that could cause sharp spikes in portfolio value charts.
It analyzes transactions, cash movements, and price data around suspicious time periods.
"""

from datetime import date, datetime, timedelta

import mysql.connector
import pandas as pd

from data.config import Config
from data.portfolio_value_service import PortfolioValueService


class PortfolioSpikeTroubleshooter:
    def __init__(self):
        # Load database configuration
        config = Config()
        self.db_config = config.get_database_config()
        self.current_connection = None
        self.portfolio_service = None

    def connect(self):
        """Establish database connection."""
        try:
            self.current_connection = mysql.connector.connect(**self.db_config)
            self.portfolio_service = PortfolioValueService(
                self.db_config["user"],
                self.db_config["password"],
                self.db_config["host"],
                self.db_config["database"],
            )
            print("✓ Database connection established")
        except mysql.connector.Error as e:
            print(f"✗ Error connecting to database: {e}")
            return False
        return True

    def close(self):
        """Close database connections."""
        if self.current_connection:
            self.current_connection.close()
        if self.portfolio_service:
            self.portfolio_service.close_connection()

    def get_portfolios(self):
        """Get list of all portfolios."""
        try:
            cursor = self.current_connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name, description FROM portfolio WHERE active = 1")
            return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Error getting portfolios: {e}")
            return []

    def analyze_portfolio_value_timeline(self, portfolio_id, start_date=None, end_date=None):
        """
        Analyze portfolio value over time to identify spikes.

        Args:
            portfolio_id (int): Portfolio ID to analyze
            start_date (date, optional): Start date for analysis
            end_date (date, optional): End date for analysis
        """
        print(f"\n{'=' * 60}")
        print(f"PORTFOLIO VALUE TIMELINE ANALYSIS - Portfolio {portfolio_id}")
        print(f"{'=' * 60}")

        if start_date is None:
            start_date = date(2024, 1, 1)
        if end_date is None:
            end_date = date.today()

        # Calculate portfolio values for each day in the range
        values = []
        current_date = start_date

        print(f"Calculating daily values from {start_date} to {end_date}...")

        while current_date <= end_date:
            try:
                result = self.portfolio_service.calculate_portfolio_value(
                    portfolio_id,
                    calculation_date=current_date,
                    include_cash=True,
                    include_dividends=True,
                )

                values.append(
                    {
                        "date": current_date,
                        "total_value": result["total_value"],
                        "stock_value": result["stock_value"],
                        "cash_balance": result["cash_balance"],
                        "dividend_value": result["dividend_value"],
                        "position_count": result["metadata"]["position_count"],
                    }
                )

                # Skip weekends for faster processing
                if current_date.weekday() < 4:  # Mon-Thu
                    current_date += timedelta(days=1)
                else:  # Fri
                    current_date += timedelta(days=3)  # Skip to Monday

            except Exception as e:
                print(f"Error calculating value for {current_date}: {e}")
                current_date += timedelta(days=1)

        # Convert to DataFrame for analysis
        df = pd.DataFrame(values)
        if df.empty:
            print("No data found for analysis")
            return None, None

        # Calculate daily changes
        df["daily_change"] = df["total_value"].diff()
        df["daily_change_pct"] = df["total_value"].pct_change() * 100

        # Identify significant spikes (>10% daily change)
        spikes = df[abs(df["daily_change_pct"]) > 10].copy()

        print("\nSUMMARY:")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"Starting value: ${df['total_value'].iloc[0]:,.2f}")
        print(f"Ending value: ${df['total_value'].iloc[-1]:,.2f}")
        print(f"Maximum value: ${df['total_value'].max():,.2f}")
        print(f"Minimum value: ${df['total_value'].min():,.2f}")
        print(f"Number of significant spikes (>10%): {len(spikes)}")

        if not spikes.empty:
            print("\nSIGNIFICANT SPIKES DETECTED:")
            print("-" * 80)
            for _, spike in spikes.iterrows():
                print(f"Date: {spike['date']}")
                print(f"  Value: ${spike['total_value']:,.2f}")
                print(f"  Daily Change: ${spike['daily_change']:,.2f} ({spike['daily_change_pct']:+.2f}%)")
                print(f"  Stock Value: ${spike['stock_value']:,.2f}")
                print(f"  Cash Balance: ${spike['cash_balance']:,.2f}")
                print(f"  Positions: {spike['position_count']}")
                print()

        return df, spikes

    def analyze_transactions_around_date(self, portfolio_id, target_date, days_window=7):
        """
        Analyze all transactions around a specific date.

        Args:
            portfolio_id (int): Portfolio ID
            target_date (date): Date to analyze around
            days_window (int): Number of days before/after to include
        """
        print(f"\n{'=' * 60}")
        print(f"TRANSACTION ANALYSIS AROUND {target_date}")
        print(f"{'=' * 60}")

        start_date = target_date - timedelta(days=days_window)
        end_date = target_date + timedelta(days=days_window)

        try:
            cursor = self.current_connection.cursor(dictionary=True)

            # Get all transactions in the window
            query = """
                SELECT 
                    t.*,
                    s.ticker_id,
                    tk.ticker as symbol,
                    (t.shares * t.price) as transaction_value
                FROM portfolio_transactions t
                LEFT JOIN portfolio_securities s ON t.security_id = s.id
                LEFT JOIN tickers tk ON s.ticker_id = tk.id
                WHERE t.portfolio_id = %s 
                AND t.transaction_date BETWEEN %s AND %s
                ORDER BY t.transaction_date ASC, t.id ASC
            """
            cursor.execute(query, (portfolio_id, start_date, end_date))
            transactions = cursor.fetchall()

            if not transactions:
                print(f"No transactions found between {start_date} and {end_date}")
                return

            print(f"Found {len(transactions)} transactions:")
            print("-" * 100)
            print(f"{'Date':<12} {'Type':<10} {'Symbol':<8} {'Shares':<10} {'Price':<10} {'Amount':<12} {'Value':<12}")
            print("-" * 100)

            total_buy_value = 0
            total_sell_value = 0

            for trans in transactions:
                date_str = trans["transaction_date"].strftime("%Y-%m-%d")
                trans_type = trans["transaction_type"] or "N/A"
                symbol = trans["symbol"] or "CASH"
                shares = trans["shares"] or 0
                price = trans["price"] or 0
                amount = trans["amount"] or 0
                value = trans["transaction_value"] or amount or 0

                print(
                    f"{date_str:<12} {trans_type:<10} {symbol:<8} {shares:<10.2f} {price:<10.2f} {amount:<12.2f} {value:<12.2f}"
                )

                if trans_type == "buy":
                    total_buy_value += value
                elif trans_type == "sell":
                    total_sell_value += value

            print("-" * 100)
            print(f"Total Buy Value: ${total_buy_value:,.2f}")
            print(f"Total Sell Value: ${total_sell_value:,.2f}")
            print(f"Net Transaction Value: ${total_buy_value - total_sell_value:,.2f}")

            return transactions

        except mysql.connector.Error as e:
            print(f"Error analyzing transactions: {e}")
            return []

    def analyze_cash_history_around_date(self, portfolio_id, target_date, days_window=7):
        """
        Analyze cash balance history around a specific date.

        Args:
            portfolio_id (int): Portfolio ID
            target_date (date): Date to analyze around
            days_window (int): Number of days before/after to include
        """
        print(f"\n{'=' * 60}")
        print(f"CASH HISTORY ANALYSIS AROUND {target_date}")
        print(f"{'=' * 60}")

        start_date = target_date - timedelta(days=days_window)
        end_date = target_date + timedelta(days=days_window)

        try:
            cursor = self.current_connection.cursor(dictionary=True)

            # Check if cash_balance_history table exists
            cursor.execute(
                """
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'cash_balance_history'
            """
            )

            if cursor.fetchone()["count"] == 0:
                print("Cash balance history table does not exist")
                return

            # Get cash transactions in the window
            query = """
                SELECT *
                FROM cash_balance_history
                WHERE portfolio_id = %s 
                AND transaction_date BETWEEN %s AND %s
                ORDER BY transaction_date ASC, id ASC
            """
            cursor.execute(query, (portfolio_id, start_date, end_date))
            cash_transactions = cursor.fetchall()

            if not cash_transactions:
                print(f"No cash transactions found between {start_date} and {end_date}")
                return

            print(f"Found {len(cash_transactions)} cash transactions:")
            print("-" * 80)
            print(f"{'Date':<20} {'Type':<15} {'Amount':<12} {'Balance After':<15} {'Description':<20}")
            print("-" * 80)

            for trans in cash_transactions:
                date_str = trans["transaction_date"].strftime("%Y-%m-%d %H:%M")
                trans_type = trans["transaction_type"]
                amount = float(trans["amount"])
                balance_after = float(trans["balance_after"])
                description = trans["description"] or ""

                print(f"{date_str:<20} {trans_type:<15} {amount:<12.2f} {balance_after:<15.2f} {description:<20}")

            return cash_transactions

        except mysql.connector.Error as e:
            print(f"Error analyzing cash history: {e}")
            return []

    def check_for_duplicate_transactions(self, portfolio_id):
        """
        Check for potential duplicate transactions that could cause spikes.
        """
        print(f"\n{'=' * 60}")
        print(f"DUPLICATE TRANSACTION CHECK - Portfolio {portfolio_id}")
        print(f"{'=' * 60}")

        try:
            cursor = self.current_connection.cursor(dictionary=True)

            # Look for potential duplicates based on same date, type, symbol, shares, price
            query = """
                SELECT 
                    t.transaction_date,
                    t.transaction_type,
                    tk.ticker as symbol,
                    t.shares,
                    t.price,
                    t.amount,
                    COUNT(*) as duplicate_count,
                    GROUP_CONCAT(t.id) as transaction_ids
                FROM portfolio_transactions t
                LEFT JOIN portfolio_securities s ON t.security_id = s.id
                LEFT JOIN tickers tk ON s.ticker_id = tk.id
                WHERE t.portfolio_id = %s
                GROUP BY t.transaction_date, t.transaction_type, tk.ticker, t.shares, t.price, t.amount
                HAVING COUNT(*) > 1
                ORDER BY t.transaction_date DESC
            """
            cursor.execute(query, (portfolio_id,))
            duplicates = cursor.fetchall()

            if not duplicates:
                print("✓ No duplicate transactions found")
                return

            print(f"⚠ Found {len(duplicates)} sets of potential duplicate transactions:")
            print("-" * 100)

            for dup in duplicates:
                print(f"Date: {dup['transaction_date']}")
                print(f"  Type: {dup['transaction_type']}, Symbol: {dup['symbol']}")
                print(f"  Shares: {dup['shares']}, Price: {dup['price']}, Amount: {dup['amount']}")
                print(f"  Count: {dup['duplicate_count']}, IDs: {dup['transaction_ids']}")
                print()

            return duplicates

        except mysql.connector.Error as e:
            print(f"Error checking for duplicates: {e}")
            return []

    def check_for_unusual_prices(self, portfolio_id, price_change_threshold=500):
        """
        Check for transactions with unusually high prices that could cause spikes.

        Args:
            portfolio_id (int): Portfolio ID
            price_change_threshold (float): Percentage change threshold to flag as unusual
        """
        print(f"\n{'=' * 60}")
        print(f"UNUSUAL PRICE CHECK - Portfolio {portfolio_id}")
        print(f"{'=' * 60}")

        try:
            cursor = self.current_connection.cursor(dictionary=True)

            # Get all buy/sell transactions with prices
            query = """
                SELECT 
                    t.*,
                    tk.ticker as symbol,
                    LAG(t.price) OVER (PARTITION BY tk.ticker ORDER BY t.transaction_date) as prev_price
                FROM portfolio_transactions t
                JOIN portfolio_securities s ON t.security_id = s.id
                JOIN tickers tk ON s.ticker_id = tk.id
                WHERE t.portfolio_id = %s 
                AND t.transaction_type IN ('buy', 'sell')
                AND t.price IS NOT NULL
                AND t.price > 0
                ORDER BY tk.ticker, t.transaction_date
            """
            cursor.execute(query, (portfolio_id,))
            transactions = cursor.fetchall()

            unusual_prices = []

            for trans in transactions:
                if trans["prev_price"] and trans["prev_price"] > 0:
                    price_change_pct = ((trans["price"] - trans["prev_price"]) / trans["prev_price"]) * 100

                    if abs(price_change_pct) > price_change_threshold:
                        unusual_prices.append({"transaction": trans, "price_change_pct": price_change_pct})

            if not unusual_prices:
                print(f"✓ No unusual price changes found (threshold: {price_change_threshold}%)")
                return

            print(f"⚠ Found {len(unusual_prices)} transactions with unusual price changes:")
            print("-" * 100)

            for item in unusual_prices:
                trans = item["transaction"]
                change_pct = item["price_change_pct"]

                print(f"Date: {trans['transaction_date']}")
                print(f"  Symbol: {trans['symbol']}, Type: {trans['transaction_type']}")
                print(f"  Previous Price: ${trans['prev_price']:.2f}")
                print(f"  Current Price: ${trans['price']:.2f}")
                print(f"  Change: {change_pct:+.2f}%")
                print(f"  Transaction ID: {trans['id']}")
                print()

            return unusual_prices

        except mysql.connector.Error as e:
            print(f"Error checking for unusual prices: {e}")
            return []

    def run_comprehensive_analysis(self, portfolio_id, spike_date=None):
        """
        Run a comprehensive analysis to identify the cause of portfolio value spikes.

        Args:
            portfolio_id (int): Portfolio ID to analyze
            spike_date (date, optional): Specific date where spike occurred
        """
        print(f"\n{'#' * 80}")
        print("COMPREHENSIVE PORTFOLIO SPIKE ANALYSIS")
        print(f"Portfolio ID: {portfolio_id}")
        if spike_date:
            print(f"Focus Date: {spike_date}")
        print(f"{'#' * 80}")

        # 1. Portfolio value timeline analysis
        df, spikes = self.analyze_portfolio_value_timeline(portfolio_id)

        # 2. If no specific spike date provided, use the largest spike from timeline
        if spike_date is None and not spikes.empty:
            spike_date = spikes.loc[spikes["daily_change_pct"].abs().idxmax(), "date"]
            print(f"\nUsing largest spike date for detailed analysis: {spike_date}")

        if spike_date:
            # 3. Transaction analysis around spike date
            self.analyze_transactions_around_date(portfolio_id, spike_date)

            # 4. Cash history analysis around spike date
            self.analyze_cash_history_around_date(portfolio_id, spike_date)

        # 5. Check for duplicate transactions
        self.check_for_duplicate_transactions(portfolio_id)

        # 6. Check for unusual prices
        self.check_for_unusual_prices(portfolio_id)

        print(f"\n{'#' * 80}")
        print("ANALYSIS COMPLETE")
        print(f"{'#' * 80}")


def main():
    """Main function to run the troubleshooting tool."""
    troubleshooter = PortfolioSpikeTroubleshooter()

    if not troubleshooter.connect():
        return

    try:
        # Get available portfolios
        portfolios = troubleshooter.get_portfolios()

        if not portfolios:
            print("No active portfolios found")
            return

        print("Available portfolios:")
        for portfolio in portfolios:
            print(f"  {portfolio['id']}: {portfolio['name']} - {portfolio['description']}")

        # Get user input for portfolio to analyze
        while True:
            try:
                portfolio_id = int(input(f"\nEnter portfolio ID to analyze (1-{len(portfolios)}): "))
                if any(p["id"] == portfolio_id for p in portfolios):
                    break
                else:
                    print("Invalid portfolio ID")
            except ValueError:
                print("Please enter a valid number")

        # Ask if user wants to specify a spike date
        spike_date_input = input("Enter spike date to focus on (YYYY-MM-DD) or press Enter to auto-detect: ").strip()
        spike_date = None

        if spike_date_input:
            try:
                spike_date = datetime.strptime(spike_date_input, "%Y-%m-%d").date()
            except ValueError:
                print("Invalid date format, will auto-detect spikes")

        # Run comprehensive analysis
        troubleshooter.run_comprehensive_analysis(portfolio_id, spike_date)

    finally:
        troubleshooter.close()


if __name__ == "__main__":
    main()
