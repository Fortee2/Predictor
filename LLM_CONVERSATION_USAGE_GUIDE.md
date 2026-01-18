# LLM Conversation Usage Guide

## Overview

After implementing the conversation history persistence improvements, the LLM Portfolio Analyzer now provides more consistent and predictable analysis results. This guide explains how conversation management works and when to use different modes.

---

## Key Changes Implemented

### 1. **Default Behavior: Fresh Context Per Query**
- Each analysis now starts with a **clean slate** by default
- Previous conversation history does NOT influence new queries
- Ensures consistent results for identical queries
- Prevents "context bleed" between unrelated analyses

### 2. **Deterministic Settings**
- Temperature: 0.0 (maximum consistency)
- TopP: 1.0 (uses all probability mass)
- Same query = Same response (with same data)

### 3. **Optional Conversation Continuation**
- Can explicitly continue conversations when needed
- Useful for follow-up questions or multi-step analysis

---

## How to Use

### Basic Usage (Default: Fresh Context)

```python
from data.llm_portfolio_analyzer import LLMPortfolioAnalyzer
from data.utility import DatabaseConnectionPool

# Initialize
pool = DatabaseConnectionPool(...)
analyzer = LLMPortfolioAnalyzer(pool=pool)

# Each query starts fresh - no context from previous queries
response1 = analyzer.chat("What is my portfolio's total value?", portfolio_id=1)
response2 = analyzer.chat("What is the RSI for AAPL?", portfolio_id=1)
response3 = analyzer.chat("Should I buy or sell MSFT?", portfolio_id=1)

# Each of these queries is independent - response2 doesn't "remember" response1
```

**Result:** Each query gets analyzed independently with fresh context, ensuring consistency.

---

### Continuing a Conversation

When you want the LLM to remember previous context (for follow-up questions):

```python
analyzer = LLMPortfolioAnalyzer(pool=pool)

# Start fresh conversation
response1 = analyzer.chat(
    "Analyze AAPL's technical indicators",
    portfolio_id=1,
    reset_context=True  # Default, can omit
)

# Continue the conversation - LLM remembers previous analysis
response2 = analyzer.chat(
    "Based on that analysis, should I buy more?",
    portfolio_id=1,
    reset_context=False  # Keep conversation history
)

# Another follow-up
response3 = analyzer.chat(
    "What about risk factors?",
    portfolio_id=1,
    reset_context=False  # Still continuing
)

# Start a completely new topic
response4 = analyzer.chat(
    "Now analyze MSFT instead",
    portfolio_id=1,
    reset_context=True  # Fresh start
)
```

**Result:** Follow-up questions can reference previous context when needed.

---

## Use Cases

### ✅ When to Use Default (reset_context=True)

1. **Independent Queries**
   ```python
   # Different topics - no need for context
   analyzer.chat("What's my cash balance?", portfolio_id=1)
   analyzer.chat("Show me TSLA's technical indicators", portfolio_id=1)
   ```

2. **Scheduled/Automated Analysis**
   ```python
   # Weekly portfolio review - always start fresh
   weekly_analysis = analyzer.chat(
       "Provide weekly portfolio recommendations",
       portfolio_id=1
   )
   ```

3. **Testing for Consistency**
   ```python
   # Verify same query produces same result
   for i in range(5):
       result = analyzer.chat("What is AAPL's RSI?", portfolio_id=1)
       # All results should be identical
   ```

4. **Multiple Users/Sessions**
   ```python
   # Different users shouldn't see each other's context
   user1_result = analyzer.chat("Analyze my portfolio", portfolio_id=1)
   user2_result = analyzer.chat("Analyze my portfolio", portfolio_id=2)
   ```

### ✅ When to Use Conversation Mode (reset_context=False)

1. **Multi-Step Analysis**
   ```python
   # Step 1: Get overview
   overview = analyzer.chat("Analyze my portfolio", portfolio_id=1)
   
   # Step 2: Deep dive on specific aspect
   details = analyzer.chat(
       "Tell me more about the risk factors you mentioned",
       portfolio_id=1,
       reset_context=False
   )
   ```

2. **Follow-Up Questions**
   ```python
   # Initial question
   analysis = analyzer.chat(
       "Should I buy NVDA?",
       portfolio_id=1
   )
   
   # Clarifying question
   clarification = analyzer.chat(
       "What price level would you recommend?",
       portfolio_id=1,
       reset_context=False
   )
   ```

3. **Interactive Advisory Session**
   ```python
   # Simulating a conversation with financial advisor
   q1 = analyzer.chat("I have $5000 to invest. What do you recommend?", portfolio_id=1)
   q2 = analyzer.chat("I'm risk-averse. Does that change your recommendation?", 
                      portfolio_id=1, reset_context=False)
   q3 = analyzer.chat("How should I split between those options?",
                      portfolio_id=1, reset_context=False)
   ```

4. **Refinement Iterations**
   ```python
   # Initial recommendation
   rec1 = analyzer.chat("Recommend swing trade opportunities", portfolio_id=1)
   
   # Refine based on preferences
   rec2 = analyzer.chat("Focus only on tech stocks", 
                        portfolio_id=1, reset_context=False)
   ```

---

## Managing Conversation History Manually

### Check Current History

```python
history = analyzer.get_conversation_history()
print(f"Current conversation has {len(history)} messages")
```

### Clear History Manually

```python
# Explicitly clear conversation history
analyzer.reset_conversation()

# Now next query will start fresh even with reset_context=False
response = analyzer.chat("New topic", portfolio_id=1, reset_context=False)
```

### Save and Restore Conversations

```python
# Save conversation state
saved_history = analyzer.get_conversation_history()

# Do other work...
analyzer.chat("Unrelated query", portfolio_id=1)

# Restore previous conversation
analyzer.set_conversation_history(saved_history)

# Continue where you left off
response = analyzer.chat("Continue previous topic", 
                        portfolio_id=1, reset_context=False)
```

---

## CLI Integration Example

In the CLI, you might implement conversation mode like this:

```python
# In enhanced_cli/ai_assistant_views.py

class AIAssistantView:
    def __init__(self):
        self.analyzer = LLMPortfolioAnalyzer(pool=db_pool)
        self.conversation_mode = False  # Track mode
    
    def handle_query(self, query: str, portfolio_id: int):
        """Handle user query with conversation mode support."""
        
        # Use conversation mode setting
        response = self.analyzer.chat(
            query,
            portfolio_id=portfolio_id,
            reset_context=not self.conversation_mode
        )
        
        return response
    
    def toggle_conversation_mode(self):
        """Toggle between single-query and conversation modes."""
        self.conversation_mode = not self.conversation_mode
        
        if not self.conversation_mode:
            # Switched to single-query mode - clear history
            self.analyzer.reset_conversation()
        
        mode_name = "Conversation" if self.conversation_mode else "Single Query"
        print(f"Switched to {mode_name} mode")
```

Usage in CLI:
```
> ask What is my portfolio worth?
[Single Query Mode] Your portfolio is worth $125,432.50

> toggle-conversation
Switched to Conversation mode

> ask What are my best performing stocks?
[Conversation Mode] Based on your portfolio...

> ask What about worst performers?
[Conversation Mode] Continuing from previous analysis...

> toggle-conversation
Switched to Single Query mode
[Conversation history cleared]
```

---

## Benefits of These Changes

### 1. **Consistency**
```python
# Same query = Same response (assuming data hasn't changed)
for _ in range(10):
    result = analyzer.chat("What is AAPL's RSI?", portfolio_id=1)
    # All 10 results will be identical
```

### 2. **Predictability**
```python
# No unexpected context from previous queries
analyzer.chat("Buy AAPL", portfolio_id=1)
result = analyzer.chat("What did I just ask about?", portfolio_id=1)
# Result won't know about AAPL (fresh context)
```

### 3. **Debugging**
```python
# Easy to reproduce issues
query = "Analyze MSFT"
result1 = analyzer.chat(query, portfolio_id=1)
# ... time passes ...
result2 = analyzer.chat(query, portfolio_id=1)
# Results should be identical for debugging
```

### 4. **Testing**
```python
# Reliable unit tests
def test_rsi_query():
    result = analyzer.chat("Get RSI for AAPL", portfolio_id=1)
    assert "RSI" in result
    # Test will consistently pass/fail
```

---

## Best Practices

### ✅ DO

1. **Use default mode for independent queries**
   ```python
   result = analyzer.chat("Query here", portfolio_id=1)  # reset_context=True by default
   ```

2. **Be explicit when continuing conversations**
   ```python
   result = analyzer.chat("Follow-up", portfolio_id=1, reset_context=False)
   ```

3. **Clear history when switching topics**
   ```python
   analyzer.reset_conversation()
   result = analyzer.chat("New topic", portfolio_id=1)
   ```

4. **Use conversation mode for natural follow-ups**
   ```python
   initial = analyzer.chat("Analyze AAPL", portfolio_id=1)
   followup = analyzer.chat("What about entry price?", portfolio_id=1, reset_context=False)
   ```

### ❌ DON'T

1. **Don't accumulate history unintentionally**
   ```python
   # BAD - conversation grows indefinitely
   for stock in ["AAPL", "MSFT", "GOOGL"]:
       analyzer.chat(f"Analyze {stock}", portfolio_id=1, reset_context=False)
   ```

2. **Don't mix contexts without clearing**
   ```python
   # BAD - portfolio 2 analysis might reference portfolio 1 data
   analyzer.chat("Analyze portfolio", portfolio_id=1, reset_context=False)
   analyzer.chat("Analyze portfolio", portfolio_id=2, reset_context=False)
   ```

3. **Don't rely on context for unrelated queries**
   ```python
   # BAD - expecting context when it won't exist
   analyzer.chat("Analyze AAPL", portfolio_id=1)
   analyzer.chat("What was that ticker again?", portfolio_id=1)  # Won't work - fresh context
   ```

---

## Migration Guide

### Old Code (Before Changes)
```python
# Previously - context accumulated automatically
analyzer = LLMPortfolioAnalyzer(pool=pool)
result1 = analyzer.chat("Query 1", portfolio_id=1)
result2 = analyzer.chat("Query 2", portfolio_id=1)
# result2 would remember result1 (unwanted context bleed)
```

### New Code (After Changes)
```python
# Now - explicit control over context
analyzer = LLMPortfolioAnalyzer(pool=pool)

# Independent queries (default)
result1 = analyzer.chat("Query 1", portfolio_id=1)
result2 = analyzer.chat("Query 2", portfolio_id=1)
# result2 does NOT remember result1 (clean slate)

# OR - Explicit conversation
result1 = analyzer.chat("Query 1", portfolio_id=1, reset_context=True)
result2 = analyzer.chat("Query 2", portfolio_id=1, reset_context=False)
# result2 DOES remember result1 (when intended)
```

---

## CLI Implementation: AI Portfolio Assistant

### Single Unified Interface

The **AI Portfolio Assistant** (`ai_chat` command) is now your **single point of contact** for all portfolio advisory needs. It maintains full conversation context throughout your session:

```
> ai_chat

🤖 AI Portfolio Assistant - Your Personal Advisor

Welcome to your continuous portfolio advisory session!

Ask me anything:
• 📈 Weekly recommendations - "What should I buy this week?"
• 📊 Portfolio analysis - "How is my portfolio performing?"
• ⚠️  Risk assessment - "What are my portfolio risks?"
• 🎯 Technical analysis - "Show me RSI for AAPL"
• 💡 Investment ideas - "Which stocks look good?"
• 🤔 Follow-up questions - "Why did you recommend that?"

I maintain full context:
• Track recommendations and their outcomes
• Remember why actions were suggested
• Monitor which suggestions you follow
• Provide consistent, context-aware advice

Commands:
  • 'clear' - Start a fresh session
  • 'history' - See conversation summary
  • 'exit' - End session
```

**How it works:**
1. **First query**: Starts fresh advisory session (`reset_context=True`)
2. **All follow-ups**: Maintains conversation context (`reset_context=False`)
3. **Flexible**: Ask for any type of analysis in natural language
4. **Session persists**: Context maintained until you type 'clear' or 'exit'

**Example Session:**
```
> How is my portfolio performing?
[AI provides comprehensive portfolio analysis]

> What are the biggest risks?
[AI provides risk assessment, remembering portfolio details from above]

> What should I buy this week?
[AI provides weekly recommendations considering previous discussion]

> I bought AAPL. Should I also buy MSFT?
[AI remembers AAPL purchase and provides context-aware advice]

> Why do you recommend MSFT?
[AI recalls its MSFT recommendation and explains reasoning]
```

### Standalone Risk Assessment

The **AI Risk Assessment** (`ai_risk_assessment` command) remains available as a standalone report for formal risk documentation. It uses fresh context (`reset_context=True`) for consistent, independent risk reports.

## Summary

| Use Case | reset_context | Where Used |
|----------|---------------|------------|
| **AI Portfolio Assistant** (all-in-one) | `False` after first query | CLI `ai_chat` command |
| Risk assessment (standalone) | `True` (default) | CLI `ai_risk_assessment` command |
| Independent API queries | `True` (default) | Direct API usage |
| Follow-up questions | `False` | Within advisory sessions |
| Testing consistency | `True` | Test suites |

**Key Principle:** 
- **AI Portfolio Assistant** = Your unified interface with maintained context
  - Ask for weekly recommendations, portfolio analysis, risk assessment, etc.
  - All within one continuous advisory session
- **Standalone reports** = Fresh context for independent documentation

---

*Last Updated: 2026-01-06*
*Related: LLM_CONSISTENCY_RECOMMENDATIONS.md*
