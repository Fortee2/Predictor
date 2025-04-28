import pandas as pd
import numpy as np
from enum import Enum
import mysql.connector
import decimal

class TrendDirection(Enum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"
    
class TrendStrength(Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"

class TrendAnalyzer:
    """Class for analyzing trend direction and strength of various indicators."""
    
    def __init__(self, user, password, host, database):
        self.db_user = user
        self.db_password = password
        self.db_host = host
        self.db_name = database
        self.current_connection = None
        
    def open_connection(self):
        self.current_connection = mysql.connector.connect(user=self.db_user, 
                      password=self.db_password,
                      host=self.db_host,
                      database=self.db_name)

    def close_connection(self):
        if self.current_connection:
            self.current_connection.close()
    
    def analyze_ma_trend(self, ticker_id, period=20, lookback_days=5):
        """
        Analyzes the moving average trend for a given ticker and period.
        
        Args:
            ticker_id (int): Ticker ID to analyze
            period (int): MA period (e.g., 20 for 20-day MA)
            lookback_days (int): Number of days to look back for trend analysis
            
        Returns:
            dict: A dictionary containing trend direction, strength, and angle
        """
        if self.current_connection is None:
            self.open_connection()
            
        cursor = self.current_connection.cursor()
        
        # Retrieve MA values for the last {lookback_days} days
        cursor.execute("""
            SELECT activity_date, value 
            FROM investing.averages
            WHERE ticker_id = %s 
            AND average_type = %s
            ORDER BY activity_date DESC
            LIMIT %s
        """, (ticker_id, period, lookback_days))
        
        result = cursor.fetchall()
        cursor.close()
        
        # Handle case where not enough data is available
        if len(result) < 2:
            return {
                "direction": TrendDirection.UNKNOWN.value,
                "strength": TrendStrength.UNKNOWN.value,
                "angle": None,
                "values": []
            }
        
        # Convert to dataframe and sort by date
        df = pd.DataFrame(result, columns=['date', 'value'])
        df = df.sort_values('date')
        
        # Calculate the slope (direction and strength)
        latest_value = float(df.iloc[-1]['value'])
        previous_value = float(df.iloc[-2]['value'])
        
        # Calculate the percentage change rate
        # Additional checks for division by zero or very small values
        try:
            if abs(previous_value) < 0.0001:
                percent_change = 0
            else:
                percent_change = (latest_value - previous_value) / previous_value * 100
        except (ZeroDivisionError, decimal.DivisionUndefined):
            percent_change = 0
            
        # Calculate angle of the trend
        if len(df) >= 3:
            # Fit a line to the data points
            x = np.arange(len(df))
            # Ensure all values are converted to float for numpy operations
            y = np.array([float(val) for val in df['value'].values])
            z = np.polyfit(x, y, 1)
            slope = float(z[0])
            
            # Calculate the angle in degrees
            angle = float(np.degrees(np.arctan(slope)))
        else:
            angle = None
            
        # Determine direction
        if latest_value > previous_value:
            direction = TrendDirection.UP.value
        elif latest_value < previous_value:
            direction = TrendDirection.DOWN.value
        else:
            direction = TrendDirection.FLAT.value
        
        # Determine strength based on percentage change
        abs_percent_change = abs(percent_change)
        
        if abs_percent_change > 1.0:
            strength = TrendStrength.STRONG.value
        elif abs_percent_change > 0.5:
            strength = TrendStrength.MODERATE.value
        else:
            strength = TrendStrength.WEAK.value
        
        # Convert the MA values to a list for return
        values = df['value'].tolist()
        
        return {
            "direction": direction,
            "strength": strength,
            "angle": angle,
            "percent_change": percent_change,
            "values": values
        }
    
    def analyze_price_vs_ma(self, ticker_id, ma_period=20):
        """
        Analyzes the relationship between price and its moving average.
        
        Args:
            ticker_id (int): Ticker ID to analyze
            ma_period (int): Moving average period
            
        Returns:
            dict: A dictionary describing the price location relative to MA
        """
        if self.current_connection is None:
            self.open_connection()
            
        cursor = self.current_connection.cursor()
        
        # Get latest price
        cursor.execute("""
            SELECT close FROM investing.activity
            WHERE ticker_id = %s
            ORDER BY activity_date DESC
            LIMIT 1
        """, (ticker_id,))
        
        price_result = cursor.fetchone()
        
        # Get latest MA
        cursor.execute("""
            SELECT value FROM investing.averages
            WHERE ticker_id = %s AND average_type = %s
            ORDER BY activity_date DESC
            LIMIT 1
        """, (ticker_id, ma_period))
        
        ma_result = cursor.fetchone()
        cursor.close()
        
        if not price_result or not ma_result:
            return {
                "position": "UNKNOWN",
                "distance_percent": None,
                "price": None,
                "ma_value": None
            }
        
        # Use explicit float conversion to avoid decimal/float mixing
        price = float(price_result[0])
        ma_value = float(ma_result[0])
        
        # Calculate percentage distance from MA
        # Additional checks for division by zero or very small values
        try:
            if abs(ma_value) < 0.0001:
                distance_percent = 0
            else:
                distance_percent = (price - ma_value) / ma_value * 100
        except (ZeroDivisionError, decimal.DivisionUndefined):
            distance_percent = 0
            
        # Determine position relative to MA
        if price > ma_value:
            position = "ABOVE_MA"
        elif price < ma_value:
            position = "BELOW_MA"
        else:
            position = "AT_MA"
            
        return {
            "position": position,
            "distance_percent": distance_percent,
            "price": price,
            "ma_value": ma_value
        }
