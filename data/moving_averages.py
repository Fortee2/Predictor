import logging
from contextlib import contextmanager
from datetime import timedelta

import mysql.connector
import pandas as pd

from data.utility import DatabaseConnectionPool

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


class moving_averages:

    def __init__(self, user, password, host, database):
        self.db_user = user
        self.db_password = password
        self.db_host = host
        self.db_name = database

        # Initialize connection pool if not already initialized
        try:
            self.pool = DatabaseConnectionPool(user, password, host, database)
            self.current_connection = None
            logger.info("Moving averages initialized with database connection pool")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {str(e)}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        connection = None
        try:
            if (
                self.current_connection is not None
                and self.current_connection.is_connected()
            ):
                # Use existing connection if it's still valid
                connection = self.current_connection
                yield connection
            else:
                # Get a new connection from the pool
                connection = self.pool.get_connection()
                self.current_connection = connection
                yield connection
        except mysql.connector.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            # Don't close the connection here, just pass
            # The connection will be closed when open_connection() is explicitly called
            pass

    def open_connection(self):
        """Open a new database connection or return the existing one if valid."""
        try:
            if (
                self.current_connection is None
                or not self.current_connection.is_connected()
            ):
                self.current_connection = self.pool.get_connection()
                logger.debug("Opened new database connection")
            return self.current_connection
        except mysql.connector.Error as e:
            logger.error(f"Failed to open database connection: {str(e)}")
            raise

    def close_connection(self):
        """Close the current database connection if open."""
        try:
            if (
                self.current_connection is not None
                and self.current_connection.is_connected()
            ):
                self.current_connection.close()
                logger.debug("Closed database connection")
                self.current_connection = None
        except mysql.connector.Error as e:
            logger.error(f"Error closing database connection: {str(e)}")

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
            logger.error(f"Error calculating average: {str(e)}")
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
                    f"Loaded {len(df)} average data points for ticker {ticker_id}, type {averageType}"
                )
                return df
        except mysql.connector.Error as e:
            logger.error(
                f"Database error loading averages for ticker {ticker_id}, type {averageType}: {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(f"Error loading averages from DB: {str(e)}")
            raise

    def update_moving_averages(self, ticker_id, period):
        """Calculate and update moving averages for a ticker over a period."""
        logger.info(f"Updating moving averages for ticker {ticker_id}, period {period}")

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
                        f"No previous moving averages found for ticker {ticker_id}, calculating all"
                    )
                else:
                    last_date = last_date - timedelta(days=period)
                    logger.debug(
                        f"Last moving average date for ticker {ticker_id}: {last_date}"
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
                        f"Found {len(new_data)} new data points to calculate moving averages"
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
                        f"Updated {rows_updated} moving averages for ticker {ticker_id}"
                    )
                else:
                    logger.info(
                        f"No new data found for ticker {ticker_id} since {last_date}"
                    )

                cursor.close()

                # Return the updated moving averages from the database
                return self.loadAveragesFromDB(ticker_id, period)
        except mysql.connector.Error as e:
            logger.error(f"Database error updating moving averages: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating moving averages: {str(e)}")
            raise
