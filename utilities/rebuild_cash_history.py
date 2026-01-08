"""
Rebuild the cash balance history for a given portfolio based on its transactions.
Useful for correcting discrepancies or initializing history for existing portfolios.
"""

import sys
import os

# Add parent directory to path to allow imports from data module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.config import Config
from data.portfolio_dao import PortfolioDAO
from data.utility import DatabaseConnectionPool


def main():
    if len(sys.argv) != 2:
        print("Usage: python rebuild_cash_history.py <portfolio_id>")
        sys.exit(1)

    try:
        portfolio_id = int(sys.argv[1])

        # Get database configuration
        config = Config()
        db_config = config.get_database_config()

        # Initialize PortfolioDAO
        connection_pool = DatabaseConnectionPool(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            database=db_config["database"],
        )

        portfolio_dao = PortfolioDAO(
            connection_pool,
        )

        # Open connection
        with connection_pool.get_connection() as connection:
            cursor = connection.cursor()

            try:
                # Delete existing history for this portfolio
                delete_query = "DELETE FROM cash_balance_history WHERE portfolio_id = %s"
                cursor.execute(delete_query, (portfolio_id,))
                connection.commit()
                print("Cleared existing cash history")

                # Get initial portfolio funding
                query = "SELECT date_added, intial_funds FROM portfolio WHERE id = %s"
                cursor.execute(query, (portfolio_id,))
                result = cursor.fetchone()
                creation_date = result[0]
                initial_cash = float(result[1]) if result[1] else 0

                if initial_cash > 0:
                    # Record initial funding
                    insert_query = """
                        INSERT INTO cash_balance_history 
                        (portfolio_id, transaction_date, amount, transaction_type, description, balance_after)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        portfolio_id,
                        creation_date,
                        initial_cash,
                        "initial",
                        "Initial portfolio funding",
                        initial_cash,
                    )
                    cursor.execute(insert_query, values)
                    connection.commit()
                    print(f"Recorded initial funding: ${initial_cash:.2f}")

                # Get all transactions that affect cash
                query = """
                    SELECT 
                        pt.transaction_date,
                        pt.transaction_type,
                        pt.shares,
                        pt.price,
                        pt.amount,
                        tk.ticker as symbol
                    FROM portfolio_transactions pt
                    JOIN portfolio_securities ps ON pt.security_id = ps.id
                    JOIN tickers tk ON ps.ticker_id = tk.id
                    WHERE pt.portfolio_id = %s
                    ORDER BY pt.transaction_date ASC, pt.id ASC
                """
                cursor.execute(query, (portfolio_id,))
                transactions = cursor.fetchall()

                # Process each transaction
                running_balance = initial_cash
                for t in transactions:
                    cash_impact = 0
                    description = ""
                    transaction_type = ""

                    if t[1] == "buy":
                        # Buy transactions decrease cash
                        shares = float(t[2]) if t[2] else 0
                        price = float(t[3]) if t[3] else 0
                        cash_impact = -(shares * price)
                        transaction_type = "buy"
                        description = f"Purchase of {shares} {t[5]} at ${price:.2f}"
                    elif t[1] == "sell":
                        # Sell transactions increase cash
                        shares = float(t[2]) if t[2] else 0
                        price = float(t[3]) if t[3] else 0
                        cash_impact = shares * price
                        transaction_type = "sell"
                        description = f"Sale of {shares} {t[5]} at ${price:.2f}"
                    elif t[1] == "dividend":
                        # Dividend transactions increase cash
                        amount = float(t[4]) if t[4] else 0
                        cash_impact = amount
                        transaction_type = "dividend"
                        description = f"Dividend from {t[5]}"

                    if cash_impact != 0:
                        running_balance += cash_impact
                        insert_query = """
                            INSERT INTO cash_balance_history 
                            (portfolio_id, transaction_date, amount, transaction_type, description, balance_after)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        values = (
                            portfolio_id,
                            t[0],
                            cash_impact,
                            transaction_type,
                            description,
                            running_balance,
                        )
                        cursor.execute(insert_query, values)
                        connection.commit()
                # Update portfolio's current cash balance
                portfolio_dao.update_cash_balance(portfolio_id, running_balance)

                print("\nCash history rebuilt successfully")
                print(f"Final cash balance: ${running_balance:.2f}")
                print(f"Processed {len(transactions)} transactions")

            finally:
                cursor.close()

    except ValueError:
        print("Error: Portfolio ID must be a number")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
