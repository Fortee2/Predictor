import sys
import os

# Add parent directory to path to allow imports from data module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.config import Config
from data.portfolio_dao import PortfolioDAO
from data.utility import DatabaseConnectionPool


def main():
    if len(sys.argv) != 2:
        print("Usage: python recalculate_cash.py <portfolio_id>")
        sys.exit(1)

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

    # Get current balance before recalculation
    old_balance = portfolio_dao.get_cash_balance(portfolio_id)
    print(f"Current cash balance: ${old_balance:.2f}")

    # Recalculate cash balance
    new_balance = portfolio_dao.recalculate_cash_balance(portfolio_id)
    print(f"Recalculated cash balance: ${new_balance:.2f}")

    if old_balance != new_balance:
        print(f"Balance adjusted by: ${new_balance - old_balance:.2f}")
    else:
        print("No balance adjustment needed")



if __name__ == "__main__":
    main()
