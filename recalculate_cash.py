import sys

from data.config import Config
from data.portfolio_dao import PortfolioDAO


def main():
    if len(sys.argv) != 2:
        print("Usage: python recalculate_cash.py <portfolio_id>")
        sys.exit(1)

    try:
        portfolio_id = int(sys.argv[1])

        # Get database configuration
        config = Config()
        db_config = config.get_database_config()

        # Initialize PortfolioDAO
        portfolio_dao = PortfolioDAO(
            db_config["user"],
            db_config["password"],
            db_config["host"],
            db_config["database"],
        )

        # Open connection
        portfolio_dao.open_connection()

        try:
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

        finally:
            # Close connection
            portfolio_dao.close_connection()

    except ValueError:
        print("Error: Portfolio ID must be a number")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
