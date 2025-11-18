import logging
from decimal import Decimal

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

            sql = "select max(a.id) from investing.activity a inner join investing.rsi r on a.ticker_id = r.ticker_id and a.activity_date = r.activity_date where a.ticker_id = %s limit 1;"

            cursor.execute(sql, (int(ticker_id),))
            df = pd.DataFrame(cursor.fetchall())

            cursor.close()

            try:
                return df.iloc[0, 0]
            except:
                return None

    def retrievePrices(self, id, ticker_id):
        """
        Retrieves price data and RSI calculations for a given ticker ID after a specified ID.

        Parameters:
        - id (int): The starting ID for fetching records.
        - ticker_id (int): The ticker ID for which to fetch the data.

        Returns:
        - pd.DataFrame: A DataFrame containing the fetched data, indexed by 'activity_date'.
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                sql = """
                SELECT a.close, a.activity_date, avg_loss, avg_gain, rs, rsi
                FROM investing.activity a
                LEFT JOIN investing.rsi r ON a.ticker_id = r.ticker_id AND a.activity_date = r.activity_date
                WHERE a.id >= %s AND a.ticker_id = %s
                ORDER BY a.activity_date;
                """
                cursor.execute(sql, (int(id), int(ticker_id)))
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
                df["activity_date"] = pd.to_datetime(df["activity_date"])
                df = df.set_index("activity_date")
        except Exception as e:
            logger.error("An error occurred: %s", e)
            # Depending on your use case, you might want to re-raise the exception or return an empty DataFrame
            return pd.DataFrame()

        return df

    def createAverages(self, activity_date, ticker_id, avg_gain, avg_loss, rs, rsi):
        with self.get_connection() as connection:
            cursor = connection.cursor()

            sql = "insert into investing.rsi (activity_date, ticker_id, avg_gain, avg_loss, rs, rsi) values (%s, %s, %s, %s, %s, %s);"

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
            pd.DataFrame(cursor.fetchall())

            connection.commit()
            cursor.close()

    def calculateWeightedAverages(self, ticker_id):
        # Check to see if this job has run before
        id = self.averagesLastCalculated(ticker_id)

        if id == None:
            id = 1  # No history

        # retrieve price information so we can calculate
        df_avg = self.retrievePrices(id, ticker_id)

        # Add in columns we need to calculate steps with
        df_rs = df_avg.assign(gain=0, loss=0, rs=0).astype({"gain": "float64", "loss": "float64", "rs": "float64"})

        # We are using index based access so we need to find column positions
        gain_idx = int(df_rs.columns.get_loc("gain"))  # type: ignore[arg-type]
        loss_idx = int(df_rs.columns.get_loc("loss"))  # type: ignore[arg-type]
        avgGain_idx = int(df_rs.columns.get_loc("avg_gain"))  # type: ignore[arg-type]
        avgLoss_idx = int(df_rs.columns.get_loc("avg_loss"))  # type: ignore[arg-type]
        rs_idx = int(df_rs.columns.get_loc("rs"))  # type: ignore[arg-type] - relative strength
        rsi_idx = int(df_rs.columns.get_loc("rsi"))  # type: ignore[arg-type] - relative strength index (Converts RS to a value between 0 and 100)

        # this is our loop length
        array_len = len(df_rs)

        for rsi in range(array_len):
            if id != 1 and rsi == 0:
                continue  # We have historical data and the first row is going to have our seed values we just need to jump ahead one to start processing

            # set our values
            if rsi > 0:
                idx = df_rs.index[rsi]  # dataset is indexed on activity data
                prvidx = df_rs.index[rsi - 1]

                current_price = float(df_rs.loc[idx, "close"])  # type: ignore
                prev_price = float(df_rs.loc[prvidx, "close"])  # type: ignore

                if current_price > prev_price:
                    # stock is up
                    df_rs.loc[idx, "gain"] = float(current_price - prev_price)
                else:
                    # stock is down
                    df_rs.loc[idx, "loss"] = np.abs(float(current_price - prev_price))

            # This group has no history so we need to accumulate some averages
            if rsi < 13 and id == 1:
                continue

            if rsi == 13 and id == 1:  # We only want to hit here if no history has been calculated
                df_rs.iloc[13, avgGain_idx] = round(float(np.mean(df_rs.iloc[0:13, gain_idx].to_numpy())), 2)
                df_rs.iloc[13, avgLoss_idx] = round(float(np.mean(df_rs.iloc[0:13, loss_idx].to_numpy())), 2)
            elif rsi > 13 or id > 1:  # type: ignore[operator]  # Only want to hit here if we have done seed calculation or we have past history
                prev_avg_gain = float(df_rs.iloc[rsi - 1, avgGain_idx])  # type: ignore
                curr_gain = float(df_rs.loc[idx, "gain"])  # type: ignore
                df_rs.iloc[rsi, avgGain_idx] = round((prev_avg_gain * 13 + curr_gain) / 14, 2)

                prev_avg_loss = float(df_rs.iloc[rsi - 1, avgLoss_idx])  # type: ignore
                curr_loss = float(df_rs.loc[idx, "loss"])  # type: ignore
                df_rs.iloc[rsi, avgLoss_idx] = round((prev_avg_loss * 13 + curr_loss) / 14, 2)

            # Handle division by zero for RS calculation
            avg_loss_val = float(df_rs.iloc[rsi, avgLoss_idx])  # type: ignore
            avg_gain_val = float(df_rs.iloc[rsi, avgGain_idx])  # type: ignore

            try:
                if avg_loss_val == 0 or avg_loss_val < 0.0001:
                    # If average loss is zero or very small, set RS to a large value (100 is common in finance)
                    df_rs.iloc[rsi, rs_idx] = 100.0
                else:
                    df_rs.iloc[rsi, rs_idx] = avg_gain_val / avg_loss_val
            except ZeroDivisionError:
                # Handle any other division errors
                df_rs.iloc[rsi, rs_idx] = 100.0

            # Calculate RSI from RS
            rs_val = float(df_rs.iloc[rsi, rs_idx])  # type: ignore
            df_rs.iloc[rsi, rsi_idx] = round(100 - (100 / (rs_val + 1)), 0)  # convert to an index

            # Save the data so we have it for next time
            self.createAverages(
                idx,
                ticker_id,
                df_rs.iloc[rsi, avgGain_idx],
                df_rs.iloc[rsi, avgLoss_idx],
                df_rs.iloc[rsi, rs_idx],
                df_rs.iloc[rsi, rsi_idx],
            )
