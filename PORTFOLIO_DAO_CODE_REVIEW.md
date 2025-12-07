# Code Review: portfolio_dao.py

## Overview
The file has been **partially refactored** to use the connection pool pattern, but contains **critical bugs** that will cause runtime failures. The refactoring is incomplete and inconsistent.

## Critical Issues (Must Fix Immediately) 🔴

### 1. **Broken Connection Management - CRITICAL BUG**
**Lines: 20, 54, 158, 164, 170, 221, 233, 313, 336, 366, 407, 423, 450, 525, 547, 565**

**Problem**: `self.connection` is initialized as `None` (line 20) and **never assigned a value**, yet many methods try to use it directly:

```python
# Line 20 - connection is None
self.connection = None

# Line 54 - tries to commit on None!
self.connection.commit()  # ❌ AttributeError: 'NoneType' object has no attribute 'commit'

# Line 108 - uses None connection
cursor = self.connection.cursor(dictionary=True)  # ❌ Will fail!
```

**Impact**: Methods will crash with `AttributeError` when calling `.commit()`, `.cursor()`, `.rollback()` on `None`.

**Affected Methods**:
- `create_portfolio()` - line 54
- `update_cash_balance()` - lines 158, 164
- `recalculate_cash_balance()` - lines 221, 233
- `read_portfolio()` - line 280
- `update_portfolio()` - line 313
- `delete_portfolio()` - line 336
- `add_tickers_to_portfolio()` - lines 366, 407
- `remove_tickers_from_portfolio()` - lines 423, 450
- `log_cash_transaction()` - lines 525, 547
- `get_cash_transaction_history()` - lines 565, 579

### 2. **Inconsistent Connection Pattern - ARCHITECTURAL FLAW**
**Throughout the file**

The file uses **THREE different connection patterns**:

```python
# Pattern 1: Context manager (CORRECT) ✅
with self.get_connection() as connection:
    cursor = connection.cursor()
    # ... operations
    connection.commit()

# Pattern 2: Direct self.connection (BROKEN) ❌
cursor = self.connection.cursor()  # self.connection is None!
self.connection.commit()

# Pattern 3: Mixed (INCONSISTENT) ⚠️
with self.get_connection() as connection:
    cursor = connection.cursor()
    # ... operations
self.connection.commit()  # Wrong! Should be connection.commit()
```

**Methods Using Correct Pattern** (9 methods): ✅
- `create_portfolio()` - uses context manager
- `get_cash_balance()` - uses context manager
- `update_cash_balance()` - uses context manager
- `recalculate_cash_balance()` - uses context manager
- `update_portfolio()` - uses context manager
- `delete_portfolio()` - uses context manager
- Multiple get/check methods

**Methods Using Broken Pattern** (7 methods): ❌
- `get_historical_cash_balance()` - line 108
- `read_portfolio()` - line 280
- `log_cash_transaction()` - line 512
- `get_cash_transaction_history()` - line 554

**Methods Using Mixed Pattern** (5 methods): ⚠️
- `create_portfolio()` - context manager but commits on `self.connection`
- `update_cash_balance()` - same issue
- `add_tickers_to_portfolio()` - same issue
- `remove_tickers_from_portfolio()` - same issue
- `log_cash_transaction()` - same issue

### 3. **Wrong Logger Import**
**Line: 1**

```python
from asyncio.log import logger  # ❌ Wrong import!
```

**Problems**:
1. `asyncio.log` is for asyncio internal logging, not application logging
2. Logger is never configured, so errors won't be logged properly
3. Should use standard `logging` module

**Fix**:
```python
import logging
logger = logging.getLogger(__name__)
```

### 4. **LRU Cache on Instance Methods Accessing self.connection**
**Lines: 276, 468**

```python
@lru_cache(maxsize=32)
def read_portfolio(self, portfolio_id=None):
    cursor = self.connection.cursor(dictionary=True)  # ❌ Accesses None!
```

**Problems**:
1. `self.connection` is `None`, will crash
2. LRU cache on instance methods can cause memory leaks
3. Cache doesn't account for database changes

**Impact**: Any cached method will fail and the cache will hold stale data.

## Major Issues (High Priority) 🟠

### 5. **Incomplete Context Manager Commits**
**Lines: 54, 158, 313, 336, 366, 423**

Methods use context manager but commit on wrong connection:

```python
with self.get_connection() as connection:
    cursor = connection.cursor()
    cursor.execute(query, values)
    self.connection.commit()  # ❌ Should be: connection.commit()
```

### 6. **No Transaction Rollback in Context Manager**
**Lines: 25-46**

The `get_connection()` context manager doesn't handle rollback:

```python
@contextmanager
def get_connection(self):
    connection = None
    try:
        # ... get connection
        yield connection
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise  # ❌ No rollback before re-raising!
    finally:
        pass  # ❌ No connection close or return to pool!
```

**Should be**:
```python
@contextmanager
def get_connection(self):
    connection = None
    try:
        if self.current_connection is not None and self.current_connection.is_connected():
            connection = self.current_connection
            yield connection
        else:
            connection = self.pool.get_connection()
            self.current_connection = connection
            yield connection
    except mysql.connector.Error as e:
        if connection:
            connection.rollback()  # ✅ Rollback on error
        logger.error(f"Database connection error: {str(e)}")
        raise
    finally:
        pass  # Connection stays in current_connection for reuse
```

### 7. **Inconsistent Error Handling**
**Throughout**

Methods return different values on error:
- Some return `None`
- Some return `0.0`
- Some return `[]`
- Some return current value
- Some just print and continue

Example inconsistencies:
```python
def create_portfolio(...):
    except mysql.connector.Error as e:
        return None  # Returns None

def get_cash_balance(...):
    except mysql.connector.Error as e:
        return 0.0  # Returns 0.0

def get_tickers_in_portfolio(...):
    except mysql.connector.Error as e:
        return []  # Returns empty list
```

### 8. **Missing Cursor Cleanup**
**Multiple locations**

Cursors are created but not always closed:

```python
cursor = connection.cursor()
cursor.execute(query, values)
# ❌ No cursor.close()
```

**Best Practice**: Use try/finally or context manager for cursors.

## Medium Issues (Should Fix) 🟡

### 9. **Duplicate Security Check Logic**
**Lines: 353-362, 387-397**

Same ticker existence check repeated in multiple places.

### 10. **SQL Injection Risk - Low but Present**
**Line: 306**

Dynamic query building without proper validation:

```python
query = "UPDATE portfolio SET "
if name:
    query += "name = %s, "  # OK - uses parameterized query
```

While parameters are used, the dynamic building could be cleaner.

### 11. **Inefficient Multiple Database Calls**
**Lines: 352-365**

Loop calls `get_ticker_id()` for each ticker:

```python
for symbol in ticker_symbols:
    ticker_id = self.ticker_dao.get_ticker_id(symbol)  # ❌ N+1 query problem
```

Could batch this into single query.

### 12. **Print Statements Instead of Logging**
**Throughout**

Uses `print()` for errors instead of proper logging:

```python
print(f"Error creating portfolio: {e}")  # ❌ Should use logger.error()
```

### 13. **Unnecessary Connection Context in Some Methods**
**Lines: 488-500**

`is_ticker_in_portfolio()` wraps entire method in context manager but only needs it for the query.

## Minor Issues (Nice to Have) 🟢

### 14. **Missing Type Hints**
No type hints on method parameters or return values.

### 15. **Magic Strings**
Transaction types like 'deposit', 'withdrawal', 'buy' should be constants or enums.

### 16. **Mixed Date Handling**
Some methods use `datetime.datetime.now()`, others expect date objects, inconsistent.

### 17. **Docstring Quality**
Some methods have good docstrings, others have none. Inconsistent format.

## Refactoring Required

### Summary of Changes Needed:

1. **Remove `self.connection = None`** (line 20)
2. **Fix all methods** to use only the context manager pattern
3. **Remove all `self.connection` references** (replace with `connection` from context manager)
4. **Fix logger import** 
5. **Remove `@lru_cache`** from instance methods or fix properly
6. **Add rollback** to context manager exception handler
7. **Standardize error handling** (decide on consistent return values)
8. **Add cursor cleanup** (try/finally blocks)
9. **Replace `print()` with `logger.error()`**
10. **Add type hints**

## Risk Assessment

| Risk Level | Count | Impact |
|-----------|-------|---------|
| 🔴 Critical | 4 | **Application will crash on most operations** |
| 🟠 Major | 4 | Data corruption, connection leaks |
| 🟡 Medium | 6 | Performance issues, maintenance problems |
| 🟢 Minor | 4 | Code quality, readability |

## Testing Required

After refactoring, test:
1. ✅ Portfolio CRUD operations
2. ✅ Cash balance management
3. ✅ Ticker management
4. ✅ Transaction logging
5. ✅ Error handling paths
6. ✅ Concurrent operations
7. ✅ Connection pool behavior

## Recommended Action Plan

### Phase 1: Critical Fixes (Do First)
1. Remove `self.connection = None`
2. Fix all methods to use context manager exclusively
3. Fix logger import
4. Remove broken @lru_cache decorators

### Phase 2: Major Fixes
5. Add rollback to context manager
6. Standardize error handling
7. Add cursor cleanup

### Phase 3: Improvements
8. Replace print with logging
9. Add type hints
10. Optimize database calls

## Example: Fixed Method

**Before (Broken)**:
```python
def create_portfolio(self, name, description, initial_cash=0.0):
    try:
        with self.get_connection() as connection:
            cursor = connection.cursor()
            query = "INSERT INTO portfolio (...) VALUES (...)"
            cursor.execute(query, values)
            self.connection.commit()  # ❌ Wrong connection!
            portfolio_id = cursor.lastrowid
            return portfolio_id
    except mysql.connector.Error as e:
        print(f"Error: {e}")  # ❌ Should log
        return None
```

**After (Fixed)**:
```python
def create_portfolio(self, name: str, description: str, initial_cash: float = 0.0) -> Optional[int]:
    """Create a new portfolio."""
    try:
        with self.get_connection() as connection:
            cursor = connection.cursor()
            try:
                query = "INSERT INTO portfolio (name, description, date_added, cash_balance) VALUES (%s, %s, NOW(), %s)"
                cursor.execute(query, (name, description, initial_cash))
                connection.commit()  # ✅ Correct connection
                portfolio_id = cursor.lastrowid
                logger.info(f"Created portfolio {portfolio_id}: {name}")
                return portfolio_id
            finally:
                cursor.close()  # ✅ Always close cursor
    except mysql.connector.Error as e:
        logger.error(f"Error creating portfolio: {e}")  # ✅ Proper logging
        return None
```

## Conclusion

The file shows signs of incomplete refactoring. While the connection pool infrastructure is in place (lines 14-23), the actual implementation is severely broken. **The code will not run correctly in its current state** due to the `self.connection = None` issue affecting 15+ methods.

**Estimated Effort**: 4-6 hours to properly refactor and test.

**Priority**: **CRITICAL** - Should be fixed before any further development.
