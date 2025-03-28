from datetime import date
import os
import mysql.connector
from dotenv import load_dotenv
from mysql.connector import errorcode
from data.ticker_dao import TickerDao
import pandas as pd

class BollingerBandAnalyzer:

    def __init__(self, ticker_dao):
        self.ticker_dao = ticker_dao
        self.tickers = {}
        self.data_points = {}

    def generate_bollinger_band_data(self, ticker_id):
        """Generate data points for a Bollinger Band chart"""
        
        # Get symbol for the ticker_id
        symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
        if not symbol:
            return None
            
        if symbol not in self.tickers:
            self.tickers[symbol] = []
            
        # Retrieve the latest tickers and activity history
        last_activity_date = self.ticker_dao.retrieve_last_activity_date(ticker_id)
        if not last_activity_date.empty:
            self.data_points[symbol] = {
                'last_activity': pd.to_datetime(last_activity_date['activity_date']),
                'open': float(last_activity_date.iloc[0]['open']),
                'close': float(last_activity_date.iloc[0]['close']),
                'high': float(last_activity_date.iloc[0]['high']),
                'low': float(last_activity_date.iloc[0]['low'])
            }
        
        # Retrieve the latest activity history for the Bollinger Band
        last_bollinger_band_activity = self.ticker_dao.retrieve_last_rsi(ticker_id)
        if not last_bollinger_band_activity.empty:
            self.data_points[symbol]['bollinger_bands'] = {
                'mean': float(last_bollinger_band_activity.iloc[0]['rsi']),
                'stddev': 0.0  # Delta column doesn't exist, using default value
            }
        
        # Calculate the previous day's data
        last_day = date.today() - pd.DateOffset(days=1)
        for ticker in self.tickers:
            if symbol not in self.tickers[ticker]:
                continue
            
            prev_data_points = {}
            
            # Retrieve the previous day's data points
            for i, (activity_date, value) in enumerate(self.data_points[ticker].items()):
                next_activity_date = activity_date + pd.DateOffset(days=i+1)
                if not self.ticker_dao.retrieve_ticker_activity_by_day(ticker_id, next_activity_date):
                    continue
                
                prev_data_points[next_activity_date] = {'open': float(value['open']), 'close': float(value['close']), 'high': float(value['high']), 'low': float(value['low'])}
            
            # Update the last day's data
            if len(prev_data_points) > 1:
                self.data_points[ticker][last_day] = prev_data_points[last_day]
        
        return {
            'bollinger_bands': {
                'mean': self.data_points[symbol]['bollinger_bands']['mean'],
                'stddev': self.data_points[symbol]['bollinger_bands']['stddev']
            }
        }

    def generate_interpretation(self, ticker_id):
        """Generate an interpretation of the Bollinger Band"""
        
        # Get symbol for the ticker_id
        symbol = self.ticker_dao.get_ticker_symbol(ticker_id)
        if not symbol:
            print(f"No data available for ticker ID {ticker_id}")
            return
        
        bollinger_band = self.generate_bollinger_band_data(ticker_id)
        
        mean = bollinger_band['bollinger_bands']['mean']
        stddev = bollinger_band['bollinger_bands']['stddev']
        
        # Interpret the Bollinger Band
        if mean >= 50:
            print(f"{symbol} is above its 20-day moving average, indicating a strong uptrend.")
        elif mean <= 30:
            print(f"{symbol} is below its 20-day moving average, indicating a weak downtrend.")
        else:
            print(f"{symbol} has a neutral Bollinger Band, suggesting a balanced market.")
        
        if stddev < 10:
            print(f"The Bollinger Band is relatively narrow, indicating high volatility.")
        elif stddev > 30:
            print(f"The Bollinger Band is wide, indicating low volatility.")
        else:
            print(f"The Bollinger Band is in a neutral range, suggesting stability.")

if __name__ == '__main__':
    load_dotenv()
    
    analyzer = BollingerBandAnalyzer(ticker_dao=TickerDao(os.getenv('DB_USER'), os.getenv('DB_PASSWORD'), os.getenv('DB_HOST'), os.getenv('DB_NAME')))
    data_points = analyzer.generate_bollinger_band_data('AAPL')
    print(data_points)

    analyzer.generate_interpretation('AAPL')
