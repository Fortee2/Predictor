#!/usr/bin/env python3
"""
Quick Data Validation Script

A simplified tool to quickly identify common data issues that cause portfolio value spikes.
"""

import mysql.connector
from datetime import datetime, date, timedelta
from data.config import Config

def connect_to_db():
    """Connect to the database."""
    config = Config()
    db_config = config.get_database_config()
    try:
        connection = mysql.connector.connect(
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            database=db_config['database']
        )
        return connection
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return None

def check_for_data_issues(portfolio_id, focus_date=None):
    """
    Quick check for common data issues that cause spikes.
    
    Args:
        portfolio_id (int): Portfolio ID to check
        focus_date (str): Date to focus on in YYYY-MM-DD format (optional)
    """
    connection = connect_to_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        print(f"QUICK DATA VALIDATION - Portfolio {portfolio_id}")
        print("=" * 60)
        
        # 1. Check for transactions with unusually high prices
        print("\n1. CHECKING FOR UNUSUAL TRANSACTION PRICES...")
        query = """
            SELECT t.id, t.transaction_date, t.transaction_type, tk.ticker, 
                   t.shares, t.price, (t.shares * t.price) as value
            FROM portfolio_transactions t
            JOIN portfolio_securities s ON t.security_id = s.id
            JOIN tickers tk ON s.ticker_id = tk.id
            WHERE t.portfolio_id = %s 
            AND t.price > 1000  -- Flag prices over $1000
            ORDER BY t.price DESC
            LIMIT 10
        """
        cursor.execute(query, (portfolio_id,))
        high_prices = cursor.fetchall()
        
        if high_prices:
            print(f"⚠ Found {len(high_prices)} transactions with high prices:")
            for trans in high_prices:
                print(f"  {trans['transaction_date']} - {trans['ticker']}: ${trans['price']:.2f} "
                      f"({trans['shares']} shares = ${trans['value']:,.2f})")
        else:
            print("✓ No unusually high prices found")
        
        # 2. Check for duplicate transactions
        print("\n2. CHECKING FOR DUPLICATE TRANSACTIONS...")
        query = """
            SELECT transaction_date, transaction_type, tk.ticker, shares, price, 
                   COUNT(*) as count, GROUP_CONCAT(t.id) as ids
            FROM portfolio_transactions t
            LEFT JOIN portfolio_securities s ON t.security_id = s.id
            LEFT JOIN tickers tk ON s.ticker_id = tk.id
            WHERE t.portfolio_id = %s
            GROUP BY transaction_date, transaction_type, tk.ticker, shares, price
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 5
        """
        cursor.execute(query, (portfolio_id,))
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"⚠ Found {len(duplicates)} sets of potential duplicates:")
            for dup in duplicates:
                print(f"  {dup['transaction_date']} - {dup['ticker']}: {dup['count']} identical transactions")
                print(f"    IDs: {dup['ids']}")
        else:
            print("✓ No duplicate transactions found")
        
        # 3. Check for large single-day transaction volumes
        print("\n3. CHECKING FOR LARGE TRANSACTION VOLUMES...")
        query = """
            SELECT transaction_date, 
                   SUM(CASE WHEN transaction_type = 'buy' THEN shares * price ELSE 0 END) as buy_volume,
                   SUM(CASE WHEN transaction_type = 'sell' THEN shares * price ELSE 0 END) as sell_volume,
                   COUNT(*) as transaction_count
            FROM portfolio_transactions t
            JOIN portfolio_securities s ON t.security_id = s.id
            WHERE t.portfolio_id = %s 
            AND t.transaction_type IN ('buy', 'sell')
            GROUP BY transaction_date
            HAVING (buy_volume + sell_volume) > 50000  -- Flag days with >$50k volume
            ORDER BY (buy_volume + sell_volume) DESC
            LIMIT 10
        """
        cursor.execute(query, (portfolio_id,))
        large_volumes = cursor.fetchall()
        
        if large_volumes:
            print(f"⚠ Found {len(large_volumes)} days with large transaction volumes:")
            for vol in large_volumes:
                total_vol = vol['buy_volume'] + vol['sell_volume']
                print(f"  {vol['transaction_date']}: ${total_vol:,.2f} "
                      f"(Buy: ${vol['buy_volume']:,.2f}, Sell: ${vol['sell_volume']:,.2f})")
        else:
            print("✓ No unusually large transaction volumes found")
        
        # 4. Check for transactions around focus date if provided
        if focus_date:
            print(f"\n4. TRANSACTIONS AROUND {focus_date}...")
            focus_dt = datetime.strptime(focus_date, '%Y-%m-%d').date()
            start_date = focus_dt - timedelta(days=3)
            end_date = focus_dt + timedelta(days=3)
            
            query = """
                SELECT t.transaction_date, t.transaction_type, tk.ticker, 
                       t.shares, t.price, (t.shares * t.price) as value
                FROM portfolio_transactions t
                LEFT JOIN portfolio_securities s ON t.security_id = s.id
                LEFT JOIN tickers tk ON s.ticker_id = tk.id
                WHERE t.portfolio_id = %s 
                AND t.transaction_date BETWEEN %s AND %s
                ORDER BY t.transaction_date, t.id
            """
            cursor.execute(query, (portfolio_id, start_date, end_date))
            focus_transactions = cursor.fetchall()
            
            if focus_transactions:
                print(f"Found {len(focus_transactions)} transactions around {focus_date}:")
                for trans in focus_transactions:
                    symbol = trans['ticker'] or 'CASH'
                    shares = trans['shares'] or 0
                    price = trans['price'] or 0
                    value = trans['value'] or 0
                    print(f"  {trans['transaction_date']} - {trans['transaction_type']} {symbol}: "
                          f"{shares} @ ${price:.2f} = ${value:,.2f}")
            else:
                print(f"No transactions found around {focus_date}")
        
        # 5. Check cash balance history if table exists
        print("\n5. CHECKING CASH BALANCE HISTORY...")
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'cash_balance_history'
        """)
        
        if cursor.fetchone()['count'] > 0:
            query = """
                SELECT transaction_date, transaction_type, amount, balance_after
                FROM cash_balance_history
                WHERE portfolio_id = %s
                AND ABS(amount) > 10000  -- Flag large cash movements
                ORDER BY ABS(amount) DESC
                LIMIT 10
            """
            cursor.execute(query, (portfolio_id,))
            large_cash = cursor.fetchall()
            
            if large_cash:
                print(f"⚠ Found {len(large_cash)} large cash movements:")
                for cash in large_cash:
                    print(f"  {cash['transaction_date']} - {cash['transaction_type']}: "
                          f"${cash['amount']:,.2f} (Balance: ${cash['balance_after']:,.2f})")
            else:
                print("✓ No unusually large cash movements found")
        else:
            print("Cash balance history table not found")
        
        print("\n" + "=" * 60)
        print("QUICK CHECK COMPLETE")
        print("=" * 60)
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
    finally:
        connection.close()

def main():
    """Main function."""
    print("Portfolio Data Quick Check")
    print("=" * 30)
    
    try:
        portfolio_id = int(input("Enter portfolio ID to check: "))
        focus_date = input("Enter focus date (YYYY-MM-DD) or press Enter to skip: ").strip()
        
        if not focus_date:
            focus_date = None
        
        check_for_data_issues(portfolio_id, focus_date)
        
    except ValueError:
        print("Invalid input. Please enter a valid portfolio ID.")
    except KeyboardInterrupt:
        print("\nOperation cancelled.")

if __name__ == "__main__":
    main()
