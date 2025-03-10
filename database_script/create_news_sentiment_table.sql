CREATE TABLE IF NOT EXISTS news_sentiment (
  id INT NOT NULL AUTO_INCREMENT,
  ticker_id INT NOT NULL,
  headline VARCHAR(255) NOT NULL,
  publisher VARCHAR(100) NOT NULL,
  publish_date DATETIME NOT NULL,
  sentiment_score DECIMAL(10,4) NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  article_link VARCHAR(500) NOT NULL,
  PRIMARY KEY (id),
  KEY ticker_id (ticker_id),
  CONSTRAINT news_ticker_fk FOREIGN KEY (ticker_id) REFERENCES tickers (id)
);
