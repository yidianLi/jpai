CREATE TABLE IF NOT EXISTS ai_job (
  id VARCHAR(64) PRIMARY KEY, job_type VARCHAR(64) NOT NULL, idempotency_key VARCHAR(255) NOT NULL UNIQUE,
  status VARCHAR(16) NOT NULL DEFAULT 'queued', progress INT NOT NULL DEFAULT 0,
  owner_user_id BIGINT NULL, owner_name VARCHAR(64) NULL, payload TEXT NULL, result TEXT NULL, error TEXT NULL,
  retry_count INT NOT NULL DEFAULT 0, max_retries INT NOT NULL DEFAULT 2, timeout_seconds INT NOT NULL DEFAULT 900,
  created_at DATETIME NOT NULL, started_at DATETIME NULL, finished_at DATETIME NULL, updated_at DATETIME NOT NULL,
  INDEX idx_ai_job_type (job_type), INDEX idx_ai_job_status_updated (status, updated_at), INDEX idx_ai_job_owner (owner_user_id)
);
