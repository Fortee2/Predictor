# AI Portfolio Assistant - Continuous Advisory Mode

## Overview

The **AI Portfolio Assistant** (`ai_chat` command) now operates as a **continuous advisory session** that maintains full conversation context throughout your interaction. This allows the AI to track recommendations, remember decisions, and provide context-aware advice over time.

---

## How It Works

### Session-Based Context Management

When you start the AI Portfolio Assistant:

```
> ai_chat

🤖 AI Portfolio Assistant - Advisory Session

Welcome to your continuous portfolio advisory session!

I'll maintain context of our conversation to:
• Track recommendations and their outcomes
• Remember why actions were suggested
• Monitor which suggestions you follow
• Provide consistent, context-aware advice
```

**Technical Implementation:**
- **First query**: Resets context to start fresh (`reset_context=True`)
- **All subsequent queries**: Maintains conversation history (`reset_context=False`)
- **Session persists**: Until you type 'exit' or 'clear'

### Why This Matters

In an advisory relationship, context is crucial:

1. **Track Recommendations**: The AI remembers what it suggested and when
2. **Monitor Outcomes**: It knows which suggestions you followed
3. **Understand Reasoning**: It recalls why specific actions were recommended
4. **Provide Continuity**: Advice builds on previous discussions

---

## Example Advisory Session

### Scenario: Following an Investment Plan

```
Query 1:
> What stocks should I consider buying this week?

AI Response:
Based on your portfolio analysis, I recommend:
1. AAPL - Strong technicals, oversold RSI at 28
2. MSFT - Bullish MACD crossover
3. NVDA - Bounce from support level

I suggest allocating $5,000 across these three positions...

---

Query 2:
> I bought 50 shares of AAPL at $178. What about the others?

AI Response:
Great! You've executed the AAPL recommendation. At $178, you got a 
good entry near the support level I mentioned. That's $8,900 invested.

For MSFT and NVDA:
- MSFT is still showing the bullish MACD signal...
- NVDA has moved up 3% since my recommendation...

---

Query 3:
> MSFT seems risky given the tech sector pullback. Why did you recommend it?

AI Response:
I understand your concern about sector risk. I recommended MSFT because:

1. In my initial analysis, the MACD showed a bullish crossover
2. The stock was trading at a reasonable P/E of 32.5
3. It provides diversification from AAPL (different tech subsector)

However, given your risk concerns and the sector pullback you've observed,
it's perfectly reasonable to skip MSFT. Would you like to explore other
sectors instead?

---

Query 4:
> Yes, what about financial sector stocks?

AI Response:
Good thinking on diversification away from tech, especially since you've
already invested in AAPL and you're concerned about the tech sector.

Let me analyze financial sector opportunities...
[Provides financial sector analysis]

---

Query 5:
> I'll add JPM. Should I still consider NVDA or is that too much tech exposure?

AI Response:
You're right to be cautious. Let's review your current plan:
- ✅ AAPL: $8,900 (50 shares @ $178) - executed
- ❌ MSFT: Skipped due to sector concerns
- ❌ NVDA: Reconsidering due to tech exposure
- 🆕 JPM: Considering

With AAPL already in your portfolio, adding NVDA would give you 
significant tech concentration. Given that you:
1. Skipped MSFT specifically due to tech sector concerns
2. Are now diversifying into financials

I'd recommend skipping NVDA as well and focusing on JPM for now...
```

**Key Point**: The AI remembers the entire conversation flow, tracking what was recommended, what was executed, what was skipped, and why decisions were made.

---

## Session Management Commands

### Special Commands

While in an advisory session, you can use:

| Command | Description | Example |
|---------|-------------|---------|
| `clear` | Start a new advisory session | Clears all conversation history |
| `history` | View conversation summary | Shows # of exchanges and messages |
| `exit` | End the advisory session | Shows session summary |

### Using 'clear'

```
> clear
⚠️ Start a new advisory session? This will clear conversation history.
[yes/no]: yes

✅ Started fresh advisory session. Previous context cleared.
```

Use this when:
- Starting a completely new discussion topic
- The conversation has become too long
- You want to reset the advisory relationship

### Using 'history'

```
> history

Current advisory session:
  • Total exchanges: 8
  • Conversation history: 16 messages
  • Session maintains full context of all recommendations and discussions
```

### Using 'exit'

```
> exit

Advisory session ended. Total exchanges: 12
```

---

## The AI Portfolio Assistant - Your All-in-One Advisor

The **AI Portfolio Assistant** (`ai_chat` command) is now your **single point of contact** for all portfolio advisory needs. Rather than having separate commands for different types of analysis, you simply ask the AI what you need in natural language.

### What You Can Ask

Within a single advisory session, you can ask for:

- **Weekly Recommendations**: "What should I buy this week?"
- **Portfolio Analysis**: "How is my portfolio performing?"
- **Risk Assessment**: "What are my portfolio risks?"
- **Technical Analysis**: "Show me RSI for AAPL"
- **Investment Ideas**: "Which tech stocks look good?"
- **Follow-up Questions**: "Why did you recommend that?"

### Why This Approach?

**Benefits of unified interface:**
- 🎯 **Natural Conversation**: Ask questions the way you think about them
- 🔄 **Flexible Analysis**: Switch topics naturally within same session
- 📊 **Context-Aware**: AI remembers what you've already discussed
- 💡 **Learning**: AI understands your preferences over time

**Example:**
```
> How is my portfolio doing?
[AI provides comprehensive analysis]

> What are the biggest risks?
[AI provides risk assessment, remembering portfolio details from above]

> Should I buy more AAPL?
[AI considers your portfolio, risks, and previous discussion]
```

### Standalone Risk Assessment

The **AI Risk Assessment** (`ai_risk_assessment` command) remains available as a standalone report for formal risk documentation.

---

## Best Practices for Advisory Sessions

### ✅ DO

1. **Build on Previous Discussions**
   ```
   > What should I buy?
   [AI suggests stocks]
   
   > I bought the first one. What about the others?
   [AI remembers first suggestion and continues]
   ```

2. **Reference Past Recommendations**
   ```
   > You suggested AAPL last week. How's it doing?
   [AI recalls the AAPL recommendation]
   ```

3. **Explain Your Decisions**
   ```
   > I didn't buy MSFT because I'm worried about tech exposure
   [AI understands your risk preference]
   ```

4. **Ask "Why" Questions**
   ```
   > Why did you recommend that specific entry price?
   [AI can reference its previous analysis]
   ```

### ❌ DON'T

1. **Don't Mix Portfolios in Same Session**
   ```
   # BAD - Confusing context
   > Analyze portfolio 1
   > Now analyze portfolio 2
   
   # GOOD - Clear the session between portfolios
   > Analyze portfolio 1
   > clear
   > Analyze portfolio 2
   ```

2. **Don't Expect Memory Across Sessions**
   ```
   # Each new ai_chat session starts fresh
   # Previous sessions are not remembered
   ```

3. **Don't Let Sessions Become Too Long**
   ```
   # If conversation has 30+ exchanges, consider:
   > clear
   > Can you summarize our discussion and recommendations?
   ```

---

## Technical Details

### Implementation in `ai_assistant_views.py`

```python
def ai_chat_interface(console: Console, portfolio_id: int):
    """
    Interactive chat interface maintaining advisory session context.
    """
    analyzer = create_llm_analyzer()
    analyzer.reset_conversation()  # Start fresh session
    
    first_query = True
    
    while True:
        user_question = get_user_input()
        
        # First query: reset context (start fresh)
        # All others: maintain context (remember previous)
        response = analyzer.chat(
            user_question,
            portfolio_id=portfolio_id,
            reset_context=first_query  # True only once
        )
        
        first_query = False  # All subsequent queries maintain context
```

### Key Parameters

| Parameter | Value | Effect |
|-----------|-------|--------|
| `reset_context` | `True` (first query) | Starts fresh advisory session |
| `reset_context` | `False` (subsequent) | Maintains conversation context |
| `temperature` | `0.0` | Ensures consistent, deterministic responses |
| `topP` | `1.0` | Uses all probability mass |

---

## Benefits

### For You (The User)

1. **Natural Conversation Flow**: Ask follow-up questions naturally
2. **Context-Aware Advice**: AI remembers your preferences and decisions
3. **Track Progress**: Monitor how your plan is being executed
4. **Continuous Relationship**: Feels like talking to a real advisor

### For the AI

1. **Better Understanding**: Knows your risk tolerance and preferences
2. **Consistent Advice**: Recommendations build on each other logically
3. **Outcome Tracking**: Can assess if previous suggestions worked
4. **Learning from Decisions**: Understands why you accept or reject ideas

---

## When to Use AI Portfolio Assistant

**Use for everything:** The AI Portfolio Assistant is now your primary interface for:
- 📊 All portfolio analysis needs
- 📈 Weekly and daily recommendations  
- 🤔 Investment decision support
- 💬 Extended advisory discussions
- 🎯 Technical analysis queries
- ⚠️ Risk evaluations
- 💡 General portfolio questions

Simply ask what you need, and the AI will provide the appropriate analysis while maintaining conversation context.

---

## Session Persistence

**Important**: Advisory sessions are **not saved between application restarts**. Each time you run `ai_chat`, it starts a new session.

If you need to preserve context across restarts, consider:
1. Taking notes of key recommendations
2. Saving analysis to files (offered after each report)
3. Using the `history` command to review current session

---

## Cost Considerations

**Advisory sessions maintain conversation history**, which means:
- Each query includes the full conversation context
- Token usage increases as the session grows longer
- Longer sessions = Higher AWS Bedrock costs

**Recommendation**: Use the `clear` command periodically to start fresh sessions when appropriate.

---

## Summary

The AI Portfolio Assistant now provides a **true advisory experience** where context matters:

- ✅ Remembers what it recommended
- ✅ Tracks what you decided to do
- ✅ Understands why actions were taken
- ✅ Provides consistent, context-aware follow-up advice

This creates a more natural, productive advisory relationship while still maintaining the consistency and determinism improvements from the conversation history persistence updates.

---

*Last Updated: 2026-01-06*
*Related Documents:*
- *LLM_CONSISTENCY_RECOMMENDATIONS.md*
- *LLM_CONVERSATION_USAGE_GUIDE.md*
