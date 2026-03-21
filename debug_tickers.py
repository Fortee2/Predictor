import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.config import Config
from data.portfolio_dao import PortfolioDAO
from data.utility import DatabaseConnectionPool

def main():
    config = Config()
    db_config = config.get_database_config()
    pool = DatabaseConnectionPool(
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        database=db_config["database"],
    )
    dao = PortfolioDAO(pool)
    tickers = dao.get_all_tickers_in_portfolios()
    print(f"Count: {len(tickers)}")
    for t in tickers:
        print(t)

if __name__ == "__main__":
    main()
