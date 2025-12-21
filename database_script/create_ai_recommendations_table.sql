CREATE TABLE IF NOT EXISTS ai_recommendations (
  id INT NOT NULL AUTO_INCREMENT,
  portfolio_id INT NOT NULL,
  ticker_id INT NOT NULL,
  recommendation_type ENUM('BUY', 'SELL', 'HOLD', 'REDUCE', 'INCREASE') NOT NULL,
  recommended_quantity DECIMAL(10,2) NULL,
  recommended_price DECIMAL(10,2) NULL,
  confidence_score DECIMAL(5,2) NULL COMMENT 'Confidence score 0-100',
  reasoning TEXT NULL COMMENT 'AI explanation for recommendation',
  technical_indicators JSON NULL COMMENT 'RSI, MACD, MA values at time of recommendation',
  sentiment_score DECIMAL(5,2) NULL COMMENT 'News sentiment score at time',
  recommendation_date DATETIME NOT NULL,
  expires_date DATETIME NULL COMMENT 'When recommendation becomes stale',
  status ENUM('PENDING', 'FOLLOWED', 'PARTIALLY_FOLLOWED', 'IGNORED', 'EXPIRED') NOT NULL DEFAULT 'PENDING',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY portfolio_id (portfolio_id),
  KEY ticker_id (ticker_id),
  KEY status (status),
  KEY recommendation_date (recommendation_date),
  CONSTRAINT ai_recommendations_portfolio_fk FOREIGN KEY (portfolio_id) REFERENCES portfolio (id),
  CONSTRAINT ai_recommendations_ticker_fk FOREIGN KEY (ticker_id) REFERENCES tickers (id)
);

CREATE INDEX idx_ai_rec_portfolio_status ON ai_recommendations (portfolio_id, status);
CREATE INDEX idx_ai_rec_ticker_date ON ai_recommendations (ticker_id, recommendation_date);