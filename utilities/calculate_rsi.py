import sys
import os

# Add parent directory to path to allow imports from data module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.config import Config
from data.ticker_dao import TickerDao
from data.rsi_calculations import rsi_calculations
from data.utility import DatabaseConnectionPool

def main():
    if len(sys.argv) != 2:
        print("Usage: python calculate_rsi.py <symbol>")
        sys.exit(1)

    symbol = sys.argv[1].upper()

    # Get database configuration
    config = Config()
    db_config = config.get_database_config()

    # Initialize Connection Pool
    connection_pool = DatabaseConnectionPool(
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        database=db_config["database"],
    )

    ticker_dao = TickerDao(connection_pool)
    rsi_calc = rsi_calculations(connection_pool)

    # Get Ticker ID
    ticker_id = ticker_dao.get_ticker_id(symbol)
    if not ticker_id:
        print(f"Error: Symbol {symbol} not found in database.")
        sys.exit(1)

    print(f"Calculating RSI for {symbol} (ID: {ticker_id})...")
    
    try:
        rsi_calc.calculateRSI(ticker_id)
        print(f"Successfully calculated RSI for {symbol}.")
        
    except Exception as e:
        print(f"Error calculating RSI: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
