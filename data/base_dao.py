import logging
from contextlib import contextmanager

import mysql.connector

from data.utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class BaseDAO:
    
    def __init__(self, pool: DatabaseConnectionPool):

        self.pool = pool
        self.current_connection = None


    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        connection = None
        try:
            if (
                self.current_connection is not None
                and self.current_connection.is_connected()
            ):
                connection = self.current_connection
                yield connection
            else:
                connection = self.pool.get_connection()
                self.current_connection = connection
                yield connection
        except mysql.connector.Error as e:
            logger.error("Database connection error: %s", str(e))
            raise
        finally:
            pass
