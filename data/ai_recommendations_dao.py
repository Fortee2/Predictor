import datetime
import json
import logging
from typing import Dict, List, Optional

import mysql.connector

from .base_dao import BaseDAO
from .ticker_dao import TickerDao
from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class AIRecommendationsDAO(BaseDAO):
    """Data Access Object for managing AI trading recommendations."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__(pool)
        self.ticker_dao = TickerDao(pool)

    def save_recommendation(
        self,
        portfolio_id: int,
        ticker_symbol: str,
        recommendation_type: str,
        recommended_quantity: Optional[float] = None,
        recommended_price: Optional[float] = None,
        confidence_score: Optional[float] = None,
        reasoning: Optional[str] = None,
        technical_indicators: Optional[Dict] = None,
        sentiment_score: Optional[float] = None,
        recommendation_date: Optional[datetime.datetime] = None,
        expires_date: Optional[datetime.datetime] = None,
    ) -> Optional[int]:
        """
        Save a new AI recommendation to the database.

        Args:
            portfolio_id: The portfolio ID
            ticker_symbol: The stock ticker symbol
            recommendation_type: Type of recommendation (BUY, SELL, HOLD, REDUCE, INCREASE)
            recommended_quantity: Suggested number of shares
            recommended_price: Suggested price point
            confidence_score: AI confidence score (0-100)
            reasoning: Text explanation of the recommendation
            technical_indicators: Dict of technical indicator values (stored as JSON)
            sentiment_score: News sentiment score
            recommendation_date: Date of recommendation (defaults to now)
            expires_date: When recommendation becomes stale

        Returns:
            int: The ID of the created recommendation, or None on error
        """
        try:
            # Get ticker_id from symbol
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                logger.error(f"Ticker symbol {ticker_symbol} not found in database")
                return None

            # Default to current datetime if not specified
            if recommendation_date is None:
                recommendation_date = datetime.datetime.now()

            # Convert technical_indicators dict to JSON string
            technical_indicators_json = None
            if technical_indicators:
                technical_indicators_json = json.dumps(technical_indicators)

            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = """
                    INSERT INTO ai_recommendations
                    (portfolio_id, ticker_id, recommendation_type, recommended_quantity,
                     recommended_price, confidence_score, reasoning, technical_indicators,
                     sentiment_score, recommendation_date, expires_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
                """
                values = (
                    portfolio_id,
                    ticker_id,
                    recommendation_type,
                    recommended_quantity,
                    recommended_price,
                    confidence_score,
                    reasoning,
                    technical_indicators_json,
                    sentiment_score,
                    recommendation_date,
                    expires_date,
                )
                cursor.execute(query, values)
                recommendation_id = cursor.lastrowid
                logger.info(f"Created AI recommendation {recommendation_id} for {ticker_symbol}")
                return recommendation_id

        except mysql.connector.Error as e:
            logger.error(f"Error saving AI recommendation: {e}")
            return None

    def get_recommendation_by_id(self, recommendation_id: int) -> Optional[Dict]:
        """
        Get a specific recommendation by ID.

        Args:
            recommendation_id: The recommendation ID

        Returns:
            Dict containing recommendation details, or None if not found
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT r.*, t.ticker as ticker_symbol, t.ticker_name
                    FROM ai_recommendations r
                    INNER JOIN tickers t ON r.ticker_id = t.id
                    WHERE r.id = %s
                """
                cursor.execute(query, (recommendation_id,))
                result = cursor.fetchone()

                if result and result.get('technical_indicators'):
                    # Parse JSON string back to dict
                    result['technical_indicators'] = json.loads(result['technical_indicators'])

                return result

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving recommendation {recommendation_id}: {e}")
            return None

    def get_active_recommendations(self, portfolio_id: int) -> List[Dict]:
        """
        Get all active (pending) recommendations for a portfolio.

        Args:
            portfolio_id: The portfolio ID

        Returns:
            List of active recommendation dictionaries
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT r.*, t.ticker as ticker_symbol, t.ticker_name
                    FROM ai_recommendations r
                    INNER JOIN tickers t ON r.ticker_id = t.id
                    WHERE r.portfolio_id = %s
                    AND r.status = 'PENDING'
                    AND (r.expires_date IS NULL OR r.expires_date > NOW())
                    ORDER BY r.recommendation_date DESC
                """
                cursor.execute(query, (portfolio_id,))
                results = cursor.fetchall()

                # Parse JSON for technical indicators
                for result in results:
                    if result.get('technical_indicators'):
                        result['technical_indicators'] = json.loads(result['technical_indicators'])

                return results

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving active recommendations: {e}")
            return []

    def get_recommendations_by_ticker(
        self, portfolio_id: int, ticker_symbol: str, limit: int = 10
    ) -> List[Dict]:
        """
        Get recommendation history for a specific ticker.

        Args:
            portfolio_id: The portfolio ID
            ticker_symbol: The stock ticker symbol
            limit: Maximum number of recommendations to return

        Returns:
            List of recommendation dictionaries
        """
        try:
            ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
            if not ticker_id:
                return []

            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT r.*, t.ticker as ticker_symbol, t.ticker_name
                    FROM ai_recommendations r
                    INNER JOIN tickers t ON r.ticker_id = t.id
                    WHERE r.portfolio_id = %s
                    AND r.ticker_id = %s
                    ORDER BY r.recommendation_date DESC
                    LIMIT %s
                """
                cursor.execute(query, (portfolio_id, ticker_id, limit))
                results = cursor.fetchall()

                # Parse JSON for technical indicators
                for result in results:
                    if result.get('technical_indicators'):
                        result['technical_indicators'] = json.loads(result['technical_indicators'])

                return results

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving recommendations for {ticker_symbol}: {e}")
            return []

    def get_recommendations_by_portfolio(
        self,
        portfolio_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get all recommendations for a portfolio, optionally filtered by status.

        Args:
            portfolio_id: The portfolio ID
            status: Optional status filter (PENDING, FOLLOWED, PARTIALLY_FOLLOWED, IGNORED, EXPIRED)
            limit: Maximum number of recommendations to return

        Returns:
            List of recommendation dictionaries
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                if status:
                    query = """
                        SELECT r.*, t.ticker as ticker_symbol, t.ticker_name
                        FROM ai_recommendations r
                        INNER JOIN tickers t ON r.ticker_id = t.id
                        WHERE r.portfolio_id = %s AND r.status = %s
                        ORDER BY r.recommendation_date DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (portfolio_id, status, limit))
                else:
                    query = """
                        SELECT r.*, t.ticker as ticker_symbol, t.ticker_name
                        FROM ai_recommendations r
                        INNER JOIN tickers t ON r.ticker_id = t.id
                        WHERE r.portfolio_id = %s
                        ORDER BY r.recommendation_date DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (portfolio_id, limit))

                results = cursor.fetchall()

                # Parse JSON for technical indicators
                for result in results:
                    if result.get('technical_indicators'):
                        result['technical_indicators'] = json.loads(result['technical_indicators'])

                return results

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving recommendations for portfolio {portfolio_id}: {e}")
            return []

    def update_recommendation_status(
        self,
        recommendation_id: int,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update the status of a recommendation.

        Args:
            recommendation_id: The recommendation ID
            status: New status (PENDING, FOLLOWED, PARTIALLY_FOLLOWED, IGNORED, EXPIRED)
            notes: Optional notes about the status change

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # If notes provided, we might want to store them somewhere
                # For now, just update the status
                query = """
                    UPDATE ai_recommendations
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s
                """
                cursor.execute(query, (status, recommendation_id))
                logger.info(f"Updated recommendation {recommendation_id} status to {status}")
                return True

        except mysql.connector.Error as e:
            logger.error(f"Error updating recommendation status: {e}")
            return False

    def expire_old_recommendations(self, portfolio_id: int) -> int:
        """
        Mark expired recommendations as EXPIRED.

        Args:
            portfolio_id: The portfolio ID

        Returns:
            int: Number of recommendations expired
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = """
                    UPDATE ai_recommendations
                    SET status = 'EXPIRED', updated_at = NOW()
                    WHERE portfolio_id = %s
                    AND status = 'PENDING'
                    AND expires_date IS NOT NULL
                    AND expires_date < NOW()
                """
                cursor.execute(query, (portfolio_id,))
                expired_count = cursor.rowcount
                if expired_count > 0:
                    logger.info(f"Expired {expired_count} old recommendations for portfolio {portfolio_id}")
                return expired_count

        except mysql.connector.Error as e:
            logger.error(f"Error expiring old recommendations: {e}")
            return 0

    def get_recommendation_statistics(self, portfolio_id: int) -> Dict:
        """
        Get statistics about recommendations for a portfolio.

        Args:
            portfolio_id: The portfolio ID

        Returns:
            Dict containing statistics
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT
                        status,
                        COUNT(*) as count,
                        AVG(confidence_score) as avg_confidence
                    FROM ai_recommendations
                    WHERE portfolio_id = %s
                    GROUP BY status
                """
                cursor.execute(query, (portfolio_id,))
                results = cursor.fetchall()

                # Convert to more useful format
                stats = {
                    'total': 0,
                    'by_status': {}
                }

                for row in results:
                    status = row['status']
                    count = row['count']
                    stats['total'] += count
                    stats['by_status'][status] = {
                        'count': count,
                        'avg_confidence': float(row['avg_confidence']) if row['avg_confidence'] else 0
                    }

                return stats

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving recommendation statistics: {e}")
            return {'total': 0, 'by_status': {}}

    def link_transaction_to_recommendation(
        self,
        recommendation_id: int,
        transaction_id: int
    ) -> bool:
        """
        Link a transaction to a recommendation (to be called when transaction is created).
        This updates the recommendation status based on whether it was followed.

        Args:
            recommendation_id: The recommendation ID
            transaction_id: The portfolio transaction ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # For now, we'll just mark the recommendation as FOLLOWED
            # In the future, we could add more sophisticated logic to determine
            # if it was PARTIALLY_FOLLOWED
            return self.update_recommendation_status(recommendation_id, 'FOLLOWED')

        except Exception as e:
            logger.error(f"Error linking transaction to recommendation: {e}")
            return False

    def delete_recommendation(self, recommendation_id: int) -> bool:
        """
        Delete a recommendation (use with caution - may want to mark as deleted instead).

        Args:
            recommendation_id: The recommendation ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = "DELETE FROM ai_recommendations WHERE id = %s"
                cursor.execute(query, (recommendation_id,))
                logger.info(f"Deleted recommendation {recommendation_id}")
                return True

        except mysql.connector.Error as e:
            logger.error(f"Error deleting recommendation: {e}")
            return False
