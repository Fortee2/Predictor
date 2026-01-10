"""
DAO for AI Conversation History Persistence

This module handles saving and loading LLM conversation sessions to/from the database.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .base_dao import BaseDAO


class ConversationHistoryDAO(BaseDAO):
    """Data Access Object for AI conversation history."""

    def __init__(self, pool):
        """
        Initialize the ConversationHistoryDAO.

        Args:
            pool: Database connection pool
        """
        super().__init__(pool)
        self.logger = logging.getLogger(__name__)

    def save_conversation(
        self,
        portfolio_id: int,
        conversation_data: List[Dict],
        session_name: Optional[str] = None,
        set_as_active: bool = True
    ) -> Optional[int]:
        """
        Save or update a conversation session.

        Args:
            portfolio_id: Portfolio ID this conversation belongs to
            conversation_data: List of conversation messages
            session_name: Optional name for the session
            set_as_active: Whether to mark this as the active session

        Returns:
            Session ID if successful, None otherwise
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor()

            # Calculate message and exchange counts
            message_count = len(conversation_data)
            exchange_count = message_count // 2  # Each exchange is user + assistant

            # Convert conversation data to JSON
            conversation_json = json.dumps(conversation_data)

            # If set_as_active, deactivate other sessions for this portfolio
            if set_as_active:
                cursor.execute(
                    """
                    UPDATE ai_conversation_history 
                    SET is_active = FALSE 
                    WHERE portfolio_id = %s AND is_active = TRUE
                    """,
                    (portfolio_id,)
                )

            # Check if there's an active session to update
            cursor.execute(
                """
                SELECT id FROM ai_conversation_history 
                WHERE portfolio_id = %s AND is_active = TRUE 
                ORDER BY last_accessed_at DESC LIMIT 1
                """,
                (portfolio_id,)
            )
            result = cursor.fetchone()

            if result and set_as_active:
                # Update existing active session
                session_id = result[0]
                cursor.execute(
                    """
                    UPDATE ai_conversation_history 
                    SET conversation_data = %s,
                        message_count = %s,
                        exchange_count = %s,
                        session_name = COALESCE(%s, session_name),
                        last_accessed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (conversation_json, message_count, exchange_count, session_name, session_id)
                )
                self.logger.info(f"Updated conversation session {session_id} for portfolio {portfolio_id}")
            else:
                # Create new session
                cursor.execute(
                    """
                    INSERT INTO ai_conversation_history 
                    (portfolio_id, session_name, conversation_data, message_count, 
                     exchange_count, is_active, last_accessed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (portfolio_id, session_name, conversation_json, message_count,
                     exchange_count, set_as_active)
                )
                session_id = cursor.lastrowid
                self.logger.info(f"Created new conversation session {session_id} for portfolio {portfolio_id}")

            connection.commit()
            return session_id

        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}")
            if connection:
                connection.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.pool.release_connection(connection)

    def load_active_conversation(self, portfolio_id: int) -> Optional[Dict]:
        """
        Load the active conversation session for a portfolio.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Dictionary with session info and conversation data, or None if no active session
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, session_name, conversation_data, message_count, 
                       exchange_count, created_at, updated_at, last_accessed_at
                FROM ai_conversation_history
                WHERE portfolio_id = %s AND is_active = TRUE
                ORDER BY last_accessed_at DESC
                LIMIT 1
                """,
                (portfolio_id,)
            )

            result = cursor.fetchone()

            if result:
                # Parse JSON conversation data
                result['conversation_data'] = json.loads(result['conversation_data'])
                
                # Update last_accessed_at
                cursor.execute(
                    """
                    UPDATE ai_conversation_history 
                    SET last_accessed_at = NOW() 
                    WHERE id = %s
                    """,
                    (result['id'],)
                )
                connection.commit()

                self.logger.info(f"Loaded active conversation session {result['id']} for portfolio {portfolio_id}")
                return result

            return None

        except Exception as e:
            self.logger.error(f"Error loading active conversation: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.pool.release_connection(connection)

    def get_conversation_by_id(self, session_id: int) -> Optional[Dict]:
        """
        Load a specific conversation session by ID.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session info and conversation data, or None if not found
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, portfolio_id, session_name, conversation_data, 
                       message_count, exchange_count, created_at, updated_at, 
                       last_accessed_at, is_active
                FROM ai_conversation_history
                WHERE id = %s
                """,
                (session_id,)
            )

            result = cursor.fetchone()

            if result:
                # Parse JSON conversation data
                result['conversation_data'] = json.loads(result['conversation_data'])

                # Update last_accessed_at
                cursor.execute(
                    """
                    UPDATE ai_conversation_history 
                    SET last_accessed_at = NOW() 
                    WHERE id = %s
                    """,
                    (session_id,)
                )
                connection.commit()

                return result

            return None

        except Exception as e:
            self.logger.error(f"Error loading conversation by ID: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.pool.release_connection(connection)

    def list_sessions(self, portfolio_id: int, limit: int = 10) -> List[Dict]:
        """
        List recent conversation sessions for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries (without full conversation data)
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, session_name, message_count, exchange_count, 
                       created_at, updated_at, last_accessed_at, is_active
                FROM ai_conversation_history
                WHERE portfolio_id = %s
                ORDER BY last_accessed_at DESC
                LIMIT %s
                """,
                (portfolio_id, limit)
            )

            results = cursor.fetchall()
            return results

        except Exception as e:
            self.logger.error(f"Error listing conversation sessions: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.pool.release_connection(connection)

    def delete_session(self, session_id: int) -> bool:
        """
        Delete a conversation session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor()

            cursor.execute(
                "DELETE FROM ai_conversation_history WHERE id = %s",
                (session_id,)
            )

            connection.commit()
            self.logger.info(f"Deleted conversation session {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting conversation session: {e}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.pool.release_connection(connection)

    def clear_old_sessions(self, portfolio_id: int, days_old: int = 30) -> int:
        """
        Delete conversation sessions older than specified days.

        Args:
            portfolio_id: Portfolio ID
            days_old: Delete sessions not accessed in this many days

        Returns:
            Number of sessions deleted
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                DELETE FROM ai_conversation_history 
                WHERE portfolio_id = %s 
                AND is_active = FALSE
                AND last_accessed_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """,
                (portfolio_id, days_old)
            )

            deleted_count = cursor.rowcount
            connection.commit()

            self.logger.info(f"Deleted {deleted_count} old conversation sessions for portfolio {portfolio_id}")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Error clearing old sessions: {e}")
            if connection:
                connection.rollback()
            return 0
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.pool.release_connection(connection)

    def deactivate_session(self, session_id: int) -> bool:
        """
        Mark a session as inactive.

        Args:
            session_id: Session ID

        Returns:
            True if successful, False otherwise
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor()

            cursor.execute(
                "UPDATE ai_conversation_history SET is_active = FALSE WHERE id = %s",
                (session_id,)
            )

            connection.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error deactivating session: {e}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.pool.release_connection(connection)

    def set_session_name(self, session_id: int, session_name: str) -> bool:
        """
        Set or update the name of a session.

        Args:
            session_id: Session ID
            session_name: New session name

        Returns:
            True if successful, False otherwise
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor()

            cursor.execute(
                "UPDATE ai_conversation_history SET session_name = %s WHERE id = %s",
                (session_name, session_id)
            )

            connection.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error setting session name: {e}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.pool.release_connection(connection)
