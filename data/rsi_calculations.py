import logging
from datetime import date, datetime
import numpy as np
import pandas as pd

from .base_dao import BaseDAO
from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class rsi_calculations(BaseDAO):
    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__(pool)

    def calculateRSI(self, ticker_id):
        self.calculateWeightedAverages(ticker_id)

    def averagesLastCalculated(self, ticker_id):
        with self.get_connection() as connection:
            cursor = connection.cursor()

            # Get the latest activity_date that has RSI calculated
            sql = "select max(activity_date) from investing.rsi where ticker_id = %s;"

            cursor.execute(sql, (int(ticker_id),))
            df = pd.DataFrame(cursor.fetchall())

            cursor.close()

            try:
                val = df.iloc[0, 0]
                if pd.isna(val):
                    return None
                return val
            except:
                return None

    def retrievePrices(self, start_criteria, ticker_id):
        """
        Retrieves price data for a given ticker ID.
        Seed RSI values for incremental updates are fetched separately
        via _fetch_last_rsi_values, so no LEFT JOIN is needed here.

        Parameters:
        - start_criteria (int or datetime/date): The starting point (ID or Date) for fetching records.
        - ticker_id (int): The ticker ID for which to fetch the data.

        Returns:
        - pd.DataFrame: A DataFrame containing the fetched data, indexed by 'activity_date'.
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                if isinstance(start_criteria, int):
                    sql = """
                    SELECT close, activity_date
                    FROM investing.activity
                    WHERE id >= %s AND ticker_id = %s
                    ORDER BY activity_date;
                    """
                    cursor.execute(sql, (int(start_criteria), int(ticker_id)))
                elif isinstance(start_criteria, (date, datetime)):
                    sql = """
                    SELECT close, activity_date
                    FROM investing.activity
                    WHERE activity_date >= %s AND ticker_id = %s
                    ORDER BY activity_date;
                    """
                    cursor.execute(sql, (start_criteria, int(ticker_id)))
                else:
                    sql = """
                    SELECT close, activity_date
                    FROM investing.activity
                    WHERE ticker_id = %s
                    ORDER BY activity_date;
                    """
                    cursor.execute(sql, (int(ticker_id),))

                df = pd.DataFrame(
                    cursor.fetchall(),
                    columns=["close", "activity_date"],
                )
                df["activity_date"] = pd.to_datetime(df["activity_date"])
                df = df.set_index("activity_date")
        except Exception as e:
            logger.error("An error occurred: %s", e)
            return pd.DataFrame()

        return df

    def createAverages(self, activity_date, ticker_id, avg_gain, avg_loss, rs, rsi):
        with self.get_connection() as connection:
            cursor = connection.cursor()

            sql = """
            INSERT INTO investing.rsi (activity_date, ticker_id, avg_gain, avg_loss, rs, rsi) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            avg_gain = VALUES(avg_gain), 
            avg_loss = VALUES(avg_loss), 
            rs = VALUES(rs), 
            rsi = VALUES(rsi);
            """

            cursor.execute(
                sql,
                (
                    activity_date,
                    int(ticker_id),
                    float(avg_gain),
                    float(avg_loss),
                    float(rs),
                    float(rsi),
                ),
            )
            # Removed invalid fetchall() call after insert

            connection.commit()
            cursor.close()

    def save_rsi_batch(self, batch_data):
        if not batch_data:
            return

        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                sql = """
                INSERT INTO investing.rsi (activity_date, ticker_id, avg_gain, avg_loss, rs, rsi) 
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                avg_gain = VALUES(avg_gain), 
                avg_loss = VALUES(avg_loss), 
                rs = VALUES(rs), 
                rsi = VALUES(rsi);
                """
                cursor.executemany(sql, batch_data)
                connection.commit()
                cursor.close()
        except Exception as e:
            logger.error(f"Error saving RSI batch: {e}")
            raise

    def _fetch_last_rsi_values(self, ticker_id):
        """Fetch the most recent RSI values directly from the rsi table."""
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """SELECT avg_gain, avg_loss, rs, rsi
                    FROM investing.rsi
                    WHERE ticker_id = %s
                    ORDER BY activity_date DESC LIMIT 1""",
                    (int(ticker_id),),
                )
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return {
                        "avg_gain": float(row[0]),
                        "avg_loss": float(row[1]),
                        "rs": float(row[2]),
                        "rsi": float(row[3]),
                    }
        except Exception as e:
            logger.error("Error fetching last RSI values for ticker %s: %s", ticker_id, e)
        return None

    def calculateWeightedAverages(self, ticker_id):
        # Check to see if this job has run before
        last_date = self.averagesLastCalculated(ticker_id)
        print(f"  Last RSI date: {last_date}")

        # retrieve price information so we can calculate
        # If last_date is None, this will retrieve all history (as None is handled in retrievePrices)
        print(f"  Fetching price data...")
        df_avg = self.retrievePrices(last_date, ticker_id)

        if df_avg.empty:
            print("  No price data found.")
            return

        array_len = len(df_avg)
        print(f"  Retrieved {array_len} rows (dates: {df_avg.index[0]} to {df_avg.index[-1]})")

        # Extract to numpy arrays to avoid slow pandas iloc in the loop
        close = np.array([float(v) for v in df_avg["close"].values])
        dates = df_avg.index.tolist()

        # Working arrays
        gain = np.zeros(array_len)
        loss = np.zeros(array_len)
        avg_gain = np.zeros(array_len)
        avg_loss = np.zeros(array_len)
        rs = np.zeros(array_len)
        rsi_arr = np.zeros(array_len)

        batch_data = []
        BATCH_SIZE = 1000

        # Calculate gain/loss for all rows at once
        for i in range(1, array_len):
            diff = close[i] - close[i - 1]
            if diff > 0:
                gain[i] = diff
            else:
                loss[i] = abs(diff)

        # Determine where to start producing RSI records
        if last_date is not None:
            # Resuming: fetch seed values directly from RSI table
            seed_vals = self._fetch_last_rsi_values(ticker_id)
            if seed_vals is None:
                logger.warning("No seed RSI values found for ticker %s, cannot resume", ticker_id)
                return

            avg_gain[0] = seed_vals["avg_gain"]
            avg_loss[0] = seed_vals["avg_loss"]

            # Calculate from row 1 onward
            start = 1
        else:
            # Fresh calculation: need 14 rows to seed
            if array_len < 14:
                return

            avg_gain[13] = round(float(np.mean(gain[0:13])), 2)
            avg_loss[13] = round(float(np.mean(loss[0:13])), 2)

            start = 13

        # Weighted average calculation (the RSI formula)
        for i in range(start, array_len):
            if i > start:
                avg_gain[i] = round((avg_gain[i - 1] * 13 + gain[i]) / 14, 2)
                avg_loss[i] = round((avg_loss[i - 1] * 13 + loss[i]) / 14, 2)
            elif i == start and last_date is None:
                # Row 13 seed — already set above
                pass
            else:
                # Row 1 when resuming — use seed from row 0
                avg_gain[i] = round((avg_gain[i - 1] * 13 + gain[i]) / 14, 2)
                avg_loss[i] = round((avg_loss[i - 1] * 13 + loss[i]) / 14, 2)

            # RS calculation
            if avg_loss[i] < 0.0001:
                rs[i] = 100.0
            else:
                rs[i] = avg_gain[i] / avg_loss[i]

            # RSI from RS
            rsi_arr[i] = round(100 - (100 / (rs[i] + 1)), 0)

            # Skip row 0 (seed row) when resuming — don't re-save it
            if last_date is not None and i == 0:
                continue

            record = (
                dates[i],
                int(ticker_id),
                float(avg_gain[i]),
                float(avg_loss[i]),
                float(rs[i]),
                float(rsi_arr[i]),
            )
            batch_data.append(record)

            if len(batch_data) >= BATCH_SIZE:
                self.save_rsi_batch(batch_data)
                batch_data = []

        # Save any remaining records
        if batch_data:
            self.save_rsi_batch(batch_data)

        total_saved = sum(1 for i in range(start, array_len) if not (last_date is not None and i == 0))
        print(f"  RSI calculation complete. {total_saved} records saved.")
