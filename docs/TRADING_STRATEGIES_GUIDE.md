# Trading Strategies Guide

## Table of Contents
1. [Overview](#overview)
2. [How Strategies Work](#how-strategies-work)
3. [Getting Started](#getting-started)
4. [Available Strategy Templates](#available-strategy-templates)
5. [Managing Strategies](#managing-strategies)
6. [Working with Signals](#working-with-signals)
7. [Performance Tracking](#performance-tracking)
8. [Backtesting](#backtesting)
9. [Advanced Topics](#advanced-topics)

---

## Overview

The Trading Strategies system in Predictor provides an automated, rule-based approach to generating buy and sell signals based on technical indicators. Instead of manually analyzing each stock, you can create strategies that continuously monitor your portfolios and watchlists, automatically generating signals when conditions are met.

### Key Features

- **Template-Based Creation**: Start with proven strategy patterns (RSI Reversal, MACD Momentum, etc.)
- **Multi-Indicator Confirmation**: Combine multiple technical indicators for higher confidence signals
- **Automated Signal Generation**: Strategies run automatically to detect trading opportunities
- **Performance Tracking**: Monitor win rates, profit/loss, and other metrics
- **Backtesting**: Test strategies against historical data before using them live
- **Portfolio/Watchlist Scoping**: Apply strategies globally or to specific portfolios/watchlists

---

## How Strategies Work

### Core Concepts

#### Anchor Indicator
The **anchor indicator** is the primary trigger for your strategy. When its conditions are met, a signal is generated. Available anchor indicators include:

- **RSI** (Relative Strength Index) - Momentum oscillator
- **MACD** (Moving Average Convergence Divergence) - Trend and momentum
- **Moving Average** - Trend direction
- **Bollinger Bands** - Volatility and price extremes
- **Stochastic** - Momentum oscillator
- **Trend** - Overall trend direction and strength
- **Volume** - Trading volume patterns

#### Confirmation Indicators
**Confirmation indicators** are optional validators that increase or decrease the confidence score of a signal. Each confirmation indicator has:

- **Weight**: How much it contributes to the confidence score (e.g., 10-25 points)
- **Required Flag**: If true, signal won't be generated unless conditions are met
- **Conditions**: Specific criteria that must be satisfied

#### Signal Generation Process

1. **Anchor Check**: System evaluates anchor indicator conditions
2. **Confirmation Check**: Evaluates each confirmation indicator
3. **Confidence Calculation**:
   - Start with base score (typically 50)
   - Add weight for each satisfied confirmation
   - Subtract weight for failed required confirmations
4. **Signal Creation**: If confidence ≥ minimum threshold, generate signal

#### Signal Attributes

Each generated signal includes:

- **Signal Type**: BUY, SELL, or HOLD
- **Signal Strength**: STRONG, MODERATE, or WEAK
- **Confidence Score**: 0-100 rating
- **Price at Signal**: Stock price when signal was generated
- **Indicator Snapshot**: All indicator values at signal time
- **Status**: PENDING, ACTED_ON, IGNORED, EXPIRED, or CANCELLED

---

## Getting Started

### Accessing the Strategies Menu

From the Enhanced CLI main menu:

```bash
python launch.py
# or
python enhanced_cli.py
```

Navigate to: **Trading Strategies** → Select from available options

### Creating Your First Strategy

1. **Select "Create New Strategy"** from the Strategies menu
2. **Choose a template** from the available options (see templates section below)
3. **Customize the name** (optional) - default uses template name
4. **Assign scope**:
   - **All portfolios (global)**: Strategy applies to all tickers in all portfolios
   - **Specific portfolio**: Strategy only monitors tickers in one portfolio
   - **Specific watchlist**: Strategy only monitors tickers in one watchlist

Example session:
```
Available Strategy Templates:

1. RSI Reversal
   Buy when RSI indicates oversold conditions (≤30), sell when overbought...
   Type: RSI_REVERSAL, Anchor: rsi

2. MACD Momentum
   Buy on bullish MACD crossover (MACD crosses above signal line), sell...
   Type: MACD_MOMENTUM, Anchor: macd

Select template number: 1
Strategy name [RSI Reversal]: My RSI Strategy
Assign strategy to:
  1. All portfolios (global)
  2. Specific portfolio
  3. Specific watchlist
Choose: 1

✓ Strategy created successfully with ID 1
```

---

## Available Strategy Templates

### 1. RSI Reversal

**Description**: Classic mean-reversion strategy that buys oversold stocks and sells overbought stocks.

**Strategy Type**: RSI_REVERSAL
**Anchor Indicator**: RSI (14-period)
**Minimum Confidence**: 65%

**Buy Conditions**:
- RSI ≤ 30 (oversold)

**Sell Conditions**:
- RSI ≥ 70 (overbought)

**Confirmations**:
- Trend direction not DOWN (optional, +10 points)
- Volume trending INCREASING (optional, +5 points)

**Best For**: Ranging markets with regular price oscillations

---

### 2. MACD Momentum

**Description**: Captures momentum shifts and trend changes using MACD crossovers.

**Strategy Type**: MACD_MOMENTUM
**Anchor Indicator**: MACD (12, 26, 9)
**Minimum Confidence**: 70%

**Buy Conditions**:
- Current signal = BUY (MACD crosses above signal line)
- Histogram > 0

**Sell Conditions**:
- Current signal = SELL (MACD crosses below signal line)
- Histogram < 0

**Confirmations**:
- RSI < 70 to avoid overbought (required, +15 points)
- Price above 50-day MA (optional, +10 points)

**Best For**: Trending markets and momentum trading

---

### 3. Golden Cross / Death Cross

**Description**: Long-term trend-following strategy using 50-day and 200-day moving average crossovers.

**Strategy Type**: MA_CROSSOVER
**Anchor Indicator**: Moving Average (50 & 200 periods)
**Minimum Confidence**: 75%

**Buy Conditions** (Golden Cross):
- 50-day MA > 200-day MA
- Price above MA
- Crossover occurred within last 5 days

**Sell Conditions** (Death Cross):
- 50-day MA < 200-day MA
- Crossover occurred within last 5 days

**Confirmations**:
- Trend direction UP with non-WEAK strength (required, +20 points)
- Volume trending INCREASING (optional, +10 points)

**Best For**: Long-term position trading and trend identification

---

### 4. Bollinger Band Bounce

**Description**: Mean-reversion strategy that trades bounces off Bollinger Band extremes.

**Strategy Type**: BOLLINGER_BOUNCE
**Anchor Indicator**: Bollinger Bands (20-period, 2 std dev)
**Minimum Confidence**: 65%

**Buy Conditions**:
- Price at or near lower band (within 2%)

**Sell Conditions**:
- Price at or near upper band (within 2%)

**Confirmations**:
- RSI ≤ 35 for buys, ≥ 65 for sells (optional, +15 points)
- Trend direction FLAT (optional, +10 points)

**Best For**: Range-bound markets with normal volatility

---

### 5. Multi-Indicator Consensus

**Description**: Conservative approach requiring alignment of multiple indicators for high-confidence signals.

**Strategy Type**: MULTI_INDICATOR
**Anchor Indicator**: RSI (14-period)
**Minimum Confidence**: 80%

**Buy Conditions**:
- RSI between 40 and 70

**Sell Conditions**:
- RSI between 30 and 60

**Confirmations**:
- MACD signal = BUY (required, +25 points)
- Stochastic not OVERBOUGHT and K > 20 (required, +25 points)
- Trend direction UP (required, +15 points)
- Price above 50-day MA (optional, +10 points)

**Best For**: Risk-averse traders seeking high-probability setups

---

## Managing Strategies

### List All Strategies

View all created strategies with their status and basic info:

```
Strategies Menu → List Strategies
```

Displays:
- Strategy ID
- Name
- Type
- Anchor Indicator
- Active status
- Assigned portfolio/watchlist

**Tip**: You can also see which strategies are assigned to a specific portfolio:

```
Portfolio Management → View/Manage Portfolio → Select a portfolio
  ↓
Portfolio view shows: "Active Strategies: X portfolio-specific + Y global"
  ↓
Select "View Assigned Strategies" from the Portfolio Actions menu
```

This helps you understand which signals to expect for each portfolio.

### View Strategy Details

See complete configuration and recent performance:

```
Strategies Menu → View Strategy Details → Enter strategy ID
```

Shows:
- Full strategy configuration
- Anchor and confirmation indicator settings
- Buy/sell conditions
- Recent signals generated
- Performance metrics

### Toggle Strategy On/Off

Enable or disable a strategy without deleting it:

```
Strategies Menu → Toggle Strategy On/Off → Enter strategy ID
```

Inactive strategies:
- Stop generating new signals
- Retain existing signals and performance history
- Can be re-enabled at any time

### Delete Strategy

Permanently remove a strategy:

```
Strategies Menu → Delete Strategy → Enter strategy ID
```

**Warning**: This action:
- Deletes the strategy permanently
- Removes all associated signals
- Deletes performance metrics
- Cannot be undone

---

## Working with Signals

### Generate Signals

There are two ways to generate signals:

#### Automatic Generation (Recommended)

When you update ticker data, the system can automatically generate signals with the fresh data:

```
Data Management → Update Data
  ↓
Do you want to generate trading signals after data update? [Y/n]
  ↓
System updates data, then automatically evaluates all active strategies
```

This is the recommended approach because:
- Signals are always based on the freshest data
- You don't have to remember two separate steps
- It's more efficient - evaluates strategies immediately after data is loaded
- Ensures signals stay current

#### Manual Generation

You can also manually trigger signal generation:

```
Strategies Menu → Generate Signals
```

Options:
- **Current Portfolio**: Generate signals for current portfolio only
- **Specific Watchlist**: Generate signals for watchlist tickers
- **Cancel**: Return to menu

The system will:
1. Retrieve latest market data for relevant tickers
2. Calculate all required technical indicators
3. Evaluate strategy conditions
4. Generate signals that meet confidence thresholds
5. Display results summary

Example output:
```
Generating signals for strategy: RSI Reversal

Analyzing 15 tickers...
Progress: ████████████████████ 100%

Results:
✓ 3 BUY signals generated
✓ 1 SELL signal generated
✓ 11 tickers evaluated (no signal threshold met)

View signals: Strategies Menu → View Active Signals
```

### View Active Signals

See all pending signals awaiting action:

```
Strategies Menu → View Active Signals
```

Displays table with:
- Signal ID
- Ticker Symbol
- Signal Type (BUY/SELL)
- Strength (STRONG/MODERATE/WEAK)
- Confidence Score
- Price at Signal
- Signal Date
- Strategy Name
- Status

Filters available:
- By portfolio
- By ticker
- By signal type
- By status

### Signal Lifecycle

**PENDING**: Signal just generated, awaiting action

**ACTED_ON**: You executed a trade based on this signal
- Link the signal to a transaction via transaction_id
- System tracks actual profit/loss vs prediction

**IGNORED**: You chose not to act on this signal
- Useful for performance analysis (what if you had acted?)

**EXPIRED**: Signal passed its expiration date
- Automatically set if expires_date is configured
- Can run expire_old_trading_signals() stored procedure

**CANCELLED**: Signal manually cancelled
- Use if market conditions changed significantly

### Acting on Signals

When you decide to trade based on a signal:

1. **Execute the trade** via your broker
2. **Log the transaction** in Predictor:
   ```
   Portfolio Management → Log Transaction
   ```
3. **Link signal to transaction**:
   ```
   Strategies Menu → Link Signal to Transaction
   Enter signal ID: 123
   Enter transaction ID: 456
   ```
4. **System tracks outcome**:
   - Monitors price movement
   - Calculates actual profit/loss
   - Updates signal status to ACTED_ON
   - Records outcome (SUCCESS/FAILURE/NEUTRAL)

---

## Performance Tracking

### Strategy Performance

View detailed performance metrics for a strategy:

```
Strategies Menu → Strategy Performance → Enter strategy ID
```

Displays:
- **Signal Metrics**:
  - Total signals generated
  - Buy vs sell signal breakdown
  - Average confidence score
  - Signals per day rate

- **Outcome Metrics**:
  - Signals acted upon
  - Successful vs failed signals
  - Win rate percentage
  - Average profit/loss per signal
  - Total profit/loss

- **Time Series Data**:
  - Performance over different time periods
  - Monthly/quarterly breakdown
  - Trend analysis

### Strategy Leaderboard

Compare all strategies by performance:

```
Strategies Menu → Strategy Leaderboard
```

Ranks strategies by:
1. Win rate (primary)
2. Total profit/loss (secondary)
3. Average confidence
4. Total signals generated

Useful for:
- Identifying your best-performing strategies
- Deciding which strategies to keep active
- Finding which strategy types work best for your portfolio

### Performance Calculation

Metrics are calculated by the `calculate_strategy_performance()` stored procedure:

```sql
CALL calculate_strategy_performance(
  strategy_id,      -- Which strategy to analyze
  portfolio_id,     -- NULL for all portfolios
  ticker_id,        -- NULL for all tickers
  period_start,     -- Start date
  period_end        -- End date
);
```

This can be run:
- Automatically (scheduled)
- Manually via CLI
- After significant trading activity

---

## Backtesting

Backtesting allows you to test a strategy against historical data to see how it would have performed.

### Run a Backtest

```
Strategies Menu → Backtest Strategy → Enter strategy ID
```

Configuration options:
- **Start Date**: Beginning of backtest period
- **End Date**: End of backtest period
- **Initial Capital**: Starting portfolio value (default: $10,000)
- **Position Size**: How much to invest per signal ($ amount or % of capital)
- **Commission**: Trading costs per transaction
- **Slippage**: Expected price difference between signal and execution

### Backtest Process

1. **Historical Data Load**: System retrieves price and indicator data for period
2. **Signal Generation**: Applies strategy rules to historical data
3. **Trade Simulation**:
   - Executes hypothetical trades at signal prices
   - Applies commission and slippage
   - Tracks portfolio value over time
4. **Performance Calculation**:
   - Total return
   - Annualized return
   - Maximum drawdown
   - Sharpe ratio
   - Win rate
   - Profit factor

### Backtest Results

Example output:
```
Backtest Results: RSI Reversal Strategy
Period: 2023-01-01 to 2024-12-31 (730 days)
═══════════════════════════════════════════════

Portfolio Performance:
Initial Capital:        $10,000.00
Final Value:           $12,450.00
Total Return:              24.50%
Annualized Return:         11.75%
Maximum Drawdown:         -15.30%

Trade Statistics:
Total Trades:                  45
Winning Trades:                28
Losing Trades:                 17
Win Rate:                   62.22%
Average Win:              $145.50
Average Loss:             -$78.25
Profit Factor:               2.15
Sharpe Ratio:                1.45

Signal Quality:
Signals Generated:             68
Signals Acted On:              45
Average Confidence:         72.5%
Avg Days Held:                12.3
```

### Interpreting Backtest Results

**Good indicators**:
- Win rate > 55%
- Profit factor > 1.5
- Sharpe ratio > 1.0
- Maximum drawdown < 20%
- Consistent returns over time

**Warning signs**:
- Win rate < 45%
- Profit factor < 1.0
- Large maximum drawdown
- Too few trades (< 20 for meaningful data)
- High sensitivity to parameter changes (overfitting)

### Backtest Limitations

Remember:
- Past performance doesn't guarantee future results
- Backtest uses perfect information (no real-world uncertainty)
- May not account for all market conditions
- Slippage and commission estimates may differ from reality
- Market dynamics change over time

---

## Advanced Topics

### Custom Strategy Configuration

While templates are pre-configured, you can modify strategy parameters in the database or through advanced CLI options (if implemented).

Key configurable parameters:
- Indicator periods (RSI: 14 days, MA: 20/50/200 days, etc.)
- Threshold values (RSI: 30/70, confidence: 50-100)
- Confirmation weights (5-25 points)
- Signal expiration (1-30 days)
- Max signals per day (1-50)

### Understanding Indicator Snapshots

Each signal stores a complete snapshot of all indicator values at the time of generation:

```json
{
  "rsi": {
    "value": 28.5,
    "period": 14,
    "status": "OVERSOLD"
  },
  "macd": {
    "macd_line": 0.45,
    "signal_line": 0.60,
    "histogram": -0.15,
    "signal": "BEARISH"
  },
  "moving_average": {
    "ma_20": 152.30,
    "current_price": 148.50,
    "position": "BELOW_MA",
    "distance_pct": -2.49
  },
  "trend": {
    "direction": "DOWN",
    "strength": "MODERATE",
    "rate_of_change": -1.25
  },
  "volume": {
    "current": 15500000,
    "average": 12000000,
    "trend": "INCREASING"
  }
}
```

This snapshot allows you to:
- Review exact conditions that triggered the signal
- Debug unexpected signals
- Analyze which indicators most influence outcomes
- Improve strategy configurations

### Signal Evaluation

After a signal is acted upon, the system can automatically evaluate its outcome:

**Success Criteria** (configurable):
- Profit target reached (e.g., +5% for buys)
- Within time window (e.g., 30 days)

**Failure Criteria**:
- Stop loss hit (e.g., -3% for buys)
- Time expired without reaching target

**Neutral**:
- Small gain/loss within threshold
- Position still open

Evaluation updates:
- Signal `outcome` field (SUCCESS/FAILURE/NEUTRAL)
- Actual `profit_loss` and `profit_loss_pct`
- Signal status to ACTED_ON
- Strategy performance metrics

### Multi-Portfolio Strategies

Strategies can operate at different scopes:

**Global Strategy** (portfolio_id = NULL, watch_list_id = NULL):
- Monitors all tickers in all portfolios
- Useful for broad market opportunities
- Generates more signals

**Portfolio-Specific** (portfolio_id set):
- Only monitors tickers in one portfolio
- Useful for different account types (retirement vs trading)
- Different strategies for different risk profiles

**Watchlist-Specific** (watch_list_id set):
- Monitors curated list of tickers
- Useful for sector-focused strategies
- Can scan opportunities without portfolio positions

### Signal Prioritization

When multiple signals are generated, prioritize by:

1. **Confidence Score**: Higher = more reliable
2. **Signal Strength**: STRONG > MODERATE > WEAK
3. **Multiple Strategy Confirmation**: If 2+ strategies signal same ticker
4. **Strategy Historical Win Rate**: Use leaderboard data
5. **Risk/Reward Ratio**: Compare potential upside vs downside

### Database Views

The system provides pre-built views for common queries:

**v_active_strategies**: All enabled strategies with signal counts
```sql
SELECT * FROM v_active_strategies;
```

**v_recent_signals**: Latest signals with full details
```sql
SELECT * FROM v_recent_signals WHERE signal_date >= DATE_SUB(NOW(), INTERVAL 7 DAY);
```

**v_strategy_leaderboard**: Strategy performance rankings
```sql
SELECT * FROM v_strategy_leaderboard ORDER BY win_rate DESC LIMIT 10;
```

### Maintenance Procedures

**Expire Old Signals**:
```sql
CALL expire_old_trading_signals();
```
Run daily to automatically expire outdated pending signals.

**Calculate Performance**:
```sql
CALL calculate_strategy_performance(1, NULL, NULL, '2024-01-01', '2024-12-31');
```
Run weekly/monthly to update performance metrics.

### Best Practices

1. **Start with Templates**: Use proven patterns before creating custom strategies
2. **Backtest First**: Always backtest before activating a strategy
3. **Enable Auto-Signal Generation**: When updating data, always choose "Yes" to automatically generate signals - this ensures you're working with the freshest opportunities
4. **Monitor Performance**: Review strategy performance monthly
5. **Adjust Parameters**: Fine-tune based on market conditions
6. **Diversify Strategies**: Use multiple strategy types to reduce correlation
7. **Set Realistic Thresholds**: Don't require 100% confidence; 70-80% is good
8. **Track Ignored Signals**: Learn from signals you didn't take
9. **Document Changes**: Note why you modified or disabled strategies
10. **Respect Win Rates**: Even 60% win rate is excellent if profit factor is good
11. **Use Stop Losses**: Protect capital on acted-upon signals
12. **Regular Data Updates**: Update data daily or at least before market open to catch fresh signals

### Troubleshooting

**No signals generated**:
- Check strategy is active
- Verify tickers have recent data
- Lower minimum confidence threshold
- Review anchor conditions (may be too strict)
- Run data updates

**Too many signals**:
- Increase minimum confidence threshold
- Add required confirmation indicators
- Reduce max_signals_per_day
- Tighten anchor conditions

**Poor backtest performance**:
- Strategy may be overfitted
- Market conditions may have changed
- Parameter values may need adjustment
- Try different indicator periods

**Signals don't match manual analysis**:
- Check indicator_snapshot for exact values
- Verify indicator calculation periods match
- Review confirmation indicator logic
- Check signal generation timestamp

---

## Conclusion

The Trading Strategies system provides a powerful framework for automating technical analysis and signal generation. By combining anchor indicators with confirmations, you can create robust trading strategies that continuously monitor your portfolios for opportunities.

Remember:
- Strategies are tools, not guarantees
- Always backtest before using live
- Monitor and adjust based on performance
- Combine with fundamental analysis and risk management
- No strategy works in all market conditions

Start with template strategies, learn how they perform with your portfolio, and gradually customize parameters to fit your trading style and risk tolerance.

For more information on technical indicators used in strategies, see:
- `swing_trading_guide.md` - Technical analysis fundamentals
- `README.md` - System overview and setup
- `CLAUDE.md` - Development and architecture details

Happy trading!