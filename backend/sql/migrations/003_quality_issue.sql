CREATE TABLE IF NOT EXISTS ai_quality_issue (
  id BIGINT PRIMARY KEY AUTO_INCREMENT, asset_id BIGINT NOT NULL, issue_type VARCHAR(32) NOT NULL,
  issue_title VARCHAR(128) NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'open', assignee VARCHAR(64) NULL,
  due_date DATE NULL, fix_remark VARCHAR(512) NULL, created_by VARCHAR(64) NULL, created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL, verified_by VARCHAR(64) NULL, verified_at DATETIME NULL,
  INDEX idx_quality_issue_asset (asset_id), INDEX idx_quality_issue_status (status)
);
