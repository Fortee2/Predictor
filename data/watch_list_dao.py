import mysql.connector
from data.ticker_dao import TickerDao

class WatchListDAO:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)
        self.connection = None
        
    def open_connection(self):
        try:
            self.connection = mysql.connector.connect(
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                database=self.db_name
            )
            self.ticker_dao.open_connection()
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")
            
    def close_connection(self):
        if self.connection:
            self.connection.close()
            self.ticker_dao.close_connection()
    
    def create_watch_list(self, name, description=None):
        """
        Create a new watch list
        
        Args:
            name (str): The name of the watch list
            description (str, optional): A description of the watch list
            
        Returns:
            int: The ID of the created watch list
        """
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO watch_lists (name, description) VALUES (%s, %s)"
            values = (name, description)
            cursor.execute(query, values)
            self.connection.commit()
            watch_list_id = cursor.lastrowid
            return watch_list_id
        except mysql.connector.Error as e:
            print(f"Error creating watch list: {e}")
            return None
    
    def get_watch_list(self, watch_list_id=None):
        """
        Get watch list(s) by ID or all watch lists if no ID is provided
        
        Args:
            watch_list_id (int, optional): The ID of the watch list to retrieve
            
        Returns:
            dict or list: The requested watch list or all watch lists
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            if watch_list_id:
                query = "SELECT * FROM watch_lists WHERE id = %s"
                values = (watch_list_id,)
            else:
                query = "SELECT * FROM watch_lists ORDER BY name"
                values = None
            cursor.execute(query, values)
            if watch_list_id:
                return cursor.fetchone()
            return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Error retrieving watch list(s): {e}")
            return [] if watch_list_id is None else None
    
    def update_watch_list(self, watch_list_id, name=None, description=None):
        """
        Update a watch list's name or description
        
        Args:
            watch_list_id (int): The ID of the watch list to update
            name (str, optional): The new name for the watch list
            description (str, optional): The new description for the watch list
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            query = "UPDATE watch_lists SET "
            values = []
            if name:
                query += "name = %s, "
                values.append(name)
            if description:
                query += "description = %s, "
                values.append(description)
            query = query.rstrip(", ") + " WHERE id = %s"
            values.append(watch_list_id)
            
            if len(values) == 1:  # Only watch_list_id, nothing to update
                return True
                
            cursor.execute(query, values)
            self.connection.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as e:
            print(f"Error updating watch list: {e}")
            return False
    
    def delete_watch_list(self, watch_list_id):
        """
        Delete a watch list
        
        Args:
            watch_list_id (int): The ID of the watch list to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM watch_lists WHERE id = %s"
            values = (watch_list_id,)
            cursor.execute(query, values)
            self.connection.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as e:
            print(f"Error deleting watch list: {e}")
            return False
    
    def add_ticker_to_watch_list(self, watch_list_id, ticker_symbol, notes=None):
        """
        Add a ticker to a watch list
        
        Args:
            watch_list_id (int): The ID of the watch list
            ticker_symbol (str): The ticker symbol to add
            notes (str, optional): Notes about this ticker
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                print(f"Error: Ticker '{ticker_symbol}' not found")
                return False
                
            cursor = self.connection.cursor()
            query = "INSERT INTO watch_list_tickers (watch_list_id, ticker_id, notes) VALUES (%s, %s, %s)"
            values = (watch_list_id, ticker_id, notes)
            cursor.execute(query, values)
            self.connection.commit()
            return True
        except mysql.connector.IntegrityError as e:
            if e.errno == 1062:  # Duplicate entry error
                print(f"Ticker '{ticker_symbol}' is already in this watch list")
            else:
                print(f"Error adding ticker to watch list: {e}")
            return False
        except mysql.connector.Error as e:
            print(f"Error adding ticker to watch list: {e}")
            return False
    
    def remove_ticker_from_watch_list(self, watch_list_id, ticker_symbol):
        """
        Remove a ticker from a watch list
        
        Args:
            watch_list_id (int): The ID of the watch list
            ticker_symbol (str): The ticker symbol to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                print(f"Error: Ticker '{ticker_symbol}' not found")
                return False
                
            cursor = self.connection.cursor()
            query = "DELETE FROM watch_list_tickers WHERE watch_list_id = %s AND ticker_id = %s"
            values = (watch_list_id, ticker_id)
            cursor.execute(query, values)
            self.connection.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as e:
            print(f"Error removing ticker from watch list: {e}")
            return False
    
    def get_tickers_in_watch_list(self, watch_list_id):
        """
        Get all tickers in a watch list
        
        Args:
            watch_list_id (int): The ID of the watch list
            
        Returns:
            list: A list of dictionaries with ticker information
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT wlt.id, wlt.ticker_id, t.ticker as symbol, t.ticker_name as name, 
                       wlt.date_added, wlt.notes
                FROM watch_list_tickers wlt
                JOIN tickers t ON wlt.ticker_id = t.id
                WHERE wlt.watch_list_id = %s
                ORDER BY t.ticker
            """
            values = (watch_list_id,)
            cursor.execute(query, values)
            return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Error retrieving tickers in watch list: {e}")
            return []
    
    def is_ticker_in_watch_list(self, watch_list_id, ticker_symbol):
        """
        Check if a ticker is in a watch list
        
        Args:
            watch_list_id (int): The ID of the watch list
            ticker_symbol (str): The ticker symbol to check
            
        Returns:
            bool: True if the ticker is in the watch list, False otherwise
        """
        try:
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                return False
                
            cursor = self.connection.cursor()
            query = "SELECT COUNT(*) FROM watch_list_tickers WHERE watch_list_id = %s AND ticker_id = %s"
            values = (watch_list_id, ticker_id)
            cursor.execute(query, values)
            count = cursor.fetchone()[0]
            return count > 0
        except mysql.connector.Error as e:
            print(f"Error checking if ticker is in watch list: {e}")
            return False
    
    def update_ticker_notes(self, watch_list_id, ticker_symbol, notes):
        """
        Update notes for a ticker in a watch list
        
        Args:
            watch_list_id (int): The ID of the watch list
            ticker_symbol (str): The ticker symbol
            notes (str): The notes to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                print(f"Error: Ticker '{ticker_symbol}' not found")
                return False
                
            cursor = self.connection.cursor()
            query = "UPDATE watch_list_tickers SET notes = %s WHERE watch_list_id = %s AND ticker_id = %s"
            values = (notes, watch_list_id, ticker_id)
            cursor.execute(query, values)
            self.connection.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as e:
            print(f"Error updating ticker notes: {e}")
            return False