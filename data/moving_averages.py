import logging
from datetime import timedelta

import mysql.connector
import pandas as pd

from .base_dao import BaseDAO

# Set up logging - Modified to only log to file, not console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("moving_averages.log")
        # StreamHandler removed to prevent console output
    ],
)
logger = logging.getLogger("moving_averages")

# Ensure no handlers are outputting to console
for handler in logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler) and not isinstance(
        handler, logging.FileHandler
    ):
        logger.removeHandler(handler)


class moving_averages(BaseDAO):

    def calculateAverage(self, resultColumn, columnToAvg, interval, avgDataFrame):
        """Calculate moving average for a DataFrame column."""
        try:
            ma_idx = avgDataFrame.columns.get_loc(resultColumn)
            close_idx = avgDataFrame.columns.get_loc(columnToAvg)

            for i in range(
                len(avgDataFrame) - 1, interval - 1, -1
            ):  # range(start, stop, step)
                avgDataFrame.iloc[i, ma_idx] = avgDataFrame.iloc[
                    i - interval : i, close_idx
                ].mean()

            return avgDataFrame
        except Exception as e:
            logger.error("Error calculating average: %s", str(e))
            raise

    def loadAveragesFromDB(self, ticker_id, averageType):
        """Load moving averages from database for a given ticker and average type."""
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                sql = """
                    select activity_date, value 
                    from investing.averages a 
                    where a.activity_date between date_add(curdate(), interval -1 YEAR) and curdate() 
                    and ticker_id = %s and average_type = %s
                    order by a.activity_date;
                """

                cursor.execute(sql, (int(ticker_id), str(averageType)))

                df = pd.DataFrame(
                    cursor.fetchall(),
                    columns=["activity_date", str(averageType).lower()],
                )
                df = df.set_index("activity_date")

                cursor.close()

                logger.debug(
                    "Loaded %s average data points for ticker %s, type %s", len(df), ticker_id, averageType
                )
                return df
        except mysql.connector.Error as e:
            logger.error(
                "Database error loading averages for ticker %s, type %s: %s", ticker_id, averageType, str(e)
            )
            raise
        except Exception as e:
            logger.error("Error loading averages from DB: %s", str(e))
            raise

    def update_moving_averages(self, ticker_id, period):
        """Calculate and update moving averages for a ticker over a period."""
        logger.info("Updating moving averages for ticker %s, period %s", ticker_id, period)

        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Retrieve the last date for which the moving average was calculated
                cursor.execute(
                    """
                    SELECT MAX(activity_date) 
                    FROM investing.averages 
                    WHERE ticker_id = %s AND average_type = %s
                """,
                    (ticker_id, period),
                )
                result = cursor.fetchone()
                last_date = result[0] if result else None

                # If no last date, set it to a very early date to calculate for all data
                if last_date is None:
                    last_date = "1900-01-01"
                    logger.debug(
                        "No previous moving averages found for ticker %s, calculating all", ticker_id
                    )
                else:
                    last_date = last_date - timedelta(days=period)
                    logger.debug(
                        "Last moving average date for ticker %s: %s", ticker_id, last_date
                    )

                # Retrieve new data from the activity table since the last moving average calculation
                cursor.execute(
                    """
                    SELECT activity_date, close 
                    FROM investing.activity 
                    WHERE ticker_id = %s AND activity_date > %s
                    ORDER BY activity_date ASC
                """,
                    (ticker_id, last_date),
                )

                # Convert fetched data into DataFrame
                new_data = pd.DataFrame(
                    cursor.fetchall(), columns=["activity_date", "close"]
                )

                if not new_data.empty:
                    logger.info(
                        "Found %s new data points to calculate moving averages", len(new_data)
                    )

                    new_data["activity_date"] = pd.to_datetime(
                        new_data["activity_date"]
                    )
                    new_data = new_data.set_index("activity_date")

                    # Calculate moving average for the new data
                    if isinstance(new_data, pd.DataFrame):
                        new_data["moving_average"] = (
                            new_data["close"]
                            .rolling(window=period, min_periods=1)
                            .mean()
                        )

                    # Insert or update the moving averages in the investing.averages table
                    rows_updated = 0
                    for index, row in new_data.iterrows():
                        cursor.execute(
                            """
                            INSERT INTO investing.averages (ticker_id, activity_date, average_type, value)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE value = VALUES(value)
                        """,
                            (ticker_id, index.date(), period, row["moving_average"]),
                        )
                        rows_updated += cursor.rowcount

                    # Commit the changes to the database
                    connection.commit()
                    logger.info(
                        "Updated %s moving averages for ticker %s", rows_updated, ticker_id
                    )
                else:
                    logger.info(
                        "No new data found for ticker %s since %s", ticker_id, last_date
                    )

                cursor.close()

                # Return the updated moving averages from the database
                return self.loadAveragesFromDB(ticker_id, period)
        except mysql.connector.Error as e:
            logger.error("Database error updating moving averages: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error updating moving averages: %s", str(e))
            raise
