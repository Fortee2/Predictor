"""
Data Access Object for managing trading strategies.

This module provides database operations for creating, reading, updating,
and deleting trading strategies with anchor and confirmation indicators.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import mysql.connector

from .base_dao import BaseDAO
from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class TradingStrategyDAO(BaseDAO):
    """Data Access Object for trading strategies."""

    def __init__(self, pool: DatabaseConnectionPool):
        """
        Initialize the TradingStrategyDAO.

        Args:
            pool: Database connection pool
        """
        super().__init__(pool)
        self._templates_cache = None

    def create_strategy(
        self,
        name: str,
        strategy_type: str,
        anchor_indicator: str,
        anchor_config: Dict,
        buy_conditions: Dict,
        sell_conditions: Dict,
        description: Optional[str] = None,
        confirmation_indicators: Optional[List[Dict]] = None,
        min_confidence_score: float = 50.0,
        max_signals_per_day: int = 10,
        portfolio_id: Optional[int] = None,
        watch_list_id: Optional[int] = None,
        active: bool = True,
        created_by: str = "USER",
    ) -> Optional[int]:
        """
        Create a new trading strategy.

        Args:
            name: Strategy display name
            strategy_type: Strategy category (RSI_REVERSAL, MACD_MOMENTUM, etc.)
            anchor_indicator: Primary indicator name (rsi, macd, etc.)
            anchor_config: Anchor indicator configuration dict
            buy_conditions: Conditions that trigger BUY signals (dict)
            sell_conditions: Conditions that trigger SELL signals (dict)
            description: Optional strategy description
            confirmation_indicators: Optional list of confirmation indicator configs
            min_confidence_score: Minimum confidence to generate signal (0-100)
            max_signals_per_day: Maximum signals per ticker per day
            portfolio_id: Apply to specific portfolio (None = all)
            watch_list_id: Apply to specific watchlist (None = all)
            active: Whether strategy is enabled
            created_by: Creator identifier (USER or AI)

        Returns:
            int: The ID of the created strategy, or None on error
        """
        try:
            # Convert dicts/lists to JSON strings
            anchor_config_json = json.dumps(anchor_config)
            buy_conditions_json = json.dumps(buy_conditions)
            sell_conditions_json = json.dumps(sell_conditions)
            confirmation_indicators_json = (
                json.dumps(confirmation_indicators) if confirmation_indicators else None
            )

            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = """
                    INSERT INTO trading_strategies
                    (name, description, strategy_type, anchor_indicator, anchor_config,
                     confirmation_indicators, buy_conditions, sell_conditions,
                     min_confidence_score, max_signals_per_day, portfolio_id,
                     watch_list_id, active, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    name,
                    description,
                    strategy_type,
                    anchor_indicator,
                    anchor_config_json,
                    confirmation_indicators_json,
                    buy_conditions_json,
                    sell_conditions_json,
                    min_confidence_score,
                    max_signals_per_day,
                    portfolio_id,
                    watch_list_id,
                    active,
                    created_by,
                )
                cursor.execute(query, values)
                strategy_id = cursor.lastrowid
                logger.info(f"Created trading strategy {strategy_id}: {name}")
                return strategy_id

        except mysql.connector.Error as e:
            logger.error(f"Error creating trading strategy: {e}")
            return None

    def get_strategy(self, strategy_id: int) -> Optional[Dict]:
        """
        Retrieve a single strategy by ID.

        Args:
            strategy_id: The strategy ID

        Returns:
            Dict containing strategy details with parsed JSON fields, or None if not found
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT * FROM trading_strategies
                    WHERE id = %s
                """
                cursor.execute(query, (strategy_id,))
                result = cursor.fetchone()

                if result:
                    # Parse JSON fields back to Python objects
                    result["anchor_config"] = json.loads(result["anchor_config"])
                    result["buy_conditions"] = json.loads(result["buy_conditions"])
                    result["sell_conditions"] = json.loads(result["sell_conditions"])
                    if result.get("confirmation_indicators"):
                        result["confirmation_indicators"] = json.loads(
                            result["confirmation_indicators"]
                        )

                return result

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving strategy {strategy_id}: {e}")
            return None

    def get_active_strategies(
        self, portfolio_id: Optional[int] = None, watch_list_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all active (enabled) strategies, optionally filtered by portfolio or watchlist.

        Args:
            portfolio_id: Filter by portfolio ID (None = all portfolios)
            watch_list_id: Filter by watchlist ID (None = all watchlists)

        Returns:
            List of strategy dictionaries
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                # Build query with optional filters
                query = "SELECT * FROM trading_strategies WHERE active = TRUE"
                params = []

                if portfolio_id is not None:
                    query += " AND (portfolio_id IS NULL OR portfolio_id = %s)"
                    params.append(portfolio_id)

                if watch_list_id is not None:
                    query += " AND (watch_list_id IS NULL OR watch_list_id = %s)"
                    params.append(watch_list_id)

                query += " ORDER BY created_at DESC"

                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                # Parse JSON fields for each result
                for result in results:
                    result["anchor_config"] = json.loads(result["anchor_config"])
                    result["buy_conditions"] = json.loads(result["buy_conditions"])
                    result["sell_conditions"] = json.loads(result["sell_conditions"])
                    if result.get("confirmation_indicators"):
                        result["confirmation_indicators"] = json.loads(
                            result["confirmation_indicators"]
                        )

                return results

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving active strategies: {e}")
            return []

    def get_all_strategies(
        self, portfolio_id: Optional[int] = None, include_inactive: bool = True
    ) -> List[Dict]:
        """
        Get all strategies, optionally filtered.

        Args:
            portfolio_id: Filter by portfolio ID (None = all)
            include_inactive: Include inactive strategies

        Returns:
            List of strategy dictionaries
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                query = "SELECT * FROM trading_strategies WHERE 1=1"
                params = []

                if portfolio_id is not None:
                    query += " AND (portfolio_id IS NULL OR portfolio_id = %s)"
                    params.append(portfolio_id)

                if not include_inactive:
                    query += " AND active = TRUE"

                query += " ORDER BY created_at DESC"

                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                # Parse JSON fields
                for result in results:
                    result["anchor_config"] = json.loads(result["anchor_config"])
                    result["buy_conditions"] = json.loads(result["buy_conditions"])
                    result["sell_conditions"] = json.loads(result["sell_conditions"])
                    if result.get("confirmation_indicators"):
                        result["confirmation_indicators"] = json.loads(
                            result["confirmation_indicators"]
                        )

                return results

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving all strategies: {e}")
            return []

    def update_strategy(self, strategy_id: int, **updates) -> bool:
        """
        Update a strategy's fields.

        Args:
            strategy_id: The strategy ID
            **updates: Fields to update (name, description, anchor_config, etc.)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not updates:
                logger.warning("No updates provided for strategy update")
                return False

            # JSON fields that need serialization
            json_fields = [
                "anchor_config",
                "buy_conditions",
                "sell_conditions",
                "confirmation_indicators",
            ]

            # Convert JSON fields to strings
            for field in json_fields:
                if field in updates and updates[field] is not None:
                    updates[field] = json.dumps(updates[field])

            # Build UPDATE query
            set_clauses = [f"{field} = %s" for field in updates.keys()]
            query = f"""
                UPDATE trading_strategies
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """

            values = list(updates.values()) + [strategy_id]

            with self.get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(query, tuple(values))
                rows_affected = cursor.rowcount
                logger.info(f"Updated strategy {strategy_id}, rows affected: {rows_affected}")
                return rows_affected > 0

        except mysql.connector.Error as e:
            logger.error(f"Error updating strategy {strategy_id}: {e}")
            return False

    def delete_strategy(self, strategy_id: int) -> bool:
        """
        Delete a strategy (will cascade delete all related signals).

        Args:
            strategy_id: The strategy ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = "DELETE FROM trading_strategies WHERE id = %s"
                cursor.execute(query, (strategy_id,))
                rows_affected = cursor.rowcount
                logger.info(
                    f"Deleted strategy {strategy_id}, rows affected: {rows_affected}"
                )
                return rows_affected > 0

        except mysql.connector.Error as e:
            logger.error(f"Error deleting strategy {strategy_id}: {e}")
            return False

    def toggle_strategy(self, strategy_id: int, active: bool = True) -> bool:
        """
        Enable or disable a strategy.

        Args:
            strategy_id: The strategy ID
            active: True to enable, False to disable

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = """
                    UPDATE trading_strategies
                    SET active = %s
                    WHERE id = %s
                """
                cursor.execute(query, (active, strategy_id))
                rows_affected = cursor.rowcount
                status = "enabled" if active else "disabled"
                logger.info(f"Strategy {strategy_id} {status}")
                return rows_affected > 0

        except mysql.connector.Error as e:
            logger.error(f"Error toggling strategy {strategy_id}: {e}")
            return False

    def load_templates(self) -> List[Dict]:
        """
        Load strategy templates from JSON file.

        Returns:
            List of template dictionaries
        """
        if self._templates_cache is not None:
            return self._templates_cache

        try:
            # Find the templates file
            templates_path = Path(__file__).parent / "strategy_templates.json"

            if not templates_path.exists():
                logger.warning(f"Templates file not found: {templates_path}")
                return []

            with open(templates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._templates_cache = data.get("templates", [])
                logger.info(f"Loaded {len(self._templates_cache)} strategy templates")
                return self._templates_cache

        except Exception as e:
            logger.error(f"Error loading strategy templates: {e}")
            return []

    def get_template(self, template_id: str) -> Optional[Dict]:
        """
        Get a specific strategy template by ID.

        Args:
            template_id: The template ID (e.g., 'rsi_reversal')

        Returns:
            Template dictionary or None if not found
        """
        templates = self.load_templates()
        for template in templates:
            if template.get("id") == template_id:
                return template.copy()  # Return a copy to avoid mutations
        return None

    def create_strategy_from_template(
        self,
        template_id: str,
        portfolio_id: Optional[int] = None,
        watch_list_id: Optional[int] = None,
        custom_name: Optional[str] = None,
    ) -> Optional[int]:
        """
        Create a strategy from a template.

        Args:
            template_id: The template ID
            portfolio_id: Optional portfolio to assign to
            watch_list_id: Optional watchlist to assign to
            custom_name: Optional custom name (defaults to template name)

        Returns:
            int: Created strategy ID, or None on error
        """
        template = self.get_template(template_id)
        if not template:
            logger.error(f"Template not found: {template_id}")
            return None

        try:
            name = custom_name or template["name"]

            return self.create_strategy(
                name=name,
                description=template.get("description"),
                strategy_type=template["strategy_type"],
                anchor_indicator=template["anchor_indicator"],
                anchor_config=template["anchor_config"],
                buy_conditions=template["buy_conditions"],
                sell_conditions=template["sell_conditions"],
                confirmation_indicators=template.get("confirmation_indicators"),
                min_confidence_score=template.get("min_confidence_score", 50.0),
                portfolio_id=portfolio_id,
                watch_list_id=watch_list_id,
                active=True,
                created_by="TEMPLATE",
            )

        except KeyError as e:
            logger.error(f"Invalid template structure, missing field: {e}")
            return None

    def get_strategy_statistics(self, strategy_id: int) -> Dict:
        """
        Get statistics about a strategy's performance.

        Args:
            strategy_id: The strategy ID

        Returns:
            Dict containing signal counts and basic stats
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT
                        COUNT(*) as total_signals,
                        COUNT(CASE WHEN signal_type = 'BUY' THEN 1 END) as buy_signals,
                        COUNT(CASE WHEN signal_type = 'SELL' THEN 1 END) as sell_signals,
                        COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending_signals,
                        COUNT(CASE WHEN status = 'ACTED_ON' THEN 1 END) as acted_on_signals,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(CASE WHEN outcome = 'SUCCESS' THEN 1 END) as successful,
                        COUNT(CASE WHEN outcome = 'FAILURE' THEN 1 END) as failed,
                        SUM(profit_loss) as total_profit_loss
                    FROM trading_signals
                    WHERE strategy_id = %s
                """
                cursor.execute(query, (strategy_id,))
                result = cursor.fetchone()

                # Calculate win rate if applicable
                if result and result["acted_on_signals"] > 0:
                    result["win_rate"] = (
                        result["successful"] / result["acted_on_signals"]
                    ) * 100
                else:
                    result["win_rate"] = None

                return result if result else {}

        except mysql.connector.Error as e:
            logger.error(f"Error retrieving strategy statistics: {e}")
            return {}
