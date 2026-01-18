# AI Recommendation Tool Usage Guide

## Overview

The AI assistant now has the ability to save its own recommendations during conversational interactions. When the AI makes trading recommendations, it can automatically store them in the database for tracking and later linking to actual trades.

## New AI Tools

### 1. `save_recommendation`

**What it does**: Saves a trading recommendation to the database with full context.

**When the AI should use it**:
- When making a formal buy/sell/hold recommendation
- After performing technical analysis and identifying actionable signals
- When the user asks for specific trading recommendations
- When generating weekly recommendations

**Parameters**:
- `portfolio_id` (required): The portfolio this recommendation is for
- `ticker_symbol` (required): Stock symbol (e.g., "AAPL")
- `recommendation_type` (required): "BUY", "SELL", "HOLD", "REDUCE", or "INCREASE"
- `reasoning` (required): Detailed explanation of why
- `recommended_quantity` (optional): Suggested number of shares
- `recommended_price` (optional): Target price
- `confidence_score` (optional): 0-100 confidence level
- `technical_indicators` (optional): Dict of indicator values at time of recommendation
- `sentiment_score` (optional): News sentiment (-1 to 1)
- `expires_days` (optional): Days until recommendation expires (default 7)

### 2. `get_active_recommendations`

**What it does**: Retrieves all active (pending) recommendations for a portfolio.

**When the AI should use it**:
- Before making new recommendations to avoid duplicates
- When user asks "what are my current recommendations?"
- To reference previous recommendations in analysis

## Example Conversation Flow

### Scenario 1: User Asks for Recommendations

**User**: "What stocks should I buy this week?"

**AI Actions**:
1. Calls `get_current_positions` to see what user already owns
2. Calls `get_comprehensive_analysis` for each position
3. Analyzes technical indicators, sentiment, fundamentals
4. Makes recommendations and **calls `save_recommendation`** for each:

```json
{
  "portfolio_id": 1,
  "ticker_symbol": "AAPL",
  "recommendation_type": "BUY",
  "recommended_quantity": 10,
  "recommended_price": 175.50,
  "confidence_score": 85,
  "reasoning": "Strong technical setup with RSI at 28.5 (oversold), bullish MACD crossover at 1.25, and positive news sentiment of 0.75. Trading below 20-day MA presents good entry point.",
  "technical_indicators": {
    "RSI": 28.5,
    "MACD": 1.25,
    "MACD_Signal": 0.80,
    "MA_20": 177.30,
    "MA_50": 169.80,
    "Bollinger_Lower": 170.50
  },
  "sentiment_score": 0.75,
  "expires_days": 7
}
```

**AI Response to User**:
"Based on my analysis, I recommend buying 10 shares of AAPL around $175.50.

**Key Factors (Confidence: 85%)**:
- RSI at 28.5 indicates oversold conditions
- Bullish MACD crossover (1.25 above signal at 0.80)
- Trading below 20-day MA ($177.30) - good entry point
- Strong positive news sentiment (0.75)
- Price near Bollinger lower band ($170.50)

I've saved this recommendation and it will be available when you're ready to execute the trade. The recommendation expires in 7 days."

### Scenario 2: Weekly Recommendations Command

**User**: Runs `weekly_recommendations` command

**AI Actions**:
1. Analyzes entire portfolio
2. Reviews market conditions
3. Generates 3-5 actionable recommendations
4. **Calls `save_recommendation`** for each one
5. Returns markdown summary to user

**Result**: User gets both:
- Formatted recommendations to read
- Recommendations stored in database for tracking

### Scenario 3: Following Up on Previous Recommendations

**User**: "What recommendations do I have pending?"

**AI Actions**:
1. Calls `get_active_recommendations` for the portfolio
2. Reviews each recommendation
3. Updates analysis if market conditions changed

**AI Response**:
"You have 3 active recommendations:

1. **AAPL - BUY** (Saved 2 days ago, 85% confidence)
   - Recommended: 10 shares at $175.50
   - Current price: $176.20 (+0.4%)
   - Status: Still valid, entry point slightly higher but within range

2. **TSLA - SELL** (Saved 5 days ago, 72% confidence)
   - Recommended: 15 shares at $245
   - Current price: $250 (+2%)
   - Status: Consider executing - overbought conditions strengthening

3. **MSFT - HOLD** (Saved 1 day ago, 90% confidence)
   - No action needed - continues to consolidate as expected"

## Integration Points

### Transaction Logging

When users log transactions via the enhanced CLI, the system now:
1. Asks if trade was based on AI recommendation
2. Shows active recommendations for that portfolio
3. Automatically links transaction to recommendation
4. Updates recommendation status to "FOLLOWED"

**Example Flow**:
```
User: Logs buy transaction for AAPL, 10 shares @ $176
System: "Was this trade based on an AI recommendation?"
User: "Yes"
System: Shows active recommendations:
  [123] AAPL - BUY (10 shares @ $175.50, 85% confidence)
User: Selects recommendation #123
System: Links transaction to recommendation, marks as FOLLOWED
```

### Performance Tracking

The AI can later analyze its own performance:

**User**: "How accurate have your recommendations been?"

**AI can call** (future enhancement):
- `get_recommendation_statistics` to see follow rate
- Link recommendations to actual outcomes
- Calculate success rates by confidence level
- Identify which types of analysis work best

## Best Practices for the AI

### When to Save Recommendations

**DO save when**:
- Making specific, actionable recommendations (BUY X shares at Y price)
- User explicitly asks for recommendations
- Generating weekly/periodic recommendation reports
- Confidence level is moderate to high (> 60%)

**DON'T save when**:
- Giving general market commentary
- Answering "what do you think about..." questions casually
- Discussing hypothetical scenarios
- Making very low confidence suggestions

### Include Complete Context

Always provide in reasoning:
- Technical factors (RSI, MACD, MAs)
- Fundamental factors (if analyzed)
- Market conditions / sector trends
- News sentiment
- Risk factors / caveats

### Set Appropriate Confidence Scores

- **90-100%**: Very strong signals across all indicators, low risk
- **75-89%**: Strong signals, good setup, moderate risk
- **60-74%**: Decent signals, some conflicting data
- **<60%**: Weak signals, don't save as formal recommendation

### Set Reasonable Expiration

- **Swing trades**: 3-7 days
- **Position trades**: 14-30 days
- **Long-term**: 60-90 days
- **Day trades**: 1 day

## Benefits

1. **Accountability**: Complete record of what AI recommended and when
2. **Learning**: AI can analyze which recommendations were followed/ignored
3. **Performance Tracking**: Measure recommendation accuracy over time
4. **User Trust**: Users can see AI's track record
5. **Context Preservation**: Full reasoning saved with technical data

## Example AI Prompts

Here are examples of how the AI should think about using these tools:

### Good Usage

```
User asks: "Should I buy more AAPL?"

AI thinking:
1. First, get current AAPL analysis
2. Check RSI, MACD, sentiment
3. If signals are strong (>75% confidence), make recommendation
4. Call save_recommendation with full context
5. Tell user recommendation has been saved
```

### Avoid Over-Saving

```
User asks: "What do you think about tech stocks in general?"

AI thinking:
1. This is general commentary, not specific recommendation
2. No need to save anything
3. Just provide analysis and opinions
```

## Technical Details

### Database Storage

Recommendations are stored in the `ai_recommendations` table with:
- Full technical indicator snapshot (JSON)
- News sentiment at time of recommendation
- AI reasoning and confidence
- Status tracking (PENDING → FOLLOWED/IGNORED/EXPIRED)
- Expiration dates

### Linking to Transactions

When transactions are logged with `trade_rationale_type='AI_RECOMMENDATION'`:
- The `ai_recommendation_id` field links to the recommendation
- Recommendation status automatically updates
- Creates complete audit trail

### Expiration Handling

- Recommendations automatically expire based on `expires_date`
- System auto-marks as EXPIRED when retrieving active recommendations
- Users can manually update status via CLI commands

## Future Enhancements

### Phase 2: Outcome Tracking
- Track actual price movements after recommendation
- Calculate recommendation performance metrics
- Identify which signals are most predictive

### Phase 3: Adaptive Learning
- AI adjusts confidence scoring based on historical accuracy
- Learns which market conditions it performs best in
- Refines technical indicator weights

### Phase 4: Proactive Alerts
- AI monitors active recommendations
- Alerts when entry/exit points are hit
- Suggests updates when conditions change significantly

## Summary

The AI assistant can now:
✅ Save its own recommendations during conversations
✅ Include full technical and fundamental context
✅ Set confidence scores and expiration dates
✅ Retrieve and reference previous recommendations
✅ Enable complete tracking of recommendation → execution flow

This creates a feedback loop where the AI can learn from its past recommendations and continuously improve its analysis.
