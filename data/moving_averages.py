import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime, timedelta

class moving_averages:

    def __init__(self, user, password, host, database):
        self.db_user = user
        self.db_password = password
        self.db_host = host
        self.db_name = database

        self.current_connection = None

    def open_connection(self):
        self.currenct_connection = mysql.connector.connect(user=self.db_user, 
                      password=self.db_password,
                      host=self.db_host,
                      database=self.db_name)

    def close_connection(self):
       self.currenct_connection.close()

    def calculateAverage(self, resultColumn, columnToAvg, interval, avgDataFrame):  
        ma_idx = avgDataFrame.columns.get_loc(resultColumn)
        close_idx =  avgDataFrame.columns.get_loc(columnToAvg)

        for i in range(len(avgDataFrame)-1, interval - 1, -1):  #range(start, stop, step)
            avgDataFrame.iloc[i,ma_idx] = avgDataFrame.iloc[i-interval:i,close_idx].mean()  # np.round(np.average(avgDataFrame.iloc[i-interval:i,close_idx]),2)s

    def loadAveragesFromDB(self, ticker_id, averageType):
        cursor = self.currenct_connection.cursor()

        sql= """
            select activity_date, value 
            from investing.averages a 
            where a.activity_date between  date_add(curdate(), interval -1 YEAR ) and curdate() 
            and ticker_id = %s and average_type = %s
            order by a.activity_date;
        """

        cursor.execute(sql, 
            (int(ticker_id), str(averageType))
        )

        df = pd.DataFrame(cursor.fetchall(),
            columns= ['activity_date', str(averageType).lower()])
        df = df.set_index('activity_date')

        cursor.close()
        
        return df
    
    def update_moving_averages(self, ticker_id, period):
        # Ensure the database connection is open
        if self.current_connection is None:
            self.open_connection()
        
        # Retrieve the last date for which the moving average was calculated
        cursor = self.current_connection.cursor()
        cursor.execute("""
            SELECT MAX(activity_date) 
            FROM investing.averages 
            WHERE ticker_id = %s AND average_type = %s
        """, (ticker_id, period))
        last_date = cursor.fetchone()[0]
        
        # If no last date, set it to a very early date to calculate for all data
        if last_date is None:
            last_date = '1900-01-01'
        else:
            last_date = last_date - timedelta(days=period)
            
        # Retrieve new data from the activity table since the last moving average calculation
        cursor.execute("""
            SELECT activity_date, close 
            FROM investing.activity 
            WHERE ticker_id = %s AND activity_date > %s
            ORDER BY activity_date ASC
        """, (ticker_id, last_date))
        
        # Convert fetched data into DataFrame
        new_data = pd.DataFrame(cursor.fetchall(), columns=['activity_date', 'close'])
        if not new_data.empty:
            new_data['activity_date'] = pd.to_datetime(new_data['activity_date'])
            new_data = new_data.set_index('activity_date')
            
            # Calculate moving average for the new data
            if isinstance(new_data, pd.DataFrame):
                new_data['moving_average'] = new_data['close'].rolling(window=period, min_periods=1).mean()
            
            # Insert or update the moving averages in the investing.averages table
            for index, row in new_data.iterrows():
                cursor.execute("""
                    INSERT INTO investing.averages (ticker_id, activity_date, average_type, value)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = VALUES(value)
                """, (ticker_id, index.date(), period, row['moving_average']))
            
            # Commit the changes to the database
            self.current_connection.commit()
        
        cursor.close()
        
        # Return the updated moving averages from the database
        return self.loadAveragesFromDB(ticker_id, period)
   