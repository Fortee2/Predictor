# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
- `python launch.py` - Start enhanced CLI interface (recommended)
- `python launch.py --cli` - Start traditional command-line interface
- `python enhanced_cli.py` - Direct enhanced CLI entry point
- `python portfolio_cli.py` - Direct traditional CLI entry point

### Testing
- `python cash_management_test.py` - Test cash management functionality
- No automated test framework configured; testing is done through manual scripts

### Environment Setup
- Requires `.env` file with database credentials: DB_USER, DB_PASSWORD, DB_HOST, DB_NAME
- Run in Python virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

### Database Management
- MySQL database required
- Schema files in `database_script/` directory
- Main schema: `database_script/mysqlDb_build.sql`
- Additional tables: `create_*.sql` files for performance metrics, watchlists, etc.

## Architecture Overview

### Core Components

**Main Entry Points:**
- `launch.py` - Application launcher with CLI selection
- `enhanced_cli.py` - Enhanced GUI-like interface wrapper
- `portfolio_cli.py` - Traditional command-line interface

**Data Access Layer (data/ directory):**
- `portfolio_dao.py` - Portfolio management and cash operations
- `portfolio_transactions_dao.py` - Transaction recording/retrieval
- `ticker_dao.py` - Stock symbol management and data
- `data_retrieval_consolidated.py` - Yahoo Finance API integration with rate limiting
- `portfolio_value_calculator.py` - Real-time portfolio valuation

**Technical Analysis Modules:**
- `rsi_calculations.py` - Relative Strength Index calculations
- `moving_averages.py` - Moving average implementations
- `bollinger_bands.py` - Volatility band calculations
- `macd.py` - MACD indicator calculations
- `trend_analyzer.py` - Trend direction and strength analysis
- `news_sentiment_analyzer.py` - FinBERT-based sentiment analysis
- `options_data.py` - Options market data analysis

**Trading Strategy System (data/ directory):**
- `trading_strategy_dao.py` - Strategy creation and management
- `trading_signal_dao.py` - Signal generation and tracking
- `strategy_performance_dao.py` - Performance metrics and analytics
- `strategy_evaluator.py` - Signal evaluation and outcome tracking
- `strategy_backtester.py` - Historical strategy testing
- `strategy_templates.json` - Pre-configured strategy templates (RSI, MACD, MA Crossover, etc.)

**Enhanced CLI Components (enhanced_cli/ directory):**
- `main.py` - Core CLI application and menu system
- `portfolio_views.py` - Portfolio management interfaces
- `analysis_views.py` - Technical analysis displays
- `transaction_views.py` - Transaction management interfaces
- `cash_management_views.py` - Cash operation interfaces
- `trading_strategy_views.py` - Trading strategy management and signal generation
- `ui_components.py` - Reusable UI elements using Rich library
- `formatters.py` - Data formatting utilities

### Key Design Patterns

**Database Connection Management:**
- All DAO classes follow consistent pattern: constructor takes DB credentials, `open_connection()` and `close_connection()` methods
- Environment variables used for DB configuration via python-dotenv

**CLI Architecture:**
- Traditional CLI uses argparse with subcommands
- Enhanced CLI uses Rich library for improved UX with menus and tables
- Both interfaces share same underlying DAO layer

**Technical Analysis Integration:**
- Each indicator has dedicated class/module
- Analysis results formatted consistently across both CLI interfaces
- Real-time data retrieval with Yahoo Finance integration

### Configuration

**User Configuration:**
- `user_config.json` - User preferences for UI, analysis parameters, and system settings
- Default analysis periods: MA=20 days, RSI=14 days, MACD=(12,26,9)

**System Configuration:**
- Environment variables for database connection
- Logging configured to `analysis.log`
- Chart outputs saved to configurable directory

### Data Flow

1. **Portfolio Creation** → DAO layer → MySQL database
2. **Data Retrieval** → Yahoo Finance API → Consolidated data retrieval → Database storage
3. **Technical Analysis** → Historical data from DB → Indicator calculations → Formatted results
4. **Transaction Processing** → Validation → Database storage → Cash balance updates
5. **Trading Strategies** → Strategy evaluation → Signal generation → Performance tracking → Backtesting

### Important Implementation Notes

- **Rate Limiting**: Yahoo Finance API calls are rate-limited and randomized in `data_retrieval_consolidated.py`
- **Cash Management**: Recently consolidated in `portfolio_dao.py` (some duplicate functions may exist in `ticker_dao.py`)
- **Error Handling**: Database connection errors handled at DAO level
- **Rich UI**: Enhanced CLI uses Rich library extensively for formatted output, tables, and progress indicators
- **News Analysis**: Uses transformers library with FinBERT model for sentiment analysis
- **Options Data**: Implied volatility and put/call ratio analysis for market sentiment
- **Trading Strategies**: Automated signal generation using anchor indicators with optional confirmations, template-based creation, performance tracking, and backtesting capabilities

### Development Workflow

1. **Adding New Features**: Extend DAO layer first, then add CLI interfaces
2. **Technical Indicators**: Create new module in data/ directory, integrate with analysis views
3. **Database Changes**: Add schema files to database_script/ directory
4. **CLI Enhancements**: Use Rich library components from ui_components.py for consistency

### File Organization

- Root level: Main entry points and configuration
- `data/` - All data access and business logic
- `enhanced_cli/` - Enhanced user interface components
- `database_script/` - Database schema and migration scripts
- `docs/` - User documentation and guides
- `MCP/` - Model Context Protocol integration (if applicable)

### Documentation

- **User Guides:**
  - `README.md` - System overview, installation, and basic usage
  - `swing_trading_guide.md` - Technical analysis and swing trading with Predictor
  - `docs/TRADING_STRATEGIES_GUIDE.md` - Comprehensive guide to trading strategies system
  - `docs/FIFO_COST_BASIS_IMPLEMENTATION.md` - Cost basis calculation details

- **Development Documentation:**
  - `CLAUDE.md` (this file) - Development guidance and architecture overview
  - `enhanced_cli/README.md` - Enhanced CLI architecture and command pattern
  - Various `*_FIXES.md`, `*_GUIDE.md`, and `*_PLAN.md` files - Implementation notes and technical details

This system is designed for stock portfolio management with comprehensive technical analysis capabilities, supporting both simple command-line usage and rich interactive interfaces.