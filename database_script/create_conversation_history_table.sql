-- AI Conversation History Table
-- Stores LLM conversation sessions for persistence between application restarts

CREATE TABLE IF NOT EXISTS ai_conversation_history (
  id INT NOT NULL AUTO_INCREMENT,
  portfolio_id INT NOT NULL,
  session_name VARCHAR(255) NULL COMMENT 'Optional user-provided session name',
  conversation_data JSON NOT NULL COMMENT 'Full conversation history as JSON array',
  message_count INT NOT NULL DEFAULT 0 COMMENT 'Number of messages in conversation',
  exchange_count INT NOT NULL DEFAULT 0 COMMENT 'Number of user-assistant exchanges',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether this is the current active session',
  PRIMARY KEY (id),
  KEY portfolio_id (portfolio_id),
  KEY is_active (is_active),
  KEY last_accessed (last_accessed_at),
  CONSTRAINT conv_history_portfolio_fk FOREIGN KEY (portfolio_id) REFERENCES portfolio (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Persists AI conversation sessions between app restarts';

-- Index for finding active sessions by portfolio
CREATE INDEX idx_conv_portfolio_active ON ai_conversation_history (portfolio_id, is_active);

-- Index for cleanup of old sessions
CREATE INDEX idx_conv_last_accessed ON ai_conversation_history (last_accessed_at);
