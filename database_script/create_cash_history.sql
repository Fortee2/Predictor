CREATE TABLE investing.cash_balance_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    transaction_date DATETIME NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    description VARCHAR(255),
    balance_after DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
);