# AI Conversation Persistence

## Overview

The AI Portfolio Assistant now **persists conversations between sessions**, allowing you to resume your advisory discussions exactly where you left off. This feature enables true continuity in your portfolio advisory relationship with the AI.

---

## Key Features

### 🔄 **Automatic Session Persistence**
- Conversations are automatically saved to the database after each exchange
- Resume your previous conversation when you return
- No manual save required - it just works!

### 📊 **Session Management**
- View all your saved conversation sessions
- Name sessions for easy identification
- Archive old sessions and start fresh when needed
- Automatic cleanup of inactive sessions (30+ days old)

### 🧠 **True Conversation Continuity**
- AI remembers your previous discussions across application restarts
- Track recommendations over multiple sessions
- Build on previous conversations naturally
- Maintain context over days, weeks, or months

---

## Setup Instructions

### 1. Create Database Table

Run the SQL script to create the conversation history table:

```bash
mysql -u your_username -p your_database < database_script/create_conversation_history_table.sql
```

Or manually execute:

```sql
CREATE TABLE IF NOT EXISTS ai_conversation_history (
  id INT NOT NULL AUTO_INCREMENT,
  portfolio_id INT NOT NULL,
  session_name VARCHAR(255) NULL,
  conversation_data JSON NOT NULL,
  message_count INT NOT NULL DEFAULT 0,
  exchange_count INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  PRIMARY KEY (id),
  KEY portfolio_id (portfolio_id),
  CONSTRAINT conv_history_portfolio_fk 
    FOREIGN KEY (portfolio_id) REFERENCES portfolio (id) ON DELETE CASCADE
);
```

### 2. Verify Installation

The table will be automatically used by the AI assistant. No additional configuration needed!

---

## How It Works

### Starting a New Session

When you run `ai_chat`, the system checks for saved conversations:

```
> ai_chat

[Checking for saved conversations...]

📝 Found Previous Conversation

Session ID: 42
Exchanges: 8
Messages: 16

Would you like to continue where you left off?

[yes/no]:
```

**Option 1: Resume** → Continue from your last conversation  
**Option 2: Start Fresh** → Begin a new session (previous one is archived)

### During Your Session

The conversation is automatically saved after each exchange:

```
Query 1:
> What should I buy this week?
[AI Response with recommendations]
💾 Auto-saved (Session ID: 42)

Query 2:
> I bought AAPL. What about the others?
[AI remembers the previous recommendation]
💾 Auto-saved (Session ID: 42)
```

### Session Persistence

Your conversation is saved:
- ✅ After each question/answer exchange
- ✅ When you exit normally
- ✅ When you interrupt with Ctrl+C
- ✅ If the application crashes (last successful save persists)

---

## Available Commands

### Within AI Chat Session

| Command | Description | Example |
|---------|-------------|---------|
| `history` | View current session stats | Shows exchanges, messages, session ID |
| `sessions` | List all saved sessions | Shows recent 10 sessions with dates |
| `name <name>` | Name the current session | `name Weekly Review Jan 2026` |
| `clear` | Archive current & start fresh | Saves current, creates new session |
| `exit` | End session (auto-saved) | Normal exit, conversation persists |

### Examples

```bash
# View current session information
> history
Current advisory session:
  • Session ID: 42
  • Total exchanges: 8
  • Conversation history: 16 messages
  • Auto-saved: Yes

# List your saved sessions
> sessions
Recent conversation sessions:
✓ ID 42: Weekly Review Jan 2026 (8 exchanges, last: 2026-01-10 13:45)
  ID 41: Market Analysis (12 exchanges, last: 2026-01-09 15:30)
  ID 40: Risk Assessment (5 exchanges, last: 2026-01-08 10:15)

# Name your session for easy reference
> name Portfolio Rebalancing Discussion
✅ Session renamed to: Portfolio Rebalancing Discussion

# Start a fresh session (archives current)
> clear
Archive current session and start fresh? [yes/no]: yes
📦 Current session archived
✅ Started fresh advisory session.
```

---

## Use Cases

### 1. **Multi-Day Investment Planning**

**Monday:**
```
> What stocks look good this week?
[AI provides analysis and recommendations]
> exit
✅ Conversation saved
```

**Wednesday:**
```
> ai_chat
Resume previous conversation? yes
✅ Resuming previous conversation session

> I bought AAPL at $178 as you suggested. How's it doing?
[AI remembers Monday's recommendation and provides update]
```

### 2. **Long-Term Portfolio Review**

Track your portfolio's progress over weeks or months:

```
Week 1:
> Analyze my portfolio performance
[AI provides detailed analysis]
> name Q1 2026 Portfolio Review

Week 4:
> ai_chat
[Resumes Q1 2026 Portfolio Review]
> How has my portfolio changed since we last talked?
[AI can reference the previous analysis from Week 1]
```

### 3. **Following Recommendation Outcomes**

```
Day 1:
> What should I buy?
[AI: Buy MSFT at $380, RSI oversold]

Day 7:
> I followed your MSFT recommendation. How's it performing?
[AI remembers the recommendation and provides outcome analysis]
```

---

## Session Management Best Practices

### ✅ DO

1. **Name Important Sessions**
   ```
   > name Tax Loss Harvesting Strategy
   ```
   Makes it easy to find and reference later

2. **Use `clear` for New Topics**
   ```
   # Finished discussion about tech stocks
   > clear
   # Now starting discussion about bonds
   ```
   Keeps conversations focused and organized

3. **Let Sessions Build Context**
   ```
   # Over multiple sessions, build a comprehensive view
   Session 1: Initial portfolio analysis
   Session 2: Implement recommendations
   Session 3: Review outcomes
   ```

### ❌ DON'T

1. **Don't Mix Portfolios in Same Session**
   ```
   # BAD
   > Analyze portfolio 1
   > Now switch to portfolio 2
   
   # GOOD
   > clear
   [Select different portfolio]
   > ai_chat
   ```

2. **Don't Let Sessions Become Too Long**
   ```
   # If you have 30+ exchanges, consider:
   > clear
   > Summarize our previous discussions and continue
   ```

---

## Technical Details

### Data Storage

Conversations are stored in the `ai_conversation_history` table as JSON:

```json
{
  "conversation_data": [
    {"role": "user", "content": [{"text": "What should I buy?"}]},
    {"role": "assistant", "content": [{"text": "Based on analysis..."}]}
  ],
  "message_count": 16,
  "exchange_count": 8,
  "session_id": 42
}
```

### Auto-Save Mechanism

```python
# After each chat() call in llm_portfolio_analyzer.py:
if self.auto_save and portfolio_id and len(self.conversation_history) > 0:
    self.save_conversation_to_db(portfolio_id)
```

### Session Lifecycle

1. **Load**: Check for active session on startup
2. **Update**: Save after each exchange
3. **Archive**: Mark as inactive when starting fresh
4. **Cleanup**: Automatically delete sessions >30 days old (inactive)

---

## Database Schema

### Table: `ai_conversation_history`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key, session ID |
| `portfolio_id` | INT | Foreign key to portfolio |
| `session_name` | VARCHAR(255) | Optional user-provided name |
| `conversation_data` | JSON | Full conversation history |
| `message_count` | INT | Total messages in conversation |
| `exchange_count` | INT | Number of user-assistant exchanges |
| `created_at` | DATETIME | When session was created |
| `updated_at` | DATETIME | Last modification time |
| `last_accessed_at` | DATETIME | Last time session was accessed |
| `is_active` | BOOLEAN | Whether this is the current active session |

### Indexes

- `idx_conv_portfolio_active`: Fast lookup of active sessions by portfolio
- `idx_conv_last_accessed`: Efficient cleanup queries

---

## Maintenance

### Cleanup Old Sessions

The system automatically cleans up old inactive sessions, but you can also do it manually:

```python
# In Python code or via CLI
from data.conversation_history_dao import ConversationHistoryDAO

dao = ConversationHistoryDAO(pool)
deleted = dao.clear_old_sessions(portfolio_id=1, days_old=30)
print(f"Deleted {deleted} old sessions")
```

### Manual Session Management

```python
# List all sessions
sessions = dao.list_sessions(portfolio_id=1, limit=10)

# Delete a specific session
dao.delete_session(session_id=42)

# Rename a session
dao.set_session_name(session_id=42, "Important Discussion")
```

---

## Cost Considerations

### Token Usage

**With Persistence:**
- Larger context sent with each query (includes full conversation history)
- More tokens = Higher AWS Bedrock costs
- Longer conversations = More expensive queries

**Best Practices:**
1. Use `clear` periodically to start fresh sessions
2. Keep conversations focused on specific topics
3. Archive completed discussions
4. Typical cost impact: 10-30% increase for maintained conversations

### Storage

- JSON conversations are compact
- Average session: ~5-50 KB
- 1000 sessions: ~5-50 MB database storage
- Negligible storage cost

---

## Troubleshooting

### "Could not check for saved sessions"

**Cause:** Database table not created or connection issue

**Solution:**
```bash
# Create the table
mysql -u your_user -p your_db < database_script/create_conversation_history_table.sql

# Verify table exists
mysql -u your_user -p your_db -e "SHOW TABLES LIKE 'ai_conversation_history';"
```

### Session Not Resuming

**Check:**
1. Is `is_active = TRUE` for the session?
2. Is `portfolio_id` correct?
3. Check logs for error messages

```sql
-- View active sessions
SELECT id, portfolio_id, session_name, exchange_count, last_accessed_at 
FROM ai_conversation_history 
WHERE is_active = TRUE;
```

### Conversation History Lost

Sessions are auto-saved, but if data loss occurs:

1. Check `updated_at` timestamp - last successful save
2. Verify database connection was active
3. Review application logs for save errors

---

## Comparison: Before vs. After

### Before (In-Memory Only)

```
Session 1:
> What should I buy?
[AI recommends AAPL]
> exit

[Application restart]

Session 2:
> I bought AAPL as you suggested...
[AI: "I don't recall making that recommendation"]  ❌
```

### After (With Persistence)

```
Session 1:
> What should I buy?
[AI recommends AAPL]
> exit
💾 Conversation saved

[Application restart]

Session 2:
> ai_chat
Resume previous conversation? yes

> I bought AAPL as you suggested...
[AI: "Great! I recommended AAPL at $178 based on oversold RSI..."]  ✅
```

---

## Migration Notes

### For Existing Users

If you've been using the AI assistant before this feature:

1. **No action required** - feature is backward compatible
2. **First use** - Will start with empty conversation history
3. **Going forward** - All conversations will be saved automatically
4. **Old sessions** - Cannot recover pre-persistence conversations

### Data Migration

If you have conversation logs in files and want to import:

```python
# Custom migration script (example)
from data.conversation_history_dao import ConversationHistoryDAO
import json

dao = ConversationHistoryDAO(pool)

# Load from file
with open('old_conversation.json', 'r') as f:
    conv_data = json.load(f)

# Save to database
dao.save_conversation(
    portfolio_id=1,
    conversation_data=conv_data,
    session_name="Migrated Session",
    set_as_active=False
)
```

---

## Summary

The AI Conversation Persistence feature transforms the AI Portfolio Assistant from a stateless query tool into a true advisory relationship. Your conversations now have memory that persists across sessions, enabling:

- ✅ Continuous advisory discussions over days/weeks
- ✅ Tracking of recommendations and outcomes
- ✅ Building on previous conversations naturally
- ✅ True context awareness across application restarts

Simply run `ai_chat` and let the system manage session persistence automatically. Your advisory relationship with the AI now has memory!

---

*Last Updated: 2026-01-10*  
*Related Documents:*
- *AI_PORTFOLIO_ASSISTANT_ADVISORY_MODE.md*
- *LLM_CONVERSATION_USAGE_GUIDE.md*
- *LLM_CONSISTENCY_RECOMMENDATIONS.md*
