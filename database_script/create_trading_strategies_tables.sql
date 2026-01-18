-- ============================================================================
-- Trading Strategies System - Database Schema
-- ============================================================================
-- This script creates the database tables for the anchor-metric trading
-- signal system. It includes three main tables:
--   1. trading_strategies: Strategy definitions with anchor and confirmation indicators
--   2. trading_signals: Generated signals with indicator snapshots
--   3. strategy_performance_metrics: Performance tracking and analytics
--
-- Dependencies: Requires existing tables: portfolio, tickers, watch_lists,
--               ai_recommendations, portfolio_transactions
-- ============================================================================

USE investing;

-- ============================================================================
-- Table: trading_strategies
-- Purpose: Store trading strategy definitions with configurable indicators
-- ============================================================================

CREATE TABLE IF NOT EXISTS trading_strategies (
  id INT NOT NULL AUTO_INCREMENT,

  -- Strategy Metadata
  name VARCHAR(100) NOT NULL COMMENT 'Strategy display name',
  description TEXT NULL COMMENT 'Strategy description and notes',
  strategy_type ENUM(
    'RSI_REVERSAL',
    'MACD_MOMENTUM',
    'MA_CROSSOVER',
    'BOLLINGER_BOUNCE',
    'STOCHASTIC_DIVERGENCE',
    'MULTI_INDICATOR',
    'TREND_FOLLOWING',
    'CUSTOM'
  ) NOT NULL COMMENT 'Strategy category/type',

  -- Anchor Indicator (Primary Trigger)
  anchor_indicator VARCHAR(50) NOT NULL COMMENT 'Primary indicator: rsi, macd, moving_average, bollinger_bands, stochastic, trend, volume',
  anchor_config JSON NOT NULL COMMENT 'Anchor indicator parameters (e.g., {"period": 14, "threshold": 30})',

  -- Confirmation Indicators (Optional Validators)
  confirmation_indicators JSON NULL COMMENT 'Array of confirmation indicator configs with conditions',

  -- Signal Generation Rules
  buy_conditions JSON NOT NULL COMMENT 'Conditions that trigger BUY signals',
  sell_conditions JSON NOT NULL COMMENT 'Conditions that trigger SELL signals',

  -- Risk Management
  min_confidence_score DECIMAL(5,2) DEFAULT 50.0 COMMENT 'Minimum confidence (0-100) to generate signal',
  max_signals_per_day INT DEFAULT 10 COMMENT 'Maximum signals per ticker per day',

  -- Applicability Scope
  portfolio_id INT NULL COMMENT 'Apply only to specific portfolio (NULL = all portfolios)',
  watch_list_id INT NULL COMMENT 'Apply only to specific watchlist (NULL = all tickers in portfolio)',
  active BOOLEAN DEFAULT TRUE COMMENT 'Whether strategy is enabled',

  -- Audit Fields
  created_by VARCHAR(50) DEFAULT 'USER' COMMENT 'USER or AI',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  KEY idx_portfolio_active (portfolio_id, active),
  KEY idx_watchlist_active (watch_list_id, active),
  KEY idx_active (active),
  KEY idx_strategy_type (strategy_type),

  CONSTRAINT strategy_portfolio_fk FOREIGN KEY (portfolio_id)
    REFERENCES portfolio (id) ON DELETE CASCADE,
  CONSTRAINT strategy_watchlist_fk FOREIGN KEY (watch_list_id)
    REFERENCES watch_lists (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Trading strategy definitions with anchor and confirmation indicators';

-- ============================================================================
-- Table: trading_signals
-- Purpose: Store generated trading signals with full indicator snapshots
-- ============================================================================

CREATE TABLE IF NOT EXISTS trading_signals (
  id INT NOT NULL AUTO_INCREMENT,

  -- Signal Source
  strategy_id INT NOT NULL COMMENT 'Strategy that generated this signal',
  portfolio_id INT NULL COMMENT 'Portfolio this signal applies to',
  ticker_id INT NOT NULL COMMENT 'Ticker symbol this signal is for',

  -- Signal Details
  signal_type ENUM('BUY', 'SELL', 'HOLD') NOT NULL COMMENT 'Type of trading signal',
  signal_strength ENUM('STRONG', 'MODERATE', 'WEAK') NOT NULL COMMENT 'Signal strength based on confirmations',
  confidence_score DECIMAL(5,2) NOT NULL COMMENT 'Confidence level 0-100',

  -- Indicator Snapshot (at time of signal)
  indicator_snapshot JSON NOT NULL COMMENT 'All indicator values when signal was generated',
  price_at_signal DECIMAL(10,2) NOT NULL COMMENT 'Stock price when signal was generated',

  -- Signal Lifecycle
  signal_date DATETIME NOT NULL COMMENT 'When signal was generated',
  expires_date DATETIME NULL COMMENT 'When signal expires (NULL = no expiration)',
  status ENUM('PENDING', 'ACTED_ON', 'IGNORED', 'EXPIRED', 'CANCELLED') DEFAULT 'PENDING' COMMENT 'Signal status',

  -- Performance Tracking (filled in after evaluation)
  outcome ENUM('SUCCESS', 'FAILURE', 'NEUTRAL', 'PENDING') DEFAULT 'PENDING' COMMENT 'Signal outcome if acted upon',
  profit_loss DECIMAL(10,2) NULL COMMENT 'Actual P/L if signal was acted upon',
  profit_loss_pct DECIMAL(5,2) NULL COMMENT 'P/L percentage',
  evaluation_date DATETIME NULL COMMENT 'When outcome was evaluated',

  -- Links to Other Tables
  recommendation_id INT NULL COMMENT 'Link to AI recommendation if converted',
  transaction_id INT NULL COMMENT 'Link to portfolio transaction if acted upon',

  -- Audit
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  KEY idx_strategy_date (strategy_id, signal_date),
  KEY idx_ticker_status (ticker_id, status),
  KEY idx_portfolio_status (portfolio_id, status),
  KEY idx_signal_date (signal_date),
  KEY idx_status (status),
  KEY idx_signal_type (signal_type),

  CONSTRAINT signal_strategy_fk FOREIGN KEY (strategy_id)
    REFERENCES trading_strategies (id) ON DELETE CASCADE,
  CONSTRAINT signal_ticker_fk FOREIGN KEY (ticker_id)
    REFERENCES tickers (id) ON DELETE CASCADE,
  CONSTRAINT signal_portfolio_fk FOREIGN KEY (portfolio_id)
    REFERENCES portfolio (id) ON DELETE CASCADE,
  CONSTRAINT signal_recommendation_fk FOREIGN KEY (recommendation_id)
    REFERENCES ai_recommendations (id) ON DELETE SET NULL,
  CONSTRAINT signal_transaction_fk FOREIGN KEY (transaction_id)
    REFERENCES portfolio_transactions (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Generated trading signals with indicator snapshots and performance tracking';

-- ============================================================================
-- Table: strategy_performance_metrics
-- Purpose: Aggregated performance metrics for strategies over time periods
-- ============================================================================

CREATE TABLE IF NOT EXISTS strategy_performance_metrics (
  id INT NOT NULL AUTO_INCREMENT,

  -- Identification
  strategy_id INT NOT NULL COMMENT 'Strategy being measured',
  portfolio_id INT NULL COMMENT 'Portfolio for metrics (NULL = aggregate across all)',
  ticker_id INT NULL COMMENT 'Ticker for metrics (NULL = aggregate across all)',

  -- Time Period
  period_start DATE NOT NULL COMMENT 'Start of measurement period',
  period_end DATE NOT NULL COMMENT 'End of measurement period',

  -- Signal Metrics
  total_signals INT NOT NULL DEFAULT 0 COMMENT 'Total signals generated',
  buy_signals INT NOT NULL DEFAULT 0 COMMENT 'Number of BUY signals',
  sell_signals INT NOT NULL DEFAULT 0 COMMENT 'Number of SELL signals',
  avg_confidence DECIMAL(5,2) NULL COMMENT 'Average confidence score',

  -- Performance Metrics (based on acted-upon signals)
  signals_acted_on INT NOT NULL DEFAULT 0 COMMENT 'Signals that were acted upon',
  successful_signals INT NOT NULL DEFAULT 0 COMMENT 'Signals that resulted in profit',
  failed_signals INT NOT NULL DEFAULT 0 COMMENT 'Signals that resulted in loss',
  win_rate DECIMAL(5,2) NULL COMMENT 'Success percentage (successful / acted_on)',

  -- Profit/Loss Metrics
  avg_profit_loss DECIMAL(10,2) NULL COMMENT 'Average P/L per signal',
  total_profit_loss DECIMAL(10,2) NULL COMMENT 'Total P/L across all signals',

  -- Risk Metrics
  max_drawdown DECIMAL(10,2) NULL COMMENT 'Maximum portfolio drawdown',
  sharpe_ratio DECIMAL(5,2) NULL COMMENT 'Risk-adjusted return metric',

  -- Metadata
  calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When metrics were calculated',

  PRIMARY KEY (id),
  UNIQUE KEY unique_period (strategy_id, portfolio_id, ticker_id, period_start, period_end),
  KEY idx_strategy_period (strategy_id, period_start),
  KEY idx_win_rate (win_rate),
  KEY idx_total_profit_loss (total_profit_loss),

  CONSTRAINT perf_strategy_fk FOREIGN KEY (strategy_id)
    REFERENCES trading_strategies (id) ON DELETE CASCADE,
  CONSTRAINT perf_portfolio_fk FOREIGN KEY (portfolio_id)
    REFERENCES portfolio (id) ON DELETE CASCADE,
  CONSTRAINT perf_ticker_fk FOREIGN KEY (ticker_id)
    REFERENCES tickers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Aggregated performance metrics for trading strategies';

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View: Active strategies with signal counts
CREATE OR REPLACE VIEW v_active_strategies AS
SELECT
  s.*,
  COUNT(sig.id) as total_signals_generated,
  COUNT(CASE WHEN sig.status = 'PENDING' THEN 1 END) as active_signals
FROM trading_strategies s
LEFT JOIN trading_signals sig ON s.id = sig.strategy_id
WHERE s.active = TRUE
GROUP BY s.id;

-- View: Recent signals with strategy and ticker details
CREATE OR REPLACE VIEW v_recent_signals AS
SELECT
  sig.id,
  sig.signal_type,
  sig.signal_strength,
  sig.confidence_score,
  sig.price_at_signal,
  sig.signal_date,
  sig.status,
  sig.outcome,
  sig.profit_loss,
  sig.profit_loss_pct,
  strat.name as strategy_name,
  strat.strategy_type,
  t.ticker as ticker_symbol,
  t.ticker_name,
  p.name as portfolio_name
FROM trading_signals sig
INNER JOIN trading_strategies strat ON sig.strategy_id = strat.id
INNER JOIN tickers t ON sig.ticker_id = t.id
LEFT JOIN portfolio p ON sig.portfolio_id = p.id
ORDER BY sig.signal_date DESC;

-- View: Strategy performance leaderboard
CREATE OR REPLACE VIEW v_strategy_leaderboard AS
SELECT
  s.id as strategy_id,
  s.name as strategy_name,
  s.strategy_type,
  COUNT(sig.id) as total_signals,
  COUNT(CASE WHEN sig.status = 'ACTED_ON' THEN 1 END) as acted_on_count,
  COUNT(CASE WHEN sig.outcome = 'SUCCESS' THEN 1 END) as successful_count,
  COUNT(CASE WHEN sig.outcome = 'FAILURE' THEN 1 END) as failed_count,
  CASE
    WHEN COUNT(CASE WHEN sig.status = 'ACTED_ON' THEN 1 END) > 0
    THEN (COUNT(CASE WHEN sig.outcome = 'SUCCESS' THEN 1 END) * 100.0) /
         COUNT(CASE WHEN sig.status = 'ACTED_ON' THEN 1 END)
    ELSE NULL
  END as win_rate,
  AVG(sig.confidence_score) as avg_confidence,
  SUM(sig.profit_loss) as total_profit_loss
FROM trading_strategies s
LEFT JOIN trading_signals sig ON s.id = sig.strategy_id
WHERE s.active = TRUE
GROUP BY s.id, s.name, s.strategy_type
ORDER BY win_rate DESC, total_profit_loss DESC;

-- ============================================================================
-- Sample Data / Default Strategies (Optional)
-- ============================================================================

-- Note: These can be loaded via the application using strategy_templates.json
-- Keeping this commented out to avoid inserting duplicate data

/*
-- Example: RSI Reversal Strategy
INSERT INTO trading_strategies (
  name, description, strategy_type,
  anchor_indicator, anchor_config,
  buy_conditions, sell_conditions,
  confirmation_indicators, min_confidence_score
) VALUES (
  'RSI Reversal - Default',
  'Buy when RSI oversold (<=30), sell when overbought (>=70)',
  'RSI_REVERSAL',
  'rsi',
  '{"period": 14}',
  '{"rsi_value": {"operator": "<=", "value": 30}}',
  '{"rsi_value": {"operator": ">=", "value": 70}}',
  '[{"indicator": "trend", "config": {"period": 20}, "required": false, "conditions": {"trend_direction": {"not_equals": "DOWN"}}}]',
  65.0
);
*/

-- ============================================================================
-- Utility Procedures
-- ============================================================================

DELIMITER //

-- Procedure: Expire old signals
CREATE PROCEDURE IF NOT EXISTS expire_old_trading_signals()
BEGIN
  UPDATE trading_signals
  SET status = 'EXPIRED', updated_at = NOW()
  WHERE status = 'PENDING'
  AND expires_date IS NOT NULL
  AND expires_date < NOW();

  SELECT ROW_COUNT() as expired_count;
END //

-- Procedure: Calculate strategy performance metrics
CREATE PROCEDURE IF NOT EXISTS calculate_strategy_performance(
  IN p_strategy_id INT,
  IN p_portfolio_id INT,
  IN p_ticker_id INT,
  IN p_period_start DATE,
  IN p_period_end DATE
)
BEGIN
  DECLARE v_total_signals INT DEFAULT 0;
  DECLARE v_buy_signals INT DEFAULT 0;
  DECLARE v_sell_signals INT DEFAULT 0;
  DECLARE v_avg_confidence DECIMAL(5,2) DEFAULT NULL;
  DECLARE v_signals_acted_on INT DEFAULT 0;
  DECLARE v_successful INT DEFAULT 0;
  DECLARE v_failed INT DEFAULT 0;
  DECLARE v_win_rate DECIMAL(5,2) DEFAULT NULL;
  DECLARE v_avg_pl DECIMAL(10,2) DEFAULT NULL;
  DECLARE v_total_pl DECIMAL(10,2) DEFAULT NULL;

  -- Calculate metrics
  SELECT
    COUNT(*),
    SUM(CASE WHEN signal_type = 'BUY' THEN 1 ELSE 0 END),
    SUM(CASE WHEN signal_type = 'SELL' THEN 1 ELSE 0 END),
    AVG(confidence_score),
    SUM(CASE WHEN status = 'ACTED_ON' THEN 1 ELSE 0 END),
    SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END),
    SUM(CASE WHEN outcome = 'FAILURE' THEN 1 ELSE 0 END),
    AVG(profit_loss),
    SUM(profit_loss)
  INTO
    v_total_signals, v_buy_signals, v_sell_signals, v_avg_confidence,
    v_signals_acted_on, v_successful, v_failed, v_avg_pl, v_total_pl
  FROM trading_signals
  WHERE strategy_id = p_strategy_id
  AND (p_portfolio_id IS NULL OR portfolio_id = p_portfolio_id)
  AND (p_ticker_id IS NULL OR ticker_id = p_ticker_id)
  AND DATE(signal_date) BETWEEN p_period_start AND p_period_end;

  -- Calculate win rate
  IF v_signals_acted_on > 0 THEN
    SET v_win_rate = (v_successful * 100.0) / v_signals_acted_on;
  END IF;

  -- Insert or update metrics
  INSERT INTO strategy_performance_metrics (
    strategy_id, portfolio_id, ticker_id,
    period_start, period_end,
    total_signals, buy_signals, sell_signals, avg_confidence,
    signals_acted_on, successful_signals, failed_signals, win_rate,
    avg_profit_loss, total_profit_loss
  ) VALUES (
    p_strategy_id, p_portfolio_id, p_ticker_id,
    p_period_start, p_period_end,
    v_total_signals, v_buy_signals, v_sell_signals, v_avg_confidence,
    v_signals_acted_on, v_successful, v_failed, v_win_rate,
    v_avg_pl, v_total_pl
  ) ON DUPLICATE KEY UPDATE
    total_signals = v_total_signals,
    buy_signals = v_buy_signals,
    sell_signals = v_sell_signals,
    avg_confidence = v_avg_confidence,
    signals_acted_on = v_signals_acted_on,
    successful_signals = v_successful,
    failed_signals = v_failed,
    win_rate = v_win_rate,
    avg_profit_loss = v_avg_pl,
    total_profit_loss = v_total_pl,
    calculated_at = NOW();

  SELECT 'Metrics calculated successfully' as result;
END //

DELIMITER ;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check that tables were created
SELECT
  TABLE_NAME,
  TABLE_ROWS,
  CREATE_TIME,
  TABLE_COMMENT
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'investing'
AND TABLE_NAME IN ('trading_strategies', 'trading_signals', 'strategy_performance_metrics')
ORDER BY TABLE_NAME;

-- Check indexes
SELECT
  TABLE_NAME,
  INDEX_NAME,
  COLUMN_NAME,
  SEQ_IN_INDEX
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'investing'
AND TABLE_NAME IN ('trading_strategies', 'trading_signals', 'strategy_performance_metrics')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- Check foreign keys
SELECT
  CONSTRAINT_NAME,
  TABLE_NAME,
  COLUMN_NAME,
  REFERENCED_TABLE_NAME,
  REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'investing'
AND TABLE_NAME IN ('trading_strategies', 'trading_signals', 'strategy_performance_metrics')
AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME;

-- ============================================================================
-- End of Schema
-- ============================================================================
