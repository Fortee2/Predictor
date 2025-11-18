# Database Connection Pool Refactoring Plan

## Executive Summary

This document outlines the complete refactoring plan to migrate all Data Access Objects (DAOs) to use the `DatabaseConnectionPool` from `data/utility.py`. We are taking a **clean break approach** - removing the `open_connection()` and `close_connection()` anti-pattern methods entirely.

## Status: Phase 1 - COMPLETED ✅

### ✅ Completed
- **ticker_dao.py** - Fully refactored, no backward compatibility methods

### ✅ Already Using Connection Pool (2 DAOs)
1. **moving_averages.py** - Reference implementation
2. **stochastic_oscillator.py** - Reference implementation

## Why Connection Pooling?

### Current Anti-Pattern
```python
# OLD WAY - Creates new connection for each DAO instance
def __init__(self, user, password, host, database):
    self.connection = mysql.connector.connect(...)  # ❌ Single connection per DAO
    
# Manually managing connections
dao.open_connection()   # ❌ Defeats pooling purpose
dao.close_connection()  # ❌ Unnecessary with pooling
```

### Connection Pool Benefits
```python
# NEW WAY - Uses shared connection pool
def __init__(self, user, password, host, database):
    self.pool = DatabaseConnectionPool(...)  # ✅ Shared pool across DAOs
    
# Automatic connection management
with self.get_connection() as connection:  # ✅ Get from pool
    cursor = connection.cursor()
    # ... database operations
    cursor.close()
# Connection automatically returned to pool
```

**Benefits:**
- ✅ Prevents connection exhaustion
- ✅ Improves performance (no connection setup overhead)
- ✅ Better resource management
- ✅ Thread-safe operations
- ✅ Automatic connection cleanup
- ✅ Reduces database load

## Standard Refactoring Pattern - Dependency Injection

**NEW IMPROVED PATTERN**: Pass the DatabaseConnectionPool to each DAO constructor instead of database credentials.

### Benefits of Dependency Injection:
- ✅ **Explicit Shared Resource** - Makes it clear all DAOs share the same connection pool
- ✅ **Fewer Parameters** - No need to pass user/password/host/database to each DAO
- ✅ **Better Testability** - Easy to inject mock pools for testing
- ✅ **Follows Best Practices** - Proper dependency injection
- ✅ **Centralized Configuration** - Pool configuration happens once at application startup

### Application-Level Pool Initialization

```python
# In your main application file (e.g., portfolio_cli.py, data_retrieval_consolidated.py)
from data.utility import DatabaseConnectionPool
from data.ticker_dao import TickerDao
from data.portfolio_dao import PortfolioDAO
# ... other imports

# Initialize the connection pool ONCE at application startup
db_pool = DatabaseConnectionPool(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    pool_size=20
)

# Pass the pool to all DAOs
ticker_dao = TickerDao(db_pool)
portfolio_dao = PortfolioDAO(db_pool)
transactions_dao = PortfolioTransactionsDAO(db_pool)
# ... etc
```

### DAO Pattern

```python
import logging
from contextlib import contextmanager
import mysql.connector
from data.utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)

class SomeDAO:
    def __init__(self, pool: DatabaseConnectionPool):
        """
        Initialize DAO with a shared database connection pool.
        
        Args:
            pool: DatabaseConnectionPool instance shared across all DAOs
        """
        self.pool = pool
        self.current_connection = None
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
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
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            pass
    
    def some_database_operation(self):
        """Example database operation using connection pool."""
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                
                # Execute queries
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
                
                # Commit if needed
                connection.commit()
                
                cursor.close()
                return results
        except mysql.connector.Error as err:
            logger.error(f"Database error: {err}")
            return None
```

## Phase 2: High-Priority Portfolio DAOs (7 DAOs)

These DAOs manage core portfolio functionality and have dependencies on ticker_dao.

### 2.1 portfolio_dao.py
- **Status**: Not Started
- **Priority**: HIGH
- **Dependencies**: ticker_dao ✅, portfolio_transactions_dao
- **Key Changes**:
  - Remove `self.connection = mysql.connector.connect()` from `__init__`
  - Add connection pool initialization
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`
  - Remove `self.ticker_dao.open_connection()` call (line ~47)
  - Remove `self.ticker_dao.close_connection()` call (line ~450)

### 2.2 portfolio_transactions_dao.py
- **Status**: Not Started
- **Priority**: HIGH
- **Key Changes**:
  - Remove `self.connection = mysql.connector.connect()` from `__init__`
  - Remove `self.open_connection()` call in `__init__`
  - Add connection pool initialization
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

### 2.3 portfolio_value_calculator.py
- **Status**: Not Started
- **Priority**: HIGH
- **Key Changes**:
  - Remove `self.connection = mysql.connector.connect()` from `__init__`
  - Remove `self.open_connection()` call in `__init__`
  - Add connection pool initialization
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

### 2.4 portfolio_value_service.py
- **Status**: Not Started
- **Priority**: HIGH
- **Key Changes**:
  - Remove `self.connection = mysql.connector.connect()` from `__init__`
  - Remove `self.open_connection()` call in `__init__`
  - Add connection pool initialization
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

### 2.5 optimized_portfolio_recalculator.py
- **Status**: Not Started
- **Priority**: HIGH
- **Key Changes**:
  - Remove `self.connection = mysql.connector.connect()` from `__init__`
  - Remove `self.open_connection()` call in `__init__`
  - Add connection pool initialization
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`
  - Remove `self.calculator.close_connection()` call (line ~162)

### 2.6 multi_timeframe_analyzer.py
- **Status**: Not Started
- **Priority**: HIGH
- **Key Changes**:
  - Remove `self.connection = mysql.connector.connect()` from `__init__`
  - Remove `self.open_connection()` call in `__init__`
  - Add connection pool initialization
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

### 2.7 watch_list_dao.py
- **Status**: Not Started
- **Priority**: HIGH
- **Dependencies**: ticker_dao ✅
- **Key Changes**:
  - Remove `self.connection = mysql.connector.connect()` from `__init__`
  - Add connection pool initialization
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`
  - Remove `self.ticker_dao.open_connection()` call (line ~46)
  - Remove `self.ticker_dao.close_connection()` call (line ~289)

## Phase 3: Technical Analysis Indicators (6 DAOs)

### 3.1 rsi_calculations.py
- **Status**: Not Started
- **Priority**: MEDIUM
- **Pattern**: Uses `open_connection()` method
- **Key Changes**:
  - Remove `open_connection()` method
  - Add connection pool initialization in `__init__`
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

### 3.2 trend_analyzer.py
- **Status**: Not Started
- **Priority**: MEDIUM
- **Pattern**: Uses `open_connection()` method
- **Key Changes**:
  - Remove `open_connection()` method
  - Add connection pool initialization in `__init__`
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`
  - Remove manual `self.open_connection()` calls in methods

### 3.3 bollinger_bands.py
- **Status**: Not Started
- **Priority**: MEDIUM
- **Pattern**: Uses `open_connection()` method
- **Key Changes**:
  - Remove `open_connection()` method
  - Add connection pool initialization in `__init__`
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

### 3.4 macd.py
- **Status**: Not Started
- **Priority**: MEDIUM
- **Pattern**: Uses `open_connection()` method
- **Key Changes**:
  - Remove `open_connection()` method
  - Add connection pool initialization in `__init__`
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`
  - Remove manual `self.open_connection()` calls in methods

### 3.5 options_data.py
- **Status**: Not Started
- **Priority**: MEDIUM
- **Pattern**: Uses `open_connection()` method
- **Key Changes**:
  - Remove `open_connection()` method
  - Add connection pool initialization in `__init__`
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

### 3.6 comprehensive_performance_formatter.py
- **Status**: Review Needed
- **Priority**: LOW
- **Note**: Check if this file actually uses database connections

## Phase 4: External Data Sources (2 DAOs)

### 4.1 news_sentiment_dao.py
- **Status**: Not Started
- **Priority**: LOW
- **Pattern**: Uses `open_connection()` method
- **Key Changes**:
  - Remove `open_connection()` method
  - Add connection pool initialization in `__init__`
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

### 4.2 fundamental_data_dao.py
- **Status**: Not Started
- **Priority**: LOW
- **Pattern**: Uses `open_connection()` method
- **Key Changes**:
  - Remove `open_connection()` method
  - Add connection pool initialization in `__init__`
  - Add `get_connection()` context manager
  - Wrap all DB operations in `with self.get_connection() as connection:`

## Phase 5: Application Code Cleanup

After all DAOs are refactored, remove all `open_connection()` and `close_connection()` calls from application code.

### 5.1 Core CLI Files (Remove 10+ connection calls each)
- **portfolio_cli.py** - Remove 10 `open_connection()` calls
- **watchlist_cli.py** - Remove 10 `open_connection()` calls
- **ticker_cli.py** - Remove 1 `open_connection()` call

### 5.2 Data Consolidation Layer
- **data/data_retrieval_consolidated.py** - Remove 9 `open_connection()` calls

### 5.3 LLM Integration
- **data/llm_integration.py** 
  - Remove 4 `open_connection()` calls
  - Remove 10 `close_connection()` calls in cleanup methods

### 5.4 Enhanced CLI Views
- **enhanced_cli/comprehensive_analysis_views.py** - Remove 5 `close_connection()` calls
- **enhanced_cli/portfolio_views.py** - Remove 1 `close_connection()` call
- **enhanced_cli/transaction_views.py** - Remove 1 `close_connection()` call
- **enhanced_cli/llm_export_views.py** - Remove 1 `close_connection()` call

### 5.5 Utility Scripts
- **rebuild_cash_history.py** - Remove `open_connection()` and `close_connection()` calls
- **recalculate_cash.py** - Remove `open_connection()` and `close_connection()` calls
- **troubleshoot_portfolio_spike.py** - Remove `close_connection()` call
- **import_fidelity_history.py** - Remove 10 `close_connection()` calls

### 5.6 Test Files
- **test_stochastic_implementation.py** - Remove multiple connection calls
- **test_universal_value_service.py** - Remove 3 `open_connection()` and 3 `close_connection()` calls
- **cash_management_test.py** - Remove `open_connection()` and `close_connection()` calls

### 5.7 News Sentiment Analyzer
- **data/news_sentiment_analyzer.py** - Remove `open_connection()` and `close_connection()` calls

## Implementation Guidelines

### For Each DAO Refactoring:

1. **Backup**: Create a git branch or backup before changes
2. **Add Imports**:
   ```python
   import logging
   from contextlib import contextmanager
   from data.utility import DatabaseConnectionPool
   
   logger = logging.getLogger(__name__)
   ```

3. **Update `__init__`** to accept pool parameter:
   ```python
   def __init__(self, pool: DatabaseConnectionPool):
       """
       Initialize DAO with a shared database connection pool.
       
       Args:
           pool: DatabaseConnectionPool instance shared across all DAOs
       """
       self.pool = pool
       self.current_connection = None
   ```
   - Remove `self.connection = mysql.connector.connect(...)`
   - Remove any `self.open_connection()` calls
   - Remove `user, password, host, database` parameters
   - Change to accept `pool: DatabaseConnectionPool` parameter

4. **Add `get_connection()` Context Manager**:
   ```python
   @contextmanager
   def get_connection(self):
       """Context manager for database connections."""
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
           logger.error(f"Database connection error: {str(e)}")
           raise
       finally:
           pass
   ```

5. **Wrap Database Operations**:
   ```python
   # OLD
   cursor = self.connection.cursor()
   cursor.execute(query)
   self.connection.commit()
   
   # NEW
   with self.get_connection() as connection:
       cursor = connection.cursor()
       cursor.execute(query)
       connection.commit()
       cursor.close()
   ```

6. **Remove Old Methods**: Delete `open_connection()` and `close_connection()` if they exist

7. **Test**: Ensure all database operations still work correctly

### For Application Code Cleanup:

1. **Search and Remove**: Find all instances of:
   - `dao.open_connection()`
   - `dao.close_connection()`

2. **Simply Delete**: These calls are no longer needed with connection pooling

3. **Test**: Verify application still works correctly

## Testing Strategy

### Unit Testing
- Test each refactored DAO individually
- Verify all CRUD operations work correctly
- Check connection pool is properly utilized

### Integration Testing
- Test CLI applications (portfolio_cli.py, watchlist_cli.py, ticker_cli.py)
- Verify data retrieval and analysis functions
- Test transaction management

### Performance Testing
- Monitor connection pool usage
- Verify no connection leaks
- Measure performance improvements

## Success Criteria

- ✅ All 15 DAOs refactored to use connection pool
- ✅ All application code cleaned of manual connection management
- ✅ All tests passing
- ✅ No connection leaks
- ✅ Improved application performance
- ✅ Cleaner, more maintainable codebase

## Rollback Plan

If issues arise:
1. Use git to revert to previous commit
2. Address issues in refactored code
3. Re-test and retry

## Timeline Estimate

- **Phase 1**: ✅ Completed (ticker_dao.py)
- **Phase 2**: 4-6 hours (7 high-priority DAOs)
- **Phase 3**: 3-4 hours (6 technical analysis DAOs)
- **Phase 4**: 1-2 hours (2 external data DAOs)
- **Phase 5**: 2-3 hours (application code cleanup)
- **Testing**: 2-3 hours (comprehensive testing)

**Total Estimated Time**: 12-18 hours

## Next Steps

1. ✅ Complete ticker_dao.py refactoring
2. Begin Phase 2 with portfolio_transactions_dao.py (no dependencies)
3. Then refactor portfolio_dao.py (depends on ticker_dao ✅ and portfolio_transactions_dao)
4. Continue systematically through each phase
5. Clean up application code after all DAOs are complete
6. Comprehensive testing

## Notes

- Connection pooling is a singleton - all DAOs share the same pool
- Pool size is currently 20 connections (configurable in utility.py)
- Context managers automatically handle commit/rollback
- No need to manually manage connection lifecycle
- Logger should be configured for each DAO module
