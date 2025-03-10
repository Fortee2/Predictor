# Predictor: Stock Portfolio Management System

This project is a comprehensive stock portfolio management and analysis system that allows users to track, manage, and analyze stock portfolios.

## Features

### Portfolio Management
- Create and manage investment portfolios
- Add/remove tickers (stock symbols) to portfolios
- Record stock transactions (buys, sells, dividends)
- View portfolio details and transaction history

### Financial Data Management
- Store and retrieve stock prices and activity
- Track transaction history
- Calculate portfolio values based on current market prices (using Yahoo Finance)

### Technical Analysis
- Calculate and store Relative Strength Index (RSI) indicators
- Implement Moving Averages for trend analysis
- Generate Bollinger Bands for volatility analysis
- Store historical price data for analysis
- Analyze news sentiment using FinBERT model
- Track and store news article sentiment scores

## System Architecture

### Command-line Interface
- `portfolio_cli.py`: Main CLI tool for portfolio management operations

### Data Access Layer
- `portfolio_dao.py`: Portfolio creation and management
- `portfolio_transactions_dao.py`: Transaction recording and retrieval
- `ticker_dao.py`: Stock symbol management and data retrieval
- `portfolio_value_calculator.py`: Calculates portfolio values using current prices

### Technical Analysis Tools
- `rsi_calculations.py`: Calculates Relative Strength Index (momentum indicator)
- `moving_averages.py`: Implements different moving average calculations
- `bollinger_bands.py`: Calculates volatility bands around moving averages
- `news_sentiment_analyzer.py`: Analyzes news sentiment using FinBERT

### Utilities
- `utility.py`: Helper functions for API calls

### Database
- MySQL database (schema in `database_script` directory)
- Includes tables for portfolios, transactions, and technical indicators

## Workflow

1. Create portfolios and add stocks
2. Record transactions (buy/sell/dividend)
3. Retrieve current market data
4. Calculate portfolio values
5. Generate technical indicators for analysis

## Requirements

- Python 3.x
- MySQL database
- Required Python packages:
  - mysql-connector-python
  - pandas
  - numpy
  - yfinance
  - python-dotenv
  - requests
  - transformers
  - torch

## Environment Setup

The application requires the following environment variables:
- DB_USER: Database username
- DB_PASSWORD: Database password
- DB_HOST: Database host
- DB_NAME: Database name

These can be set in a `.env` file in the project root.

## Portfolio Management Guide

### Creating and Managing Portfolios

1. **Create a Portfolio**
```bash
python portfolio_cli.py create-portfolio "My Tech Portfolio" "Long-term technology investments"
```
- Creates a new portfolio with a name and description
- Returns a unique portfolio ID for future operations
- Example output:
```
Successfully created new portfolio:
Portfolio ID: 1
Name: My Tech Portfolio
Description: Long-term technology investments
```

2. **View Portfolio Details**
```bash
python portfolio_cli.py view-portfolio 1
```
- Shows portfolio information and all associated tickers
- Example output:
```
Portfolio Details:
--------------------------------------------------
Portfolio ID:  1
Name:         My Tech Portfolio
Description:  Long-term technology investments
Status:       Active
Date Added:   2025-03-10

Tickers in Portfolio:
--------------------------------------------------
Symbol: AAPL   (ID: 1)
Symbol: MSFT   (ID: 2)
Symbol: GOOGL  (ID: 3)
```

### Managing Tickers

1. **Add Tickers to Portfolio**
```bash
python portfolio_cli.py add-tickers 1 1 2 3
```
- Adds one or more tickers to a portfolio using ticker IDs
- Validates ticker existence before adding
- Shows success/failure for each ticker
- Example output:
```
Successfully added 3 ticker(s) to portfolio 1

Added tickers:
- AAPL (ID: 1)
- MSFT (ID: 2)
- GOOGL (ID: 3)
```

2. **Remove Tickers from Portfolio**
```bash
python portfolio_cli.py remove-tickers 1 2
```
- Removes one or more tickers from a portfolio
- Validates ticker presence in portfolio
- Example output:
```
Successfully removed 1 ticker(s) from portfolio 1

Removed tickers:
- MSFT (ID: 2)
```

### Managing Transactions

1. **Log Buy/Sell Transactions**
```bash
# Buy transaction
python portfolio_cli.py log-transaction 1 buy 2025-03-10 1 --shares 100 --price 150.50

# Sell transaction
python portfolio_cli.py log-transaction 1 sell 2025-03-10 1 --shares 50 --price 175.25
```
- Records buy/sell transactions for tickers in a portfolio
- Requires shares and price parameters
- Example output:
```
Successfully logged buy transactions:
- AAPL: 100 shares at $150.50 each
```

2. **Log Dividend Transactions**
```bash
python portfolio_cli.py log-transaction 1 dividend 2025-03-10 1 --amount 125.50
```
- Records dividend payments for tickers
- Requires amount parameter
- Example output:
```
Successfully logged dividend transactions:
- AAPL: $125.50 dividend
```

3. **View Transaction History**
```bash
# View all transactions
python portfolio_cli.py view-transactions 1

# View transactions for specific security
python portfolio_cli.py view-transactions 1 --security_id 1
```
- Displays formatted transaction history
- Can filter by specific security
- Example output:
```
Transaction History:
--------------------------------------------------------------------------------
Date         Type       Symbol   Shares    Price      Amount    
--------------------------------------------------------------------------------
2025-03-10   buy        AAPL     100      $150.50    N/A       
2025-03-10   sell       AAPL     50       $175.25    N/A       
2025-03-10   dividend   AAPL     N/A      N/A        $125.50   
```

### Error Handling

The system provides clear error messages for common scenarios:

1. **Invalid Portfolio**
```
Error: Portfolio 999 does not exist.
```

2. **Missing Transaction Parameters**
```
Error: buy transactions require both shares and price parameters.
```

3. **Invalid Date Format**
```
Error: Invalid date format. Please use YYYY-MM-DD format.
```

4. **Invalid Tickers**
```
Warning: The following ticker IDs were not found and were skipped:
- Ticker ID 999
```

5. **Tickers Not in Portfolio**
```
Warning: The following tickers were not found in the portfolio:
- Ticker ID 888
```

### Technical Analysis Commands

The system provides powerful technical analysis capabilities through three main indicators, fundamental data analysis, and news sentiment analysis:

1. **Analyze RSI (Relative Strength Index)**
```bash
python portfolio_cli.py analyze-rsi [portfolio_id] [--ticker_id TICKER_ID]
```
- Calculates and interprets the RSI indicator
- Provides overbought/oversold signals
- Example output:
```
RSI Analysis for AAPL (ID: 1):
--------------------------------------------------
Latest RSI (2025-03-10): 65.5
Status: Neutral
```

2. **Analyze Moving Averages**
```bash
python portfolio_cli.py analyze-ma [portfolio_id] [--ticker_id TICKER_ID] [--period PERIOD]
```
- Calculates moving averages for specified period (default: 20 days)
- Shows trend direction and strength
- Example output:
```
Moving Average Analysis for AAPL (ID: 1):
--------------------------------------------------
20-day Moving Average (2025-03-10): 175.50
```

3. **Analyze Bollinger Bands**
```bash
python portfolio_cli.py analyze-bb [portfolio_id] [--ticker_id TICKER_ID]
```
- Generates Bollinger Bands analysis
- Provides volatility insights and potential price reversals
- Example output:
```
Bollinger Bands Analysis for AAPL (ID: 1):
--------------------------------------------------
AAPL is above its 20-day moving average, indicating a strong uptrend.
The Bollinger Band is relatively narrow, indicating high volatility.
```

4. **View Fundamental Data**
```bash
python portfolio_cli.py view-fundamentals [portfolio_id] [--ticker_id TICKER_ID]
```
- Displays comprehensive fundamental data for stocks
- Includes valuation metrics, dividend info, growth rates, and financial health
- Example output:
```
Fundamental Analysis for AAPL (ID: 1):
--------------------------------------------------
Data as of: 2025-03-10

Valuation Metrics:
P/E Ratio:      25.50
Forward P/E:     22.30
PEG Ratio:       1.85
Price/Book:      35.20

Dividend Information:
Dividend Yield:  0.65%
Dividend Rate:   $0.92

Growth & Profitability:
EPS (TTM):       $6.15
EPS Growth:      15.20%
Revenue Growth:  8.50%
Profit Margin:   25.30%

Financial Health:
Debt/Equity:     1.50
Market Cap:      $2,750,000,000,000.00
```

5. **Analyze News Sentiment**
```bash
python portfolio_cli.py analyze-news [portfolio_id] [--ticker_id TICKER_ID] [--update]
```
- Analyzes sentiment of recent news articles using FinBERT model
- Provides sentiment scores and confidence levels for each article
- Optional --update flag to fetch and analyze latest news
- Example output:
```
News Sentiment Analysis for AAPL:
--------------------------------------------------
Overall Sentiment: Positive
Average Score: 0.3245
Articles Analyzed: 5

Recent Headlines:
Apple Reports Record Quarter, Exceeds Expectations
Publisher: Reuters
Date: 2025-03-10 14:30:00
Sentiment: 0.8750 (Confidence: 0.9120)
Link: https://reuters.com/article/...

Apple Announces New Product Line
Publisher: Bloomberg
Date: 2025-03-10 10:15:00
Sentiment: 0.6540 (Confidence: 0.8830)
Link: https://bloomberg.com/news/...
```

### Usage Options

For all technical analysis and fundamental data commands:
- Analyze a specific ticker by providing the `--ticker_id` parameter
- Analyze all tickers in a portfolio by omitting the `--ticker_id` parameter
- View historical data, current signals, and fundamental metrics for informed decision-making

### Best Practices

1. **Portfolio Creation**
   - Use descriptive names and descriptions
   - Keep track of portfolio IDs for future operations

2. **Transaction Management**
   - Log transactions on the actual transaction date
   - Double-check share counts and prices
   - Keep dividend records up to date

3. **Portfolio Maintenance**
   - Regularly review portfolio contents
   - Verify transaction history for accuracy
   - Remove inactive tickers when necessary

4. **Technical Analysis**
   - Use multiple indicators for confirmation
   - Monitor RSI for overbought/oversold conditions
   - Compare different moving average periods
   - Use Bollinger Bands to gauge volatility
   - Consider market context when interpreting signals
   - Combine technical signals with fundamental data for comprehensive analysis

5. **Fundamental Analysis**
   - Review valuation metrics relative to industry averages
   - Monitor dividend metrics for income potential
   - Track growth rates and profitability trends
   - Assess financial health through leverage ratios
   - Consider market cap for size and liquidity context

6. **News Sentiment Analysis**
   - Use --update flag to ensure latest news is analyzed
   - Consider sentiment trends over time
   - Look for correlation between sentiment and price movements
   - Pay attention to confidence scores for reliability
   - Cross-reference news sentiment with technical indicators

This tool is designed for investors who want to track their investments, analyze performance, and make data-driven decisions based on technical indicators. The addition of technical analysis capabilities provides deeper insights into market trends and potential trading opportunities.
