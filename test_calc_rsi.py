import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.config import Config
from data.ticker_dao import TickerDao
from data.rsi_calculations import rsi_calculations
from data.utility import DatabaseConnectionPool

config = Config()
db_config = config.get_database_config()

connection_pool = DatabaseConnectionPool(
    user=db_config["user"],
    password=db_config["password"],
    host=db_config["host"],
    database=db_config["database"],
)

ticker_dao = TickerDao(connection_pool)
rsi_calc = rsi_calculations(connection_pool)

ticker_id = ticker_dao.get_ticker_id('MSFT')
print(f"Ticker ID for MSFT: {ticker_id}")

try:
    rsi_calc.calculateWeightedAverages(ticker_id)
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()

