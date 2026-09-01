-- AI数智化资产管理系统 - 数据库初始化脚本
CREATE DATABASE IF NOT EXISTS ai_asset_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_asset_db;

-- 系统配置初始数据
INSERT INTO ai_config (config_key, config_value, description) VALUES
('system_name', '简普数智资产管理后台', '系统名称'),
('idle_threshold_days', '90', '闲置判定天数阈值'),
('residual_rate', '0.05', '残值率'),
('expire_red_days', '90', '到期红色预警天数'),
('expire_yellow_days', '180', '到期黄色预警天数'),
('sync_hour', '2', '每日同步时间(小时)'),
('depreciation_method', 'straight_line', '折旧方法')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);
