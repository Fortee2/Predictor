import logging
from contextlib import contextmanager
from typing import Iterator

import mysql.connector
from mysql.connector.pooling import PooledMySQLConnection

from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class BaseDAO:
    def __init__(self, pool: DatabaseConnectionPool):
        self.pool = pool

    @contextmanager
    def get_connection(self) -> Iterator[PooledMySQLConnection]:
        """
        Context manager for database connections.

        Properly manages connection lifecycle:
        - Acquires connection from pool
        - Yields connection for use
        - Commits transaction on success
        - Rolls back on error
        - Always returns connection to pool
        """
        connection = None
        try:
            connection = self.pool.get_connection()
            yield connection
            # Commit transaction if no exceptions occurred
            if connection.is_connected():
                connection.commit()
        except mysql.connector.Error as e:
            logger.error("Database connection error: %s", str(e))
            # Rollback on database errors
            if connection and connection.is_connected():
                connection.rollback()
            raise
        except Exception as e:
            logger.error("Unexpected error during database operation: %s", str(e))
            # Rollback on any other errors
            if connection and connection.is_connected():
                connection.rollback()
            raise
        finally:
            # Always return connection to pool
            if connection and connection.is_connected():
                connection.close()
