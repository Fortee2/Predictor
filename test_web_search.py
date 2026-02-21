"""
Test script for DuckDuckGo web search integration with LLM.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.utility import DatabaseConnectionPool
from data.llm_portfolio_analyzer import LLMPortfolioAnalyzer

# Load environment variables
load_dotenv()


def test_web_search_tool():
    """Test the web search tool directly."""
    print("Testing DuckDuckGo Web Search Integration")
    print("=" * 60)

    # Initialize database connection pool
    pool = DatabaseConnectionPool(
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        db_host=os.getenv("DB_HOST"),
        db_name=os.getenv("DB_NAME"),
        pool_size=5
    )

    # Initialize LLM analyzer
    analyzer = LLMPortfolioAnalyzer(pool=pool)

    # Test 1: Direct tool execution
    print("\n1. Testing direct tool execution...")
    test_query = "Tesla stock news 2024"
    result = analyzer._execute_tool("web_search", {
        "query": test_query,
        "max_results": 3
    })

    print(f"Query: {test_query}")
    print(f"Results count: {result.get('results_count', 0)}")

    if result.get("results"):
        for res in result["results"]:
            print(f"\n  {res['position']}. {res['title']}")
            print(f"     {res['snippet'][:100]}...")
            print(f"     URL: {res['url']}")
    else:
        print(f"Error or no results: {result}")

    # Test 2: Chat interface with web search
    print("\n\n2. Testing chat interface with web search...")
    print("-" * 60)

    response = analyzer.chat(
        user_message="Search the web for recent Apple earnings news and summarize what you find.",
        reset_context=True
    )

    print("\nLLM Response:")
    print(response)

    print("\n" + "=" * 60)
    print("Test completed successfully!")


if __name__ == "__main__":
    test_web_search_tool()
