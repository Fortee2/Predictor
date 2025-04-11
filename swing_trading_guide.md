# Swing Trading with Predictor Portfolio Module

This guide outlines how to effectively use the Predictor portfolio module for swing trading on a timeframe of a few days to a few months.

## Portfolio Module Overview

The Predictor portfolio system provides several key components:

1. **Portfolio Management** - Create portfolios, add/remove tickers
2. **Transaction Tracking** - Log buy, sell, and dividend transactions
3. **Technical Analysis** - Multiple indicators for decision making:
   - RSI (Relative Strength Index)
   - Moving Averages
   - MACD (Moving Average Convergence Divergence)
   - Bollinger Bands
4. **Fundamental Data** - PE ratios, market cap, dividends
5. **News Sentiment Analysis** - Market perception of stocks
6. **Options Data** - Implied volatility, put/call ratios

## Swing Trading Strategy Framework

### 1. Portfolio Setup

Start by creating a dedicated portfolio for your swing trading:

```bash
python portfolio_cli.py create-portfolio "Swing Trading" "Portfolio for swing trades with 3-day to 3-month hold periods"
```

### 2. Add Potential Tickers

Add stocks you want to monitor and potentially trade:

```bash
python portfolio_cli.py add-tickers 1 AAPL MSFT AMD NVDA GOOGL
```

### 3. Technical Analysis Decision Framework

For swing trading on a timeframe of a few days to a few months, focus on these indicators:

#### Primary Indicators

| Indicator | Usage in Swing Trading |
|-----------|------------------------|
| **Moving Averages (20-day)** | Track trend direction; price above MA indicates bullish trend |
| **MACD** | Primary entry/exit signal generator; crossovers signal potential trades |
| **RSI** | Identify overbought (>70) or oversold (<30) conditions |
| **Bollinger Bands** | Gauge volatility and potential price targets |

#### Secondary Indicators

| Indicator | Usage in Swing Trading |
|-----------|------------------------|
| **News Sentiment** | Validate technical analysis with market sentiment |
| **Options Data** | Use implied volatility to gauge market expectations |
| **Fundamentals** | Basic check for longer-term holds (weeks to months) |

### 4. Analysis Workflow

1. **Run analysis on potential tickers:**

```bash
python portfolio_cli.py analyze-portfolio 1
```

2. **Look for these technical setups:**

#### BUY Signals
- **MACD**: Recent bullish crossover (MACD line crosses above signal line)
- **RSI**: Coming up from oversold (<30) or in mid-range (40-60)
- **Moving Average**: Price above 20-day MA showing uptrend momentum
- **Bollinger Bands**: Price approaching the lower band and starting to rise
- **News Sentiment**: Neutral to positive

#### SELL Signals
- **MACD**: Recent bearish crossover (MACD line crosses below signal line)
- **RSI**: In overbought territory (>70) or falling from it
- **Moving Average**: Price falls below 20-day MA showing lost momentum
- **Bollinger Bands**: Price approaching upper band or breaking down from it
- **News Sentiment**: Trending negative

### 5. Transaction Execution

When you identify a buy setup:

```bash
python portfolio_cli.py log-transaction 1 buy "2025-04-09" AAPL --shares 100 --price 184.50
```

When you identify a sell setup:

```bash
python portfolio_cli.py log-transaction 1 sell "2025-04-15" AAPL --shares 100 --price 192.75
```

### 6. Maintenance Cycle

1. **Daily/Weekly**: Update data for all securities in your portfolio:

```bash
python portfolio_cli.py update-data
```

2. **Daily/Weekly**: Analyze your portfolio for new signals:

```bash
python portfolio_cli.py analyze-portfolio 1
```

3. **After trades**: Review performance:

```bash
python portfolio_cli.py view-transactions 1
```

## Decision Making Examples

### Example 1: Identifying a Potential Buy

Let's say you're analyzing AAPL:

1. **MACD Analysis**: You notice a bullish MACD crossover today
   - MACD Line: -0.45
   - Signal Line: -0.60
   - Histogram: 0.15 (positive and growing)
   - Latest Signal: BUY

2. **RSI Analysis**: RSI is at 45
   - Not overbought
   - Showing strength from recent lows

3. **Moving Average Check**: Price is above the 20-day MA
   - Current Price: $184.50
   - 20-day MA: $182.25
   - Trend is upward

4. **Bollinger Bands Analysis**:
   - Price is in the middle of the bands
   - Moderate volatility indicates potential for movement

5. **News Sentiment**:
   - Positive (0.65 score)
   - Recent product announcements well received

This combination suggests a good entry point for a swing trade that might run for several days to weeks.

### Example 2: Identifying a Potential Sell

You've been holding NVDA for two weeks and observe:

1. **MACD Analysis**:
   - MACD Line: 2.15
   - Signal Line: 2.05
   - Histogram: 0.10 (positive but shrinking)
   - Pattern suggests potential bearish crossover soon

2. **RSI Analysis**: RSI is at 78
   - Overbought condition
   - Has been above 70 for several days

3. **Moving Average Check**:
   - Price still above 20-day MA but momentum slowing
   - Percentage above MA has decreased

4. **Bollinger Bands Analysis**:
   - Price approaching upper band
   - Higher than normal volatility

5. **Options Data**:
   - Put/Call ratio increasing
   - Implied volatility rising

This suggests the uptrend may be exhausting and it might be time to take profits.

## Advanced Strategy Refinements

### Trend Analysis Features

The Predictor system now includes built-in trend analysis capabilities to help with swing trading decisions. These features automatically determine moving average direction, strength, and price position relative to the moving average.

When you run the analyze-portfolio command, the system now displays:

```bash
python portfolio_cli.py analyze-portfolio 1 --ticker_symbol AAPL
```

#### Trend Direction and Strength

The system will output:
- **MA Trend**: Shows if the moving average is trending UP, DOWN, or FLAT, with an accompanying directional arrow (↗️, ↘️, or ➡️)
- **Trend Strength**: Classified as STRONG, MODERATE, or WEAK based on the rate of change 
- **Rate of Change**: The percentage change in the MA value (higher values indicate stronger trends)

For example:
```
║ 20-day MA (2025-04-10): 182.25                                     ║
║ MA Trend: ↗️ UP (MODERATE)                                      ║
║   Rate of Change: 0.75%                                           ║
```

#### Price vs. Moving Average Analysis

The system also shows the position of the current price relative to the moving average:
- **Price Position**: Shows if price is "Above MA", "Below MA", or "At MA"
- **Distance Percentage**: The percentage difference between the price and MA

For example:
```
║ Price Position: Above MA (1.23% from MA)                       ║
```

This helps you quickly determine if a stock is trading above or below its trend line and by how much.

#### Customizing Analysis Parameters

You can customize the analysis with additional parameters:

```bash
# Change the MA period (default is 20)
python portfolio_cli.py analyze-portfolio 1 --ticker_symbol AAPL --ma_period 50

# Change the lookback days for trend calculation (default is 5)
python portfolio_cli.py analyze-portfolio 1 --ticker_symbol AAPL --lookback_days 10
```
   
### Combining Multiple Timeframes

For more reliable signals, confirm your primary timeframe analysis with a longer timeframe:

1. Use your main indicators on a daily chart for primary signals
2. Confirm the trend on a weekly chart
3. Use shorter timeframes (hourly) for fine-tuning entries and exits

### Risk Management Guidelines

1. **Position Sizing**: Limit each position to 5-10% of portfolio
2. **Stop Loss**: Set stops based on technical levels (e.g., below recent support)
3. **Take Profit**: Define exit targets using Bollinger Bands or historic resistance
4. **Risk-Reward**: Aim for minimum 1:2 risk-reward ratio on each trade

---

*This guide provides a framework for swing trading with the Predictor portfolio module. Always adjust parameters based on your risk tolerance and market conditions.*
