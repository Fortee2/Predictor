import logging
import os
from contextlib import contextmanager

import mysql.connector
import requests

logger = logging.getLogger(__name__)


class utility:
    def call_url_with_symbol(self, url, symbol):
        full_url = url + symbol  # Append the symbol to the URL
        response = requests.get(full_url)  # Send a GET request to the full URL
        return response

    def call_url_with_post_symbol(self, url, symbol):
        full_url = url + symbol  # Append the symbol to the URL
        response = requests.post(full_url)  # Send a GET request to the full URL
        return response


class DatabaseConnectionPool:
    """
    A singleton class for managing database connection pooling.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        user=None,
        password=None,
        host=None,
        database=None,
        pool_name="predictor_pool",
        pool_size=20,
    ):
        # Only initialize once
        if hasattr(self, "initialized"):
            return

        # Get database credentials from environment variables if not provided
        self.db_user = user or os.getenv("DB_USER")
        self.db_password = password or os.getenv("DB_PASSWORD")
        self.db_host = host or os.getenv("DB_HOST")
        self.db_name = database or os.getenv("DB_NAME")
        self.pool_name = pool_name
        self.pool_size = pool_size

        # Create the connection pool
        self.initialize_pool()
        self.initialized = True

    def initialize_pool(self):
        """Initialize the database connection pool."""
        try:
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=self.pool_name,
                pool_size=self.pool_size,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                database=self.db_name,
                autocommit=False,
            )
            print(f"Connection pool '{self.pool_name}' initialized with {self.pool_size} connections")
        except Exception as e:
            logger.error("Error creating connection pool: %s", str(e))
            raise

    def get_connection(self):
        """Get a connection from the pool."""
        try:
            return self.pool.get_connection()
        except Exception as e:
            logger.error("Error getting connection from pool: %s", str(e))
            raise

    @contextmanager
    def get_connection_context(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Database error: %s", str(e))
            raise
        else:
            if conn:
                conn.commit()
        finally:
            if conn:
                conn.close()
