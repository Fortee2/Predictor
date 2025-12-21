import logging

import mysql.connector
import datetime
from data.base_dao import BaseDAO

logger = logging.getLogger(__name__)


class PortfolioTransactionsDAO(BaseDAO):

    def get_transaction_history(self, portfolio_id, security_id=None):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                if security_id:
                    query = """
                            SELECT t.*, s.ticker_id, tk.ticker as symbol
                            FROM portfolio_transactions t
                                     JOIN portfolio_securities s ON t.security_id = s.id
                                     JOIN tickers tk ON s.ticker_id = tk.id
                            WHERE t.portfolio_id = %s
                              AND t.security_id = %s
                            ORDER BY t.transaction_date ASC, t.id ASC \
                            """
                    cursor.execute(query, (portfolio_id, security_id))
                else:
                    query = """
                            SELECT t.*, s.ticker_id, tk.ticker as symbol
                            FROM portfolio_transactions t
                                     JOIN portfolio_securities s ON t.security_id = s.id
                                     JOIN tickers tk ON s.ticker_id = tk.id
                            WHERE t.portfolio_id = %s
                            ORDER BY t.transaction_date ASC, t.id ASC \
                            """
                    cursor.execute(query, (portfolio_id,))
                result = cursor.fetchall()
                cursor.close()
                return result
        except mysql.connector.Error as e:
            logger.error("Error retrieving transaction history: %s", e)
            return []

    """Get transaction history for a portfolio including buys, sells, and dividends
        for a date range.  If start and end date are not provided then default to the last 
        365 days."""
    def get_transaction_history_by_date(self, portfolio_id: int, start_date: datetime.date =None, end_date: datetime.date =None):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                if not start_date:
                    start_date = datetime.date.today()-datetime.timedelta(days=365)

                if not end_date:
                    end_date = datetime.date.today()

                query = """
                        SELECT t.*, s.ticker_id, tk.ticker as symbol
                        FROM portfolio_transactions t
                                 JOIN portfolio_securities s ON t.security_id = s.id
                                 JOIN tickers tk ON s.ticker_id = tk.id
                        WHERE t.portfolio_id = %s \
                          AND t.transaction_date BETWEEN %s AND %s \
                        ORDER BY t.transaction_date ASC, t.id ASC \
                        """
                cursor.execute(query, (portfolio_id, start_date, end_date))

                result = cursor.fetchall()
                cursor.close()
                return result

        except mysql.connector.Error as e:
            logger.error("Error retrieving transaction history: %s", e)
        return []

    def insert_transaction(
            self,
            portfolio_id,
            security_id,
            transaction_type,
            transaction_date,
            shares=None,
            price=None,
            amount=None,
            trade_rationale_type=None,
            ai_recommendation_id=None,
            user_notes=None,
            override_reason=None,
    ):
        """
        Insert a transaction into the database.

        Rounds price and amount to 2 decimal places to match database DECIMAL(10,2) precision.

        Args:
            portfolio_id: The portfolio ID
            security_id: The security ID
            transaction_type: Type of transaction (buy, sell, dividend)
            transaction_date: Date of transaction
            shares: Number of shares (for buy/sell)
            price: Price per share (for buy/sell)
            amount: Amount (for dividend)
            trade_rationale_type: Why the trade was made (AI_RECOMMENDATION, MANUAL_DECISION, STOP_LOSS, etc.)
            ai_recommendation_id: Link to AI recommendation if applicable
            user_notes: User's explanation for the trade
            override_reason: Explanation if ignoring AI recommendation

        Returns:
            int: The ID of the inserted transaction, or None on error
        """
        try:
            # Round price and amount to 2 decimal places to match database DECIMAL(10,2) precision
            rounded_price = round(price, 2) if price is not None else None
            rounded_amount = round(amount, 2) if amount is not None else None

            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = """
                    INSERT INTO portfolio_transactions
                    (portfolio_id, security_id, transaction_type, transaction_date, shares, price, amount,
                     trade_rationale_type, ai_recommendation_id, user_notes, override_reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    portfolio_id,
                    security_id,
                    transaction_type,
                    transaction_date,
                    shares,
                    rounded_price,
                    rounded_amount,
                    trade_rationale_type,
                    ai_recommendation_id,
                    user_notes,
                    override_reason,
                )
                cursor.execute(query, values)
                transaction_id = cursor.lastrowid
                cursor.close()
                return transaction_id
        except mysql.connector.Error as e:
            logger.error("Error inserting transaction: %s", e)
            return None

    def get_transaction_id(
            self,
            portfolio_id,
            security_id,
            transaction_type,
            transaction_date,
            shares=None,
            price=None,
            amount=None,
    ) -> int | None:
        """
        Get the ID of a transaction that matches the given parameters.
        
        Handles rounding issues by rounding price and amount to 2 decimal places
        to match the database DECIMAL(10,2) precision before comparison.
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = """
                        SELECT id
                        FROM portfolio_transactions
                        WHERE portfolio_id = %s
                          AND security_id = %s
                          AND transaction_type = %s
                          AND transaction_date = %s"""

                values = [portfolio_id, security_id, transaction_type, transaction_date]

                # Round price and amount to 2 decimal places to match database DECIMAL(10,2) precision
                # This prevents rounding issues when comparing float values with database values
                if transaction_type in ('buy', 'sell'):
                    query += " AND shares = %s AND price = %s AND amount IS NULL"

                    # Round price to 2 decimal places to match DECIMAL(10,2)
                    rounded_price = round(price, 2) if price is not None else None

                    values.extend([
                        shares,
                        rounded_price
                    ])

                elif transaction_type == 'dividend':
                    query += " AND shares IS NULL AND price IS NULL AND amount = %s"

                    # Round amount to 2 decimal places to match DECIMAL(10,2)
                    rounded_amount = round(amount, 2) if amount is not None else None

                    values.extend([
                        rounded_amount
                    ])

                cursor.execute(query, tuple(values))
                row = cursor.fetchone()
                cursor.close()
                return row[0] if row else None
        except mysql.connector.Error as e:
            logger.error("Error retrieving transaction: %s", e)
            return None

    def delete_transactions_for_security(self, portfolio_id, security_id):
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                query = "DELETE FROM portfolio_transactions WHERE portfolio_id = %s AND security_id = %s"
                values = (portfolio_id, security_id)
                cursor.execute(query, values)
                cursor.close()
        except mysql.connector.Error as e:
            logger.error("Error deleting transactions: %s", e)

    def get_current_positions(self, portfolio_id):
        """
        Calculate the current positions in a portfolio based on transaction history.
        Returns a dictionary mapping ticker_id to position details including shares held and average price.
        Implements FIFO (First-In-First-Out) method for cost basis calculation.
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                # Get all transactions for the portfolio in a single query to improve performance
                query = """
                        SELECT s.ticker_id,
                               s.id      as security_id,
                               tk.ticker as symbol,
                               t.transaction_type,
                               t.transaction_date,
                               t.shares,
                               t.price,
                               t.amount
                        FROM portfolio_transactions t
                                 JOIN portfolio_securities s ON t.security_id = s.id
                                 JOIN tickers tk ON s.ticker_id = tk.id
                        WHERE t.portfolio_id = %s
                        ORDER BY s.ticker_id, t.transaction_date ASC, t.id ASC \
                        """
                cursor.execute(query, (portfolio_id,))
                all_transactions = cursor.fetchall()
                cursor.close()

            # Process transactions by ticker_id
            positions = {}
            current_ticker = None
            buy_queue = []  # Store (shares, price) for each buy
            symbol = None

            for transaction in all_transactions:
                ticker_id = transaction["ticker_id"]
                trans_type = transaction["transaction_type"]

                # Only process buy/sell transactions for position calculation
                # Other transaction types (dividend, cash) don't affect share positions
                if trans_type not in ("buy", "sell"):
                    continue

                # If we're starting a new ticker, calculate results for the previous one
                if current_ticker is not None and current_ticker != ticker_id and buy_queue:
                    # Calculate and store position for the previous ticker
                    self._store_position_data(positions, current_ticker, buy_queue, symbol)

                # Set or update the current ticker and its symbol
                if current_ticker != ticker_id:
                    current_ticker = ticker_id
                    symbol = transaction["symbol"]
                    # Clear the buy queue for the new ticker
                    buy_queue = []

                # Convert decimal/numeric types to float to avoid type issues
                try:
                    shares = float(transaction["shares"] or 0)
                    price = float(transaction["price"] or 0)
                except (ValueError, TypeError) as e:
                    logger.error("Error converting transaction values for {ticker_id}: %s", e)
                    continue

                # Skip invalid transactions (missing essential data)
                if shares <= 0 or price <= 0:
                    continue

                # Process the transaction
                if trans_type == "buy":
                    buy_queue.append((shares, price))
                elif trans_type == "sell":
                    shares_to_sell = shares

                    # Process FIFO sell
                    while shares_to_sell > 0 and buy_queue:
                        buy_shares, buy_price = buy_queue[0]

                        if buy_shares <= shares_to_sell:
                            # Use all of this buy lot
                            buy_queue.pop(0)
                            shares_to_sell -= buy_shares
                        else:
                            # Use part of this buy lot
                            buy_queue[0] = (buy_shares - shares_to_sell, buy_price)
                            shares_to_sell = 0

            # Calculate position for the last ticker
            if current_ticker is not None and buy_queue:
                self._store_position_data(positions, current_ticker, buy_queue, symbol)

            return positions
        except mysql.connector.Error as e:
            logger.error("Error calculating current positions: %s", e)
            return {}

    def _store_position_data(self, positions_dict, ticker_id, buy_queue, symbol):
        """Helper method to calculate and store position data from a buy queue."""
        try:
            total_shares = 0
            total_cost = 0

            for shares, price in buy_queue:
                total_shares += shares
                total_cost += shares * price

            # Only include positions with positive shares and valid cost
            rounded_shares = round(total_shares, 4)
            if rounded_shares > 0:
                positions_dict[ticker_id] = {
                    "symbol": symbol,
                    "shares": rounded_shares,
                    "avg_price": (round(total_cost / total_shares, 2) if total_shares > 0 else 0),
                }
            return positions_dict
        except Exception as e:
            logger.error("Error storing position data for {ticker_id}: %s", e)
            return positions_dict

    def update_transaction_rationale(
            self,
            transaction_id,
            trade_rationale_type=None,
            ai_recommendation_id=None,
            user_notes=None,
            override_reason=None
    ):
        """
        Update the rationale information for an existing transaction.

        Args:
            transaction_id: The transaction ID to update
            trade_rationale_type: Type of rationale (AI_RECOMMENDATION, MANUAL_DECISION, etc.)
            ai_recommendation_id: Link to AI recommendation if applicable
            user_notes: User's explanation for the trade
            override_reason: Explanation if ignoring AI recommendation

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Build dynamic update query based on provided parameters
                updates = []
                values = []

                if trade_rationale_type is not None:
                    updates.append("trade_rationale_type = %s")
                    values.append(trade_rationale_type)

                if ai_recommendation_id is not None:
                    updates.append("ai_recommendation_id = %s")
                    values.append(ai_recommendation_id)

                if user_notes is not None:
                    updates.append("user_notes = %s")
                    values.append(user_notes)

                if override_reason is not None:
                    updates.append("override_reason = %s")
                    values.append(override_reason)

                if not updates:
                    logger.warning("No rationale fields provided for update")
                    return False

                values.append(transaction_id)
                query = f"UPDATE portfolio_transactions SET {', '.join(updates)} WHERE id = %s"

                cursor.execute(query, tuple(values))
                cursor.close()
                return True

        except mysql.connector.Error as e:
            logger.error("Error updating transaction rationale: %s", e)
            return False

    def get_transactions_with_rationale(self, portfolio_id, security_id=None):
        """
        Get transaction history including rationale information.

        Args:
            portfolio_id: The portfolio ID
            security_id: Optional security ID to filter by specific security

        Returns:
            List of transaction dictionaries including rationale fields
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)

                if security_id:
                    query = """
                        SELECT t.*, s.ticker_id, tk.ticker as symbol,
                               t.trade_rationale_type, t.ai_recommendation_id,
                               t.user_notes, t.override_reason
                        FROM portfolio_transactions t
                        JOIN portfolio_securities s ON t.security_id = s.id
                        JOIN tickers tk ON s.ticker_id = tk.id
                        WHERE t.portfolio_id = %s
                        AND t.security_id = %s
                        ORDER BY t.transaction_date DESC, t.id DESC
                    """
                    cursor.execute(query, (portfolio_id, security_id))
                else:
                    query = """
                        SELECT t.*, s.ticker_id, tk.ticker as symbol,
                               t.trade_rationale_type, t.ai_recommendation_id,
                               t.user_notes, t.override_reason
                        FROM portfolio_transactions t
                        JOIN portfolio_securities s ON t.security_id = s.id
                        JOIN tickers tk ON s.ticker_id = tk.id
                        WHERE t.portfolio_id = %s
                        ORDER BY t.transaction_date DESC, t.id DESC
                    """
                    cursor.execute(query, (portfolio_id,))

                result = cursor.fetchall()
                cursor.close()
                return result

        except mysql.connector.Error as e:
            logger.error("Error retrieving transactions with rationale: %s", e)
            return []

    def get_transactions_by_recommendation(self, ai_recommendation_id):
        """
        Get all transactions linked to a specific AI recommendation.

        Args:
            ai_recommendation_id: The AI recommendation ID

        Returns:
            List of transaction dictionaries
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT t.*, s.ticker_id, tk.ticker as symbol,
                           t.trade_rationale_type, t.user_notes, t.override_reason
                    FROM portfolio_transactions t
                    JOIN portfolio_securities s ON t.security_id = s.id
                    JOIN tickers tk ON s.ticker_id = tk.id
                    WHERE t.ai_recommendation_id = %s
                    ORDER BY t.transaction_date DESC
                """
                cursor.execute(query, (ai_recommendation_id,))
                result = cursor.fetchall()
                cursor.close()
                return result

        except mysql.connector.Error as e:
            logger.error("Error retrieving transactions by recommendation: %s", e)
            return []

    def get_rationale_statistics(self, portfolio_id):
        """
        Get statistics about trade rationales for a portfolio.

        Args:
            portfolio_id: The portfolio ID

        Returns:
            Dict containing rationale statistics
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT
                        trade_rationale_type,
                        COUNT(*) as count,
                        SUM(CASE WHEN transaction_type = 'buy' THEN shares ELSE 0 END) as total_buy_shares,
                        SUM(CASE WHEN transaction_type = 'sell' THEN shares ELSE 0 END) as total_sell_shares
                    FROM portfolio_transactions
                    WHERE portfolio_id = %s
                    AND trade_rationale_type IS NOT NULL
                    GROUP BY trade_rationale_type
                """
                cursor.execute(query, (portfolio_id,))
                results = cursor.fetchall()
                cursor.close()

                # Convert to more useful format
                stats = {'total': 0, 'by_type': {}}
                for row in results:
                    rationale_type = row['trade_rationale_type']
                    count = row['count']
                    stats['total'] += count
                    stats['by_type'][rationale_type] = {
                        'count': count,
                        'buy_shares': float(row['total_buy_shares'] or 0),
                        'sell_shares': float(row['total_sell_shares'] or 0)
                    }

                return stats

        except mysql.connector.Error as e:
            logger.error("Error retrieving rationale statistics: %s", e)
            return {'total': 0, 'by_type': {}}
