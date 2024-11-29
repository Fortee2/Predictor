import os
import time
from datetime import datetime, timedelta

import rsi_calculations as rsi_calc
import ticker_dao
import utility
import yfinance as yf
from dotenv import load_dotenv

from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO

class DataRetrieval:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.dao = ticker_dao.TickerDao(db_user, db_password, db_host, db_name)
        self.utility = utility.utility()
        self.dao.open_connection()
        self.rsi = rsi_calc.rsi_calculations(db_user, db_password, db_host, db_name)
        self.rsi.open_connection()
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.portfolio_dao.open_connection()
        self.portfolio_transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        self.portfolio_transactions_dao.open_connection()

    def update_ticker_data(self, symbol):
        ticker = yf.Ticker(symbol)
        self.dao.update_stock(symbol, ticker.info["shortName"], ticker.info["industry"], ticker.info["sector"])

    def update_ticker_history(self, symbol, ticker_id):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if info.get('regularMarketPrice', None) is None and info.get('financialCurrency', None) is None:
                print(f"{symbol} might be delisted or not available.")
                self.dao.ticker_delisted(symbol)
                portfolio_ids = self.portfolio_dao.get_portfolios_with_ticker(ticker_id)
                for portfolio_id in portfolio_ids:
                    self.portfolio_dao.remove_tickers_from_portfolio(portfolio_id, [ticker_id])
                    self.portfolio_transactions_dao.insert_transaction(portfolio_id, None, 'sell', datetime.date.today())
                return

            print(info.get('fiftyTwoWeekLow', None))

            df_last_date = self.dao.retrieve_last_activity_date(ticker_id)
            start = datetime.today() - timedelta(weeks=520)  # create window with enough room for 50 day moving average

            if df_last_date.iloc[0, 0] != None:
                start = df_last_date.iloc[0, 0] + timedelta(days=1)

            end = datetime.today() + timedelta(days=1)
            hist = ticker.history(interval="1d", start=start, end=end)

            for i in range(len(hist)):
                idx = hist.index[i]
                self.dao.update_trade_history(ticker_id, idx, hist.loc[idx, 'Open'], hist.loc[idx, 'Close'], hist.loc[idx, 'Volume'], hist.loc[idx, 'High'], hist.loc[idx, 'Low'])

                # Check if the stock paid dividends on this date
                if hist.loc[idx, 'Dividends'] > 0:
                    self.log_dividend_transactions(ticker_id, idx, hist.loc[idx, 'Dividends'])

        except Exception as e:
            print(e)
            time.sleep(120)
            print('Sleeping from failure')

    def log_dividend_transactions(self, ticker_id, activity_date, amount):
        portfolio_ids = self.portfolio_dao.get_portfolios_with_ticker(ticker_id)
        for portfolio_id in portfolio_ids:
            security_id = self.portfolio_dao.get_security_id(portfolio_id, ticker_id)
            self.portfolio_transactions_dao.insert_transaction(portfolio_id, security_id, 'dividend', activity_date, amount=amount)

    def retrieve_ticker_history(self, ticker_id):
        return self.dao.retrieve_ticker_activity(ticker_id=ticker_id)

    def update_stock_activity(self):
        portfolio_tickers = self.portfolio_dao.get_all_tickers_in_portfolios()
        print(portfolio_tickers)
        count = 0

        for ticker_id in portfolio_tickers:
            symbol = self.dao.get_ticker_symbol(ticker_id)
            industry = self.dao.get_ticker_industry(ticker_id)

            print(symbol)
            print(industry)

            if industry is None:
                self.update_ticker_data(symbol)

            self.update_ticker_history(symbol, ticker_id)

            count += 1

            if count == 3:
                time.sleep(120)
                print('Sleeping')
                count = 0

            self.rsi.calculateRSI(ticker_id)

def main():
    load_dotenv()

    stock_activity = DataRetrieval(os.getenv('DB_USER'), os.getenv('DB_PASSWORD'), os.getenv('DB_HOST'), os.getenv('DB_NAME'))
    stock_activity.update_stock_activity()

if __name__ == "__main__":
    main()
