CREATE TABLE IF NOT EXISTS ai_transfer_suggestion (
  id BIGINT PRIMARY KEY AUTO_INCREMENT, asset_id BIGINT NOT NULL,
  source_company_id BIGINT NULL, source_dept_id INT NULL, source_dept_name VARCHAR(128) NULL,
  source_position VARCHAR(128) NULL, source_user_name VARCHAR(64) NULL,
  target_company_id BIGINT NULL, target_dept_id INT NOT NULL, target_dept_name VARCHAR(128) NOT NULL,
  target_position VARCHAR(128) NULL, target_user_name VARCHAR(64) NULL, reason VARCHAR(512) NULL,
  estimated_saving DECIMAL(18,2) NULL, status VARCHAR(32) NOT NULL, receiver_user_id BIGINT NULL,
  receiver_remark VARCHAR(512) NULL, receiver_time DATETIME NULL, operator_user_id BIGINT NULL,
  operator_time DATETIME NULL, version_no INT NOT NULL DEFAULT 1, asset_sync_time DATETIME NULL,
  created_by BIGINT NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  INDEX idx_transfer_asset_status (asset_id, status)
);
CREATE TABLE IF NOT EXISTS ai_transfer_audit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT, suggestion_id BIGINT NOT NULL, asset_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL, operator_user_id BIGINT NOT NULL, before_snapshot TEXT NULL,
  after_snapshot TEXT NULL, remark VARCHAR(512) NULL, created_at DATETIME NOT NULL,
  INDEX idx_transfer_audit_suggestion (suggestion_id), INDEX idx_transfer_audit_asset (asset_id)
);
