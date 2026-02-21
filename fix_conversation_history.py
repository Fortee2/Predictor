#!/usr/bin/env python3
"""
Utility script to validate and fix corrupted conversation histories in the database.

This script:
1. Loads all active conversation sessions
2. Validates each for incomplete tool exchanges
3. Fixes corrupted conversations by removing incomplete exchanges
4. Updates the database with cleaned conversations

Run this after upgrading to the new validation logic to clean up any existing corrupted data.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from data.utility import DatabaseConnectionPool
from data.llm_portfolio_analyzer import LLMPortfolioAnalyzer
from data.conversation_history_dao import ConversationHistoryDAO

def fix_all_conversations():
    """Validate and fix all conversation histories in the database."""

    print("=" * 80)
    print("Conversation History Validation and Repair Tool")
    print("=" * 80)
    print()

    try:
        # Initialize database connection
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "localhost")
        db_name = os.getenv("DB_NAME")

        if not all([db_user, db_password, db_name]):
            print("❌ Error: Missing database credentials in .env file")
            print("   Required: DB_USER, DB_PASSWORD, DB_NAME")
            return False

        print("Connecting to database...")
        pool = DatabaseConnectionPool(db_user, db_password, db_host, db_name)
        conversation_dao = ConversationHistoryDAO(pool)

        # Create analyzer instance (just to use its validation method)
        analyzer = LLMPortfolioAnalyzer(pool)

        # Get all conversation sessions
        print("Loading all conversation sessions...")

        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT portfolio_id
            FROM ai_conversation_history
            WHERE is_active = TRUE
        """)
        portfolios = cursor.fetchall()
        cursor.close()
        connection.close()

        if not portfolios:
            print("✅ No active conversations found in database")
            return True

        print(f"Found {len(portfolios)} portfolio(s) with active conversations")
        print()

        fixed_count = 0
        ok_count = 0

        for portfolio_row in portfolios:
            portfolio_id = portfolio_row['portfolio_id']
            print(f"Checking portfolio {portfolio_id}...")

            # Load conversation
            session_data = conversation_dao.load_active_conversation(portfolio_id)
            if not session_data:
                continue

            raw_history = session_data['conversation_data']
            original_count = len(raw_history)

            # Validate
            validated_history = analyzer._validate_conversation_history(raw_history)
            validated_count = len(validated_history)

            if validated_count < original_count:
                print(f"  ⚠️  Found corrupted conversation: {original_count} messages → {validated_count} valid")
                print(f"      Removed {original_count - validated_count} incomplete messages")

                # Update database
                conversation_dao.save_conversation(
                    portfolio_id=portfolio_id,
                    conversation_data=validated_history,
                    session_name=session_data.get('session_name'),
                    set_as_active=True
                )
                print(f"  ✅ Fixed and saved to database")
                fixed_count += 1
            else:
                print(f"  ✅ OK ({validated_count} messages)")
                ok_count += 1

            print()

        print("=" * 80)
        print("Summary:")
        print(f"  Total portfolios checked: {len(portfolios)}")
        print(f"  Valid conversations: {ok_count}")
        print(f"  Fixed conversations: {fixed_count}")
        print("=" * 80)
        print()

        if fixed_count > 0:
            print("✅ All corrupted conversations have been repaired!")
        else:
            print("✅ All conversations were already valid!")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_all_conversations()
    sys.exit(0 if success else 1)
