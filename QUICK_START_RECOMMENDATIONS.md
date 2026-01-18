# Quick Start: AI Recommendations & Trade Rationale

## ✅ Setup Complete!

The database tables have been created and the system is ready to use.

## Immediate Usage

### 1. Test the New Transaction Flow

Launch the enhanced CLI and log a transaction:

```bash
python launch.py
```

Then:
1. Select a portfolio
2. Choose "Log Transaction"
3. Enter buy/sell details
4. **NEW**: You'll now be prompted for trade rationale!

The system will ask:
- "Was this trade based on an AI recommendation?"
- "What is the rationale for this trade?" (MANUAL_DECISION, STOP_LOSS, etc.)
- "Notes about this trade (optional)"

### 2. Manually Add Test Recommendations

Try the new commands:

```bash
# In the enhanced CLI
add_recommendation        # Add a test AI recommendation
view_recommendations      # View active recommendations
recommendation_stats      # See statistics
```

## Next: Integrate with Your AI Assistant

To automatically save recommendations when your AI generates them, update your AI assistant code:

### Option 1: Update `ai_assistant_views.py`

Find where your AI generates recommendations (likely in `get_weekly_recommendations()` or similar functions) and add:

```python
from data.ai_recommendations_dao import AIRecommendationsDAO

def save_ai_recommendation(portfolio_id, ticker, action, reasoning, confidence, indicators):
    """Save AI recommendation to database"""
    try:
        config = Config()
        db_config = config.get_database_config()
        pool = DatabaseConnectionPool(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            database=db_config["database"],
        )
        rec_dao = AIRecommendationsDAO(pool)

        rec_id = rec_dao.save_recommendation(
            portfolio_id=portfolio_id,
            ticker_symbol=ticker,
            recommendation_type=action.upper(),  # 'BUY', 'SELL', 'HOLD'
            confidence_score=confidence,
            reasoning=reasoning,
            technical_indicators=indicators,  # Dict of RSI, MACD, etc.
            expires_date=datetime.now() + timedelta(days=7)  # 7-day expiry
        )

        return rec_id
    except Exception as e:
        logger.error(f"Error saving recommendation: {e}")
        return None
```

### Option 2: Update LLM Portfolio Analyzer

If your recommendations come from `data/llm_portfolio_analyzer.py`, modify the analysis methods to save recommendations:

```python
# In llm_portfolio_analyzer.py
from data.ai_recommendations_dao import AIRecommendationsDAO

class LLMPortfolioAnalyzer:
    def __init__(self, pool, ...):
        self.pool = pool
        self.rec_dao = AIRecommendationsDAO(pool)  # Add this

    def get_weekly_recommendations(self, portfolio_id):
        # ... existing analysis code ...

        # After generating recommendations, save them:
        for recommendation in recommendations:
            self.rec_dao.save_recommendation(
                portfolio_id=portfolio_id,
                ticker_symbol=recommendation['ticker'],
                recommendation_type=recommendation['action'],
                recommended_quantity=recommendation.get('quantity'),
                recommended_price=recommendation.get('target_price'),
                confidence_score=recommendation.get('confidence', 70.0),
                reasoning=recommendation['reasoning'],
                technical_indicators=recommendation.get('indicators', {}),
                sentiment_score=recommendation.get('sentiment'),
            )

        return recommendations
```

## Testing the Full Workflow

### Test Scenario 1: AI Recommendation → Trade

1. **Generate AI recommendation**:
   ```bash
   # In enhanced CLI
   add_recommendation
   # Enter: AAPL, BUY, 10 shares, $180, 85% confidence
   ```

2. **Execute trade based on recommendation**:
   ```bash
   log_transaction
   # Choose: Buy, AAPL, 10 shares, $180
   # When asked: "Was this based on AI recommendation?" → Yes
   # System will show the recommendation and link them automatically
   ```

3. **View results**:
   ```bash
   recommendation_history  # See recommendation marked as FOLLOWED
   recommendation_stats    # See your follow rate
   ```

### Test Scenario 2: Manual Trade

1. **Make a manual trade**:
   ```bash
   log_transaction
   # Choose: Sell, TSLA, 5 shares, $250
   # When asked: "Was this based on AI recommendation?" → No
   # Choose rationale: PROFIT_TARGET
   # Add note: "Hit my 20% profit target"
   ```

2. **Review rationale data**:
   - Transaction will be saved with your reasoning
   - Can query later: `get_transactions_with_rationale()`

## Available Commands

All new commands in the enhanced CLI:

| Command | Description |
|---------|-------------|
| `view_recommendations` | View active AI recommendations |
| `recommendation_history` | Browse past recommendations by status |
| `add_recommendation` | Manually record an AI recommendation |
| `recommendation_stats` | View statistics and follow rate |
| `update_recommendation_status` | Mark recommendations as followed/ignored |

## Example API Usage

### Save a recommendation programmatically:

```python
from data.ai_recommendations_dao import AIRecommendationsDAO
from data.utility import DatabaseConnectionPool
from datetime import datetime, timedelta

# Setup
pool = DatabaseConnectionPool(user="...", password="...", host="...", database="...")
rec_dao = AIRecommendationsDAO(pool)

# Save recommendation
rec_id = rec_dao.save_recommendation(
    portfolio_id=1,
    ticker_symbol="AAPL",
    recommendation_type="BUY",
    recommended_quantity=10,
    recommended_price=175.50,
    confidence_score=85.5,
    reasoning="Strong technical setup: RSI oversold (28.5), bullish MACD crossover (1.25), trading below 20-day MA. Positive news sentiment (0.75).",
    technical_indicators={
        "RSI": 28.5,
        "MACD": 1.25,
        "MACD_Signal": 0.80,
        "MA_20": 177.30,
        "MA_50": 169.80,
        "Bollinger_Lower": 170.50,
        "Volume_Ratio": 1.35
    },
    sentiment_score=0.75,
    expires_date=datetime.now() + timedelta(days=7)
)

print(f"Saved recommendation ID: {rec_id}")
```

### Query recommendations:

```python
# Get active recommendations
active = rec_dao.get_active_recommendations(portfolio_id=1)
for rec in active:
    print(f"{rec['ticker_symbol']}: {rec['recommendation_type']} - {rec['confidence_score']}%")

# Get statistics
stats = rec_dao.get_recommendation_statistics(portfolio_id=1)
print(f"Total: {stats['total']}")
print(f"Followed: {stats['by_status'].get('FOLLOWED', {}).get('count', 0)}")
print(f"Ignored: {stats['by_status'].get('IGNORED', {}).get('count', 0)}")

# Calculate follow rate
total_resolved = (
    stats['by_status'].get('FOLLOWED', {}).get('count', 0) +
    stats['by_status'].get('IGNORED', {}).get('count', 0)
)
if total_resolved > 0:
    follow_rate = (stats['by_status'].get('FOLLOWED', {}).get('count', 0) / total_resolved) * 100
    print(f"Follow Rate: {follow_rate:.1f}%")
```

### Log transaction with rationale:

```python
from data.portfolio_transactions_dao import PortfolioTransactionsDAO

trans_dao = PortfolioTransactionsDAO(pool)

# Log a trade following AI recommendation
transaction_id = trans_dao.insert_transaction(
    portfolio_id=1,
    security_id=123,
    transaction_type="buy",
    transaction_date=datetime.now().date(),
    shares=10,
    price=175.50,
    trade_rationale_type="AI_RECOMMENDATION",
    ai_recommendation_id=rec_id,  # Links to recommendation above
    user_notes="Following AI buy signal based on technical analysis"
)

# Update recommendation status
rec_dao.update_recommendation_status(rec_id, "FOLLOWED")
```

## What's Tracked

### For Each Recommendation:
- ✅ Ticker symbol and action (BUY/SELL/HOLD)
- ✅ Recommended quantity and price
- ✅ AI confidence score (0-100)
- ✅ Full reasoning text
- ✅ Technical indicators (JSON: RSI, MACD, MAs, etc.)
- ✅ News sentiment score
- ✅ Status (PENDING, FOLLOWED, IGNORED, EXPIRED)
- ✅ Timestamps

### For Each Transaction:
- ✅ Rationale type (AI_RECOMMENDATION, MANUAL_DECISION, STOP_LOSS, etc.)
- ✅ Link to AI recommendation (if applicable)
- ✅ User notes explaining decision
- ✅ Override reason (if ignored AI advice)

## Benefits You'll See

1. **Complete Audit Trail** - Every trade has a reason attached
2. **AI Learning** - Feed performance data back to improve recommendations
3. **Pattern Recognition** - See which recommendations you follow vs ignore
4. **Performance Analysis** - Compare AI-driven trades vs manual decisions
5. **Accountability** - Clear record of decision-making process

## Troubleshooting

**Q: Transaction logging fails with column errors**
A: Ensure both SQL migration scripts were run successfully

**Q: Recommendations don't show in CLI**
A: Verify you're using the enhanced CLI (`python launch.py`)

**Q: Can't find ai_recommendations_dao**
A: Check that `data/ai_recommendations_dao.py` exists

**Q: Want to backfill rationale for old transactions**
A: Use `update_transaction_rationale()` method:
```python
trans_dao.update_transaction_rationale(
    transaction_id=456,
    trade_rationale_type="MANUAL_DECISION",
    user_notes="Backfilled: This was a manual trade"
)
```

## Next Steps

1. ✅ **Test the new transaction flow** - Log a buy/sell and see the rationale prompts
2. ✅ **Add test recommendations** - Use `add_recommendation` command
3. ⏳ **Integrate with AI** - Update your AI assistant to save recommendations automatically
4. ⏳ **Build analytics** - Create dashboards showing recommendation performance
5. ⏳ **Add Phase 2 features** - Outcome tracking, performance metrics

Need help with any of these steps? Let me know!