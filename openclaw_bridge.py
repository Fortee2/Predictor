"""
OpenClaw Bridge for Predictor
This script gathers all relevant portfolio data and outputs it as a structured Markdown context file.
OpenClaw can then read this file to perform analysis without needing AWS Bedrock.
"""

import sys
import os
import json
from datetime import datetime
# from rich.console import Console  <-- Removed dependency

# Add parent directory to path to import data modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.config import Config
from data.utility import DatabaseConnectionPool
from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.ticker_dao import TickerDao
from data.rsi_calculations import rsi_calculations
from data.macd import MACD
from data.news_sentiment_analyzer import NewsSentimentAnalyzer
from data.fundamental_data_dao import FundamentalDataDAO

def serialize_date(obj):
    if isinstance(obj, (datetime, float, int)):
        return str(obj)
    return obj

def generate_portfolio_context(portfolio_id):
    try:
        config = Config()
        db_config = config.get_database_config()
        
        # Connect to DB
        pool = DatabaseConnectionPool(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            database=db_config["database"]
        )
        
        # Initialize DAOs
        portfolio_dao = PortfolioDAO(pool)
        transactions_dao = PortfolioTransactionsDAO(pool)
        ticker_dao = TickerDao(pool)
        rsi_calc = rsi_calculations(pool)
        macd_calc = MACD(pool)
        news_analyzer = NewsSentimentAnalyzer(pool)
        fund_dao = FundamentalDataDAO(pool)
        
        # 1. Portfolio Basic Info
        portfolio = portfolio_dao.read_portfolio(portfolio_id)
        if not portfolio:
            return f"Error: Portfolio {portfolio_id} not found."
            
        cash = portfolio_dao.get_cash_balance(portfolio_id)
        
        # 2. Positions
        positions = transactions_dao.get_current_positions(portfolio_id)
        
        output = []
        output.append(f"# Portfolio Context: {portfolio['name']}")
        output.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        output.append(f"**Cash Balance:** ${cash:,.2f}")
        output.append("\n## Current Positions")
        
        for ticker_id, pos in positions.items():
            ticker = ticker_dao.get_ticker_data(ticker_id)
            if not ticker:
                continue
                
            symbol = ticker['ticker'] # Fixed key name from 'symbol' to 'ticker'
            name = ticker.get('ticker_name', 'Unknown') # Fixed key name from 'name' to 'ticker_name'
            shares = pos['shares']
            
            # Technicals
            rsi_data = rsi_calc.retrievePrices(1, ticker_id)
            rsi = rsi_data.iloc[-1]['rsi'] if not rsi_data.empty else "N/A"
            
            # Fundamentals
            fund = fund_dao.get_latest_fundamental_data(ticker_id)
            pe = fund.get('pe_ratio', 'N/A') if fund else 'N/A'
            
            output.append(f"\n### {symbol} ({name})")
            output.append(f"- **Shares:** {shares}")
            output.append(f"- **Price:** ${ticker.get('last_price', 0)}")
            output.append(f"- **Value:** ${shares * ticker.get('last_price', 0):,.2f}")
            output.append(f"- **RSI:** {rsi}")
            output.append(f"- **P/E:** {pe}")
            
            # Recent News
            news = news_analyzer.fetch_and_analyze_news(ticker_id, symbol)
            if news and 'articles' in news:
                output.append("- **Recent News:**")
                for article in news['articles'][:2]:  # Top 2 articles
                    output.append(f"  - [{article.get('sentiment', 'N/A')}] {article.get('title')}")

        return "\n".join(output)

    except Exception as e:
        return f"Error generating context: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python openclaw_bridge.py <portfolio_id>")
        sys.exit(1)
        
    portfolio_id = int(sys.argv[1])
    content = generate_portfolio_context(portfolio_id)
    
    with open("portfolio_context.md", "w") as f:
        f.write(content)
    print("Context written to portfolio_context.md")
