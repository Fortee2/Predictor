from datetime import datetime

import mysql.connector
import pandas as pd

from data.utility import DatabaseConnectionPool


class FundamentalDataDAO:
    def __init__(self, pool: DatabaseConnectionPool):
        self.pool = pool
        self.current_connection = None

    def open_connection(self):
        """Opens a connection to the database"""
        self.current_connection = mysql.connector.connect(
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            database=self.db_name,
        )

    def close_connection(self):
        """Closes the database connection"""
        if self.current_connection:
            self.current_connection.close()

    def save_fundamental_data(
        self,
        ticker_id,
        pe_ratio,
        forward_pe,
        peg_ratio,
        price_to_book,
        dividend_yield,
        dividend_rate,
        eps_ttm,
        eps_growth,
        revenue_growth,
        profit_margin,
        debt_to_equity,
        market_cap,
    ):
        """
        Saves fundamental data for a ticker to the database
        """
        try:
            cursor = self.current_connection.cursor()

            sql = """
            INSERT INTO fundamental_data (
                ticker_id, date, pe_ratio, forward_pe, peg_ratio, price_to_book,
                dividend_yield, dividend_rate, eps_ttm, eps_growth, revenue_growth,
                profit_margin, debt_to_equity, market_cap
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            values = (
                ticker_id,
                datetime.now().date(),
                pe_ratio,
                forward_pe,
                peg_ratio,
                price_to_book,
                dividend_yield,
                dividend_rate,
                eps_ttm,
                eps_growth,
                revenue_growth,
                profit_margin,
                debt_to_equity,
                market_cap,
            )

            cursor.execute(sql, values)
            self.current_connection.commit()
            cursor.close()

            return True

        except mysql.connector.Error as err:
            print(f"Error saving fundamental data: {err}")
            return False

    def get_latest_fundamental_data(self, ticker_id):
        """
        Retrieves the latest fundamental data for a ticker
        """
        try:
            cursor = self.current_connection.cursor()

            sql = """
            SELECT 
                date, pe_ratio, forward_pe, peg_ratio, price_to_book,
                dividend_yield, dividend_rate, eps_ttm, eps_growth, revenue_growth,
                profit_margin, debt_to_equity, market_cap
            FROM fundamental_data
            WHERE ticker_id = %s
            ORDER BY date DESC
            LIMIT 1
            """

            cursor.execute(sql, (ticker_id,))
            result = cursor.fetchone()
            cursor.close()

            if result:
                return {
                    "date": result[0],
                    "pe_ratio": result[1],
                    "forward_pe": result[2],
                    "peg_ratio": result[3],
                    "price_to_book": result[4],
                    "dividend_yield": result[5],
                    "dividend_rate": result[6],
                    "eps_ttm": result[7],
                    "eps_growth": result[8],
                    "revenue_growth": result[9],
                    "profit_margin": result[10],
                    "debt_to_equity": result[11],
                    "market_cap": result[12],
                }
            return None

        except mysql.connector.Error as err:
            print(f"Error retrieving fundamental data: {err}")
            return None

    def get_fundamental_history(self, ticker_id, days=30):
        """
        Retrieves historical fundamental data for a ticker
        """
        try:
            cursor = self.current_connection.cursor()

            sql = """
            SELECT 
                date, pe_ratio, forward_pe, peg_ratio, price_to_book,
                dividend_yield, dividend_rate, eps_ttm, eps_growth, revenue_growth,
                profit_margin, debt_to_equity, market_cap
            FROM fundamental_data
            WHERE ticker_id = %s
            AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY date DESC
            """

            cursor.execute(sql, (ticker_id, days))
            columns = [
                "date",
                "pe_ratio",
                "forward_pe",
                "peg_ratio",
                "price_to_book",
                "dividend_yield",
                "dividend_rate",
                "eps_ttm",
                "eps_growth",
                "revenue_growth",
                "profit_margin",
                "debt_to_equity",
                "market_cap",
            ]
            df = pd.DataFrame(cursor.fetchall(), columns=columns)
            cursor.close()

            if not df.empty:
                df.set_index("date", inplace=True)
                return df
            return None

        except mysql.connector.Error as err:
            print(f"Error retrieving fundamental history: {err}")
            return None
