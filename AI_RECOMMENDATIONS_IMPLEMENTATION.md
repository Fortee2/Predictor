# AI Recommendations & Trade Rationale Implementation

## Overview

This implementation adds comprehensive tracking of AI recommendations and trade rationales to your portfolio management system. It addresses two critical gaps:

1. **AI recommendations are not stored** - Now all AI trading recommendations are saved with full context
2. **No way to log why trades occurred** - Transactions now include rationale fields to track decision-making

This creates a feedback loop where the AI can learn from past recommendations and understand whether users are following its guidance.

## Database Changes

### 1. New Table: `ai_recommendations`

Stores all AI trading recommendations with full context:

```sql
CREATE TABLE IF NOT EXISTS ai_recommendations (
  id INT NOT NULL AUTO_INCREMENT,
  portfolio_id INT NOT NULL,
  ticker_id INT NOT NULL,
  recommendation_type ENUM('BUY', 'SELL', 'HOLD', 'REDUCE', 'INCREASE'),
  recommended_quantity DECIMAL(10,2),
  recommended_price DECIMAL(10,2),
  confidence_score DECIMAL(5,2),          -- AI confidence 0-100
  reasoning TEXT,                          -- AI's explanation
  technical_indicators JSON,               -- RSI, MACD, MA values
  sentiment_score DECIMAL(5,2),           -- News sentiment
  recommendation_date DATETIME,
  expires_date DATETIME,
  status ENUM('PENDING', 'FOLLOWED', 'PARTIALLY_FOLLOWED', 'IGNORED', 'EXPIRED'),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (portfolio_id) REFERENCES portfolio (id),
  FOREIGN KEY (ticker_id) REFERENCES tickers (id)
);
```

### 2. Enhanced Table: `portfolio_transactions`

New columns added to track trade rationale:

```sql
ALTER TABLE portfolio_transactions
ADD COLUMN trade_rationale_type ENUM('AI_RECOMMENDATION', 'MANUAL_DECISION', 'STOP_LOSS', 'PROFIT_TARGET', 'REBALANCE', 'OTHER'),
ADD COLUMN ai_recommendation_id INT,     -- Links to ai_recommendations
ADD COLUMN user_notes TEXT,              -- User explanation
ADD COLUMN override_reason TEXT,         -- Why AI was ignored
ADD CONSTRAINT portfolio_transactions_ai_rec_fk FOREIGN KEY (ai_recommendation_id) REFERENCES ai_recommendations (id);
```

## Application Files Created/Modified

### New Files

1. **`database_script/create_ai_recommendations_table.sql`**
   - Database schema for AI recommendations table

2. **`database_script/alter_portfolio_transactions_add_rationale.sql`**
   - Adds rationale tracking columns to transactions

3. **`data/ai_recommendations_dao.py`**
   - Complete DAO for managing AI recommendations
   - Methods for saving, retrieving, updating, and analyzing recommendations

4. **`enhanced_cli/ai_recommendations_views.py`**
   - CLI interface for viewing and managing recommendations
   - Interactive commands for users

### Modified Files

1. **`data/portfolio_transactions_dao.py`**
   - Enhanced `insert_transaction()` to accept rationale parameters
   - New methods:
     - `update_transaction_rationale()` - Update rationale for existing transaction
     - `get_transactions_with_rationale()` - Retrieve transactions with rationale info
     - `get_transactions_by_recommendation()` - Find transactions linked to a recommendation
     - `get_rationale_statistics()` - Statistics on trade rationales

2. **`portfolio_cli.py`**
   - Updated `log_transaction()` to accept and pass through rationale parameters

3. **`enhanced_cli/transaction/log_transaction_command.py`**
   - Enhanced transaction logging with interactive rationale prompts
   - Automatically links transactions to AI recommendations
   - Prompts for override reasons when ignoring AI advice

4. **`enhanced_cli/main.py`**
   - Registered AI recommendations commands in the main CLI

## Setup Instructions

### 1. Run Database Migrations

Execute the SQL scripts in order:

```bash
mysql -u your_user -p your_database < database_script/create_ai_recommendations_table.sql
mysql -u your_user -p your_database < database_script/alter_portfolio_transactions_add_rationale.sql
```

### 2. No Code Changes Required

All Python code is ready to use. The system is backward compatible - existing transactions without rationale information will continue to work.

## Usage Guide

### For AI Integration

When your AI generates trading recommendations, save them using the DAO:

```python
from data.ai_recommendations_dao import AIRecommendationsDAO
from data.utility import DatabaseConnectionPool

# Create DAO
pool = DatabaseConnectionPool(user="...", password="...", host="...", database="...")
rec_dao = AIRecommendationsDAO(pool)

# Save AI recommendation
rec_id = rec_dao.save_recommendation(
    portfolio_id=1,
    ticker_symbol="AAPL",
    recommendation_type="BUY",
    recommended_quantity=10,
    recommended_price=175.50,
    confidence_score=85.5,
    reasoning="Strong technical indicators: RSI oversold, MACD bullish crossover",
    technical_indicators={
        "RSI": 28.5,
        "MACD": 1.25,
        "MA_20": 172.30,
        "MA_50": 169.80
    },
    sentiment_score=0.75,
    expires_date=datetime.now() + timedelta(days=7)
)
```

### Enhanced CLI Commands

New commands available in the enhanced CLI:

#### View Active Recommendations
```
view_recommendations
```
Shows all pending AI recommendations with full details.

#### View Recommendation History
```
recommendation_history
```
Browse past recommendations filtered by status (FOLLOWED, IGNORED, etc.).

#### Add Recommendation Manually
```
add_recommendation
```
Manually record an AI recommendation for tracking.

#### View Statistics
```
recommendation_stats
```
See statistics about recommendations:
- Total recommendations by status
- Follow rate (% of recommendations followed)
- Average confidence scores

#### Update Recommendation Status
```
update_recommendation_status
```
Mark recommendations as followed, ignored, or expired.

### Transaction Logging with Rationale

When logging buy/sell transactions via the enhanced CLI, you'll now be prompted:

1. **Was this based on an AI recommendation?**
   - If yes, system shows active recommendations and links the transaction

2. **What is the rationale for this trade?**
   - Options: MANUAL_DECISION, STOP_LOSS, PROFIT_TARGET, REBALANCE, OTHER

3. **Notes about this trade** (optional)
   - Free-text explanation

4. **Did you override an AI recommendation?**
   - If there were active recommendations, explain why you ignored them

### Programmatic API

```python
from data.portfolio_transactions_dao import PortfolioTransactionsDAO

trans_dao = PortfolioTransactionsDAO(pool)

# Log transaction with rationale
transaction_id = trans_dao.insert_transaction(
    portfolio_id=1,
    security_id=123,
    transaction_type="buy",
    transaction_date=datetime.now().date(),
    shares=10,
    price=175.50,
    trade_rationale_type="AI_RECOMMENDATION",
    ai_recommendation_id=456,  # Links to recommendation
    user_notes="Following AI buy signal based on technical analysis"
)

# Get transactions with rationale
transactions = trans_dao.get_transactions_with_rationale(portfolio_id=1)

# Get statistics
stats = trans_dao.get_rationale_statistics(portfolio_id=1)
print(f"Total trades: {stats['total']}")
print(f"AI-driven trades: {stats['by_type']['AI_RECOMMENDATION']['count']}")
```

## Benefits & Use Cases

### 1. AI Learning & Improvement
- AI can analyze which recommendations were followed vs ignored
- Identify patterns in successful vs unsuccessful recommendations
- Refine recommendation criteria based on outcomes

### 2. User Accountability
- Complete audit trail of trading decisions
- Understand your own decision-making patterns
- Identify emotional vs rational trading

### 3. Performance Analysis
- Compare AI-driven trades vs manual decisions
- Track which types of recommendations perform best
- Measure confidence score accuracy

### 4. Risk Management
- See if you're consistently ignoring certain types of recommendations
- Identify when you override stop-loss recommendations
- Track rebalancing vs opportunistic trades

## Example Workflows

### Workflow 1: AI Generates Weekly Recommendations

```python
# AI analysis generates recommendations
analyzer = LLMPortfolioAnalyzer(pool)
recommendations = analyzer.get_weekly_recommendations(portfolio_id=1)

# Save each recommendation
for rec in recommendations:
    rec_dao.save_recommendation(
        portfolio_id=1,
        ticker_symbol=rec['ticker'],
        recommendation_type=rec['action'],
        reasoning=rec['reasoning'],
        confidence_score=rec['confidence'],
        technical_indicators=rec['indicators']
    )
```

### Workflow 2: User Executes Trade

```
1. User launches enhanced CLI
2. Selects "log_transaction"
3. Enters buy/sell details
4. System asks: "Was this based on AI recommendation?"
5. If yes, shows active recommendations and links automatically
6. If no, asks for rationale type and notes
7. Transaction saved with full context
```

### Workflow 3: Review & Analysis

```python
# Get recommendation statistics
stats = rec_dao.get_recommendation_statistics(portfolio_id=1)
print(f"Follow rate: {stats['followed'] / stats['total'] * 100}%")

# Find transactions linked to a specific recommendation
rec_id = 123
transactions = trans_dao.get_transactions_by_recommendation(rec_id)
for txn in transactions:
    print(f"{txn['transaction_date']}: {txn['transaction_type']} {txn['shares']} shares")

# Get rationale breakdown
rationale_stats = trans_dao.get_rationale_statistics(portfolio_id=1)
for rationale_type, data in rationale_stats['by_type'].items():
    print(f"{rationale_type}: {data['count']} trades")
```

## Future Enhancements (Phase 2+)

### Phase 2: Recommendation Performance Tracking
- Track actual outcomes vs recommendations
- Calculate recommendation accuracy metrics
- Price tracking at recommendation time vs execution time

### Phase 3: Advanced Analytics
- Identify which market conditions AI performs best in
- Correlation between confidence scores and outcomes
- Machine learning on historical recommendation data

### Phase 4: Real-time Integration
- Automatic recommendation updates based on market changes
- Alert system for high-confidence recommendations
- Portfolio optimization suggestions

## Data Privacy & Security

- All data stored locally in your MySQL database
- No external API calls for recommendation storage
- Trade rationale information is private and not shared

## Troubleshooting

### Issue: Tables not created
**Solution**: Run the SQL migration scripts in the correct order

### Issue: Transaction logging fails with "column not found"
**Solution**: Ensure you've run the ALTER TABLE script for portfolio_transactions

### Issue: Can't import AIRecommendationsDAO
**Solution**: Ensure `data/ai_recommendations_dao.py` is in the correct location

### Issue: Recommendations not showing in CLI
**Solution**: Verify the registration in `enhanced_cli/main.py` includes `register_ai_recommendations_commands()`

## Technical Notes

- **Backward Compatibility**: Old transactions without rationale continue to work
- **JSON Storage**: Technical indicators stored as JSON for flexibility
- **Database Indexes**: Added for efficient querying by portfolio, status, and date
- **Cascading**: No cascade delete - recommendations preserved for historical analysis
- **Expiration**: Recommendations can have expiration dates; system auto-marks as EXPIRED

## Summary

This implementation provides a complete framework for:
1. ✅ Storing all AI recommendations with full context
2. ✅ Tracking why each trade was made
3. ✅ Linking trades to AI recommendations
4. ✅ Analyzing recommendation performance
5. ✅ Creating feedback loops for AI improvement

The system is now ready to track and learn from AI recommendations, providing valuable insights into trading decisions and AI performance over time.
