# Conversation History Validation Fix

## Problem

You encountered this error when using the AI Portfolio Assistant:

```
ValidationException: The model returned the following errors:
messages.90: Did not find 6 tool_result block(s) at the beginning of this message.
Messages following tool_use blocks must begin with a matching number of tool_result blocks.
```

## Root Cause

The AWS Bedrock Converse API has strict requirements for conversation structure:
- When the assistant requests tools (sends `tool_use` blocks), the next message MUST be from the user with exactly matching `tool_result` blocks
- If counts don't match or IDs are wrong, the API rejects the entire conversation

The error occurred because:
1. The AI assistant requested 6 tools to be executed
2. The conversation was auto-saved to database during or after tool execution
3. One of these scenarios happened:
   - Tool execution was interrupted mid-flight (only 5 of 6 tools completed)
   - An error occurred between adding the assistant's tool request and adding the tool results
   - The conversation was saved in an incomplete state
4. When the conversation was later loaded from database, it contained this corrupted state
5. The API rejected the conversation with the validation error you saw

## Solution Implemented

Added comprehensive conversation history validation in `data/llm_portfolio_analyzer.py`:

### 1. New Validation Method (`_validate_conversation_history`)

This method:
- Scans through conversation history messages
- Detects assistant messages that request tools
- Verifies the next message is a user message with matching tool results
- Checks:
  - ✅ Correct number of tool results (must match tool requests exactly)
  - ✅ Correct tool IDs (result IDs must match request IDs)
  - ✅ Correct message ordering (user message must follow assistant tool_use)
- If validation fails, truncates the conversation at that point to maintain a valid state
- Preserves all valid messages before the corruption

### 2. Integration Points

The validation is automatically applied at three key points:

**A. On Load (`load_conversation_from_db`)**
- Validates conversation when loading from database
- Automatically fixes corrupted conversations
- Updates database with cleaned version
- Logs what was removed

**B. On Manual Set (`set_conversation_history`)**
- Validates when setting conversation history manually
- Prevents setting invalid conversation state
- Warns if incomplete exchanges are removed

**C. On Auto-Save (`chat` method finally block)**
- Validates before saving to database
- Skips auto-save if conversation has incomplete tool exchanges
- Prevents persisting corrupted state

## How to Fix Existing Corrupted Conversations

### Option 1: Automatic Fix (Recommended)

The validation now runs automatically when you load any conversation. Just use the assistant normally:
- Next time you load a corrupted conversation, it will be automatically cleaned
- The cleaned version is saved back to the database
- You'll see log messages indicating what was fixed

### Option 2: Bulk Fix All Conversations

Run the utility script to clean all existing conversations:

```bash
python fix_conversation_history.py
```

This will:
- Load all active conversation sessions from the database
- Validate each one
- Fix any corrupted conversations
- Update the database
- Show a summary of what was fixed

### Option 3: Clear and Start Fresh

If you prefer to start with a clean slate for a specific portfolio:

```python
from data.llm_portfolio_analyzer import LLMPortfolioAnalyzer

analyzer = LLMPortfolioAnalyzer(pool)
analyzer.reset_conversation()  # Clears conversation history
```

## Verification

Run the test suite to verify the fix works correctly:

```bash
python test_conversation_validation_simple.py
```

This tests all scenarios:
- ✅ Valid conversations (no changes)
- ✅ Complete tool exchanges (preserved)
- ✅ Incomplete tool requests (removed)
- ✅ Tool count mismatches (your specific error - now fixed!)
- ✅ Tool ID mismatches (removed)
- ✅ Mixed valid/invalid (valid part preserved)

## What Changed in the Code

### Modified Files:
- `data/llm_portfolio_analyzer.py`:
  - Added `_validate_conversation_history()` method (lines ~420-520)
  - Updated `load_conversation_from_db()` to validate on load (lines ~660-690)
  - Updated `set_conversation_history()` to validate on set (lines ~700-715)
  - Updated `chat()` finally block to validate before auto-save (lines ~620-635)

### New Files:
- `fix_conversation_history.py` - Utility to bulk fix existing conversations
- `test_conversation_validation_simple.py` - Test suite for validation logic
- `CONVERSATION_VALIDATION_FIX.md` - This documentation

## Prevention

The fix prevents this error from happening again by:

1. **Never saving incomplete tool exchanges** - Auto-save now validates first
2. **Always loading valid conversations** - Corrupted data is fixed on load
3. **Comprehensive validation** - Checks tool counts, IDs, and message ordering
4. **Graceful degradation** - Truncates to last valid state instead of crashing

## Logging

You'll see helpful log messages when validation occurs:

```
WARNING: Incomplete tool exchange detected: assistant requested 6 tools but conversation ended. Truncating history.
INFO: Conversation history validated: removed 2 incomplete messages (kept 88 valid messages)
INFO: Updating database with validated conversation history
```

## Summary

Your error is now fixed! The validation system will:
- ✅ Detect and fix corrupted conversations automatically
- ✅ Prevent saving incomplete tool exchanges
- ✅ Maintain conversation integrity
- ✅ Log all validation actions for transparency

You can continue using the AI Portfolio Assistant normally. If you encounter this error again with an existing conversation, it will be automatically cleaned on the next load.
