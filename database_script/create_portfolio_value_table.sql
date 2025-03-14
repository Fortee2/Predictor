CREATE TABLE IF NOT EXISTS portfolio_value (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    calculation_date DATE NOT NULL,
    value DECIMAL(18,2) NOT NULL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
);
