# PortfolioCLI Refactoring Example

## Application Entry Points

Your application has two entry points:

1. **launch.py** - Main launcher that can start either:
   - Traditional CLI mode (`portfolio_cli.py`)
   - Enhanced GUI mode (`enhanced_cli/main.py`)

2. **enhanced_cli/main.py** - Creates a `PortfolioCLI` instance (line 20)

3. **PortfolioCLI** (`portfolio_cli.py`) - **This is where all DAOs are instantiated**

## The Key File to Refactor: portfolio_cli.py

The `PortfolioCLI.__init__()` method (lines 23-88) is where you need to implement the connection pool pattern.

## Current Code (Lines 23-88)

```python
class PortfolioCLI:
    def __init__(self):
        # Initialize configuration
        self.config = Config()
        db_config = self.config.get_database_config()
        
        # Get database credentials from config
        db_user = db_config['user']
        db_password = db_config['password']
        db_host = db_config['host']
        db_name = db_config['database']

        # Initialize ticker_dao first since it's needed by BollingerBandAnalyzer
        self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)

        # Initialize DAOs with database credentials - OLD PATTERN
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        # ... 10 more DAOs with same pattern ...

        # Open database connections - ANTI-PATTERN!
        self.portfolio_dao.open_connection()
        self.transactions_dao.open_connection()
        self.ticker_dao.open_connection()
        # ... 8 more open_connection() calls ...
```

## Refactored Code with Connection Pool

```python
from data.utility import DatabaseConnectionPool

class PortfolioCLI:
    def __init__(self):
        # Initialize configuration
        self.config = Config()
        db_config = self.config.get_database_config()
        
        # Initialize connection pool ONCE - NEW PATTERN
        self.db_pool = DatabaseConnectionPool(
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            database=db_config['database'],
            pool_size=20  # Optional, already defaults to 20
        )

        # Pass the pool to all DAOs - MUCH CLEANER!
        self.ticker_dao = TickerDao(self.db_pool)
        self.portfolio_dao = PortfolioDAO(self.db_pool)
        self.transactions_dao = PortfolioTransactionsDAO(self.db_pool)
        self.rsi_calc = rsi_calculations(self.db_pool)
        self.moving_avg = moving_averages(self.db_pool)
        self.bb_analyzer = BollingerBandAnalyzer(self.ticker_dao)  # Still takes ticker_dao
        self.fundamental_dao = FundamentalDataDAO(self.db_pool)
        self.macd_analyzer = MACD(self.db_pool)
        self.news_analyzer = NewsSentimentAnalyzer(self.db_pool)
        self.data_retrieval = DataRetrieval(self.db_pool)
        self.value_calculator = PortfolioValueCalculator(self.db_pool)
        self.value_service = PortfolioValueService(self.db_pool)
        self.options_analyzer = OptionsData(self.db_pool)
        self.trend_analyzer = TrendAnalyzer(self.db_pool)
        self.watch_list_dao = WatchListDAO(self.db_pool)
        self.stochastic_analyzer = StochasticOscillator(self.db_pool)

        # NO open_connection() calls needed! - CLEAN!

        # Initialize shared analysis metrics with stochastic support
        self.shared_metrics = SharedAnalysisMetrics(
            self.rsi_calc,
            self.moving_avg,
            self.bb_analyzer,
            self.macd_analyzer,
            self.fundamental_dao,
            self.news_analyzer,
            self.options_analyzer,
            self.trend_analyzer,
            stochastic_analyzer=self.stochastic_analyzer,
        )
```

## What Changed?

### Before (Old Pattern)
```python
# Get credentials
db_user = db_config['user']
db_password = db_config['password']
db_host = db_config['host']
db_name = db_config['database']

# Create each DAO with 4 parameters
self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)
self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
# ... repeat 12 more times

# Manually open connections (anti-pattern)
self.ticker_dao.open_connection()
self.portfolio_dao.open_connection()
# ... repeat 12 more times
```

### After (New Pattern)
```python
# Create pool ONCE
self.db_pool = DatabaseConnectionPool(
    user=db_config['user'],
    password=db_config['password'],
    host=db_config['host'],
    database=db_config['database']
)

# Pass pool to each DAO (only 1 parameter!)
self.ticker_dao = TickerDao(self.db_pool)
self.portfolio_dao = PortfolioDAO(self.db_pool)
# ... repeat 12 more times

# NO open_connection() or close_connection() calls!
```

## Side-by-Side Comparison

| Aspect | Old Pattern | New Pattern |
|--------|------------|-------------|
| **Parameters per DAO** | 4 (user, password, host, database) | 1 (pool) |
| **Lines of code** | ~30 lines for initialization | ~17 lines for initialization |
| **Manual connection management** | Yes - 14 open_connection() calls | No - automatic |
| **Connection reuse** | No - each DAO creates its own | Yes - all DAOs share pool |
| **Thread safety** | No | Yes - pool handles it |
| **Testability** | Hard - must mock 4 params per DAO | Easy - inject mock pool |
| **Resource efficiency** | Poor - unlimited connections | Good - controlled pool of 20 |

## Special Cases

### DataRetrieval Class

The `DataRetrieval` class also needs updating since it creates its own DAO instances:

**Before:**
```python
class DataRetrieval:
    def __init__(self, pool: DatabaseConnectionPool)::
        # Creates its own DAOs with credentials
        self.dao = TickerDao(user, password, host, database)
        self.rsi = rsi_calculations(user, password, host, database)
        # ... etc
```

**After:**
```python
class DataRetrieval:
    def __init__(self, pool: DatabaseConnectionPool):
        # Uses shared pool
        self.dao = TickerDao(pool)
        self.rsi = rsi_calculations(pool)
        # ... etc
```

### BollingerBandAnalyzer

Note that `BollingerBandAnalyzer` takes a `ticker_dao` instance, not database credentials or a pool. This is correct and doesn't need to change:

```python
self.bb_analyzer = BollingerBandAnalyzer(self.ticker_dao)  # Stays the same
```

## Implementation Steps

1. **Add import** at the top of `portfolio_cli.py`:
   ```python
   from data.utility import DatabaseConnectionPool
   ```

2. **Replace lines 30-35** (credential extraction and DAO initialization):
   - Remove the 4 individual db_ variables
   - Create `self.db_pool = DatabaseConnectionPool(...)`
   - Update all DAO instantiations to pass `self.db_pool`

3. **Delete lines 78-88** (all the `open_connection()` calls)

4. **Test thoroughly** - ensure all functionality still works

## Benefits Summary

✅ **Simpler code**: 13 fewer lines, 1 parameter instead of 4 per DAO  
✅ **No manual connection management**: Pool handles everything  
✅ **Better performance**: Connection reuse eliminates overhead  
✅ **Resource efficiency**: Controlled pool size prevents exhaustion  
✅ **Thread safety**: Built into connection pool  
✅ **Easier testing**: Inject a single mock pool  
✅ **Cleaner architecture**: Clear dependency injection pattern  

## Next Steps After PortfolioCLI

Once `portfolio_cli.py` is refactored, you'll need to update:

1. All 15 DAO classes to accept `pool` parameter (ticker_dao.py already done ✅)
2. `data_retrieval_consolidated.py` to use the new pattern
3. Remove all remaining `open_connection()` and `close_connection()` calls across the codebase

See `DATABASE_CONNECTION_POOL_REFACTORING_PLAN.md` for the complete plan.
