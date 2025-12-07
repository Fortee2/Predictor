# Predictor MCP Server

This MCP (Model Context Protocol) server provides LLM access to the Predictor stock portfolio management system. It exposes comprehensive portfolio management, transaction tracking, technical analysis, and market data functionality through standardized MCP tools and resources.

## Features

### Portfolio Management Tools
- **create_portfolio** - Create new investment portfolios
- **list_portfolios** - List all portfolios
- **view_portfolio** - View detailed portfolio information
- **add_tickers_to_portfolio** - Add stock tickers to portfolios
- **remove_tickers_from_portfolio** - Remove stock tickers from portfolios

### Transaction Management Tools
- **log_transaction** - Record buy, sell, or dividend transactions
- **view_transactions** - View transaction history with optional filtering

### Cash Management Tools
- **manage_cash** - Deposit, withdraw, or view cash balances

### Technical Analysis Tools
- **analyze_rsi** - RSI (Relative Strength Index) analysis
- **analyze_moving_averages** - Moving average analysis with configurable periods
- **analyze_bollinger_bands** - Bollinger Bands volatility analysis
- **analyze_news_sentiment** - News sentiment analysis using FinBERT
- **view_fundamentals** - Fundamental analysis data (P/E ratios, market cap, etc.)
- **view_performance** - Portfolio performance metrics and charts

### Market Data Tools
- **add_ticker** - Add new stock tickers to the system
- **update_ticker_data** - Update market data for specific tickers
- **list_tickers** - List all available tickers
- **calculate_portfolio_value** - Calculate current portfolio values

### Resources
The server exposes portfolio data, transaction histories, performance metrics, and market data as queryable resources:
- `predictor://portfolio/{id}` - Portfolio details and holdings
- `predictor://portfolio/{id}/transactions` - Transaction history
- `predictor://portfolio/{id}/performance` - Performance metrics
- `predictor://market/tickers` - Available tickers list

## Configuration

The server requires the following environment variables:
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password  
- `DB_HOST` - Database host (defaults to localhost)
- `DB_NAME` - Database name
- `PREDICTOR_PATH` - Path to the Predictor project directory

## Installation

1. The server is automatically configured in your MCP settings
2. Environment variables are set from your Predictor project's .env file
3. The server connects to your existing MySQL database

## Usage Examples

Once connected, you can use natural language to interact with your portfolio data:

- "Show me all my portfolios"
- "Create a new tech portfolio with $10,000 initial cash"
- "Add AAPL, MSFT, and GOOGL to portfolio 1"
- "Log a buy transaction: 100 shares of AAPL at $150 on 2025-01-15"
- "Analyze the RSI for all stocks in my portfolio"
- "Show me the performance of portfolio 1 over the last 6 months"
- "What's the news sentiment for AAPL?"
- "Calculate the current value of portfolio 2"

## Architecture

The MCP server acts as a bridge between LLMs and your Predictor system:
- Executes Python CLI commands in your Predictor directory
- Handles database connections securely through environment variables
- Provides structured JSON responses for easy LLM consumption
- Supports both real-time operations and historical data analysis

## Security

- Database credentials are stored securely in MCP configuration
- All operations are executed within your local environment
- No external API calls for sensitive portfolio data
- Full control over which tools are auto-approved

## Error Handling

The server includes comprehensive error handling:
- Database connection validation
- Command execution error reporting
- Type safety for all tool parameters
- Graceful fallbacks for missing data

This MCP server transforms your Predictor portfolio management system into a powerful, LLM-accessible financial analysis platform while maintaining security and data privacy.
