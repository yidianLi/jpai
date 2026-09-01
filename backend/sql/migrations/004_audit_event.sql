CREATE TABLE IF NOT EXISTS ai_audit_event (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  actor_user_id BIGINT NULL, actor_name VARCHAR(64) NULL,
  action VARCHAR(64) NOT NULL, resource VARCHAR(128) NULL,
  result VARCHAR(16) NOT NULL DEFAULT 'success', before_snapshot TEXT NULL,
  after_snapshot TEXT NULL, request_id VARCHAR(64) NULL, ip VARCHAR(64) NULL,
  user_agent VARCHAR(255) NULL, created_at DATETIME NOT NULL,
  INDEX idx_audit_actor (actor_user_id), INDEX idx_audit_action (action),
  INDEX idx_audit_request (request_id), INDEX idx_audit_created (created_at)
);
