# Database Connection Pool - Usage Examples

This document shows how to use the refactored DAOs with the dependency injection pattern.

## Basic Setup Pattern

### 1. Application-Level Pool Initialization

Initialize the connection pool **once** at your application's entry point:

```python
# In portfolio_cli.py, watchlist_cli.py, or any main application file
import os
from dotenv import load_dotenv
from data.utility import DatabaseConnectionPool
from data.ticker_dao import TickerDao
from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
# ... other DAO imports

# Load environment variables
load_dotenv()

# Initialize the connection pool ONCE at application startup
db_pool = DatabaseConnectionPool(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    pool_size=20  # Optional, defaults to 20
)

# Pass the same pool instance to ALL DAOs
ticker_dao = TickerDao(db_pool)
portfolio_dao = PortfolioDAO(db_pool)
transactions_dao = PortfolioTransactionsDAO(db_pool)
rsi_calc = RSICalculations(db_pool)
moving_avg = moving_averages(db_pool)
# ... etc for all DAOs
```

## Before vs After Comparison

### OLD WAY (Current Code)
```python
# Each DAO gets separate credentials
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")

# Each DAO creates its own connection
ticker_dao = TickerDao(db_user, db_password, db_host, db_name)
portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)

# Manually manage connections (anti-pattern!)
ticker_dao.open_connection()
portfolio_dao.open_connection()
transactions_dao.open_connection()

# ... use DAOs ...

# Manually close connections (tedious and error-prone!)
ticker_dao.close_connection()
portfolio_dao.close_connection()
transactions_dao.close_connection()
```

### NEW WAY (Refactored Code)
```python
# Initialize pool ONCE
db_pool = DatabaseConnectionPool(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME")
)

# Pass pool to all DAOs
ticker_dao = TickerDao(db_pool)
portfolio_dao = PortfolioDAO(db_pool)
transactions_dao = PortfolioTransactionsDAO(db_pool)

# No open_connection() or close_connection() calls needed!
# Just use the DAOs directly - they handle connections automatically

# ... use DAOs ...

# No cleanup needed - pool manages connections automatically
```

## Complete Application Example

### Example: portfolio_cli.py Refactored

```python
#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from data.utility import DatabaseConnectionPool
from data.ticker_dao import TickerDao
from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.rsi_calculations import rsi_calculations
from data.moving_averages import moving_averages
from data.macd import MACD
from data.trend_analyzer import TrendAnalyzer
from data.fundamental_data_dao import FundamentalDataDAO
from data.portfolio_value_calculator import PortfolioValueCalculator
from data.watch_list_dao import WatchListDAO
from data.stochastic_oscillator import StochasticOscillator

class PortfolioCLI:
    def __init__(self):
        """Initialize the Portfolio CLI with all necessary DAOs."""
        # Load environment variables
        load_dotenv()
        
        # Initialize connection pool ONCE
        self.db_pool = DatabaseConnectionPool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME")
        )
        
        # Initialize all DAOs with the shared pool
        self.ticker_dao = TickerDao(self.db_pool)
        self.portfolio_dao = PortfolioDAO(self.db_pool)
        self.transactions_dao = PortfolioTransactionsDAO(self.db_pool)
        self.rsi_calc = rsi_calculations(self.db_pool)
        self.moving_avg = moving_averages(self.db_pool)
        self.macd_analyzer = MACD(self.db_pool)
        self.trend_analyzer = TrendAnalyzer(self.db_pool)
        self.fundamental_dao = FundamentalDataDAO(self.db_pool)
        self.value_calculator = PortfolioValueCalculator(self.db_pool)
        self.watch_list_dao = WatchListDAO(self.db_pool)
        self.stochastic_analyzer = StochasticOscillator(self.db_pool)
        
        # No open_connection() calls needed!
    
    def create_portfolio(self, name, description):
        """Create a new portfolio."""
        # Just use the DAO - it handles connections automatically
        portfolio_id = self.portfolio_dao.create_portfolio(name, description)
        print(f"Created portfolio {portfolio_id}: {name}")
        return portfolio_id
    
    def add_transaction(self, portfolio_id, ticker_symbol, quantity, price, date):
        """Add a transaction to a portfolio."""
        # Get ticker ID
        ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
        
        if not ticker_id:
            print(f"Ticker {ticker_symbol} not found")
            return None
        
        # Add transaction - DAO handles connection automatically
        transaction_id = self.transactions_dao.insert_transaction(
            portfolio_id=portfolio_id,
            ticker_id=ticker_id,
            transaction_type='BUY',
            quantity=quantity,
            price=price,
            transaction_date=date
        )
        
        print(f"Added transaction {transaction_id}")
        return transaction_id
    
    # ... other methods ...
    
    def cleanup(self):
        """
        Optional cleanup method.
        Note: Not required with connection pooling, but can be used
        if you want to explicitly close the pool (rarely needed).
        """
        # Connection pool is a singleton and manages its own cleanup
        # No need to call close_connection() on individual DAOs
        pass

def main():
    """Main entry point."""
    cli = PortfolioCLI()
    
    # Use the CLI
    portfolio_id = cli.create_portfolio("My Portfolio", "Test portfolio")
    cli.add_transaction(portfolio_id, "AAPL", 10, 150.00, "2024-01-15")
    
    # No cleanup needed - pool manages connections automatically
    # But if you want to be explicit:
    # cli.cleanup()

if __name__ == "__main__":
    main()
```

## Data Consolidation Layer Example

### Example: data_retrieval_consolidated.py Refactored

```python
from data.utility import DatabaseConnectionPool
from data.ticker_dao import TickerDao
from data.rsi_calculations import rsi_calculations
from data.portfolio_dao import PortfolioDAO
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
# ... other imports

class DataRetrieval:
    def __init__(self, user, password, host, database):
        """Initialize with database credentials."""
        # Initialize connection pool
        self.db_pool = DatabaseConnectionPool(user, password, host, database)
        
        # Initialize all DAOs with the shared pool
        self.dao = TickerDao(self.db_pool)
        self.rsi = rsi_calculations(self.db_pool)
        self.portfolio_dao = PortfolioDAO(self.db_pool)
        self.portfolio_transactions_dao = PortfolioTransactionsDAO(self.db_pool)
        self.watch_list_dao = WatchListDAO(self.db_pool)
        self.fundamental_dao = FundamentalDataDAO(self.db_pool)
        self.macd_analyzer = MACD(self.db_pool)
        self.moving_avg = moving_averages(self.db_pool)
        self.stochastic_analyzer = StochasticOscillator(self.db_pool)
        
        # No open_connection() calls needed!
    
    def get_ticker_with_analysis(self, symbol):
        """Get ticker data with full technical analysis."""
        # All DAOs use the shared pool automatically
        ticker_id = self.dao.get_ticker_id(symbol)
        
        if not ticker_id:
            return None
        
        # Get data from multiple DAOs - all using same pool
        ticker_data = self.dao.get_ticker_data(ticker_id)
        rsi_data = self.rsi.calculate_rsi(ticker_id)
        ma_data = self.moving_avg.update_moving_averages(ticker_id, 20)
        macd_data = self.macd_analyzer.calculate_macd(ticker_id)
        
        return {
            'ticker': ticker_data,
            'rsi': rsi_data,
            'moving_average': ma_data,
            'macd': macd_data
        }
```

## Testing Example

### Unit Test with Mock Pool

```python
import unittest
from unittest.mock import Mock, MagicMock
from data.ticker_dao import TickerDao

class TestTickerDao(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock connection pool
        self.mock_pool = Mock()
        self.mock_connection = MagicMock()
        self.mock_pool.get_connection.return_value = self.mock_connection
        
        # Initialize DAO with mock pool
        self.dao = TickerDao(self.mock_pool)
    
    def test_get_ticker_id(self):
        """Test getting ticker ID."""
        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (123,)
        self.mock_connection.cursor.return_value = mock_cursor
        
        # Call the method
        ticker_id = self.dao.get_ticker_id("AAPL")
        
        # Verify
        self.assertEqual(ticker_id, 123)
        self.mock_pool.get_connection.assert_called()
        mock_cursor.execute.assert_called_once()
```

## Key Takeaways

### ✅ DO:
- Initialize `DatabaseConnectionPool` **once** at application startup
- Pass the **same pool instance** to all DAOs
- Let DAOs handle connections automatically via context managers
- Use the DAOs directly - no manual connection management

### ❌ DON'T:
- Create multiple `DatabaseConnectionPool` instances (it's a singleton anyway)
- Call `open_connection()` or `close_connection()` (removed in refactored code)
- Pass database credentials to individual DAOs
- Manually manage connection lifecycle

## Benefits Summary

1. **Simpler Code**: No more manual connection management
2. **Better Performance**: Connection reuse eliminates setup overhead
3. **Resource Efficiency**: Controlled number of connections (pool size)
4. **Thread Safety**: Pool handles concurrent access automatically
5. **Easier Testing**: Simple to inject mock pools
6. **Cleaner Architecture**: Clear separation of concerns
7. **Less Error-Prone**: No forgetting to close connections
