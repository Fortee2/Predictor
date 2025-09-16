from decimal import Decimal, DivisionUndefined

import mysql.connector
import numpy as np
import pandas as pd
from mysql.connector import errorcode


class rsi_calculations:

    def __init__(self, user, password, host, database):
        self.db_user = user
        self.db_password = password
        self.db_host = host
        self.db_name = database

        self.current_connection = None

    def open_connection(self):
        self.current_connection = mysql.connector.connect(
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            database=self.db_name,
        )

    def close_connection(self):
        self.current_connection.close()

    def calculateRSI(self, ticker_id):
        self.calculateWeightedAverages(ticker_id)

    def averagesLastCalculated(self, ticker_id):
        cursor = self.current_connection.cursor()

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
            with self.current_connection.cursor() as cursor:
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
            print(f"An error occurred: {e}")
            # Depending on your use case, you might want to re-raise the exception or return an empty DataFrame
            return pd.DataFrame()

        return df

    def createAverages(self, activity_date, ticker_id, avg_gain, avg_loss, rs, rsi):
        cursor = self.current_connection.cursor()

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
        df = pd.DataFrame(cursor.fetchall())

        self.current_connection.commit()
        cursor.close()

    def calculateWeightedAverages(self, ticker_id):
        # Check to see if this job has run before
        id = self.averagesLastCalculated(ticker_id)

        if id == None:
            id = 1  # No history

        # retrieve price information so we can calculate
        df_avg = self.retrievePrices(id, ticker_id)

        # Add in columns we need to calculate steps with
        df_rs = df_avg.assign(gain=0, loss=0, rs=0).astype(
            {"gain": "float64", "loss": "float64", "rs": "float64"}
        )

        # We are using index based access so we need to find column positions
        gain_idx = df_rs.columns.get_loc("gain")
        loss_idx = df_rs.columns.get_loc("loss")
        avgGain_idx = df_rs.columns.get_loc("avg_gain")
        avgLoss_idx = df_rs.columns.get_loc("avg_loss")
        rs_idx = df_rs.columns.get_loc("rs")  # relative strength
        rsi_idx = df_rs.columns.get_loc(
            "rsi"
        )  # relative strength index (Converts RS to a value between 0 and 100)

        # this is our loop length
        array_len = len(df_rs)

        for rsi in range(array_len):
            if id != 1 and rsi == 0:
                continue  # We have historical data and the first row is going to have our seed values we just need to jump ahead one to start processing

            # set our values
            if rsi > 0:
                idx = df_rs.index[rsi]  # dataset is indexed on activity data
                prvidx = df_rs.index[rsi - 1]

                current_price = df_rs.loc[idx, "close"]
                prev_price = df_rs.loc[prvidx, "close"]

                if current_price > prev_price:
                    # stock is up
                    df_rs.loc[idx, "gain"] = float(current_price - prev_price)
                else:
                    # stock is down
                    df_rs.loc[idx, "loss"] = np.abs(float(current_price - prev_price))

            # This group has no history so we need to accumulate some averages
            if rsi < 13 and id == 1:
                continue

            if (
                rsi == 13 and id == 1
            ):  # We only want to hit here if no history has been calculated
                df_rs.iloc[13, avgGain_idx] = round(
                    Decimal(df_rs.iloc[0:13, gain_idx].mean()), 2
                )
                df_rs.iloc[13, avgLoss_idx] = round(
                    Decimal(df_rs.iloc[0:13, loss_idx].mean()), 2
                )
            elif (
                rsi > 13 or id > 1
            ):  # Only want to hit here if we have done seed calculation or we have past history
                df_rs.iloc[rsi, avgGain_idx] = round(
                    (
                        Decimal(df_rs.iloc[rsi - 1, avgGain_idx]) * Decimal(13)
                        + Decimal(df_rs.loc[idx, "gain"])
                    )
                    / Decimal(14),
                    2,
                )
                df_rs.iloc[rsi, avgLoss_idx] = round(
                    (
                        Decimal(df_rs.iloc[rsi - 1, avgLoss_idx]) * Decimal(13)
                        + Decimal(df_rs.loc[idx, "loss"])
                    )
                    / Decimal(14),
                    2,
                )

            # Handle division by zero for RS calculation
            try:
                if (
                    df_rs.iloc[rsi, avgLoss_idx] == 0
                    or df_rs.iloc[rsi, avgLoss_idx] < 0.0001
                ):
                    # If average loss is zero or very small, set RS to a large value (100 is common in finance)
                    df_rs.iloc[rsi, rs_idx] = 100.0
                else:
                    df_rs.iloc[rsi, rs_idx] = float(
                        df_rs.iloc[rsi, avgGain_idx] / df_rs.iloc[rsi, avgLoss_idx]
                    )
            except (ZeroDivisionError, decimal.DivisionUndefined):
                # Handle any other division errors
                df_rs.iloc[rsi, rs_idx] = 100.0

            # Calculate RSI from RS
            df_rs.iloc[rsi, rsi_idx] = np.round(
                100 - (100 / (df_rs.iloc[rsi, rs_idx] + 1)), 0
            )  # convert to an index

            # Save the data so we have it for next time
            self.createAverages(
                idx,
                ticker_id,
                df_rs.iloc[rsi, avgGain_idx],
                df_rs.iloc[rsi, avgLoss_idx],
                df_rs.iloc[rsi, rs_idx],
                df_rs.iloc[rsi, rsi_idx],
            )
