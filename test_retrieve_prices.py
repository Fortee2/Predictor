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

last_date = rsi_calc.averagesLastCalculated(ticker_id)
print(f"Last date: {last_date}")

# Let's bypass the try/except in retrievePrices to see the exact error
try:
    with rsi_calc.get_connection() as connection:
        cursor = connection.cursor()
        if last_date is not None:
            sql = """
            SELECT a.close, a.activity_date, avg_loss, avg_gain, rs, rsi
            FROM investing.activity a
            LEFT JOIN investing.rsi r ON a.ticker_id = r.ticker_id AND a.activity_date = r.activity_date
            WHERE a.activity_date >= %s AND a.ticker_id = %s
            ORDER BY a.activity_date;
            """
            cursor.execute(sql, (last_date, int(ticker_id)))
        else:
            sql = """
            SELECT a.close, a.activity_date, avg_loss, avg_gain, rs, rsi
            FROM investing.activity a
            LEFT JOIN investing.rsi r ON a.ticker_id = r.ticker_id AND a.activity_date = r.activity_date
            WHERE a.ticker_id = %s
            ORDER BY a.activity_date;
            """
            cursor.execute(sql, (int(ticker_id),))

        import pandas as pd
        df = pd.DataFrame(
            cursor.fetchall(),
            columns=[
                "close",
                "activity_date",
                "avg_loss",
                "avg_gain",
                "rs",
                "rsi",
            ],
        )
        print(f"DataFrame before processing: {len(df)} rows")
        df["activity_date"] = pd.to_datetime(df["activity_date"])
        df = df.set_index("activity_date")
        print(f"DataFrame columns: {df.columns.tolist()}")
except Exception as e:
    import traceback
    traceback.print_exc()

