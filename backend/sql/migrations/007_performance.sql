CREATE INDEX idx_asset_scope_state_idle ON ai_asset(company_id, dept_id, state_id, is_idle, asset_id);
CREATE INDEX idx_transfer_asset_type_date ON ai_asset_transfer(asset_id, bill_type, bill_date);
CREATE INDEX idx_transfer_dept_date_type ON ai_asset_transfer(new_dept_id, bill_date, bill_type);
CREATE INDEX idx_warning_created_status ON ai_warning(create_time, status);
CREATE INDEX idx_check_date_state ON ai_check_record(check_date, check_state);
CREATE TABLE IF NOT EXISTS ai_metric_daily (
  metric_date DATE NOT NULL, scope_type VARCHAR(16) NOT NULL DEFAULT 'global', scope_id BIGINT NULL,
  metric_key VARCHAR(64) NOT NULL, metric_value DECIMAL(18,4) NOT NULL DEFAULT 0,
  source_version VARCHAR(32) NOT NULL, created_at DATETIME NOT NULL,
  PRIMARY KEY(metric_date, scope_type, scope_id, metric_key)
);
