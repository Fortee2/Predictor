-- Add trade rationale tracking columns to portfolio_transactions table
-- This allows tracking why a trade was made and linking to AI recommendations

ALTER TABLE portfolio_transactions
ADD COLUMN trade_rationale_type ENUM('AI_RECOMMENDATION', 'MANUAL_DECISION', 'STOP_LOSS', 'PROFIT_TARGET', 'REBALANCE', 'OTHER') NULL COMMENT 'Type of rationale for the trade',
ADD COLUMN ai_recommendation_id INT NULL COMMENT 'Links to ai_recommendations table if trade followed AI',
ADD COLUMN user_notes TEXT NULL COMMENT 'User explanation for manual decisions',
ADD COLUMN override_reason TEXT NULL COMMENT 'Explanation if user ignored AI recommendation',
ADD CONSTRAINT portfolio_transactions_ai_rec_fk FOREIGN KEY (ai_recommendation_id) REFERENCES ai_recommendations (id);

CREATE INDEX idx_pt_rationale_type ON portfolio_transactions (trade_rationale_type);
CREATE INDEX idx_pt_ai_recommendation ON portfolio_transactions (ai_recommendation_id);