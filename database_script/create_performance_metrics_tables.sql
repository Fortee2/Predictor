-- Enhanced Portfolio Performance Analysis Tables
-- These tables support multi-timeframe analysis, risk metrics, and benchmark comparisons

-- Table to store performance metrics across different timeframes
CREATE TABLE IF NOT EXISTS `portfolio_performance_metrics` (
  `id` int NOT NULL AUTO_INCREMENT,
  `portfolio_id` int NOT NULL,
  `calculation_date` date NOT NULL,
  `timeframe` enum('1M','3M','6M','1Y','2Y','5Y','MAX') NOT NULL,
  `total_return_pct` decimal(10,4) DEFAULT NULL,
  `annualized_return_pct` decimal(10,4) DEFAULT NULL,
  `volatility_pct` decimal(10,4) DEFAULT NULL,
  `sharpe_ratio` decimal(10,4) DEFAULT NULL,
  `max_drawdown_pct` decimal(10,4) DEFAULT NULL,
  `alpha` decimal(10,4) DEFAULT NULL,
  `beta` decimal(10,4) DEFAULT NULL,
  `up_capture_ratio` decimal(10,4) DEFAULT NULL,
  `down_capture_ratio` decimal(10,4) DEFAULT NULL,
  `benchmark_return_pct` decimal(10,4) DEFAULT NULL,
  `excess_return_pct` decimal(10,4) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `portfolio_timeframe_date` (`portfolio_id`, `timeframe`, `calculation_date`),
  KEY `portfolio_id` (`portfolio_id`),
  KEY `calculation_date` (`calculation_date`),
  CONSTRAINT `portfolio_performance_metrics_ibfk_1` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolio` (`id`)
);

-- Table to store individual holding performance metrics
CREATE TABLE IF NOT EXISTS `holding_performance_metrics` (
  `id` int NOT NULL AUTO_INCREMENT,
  `portfolio_id` int NOT NULL,
  `ticker_id` int NOT NULL,
  `calculation_date` date NOT NULL,
  `timeframe` enum('1M','3M','6M','1Y','2Y','5Y','MAX') NOT NULL,
  `total_return_pct` decimal(10,4) DEFAULT NULL,
  `annualized_return_pct` decimal(10,4) DEFAULT NULL,
  `volatility_pct` decimal(10,4) DEFAULT NULL,
  `max_drawdown_pct` decimal(10,4) DEFAULT NULL,
  `sharpe_ratio` decimal(10,4) DEFAULT NULL,
  `benchmark_return_pct` decimal(10,4) DEFAULT NULL,
  `excess_return_pct` decimal(10,4) DEFAULT NULL,
  `contribution_to_portfolio_return` decimal(10,4) DEFAULT NULL,
  `weight_in_portfolio` decimal(10,4) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `portfolio_ticker_timeframe_date` (`portfolio_id`, `ticker_id`, `timeframe`, `calculation_date`),
  KEY `portfolio_id` (`portfolio_id`),
  KEY `ticker_id` (`ticker_id`),
  KEY `calculation_date` (`calculation_date`),
  CONSTRAINT `holding_performance_metrics_ibfk_1` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolio` (`id`),
  CONSTRAINT `holding_performance_metrics_ibfk_2` FOREIGN KEY (`ticker_id`) REFERENCES `tickers` (`id`)
);

-- Table to store correlation analysis between holdings
CREATE TABLE IF NOT EXISTS `portfolio_correlations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `portfolio_id` int NOT NULL,
  `ticker_id_1` int NOT NULL,
  `ticker_id_2` int NOT NULL,
  `calculation_date` date NOT NULL,
  `timeframe` enum('1M','3M','6M','1Y','2Y','5Y') NOT NULL,
  `correlation_coefficient` decimal(10,6) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `portfolio_tickers_timeframe_date` (`portfolio_id`, `ticker_id_1`, `ticker_id_2`, `timeframe`, `calculation_date`),
  KEY `portfolio_id` (`portfolio_id`),
  KEY `ticker_id_1` (`ticker_id_1`),
  KEY `ticker_id_2` (`ticker_id_2`),
  CONSTRAINT `portfolio_correlations_ibfk_1` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolio` (`id`),
  CONSTRAINT `portfolio_correlations_ibfk_2` FOREIGN KEY (`ticker_id_1`) REFERENCES `tickers` (`id`),
  CONSTRAINT `portfolio_correlations_ibfk_3` FOREIGN KEY (`ticker_id_2`) REFERENCES `tickers` (`id`)
);

-- Table to track major market events for context analysis
CREATE TABLE IF NOT EXISTS `market_events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_name` varchar(255) NOT NULL,
  `event_description` text,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `event_type` enum('CRASH','CORRECTION','RECESSION','RECOVERY','BULL_MARKET','BEAR_MARKET','VOLATILITY','OTHER') NOT NULL,
  `severity` enum('LOW','MEDIUM','HIGH','EXTREME') DEFAULT 'MEDIUM',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `start_date` (`start_date`),
  KEY `end_date` (`end_date`),
  KEY `event_type` (`event_type`)
);

-- Table to store benchmark data (S&P 500 and other indices)
CREATE TABLE IF NOT EXISTS `benchmark_performance` (
  `id` int NOT NULL AUTO_INCREMENT,
  `benchmark_ticker_id` int NOT NULL,
  `calculation_date` date NOT NULL,
  `timeframe` enum('1M','3M','6M','1Y','2Y','5Y','MAX') NOT NULL,
  `total_return_pct` decimal(10,4) DEFAULT NULL,
  `annualized_return_pct` decimal(10,4) DEFAULT NULL,
  `volatility_pct` decimal(10,4) DEFAULT NULL,
  `max_drawdown_pct` decimal(10,4) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `benchmark_timeframe_date` (`benchmark_ticker_id`, `timeframe`, `calculation_date`),
  KEY `benchmark_ticker_id` (`benchmark_ticker_id`),
  KEY `calculation_date` (`calculation_date`),
  CONSTRAINT `benchmark_performance_ibfk_1` FOREIGN KEY (`benchmark_ticker_id`) REFERENCES `tickers` (`id`)
);

-- Table to store dividend growth history
CREATE TABLE IF NOT EXISTS `dividend_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticker_id` int NOT NULL,
  `ex_dividend_date` date NOT NULL,
  `dividend_amount` decimal(10,4) NOT NULL,
  `dividend_frequency` enum('MONTHLY','QUARTERLY','SEMI_ANNUAL','ANNUAL','SPECIAL') DEFAULT 'QUARTERLY',
  `growth_rate_yoy` decimal(10,4) DEFAULT NULL,
  `payout_ratio` decimal(10,4) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ticker_ex_date` (`ticker_id`, `ex_dividend_date`),
  KEY `ticker_id` (`ticker_id`),
  KEY `ex_dividend_date` (`ex_dividend_date`),
  CONSTRAINT `dividend_history_ibfk_1` FOREIGN KEY (`ticker_id`) REFERENCES `tickers` (`id`)
);

-- Insert some major market events for context analysis
INSERT INTO `market_events` (`event_name`, `event_description`, `start_date`, `end_date`, `event_type`, `severity`) VALUES
('COVID-19 Market Crash', 'Market crash due to COVID-19 pandemic', '2020-02-19', '2020-03-23', 'CRASH', 'EXTREME'),
('COVID-19 Recovery', 'Market recovery from COVID-19 lows', '2020-03-23', '2021-12-31', 'RECOVERY', 'HIGH'),
('2022 Bear Market', 'Bear market due to inflation and rate hikes', '2022-01-03', '2022-10-12', 'BEAR_MARKET', 'HIGH'),
('2023 Recovery', 'Market recovery and new highs', '2022-10-12', '2023-12-31', 'RECOVERY', 'MEDIUM'),
('2008 Financial Crisis', 'Global financial crisis and market crash', '2007-10-09', '2009-03-09', 'CRASH', 'EXTREME'),
('Post-2008 Bull Market', 'Long bull market following financial crisis', '2009-03-09', '2020-02-19', 'BULL_MARKET', 'HIGH')
ON DUPLICATE KEY UPDATE event_description = VALUES(event_description);
