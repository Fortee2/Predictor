#!/usr/bin/env python3
import argparse

import pandas as pd
from dotenv import load_dotenv

from data.data_retrieval_consolidated import DataRetrieval
from data.ticker_dao import TickerDao


class TickerCLI:
    def __init__(self):
        load_dotenv()

        # Initialize DAOs
        self.ticker_dao = TickerDao(pool=self.db_pool)
        self.data_retrieval = DataRetrieval(pool=self.db_pool)
        self.ticker_dao.open_connection()

    def add_ticker(self, symbol, name):
        """Add a new ticker to the database"""
        try:
            self.ticker_dao.insert_stock(symbol, name)
            print("\nSuccessfully added new ticker:")
            print(f"Symbol: {symbol}")
            print(f"Name: {name}")
        except Exception as e:
            print(f"Error adding ticker: {str(e)}")

    def update_ticker(self, symbol, name, industry, sector):
        """Update ticker details"""
        try:
            self.ticker_dao.update_stock(symbol, name, industry, sector)
            print(f"\nSuccessfully updated ticker {symbol}:")
            print(f"Name: {name}")
            print(f"Industry: {industry}")
            print(f"Sector: {sector}")
        except Exception as e:
            print(f"Error updating ticker: {str(e)}")

    def delist_ticker(self, symbol):
        """Mark a ticker as inactive"""
        try:
            self.ticker_dao.ticker_delisted(symbol)
            print(f"\nSuccessfully marked ticker {symbol} as inactive")
        except Exception as e:
            print(f"Error delisting ticker: {str(e)}")

    def list_tickers(self):
        """List all tickers"""
        try:
            tickers_df = self.ticker_dao.retrieve_ticker_list()
            if tickers_df.empty:
                print("\nNo tickers found.")
                return

            # Convert column names to display format
            tickers_df = tickers_df.rename(
                columns={
                    "ticker": "Symbol",
                    "ticker_name": "Name",
                    "id": "ID",
                    "industry": "Industry",
                    "sector": "Sector",
                }
            )

            print("\nTicker List:")
            print("=" * 100)
            pd.set_option("display.max_rows", None)
            pd.set_option("display.max_columns", None)
            pd.set_option("display.width", 100)
            print(tickers_df.to_string(index=False))
            print("=" * 100)
        except Exception as e:
            print(f"Error listing tickers: {str(e)}")

    def update_ticker_data(self, symbol):
        """Update ticker data using yfinance"""
        try:
            print(f"\nUpdating data for {symbol}...")

            # Check if ticker exists, if not add it
            ticker_id = self.ticker_dao.get_ticker_id(symbol)
            if not ticker_id:
                print(f"Ticker {symbol} not found in database. Adding it...")
                self.ticker_dao.insert_stock(
                    symbol, symbol
                )  # Use symbol as temporary name
                ticker_id = self.ticker_dao.get_ticker_id(symbol)

            # Update all ticker data
            self.data_retrieval.update_symbol_data(symbol)
            if ticker_id:
                self.data_retrieval.update_ticker_history(symbol, ticker_id)
                print(f"Successfully updated {symbol} data")
            else:
                print(f"Error: Failed to add/update ticker {symbol}")
        except Exception as e:
            print(f"Error updating ticker data: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Ticker Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add Ticker
    add_parser = subparsers.add_parser("add", help="Add a new ticker")
    add_parser.add_argument("symbol", help="Ticker symbol")
    add_parser.add_argument("name", help="Company name")

    # Update Ticker
    update_parser = subparsers.add_parser("update", help="Update ticker details")
    update_parser.add_argument("symbol", help="Ticker symbol")
    update_parser.add_argument("name", help="Company name")
    update_parser.add_argument("industry", help="Industry")
    update_parser.add_argument("sector", help="Sector")

    # Delist Ticker
    delist_parser = subparsers.add_parser("delist", help="Mark ticker as inactive")
    delist_parser.add_argument("symbol", help="Ticker symbol")
    # Update Data
    update_data_parser = subparsers.add_parser(
        "update-data", help="Update ticker data using yfinance"
    )
    update_data_parser.add_argument("symbol", help="Ticker symbol")

    args = parser.parse_args()
    cli = TickerCLI()

    if args.command == "add":
        cli.add_ticker(args.symbol, args.name)
    elif args.command == "update":
        cli.update_ticker(args.symbol, args.name, args.industry, args.sector)
    elif args.command == "delist":
        cli.delist_ticker(args.symbol)
    elif args.command == "list":
        cli.list_tickers()
    elif args.command == "update-data":
        cli.update_ticker_data(args.symbol)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
