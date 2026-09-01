CREATE TABLE IF NOT EXISTS ai_usage_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NULL,
  provider VARCHAR(32) NOT NULL,
  model VARCHAR(128) NULL,
  operation VARCHAR(64) NOT NULL,
  request_id VARCHAR(64) NULL,
  status VARCHAR(16) NOT NULL,
  input_tokens INT NOT NULL DEFAULT 0,
  output_tokens INT NOT NULL DEFAULT 0,
  cost DECIMAL(12,6) NOT NULL DEFAULT 0,
  latency_ms INT NOT NULL DEFAULT 0,
  error_code VARCHAR(64) NULL,
  redacted_input TEXT NULL,
  created_at DATETIME NOT NULL,
  KEY idx_ai_usage_user_time(user_id, created_at),
  KEY idx_ai_usage_operation_time(operation, created_at),
  KEY idx_ai_usage_status_time(status, created_at)
);
