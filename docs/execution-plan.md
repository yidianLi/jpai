# 国产化智能资产运营平台执行方案

> 本文档是计划书的可执行版本，供后续阶段清单和代码实施引用。当前仅完成设计，不代表数据库或代码已经修改。

## 1. 实施原则

- 先建立数据口径和后端接口，再开发页面。
- 所有写入操作必须经过后端权限校验、事务和审计。
- AI 只做理解和解释；统计、评分、金额、状态迁移由规则代码完成。
- 数据库访问集中在服务层，避免在 API 或前端散落 SQL。
- 国产数据库适配通过配置和兼容 SQL 实现，禁止依赖 MySQL 专有行为。

## 2. 目标目录结构

```text
backend/
  app/
    api/
      transfer.py              # 调拨建议
      procurement.py           # 采购建议
      insight.py               # 品牌/型号表现
    models/
      transfer.py              # 调拨建议、审计
      insight.py               # 分析快照（可选缓存）
    schemas/
      transfer.py
      procurement.py
      insight.py
    services/
      transfer_service.py
      insight_service.py
      procurement_service.py
      llm_service.py           # 已有，扩展结构化输出适配
    repositories/
      asset_repository.py
      transfer_repository.py
      insight_repository.py
    core/
      permissions.py           # 统一写入权限（如现有权限不足）
      audit.py                 # 审计写入
  sql/
    migrations/
      001_transfer.sql
      002_insight_indexes.sql
frontend/src/
  api/
    index.js                   # 增加调拨、洞察、采购接口
  views/
    transfer/Index.vue
    insight/Brand.vue
    insight/Model.vue
    procurement/Index.vue
  components/
    EvidencePanel.vue          # 指标证据明细
    StatusTag.vue
docs/
  project-plan.md
  execution-plan.md
  stages/
```

如果现有项目尚未使用 `schemas` 或 `repositories`，第一阶段可以先在现有 service 层实现；只有出现跨接口复用时再拆分，避免一次性重构。

## 3. 数据库设计

### 3.1 调拨建议表

表名：`ai_transfer_suggestion`

```sql
CREATE TABLE ai_transfer_suggestion (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  asset_id BIGINT NOT NULL,
  source_company_id BIGINT NULL,
  source_dept_id INT NULL,
  source_dept_name VARCHAR(128) NULL,
  source_position VARCHAR(128) NULL,
  source_user_name VARCHAR(64) NULL,
  target_company_id BIGINT NULL,
  target_dept_id INT NOT NULL,
  target_dept_name VARCHAR(128) NOT NULL,
  target_position VARCHAR(128) NULL,
  target_user_name VARCHAR(64) NULL,
  reason VARCHAR(512) NULL,
  estimated_saving DECIMAL(18,2) NULL,
  status VARCHAR(32) NOT NULL,
  receiver_user_id BIGINT NULL,
  receiver_remark VARCHAR(512) NULL,
  receiver_time DATETIME NULL,
  operator_user_id BIGINT NULL,
  operator_time DATETIME NULL,
  version_no INT NOT NULL DEFAULT 1,
  created_by BIGINT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX idx_transfer_asset_status (asset_id, status),
  INDEX idx_transfer_target_dept_status (target_dept_id, status)
);
```

状态只允许：`draft`、`pending_receiver`、`rejected`、`confirmed`、`completed`、`cancelled`。

### 3.2 调拨审计表

表名：`ai_transfer_audit`

```sql
CREATE TABLE ai_transfer_audit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  suggestion_id BIGINT NOT NULL,
  asset_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator_user_id BIGINT NOT NULL,
  before_snapshot JSON NULL,
  after_snapshot JSON NULL,
  remark VARCHAR(512) NULL,
  created_at DATETIME NOT NULL,
  INDEX idx_transfer_audit_suggestion (suggestion_id),
  INDEX idx_transfer_audit_asset (asset_id)
);
```

`JSON` 在目标数据库不兼容时改为 `TEXT`，由应用序列化；该差异必须在适配测试中验证。

### 3.3 分析查询与索引

品牌/型号分析第一版直接从 `ai_asset` 和 `ai_asset_transfer` 聚合，不预先建立结果表。必要索引：

```sql
CREATE INDEX idx_asset_brand_class ON ai_asset (brand, class_id);
CREATE INDEX idx_asset_model_class ON ai_asset (model, class_id);
CREATE INDEX idx_transfer_repair_asset_date ON ai_asset_transfer (asset_id, bill_type, bill_date);
```

只有在查询性能验证不足时，才增加按日或按月的分析快照表。

## 4. 后端接口契约

### 4.1 调拨

```text
GET  /api/transfer/suggestions?status=&page=&size=
POST /api/transfer/suggestions
GET  /api/transfer/suggestions/{id}
POST /api/transfer/suggestions/{id}/receiver-confirm
POST /api/transfer/suggestions/{id}/receiver-reject
POST /api/transfer/suggestions/{id}/execute
POST /api/transfer/suggestions/{id}/cancel
GET  /api/transfer/suggestions/{id}/audit
```

创建请求必须包含 `asset_id`、`target_dept_id`，可选目标位置和使用人。执行接口必须在事务中：锁定/校验建议、校验资产当前字段和版本、更新资产、写审计、更新建议状态。

### 4.2 品牌/型号表现

```text
GET /api/insight/brands?class_id=&start_date=&end_date=&dept_id=&min_sample=
GET /api/insight/brands/{brand}/models?class_id=&start_date=&end_date=
GET /api/insight/models/{model_id}/evidence
```

响应必须包含 `metrics`、`score`、`confidence`、`risk_tags`、`sample_size` 和 `evidence_query`（统计口径描述，不返回 SQL）。

维修统计固定使用 `bill_type = 10700`；时间范围按 `bill_date`；维修费用使用 `fee`。

### 4.3 采购建议

```text
POST /api/procurement/recommendations/preview
POST /api/procurement/recommendations
GET  /api/procurement/recommendations/{id}
POST /api/procurement/recommendations/{id}/confirm
```

预览接口只读计算；正式建议单保存需求、可调拨数量、采购缺口、候选型号、预算和证据快照。确认不等于自动下采购单。

## 5. 评分计算约定

服务层统一输出原始指标，再输出评分。所有除法都处理分母为零和缺失值；缺失值不能当作零维修或零费用。

```text
可靠性 = 维修频率、提前报废率的归一化反向得分
成本 = 单位年成本的归一化反向得分
适配 = 闲置率和部门覆盖的组合得分
稳定性 = 盘点异常率的归一化反向得分
可信度 = 样本量、字段完整度和维修数据覆盖度
总分 = 可靠性*0.35 + 成本*0.25 + 适配*0.20 + 稳定性*0.10 + 可信度*0.10
```

默认最小样本量为 10，可通过接口参数调整；低于最小值只展示指标，不给出强推荐。

## 6. AI 接口约定

统一由 `LLMService` 提供：

- `understand_procurement_request(text) -> structured request`
- `explain_insight(metrics, evidence) -> explanation`
- `explain_transfer(asset, target_context) -> explanation`
- `polish_report(data) -> text`

结构化输出必须经过 Pydantic 校验。AI 超时、空响应、格式错误时返回规则化结果和 `ai_used=false`，不得阻断业务接口。任何模型输出中的数量和金额只作为文本输入，不能覆盖后端计算值。

## 7. 前端路由与交互

新增路由：

```text
/transfer
/insight/brands
/insight/models
/procurement
```

品牌/型号页面必须提供筛选条件、样本量提示、风险标签、证据抽屉和明细跳转。调拨页面按“待我处理、我发起的、已完成”分组，接收部门只能确认/拒绝，管理员才能执行。

## 8. 配置与部署

配置项统一通过环境变量或服务端配置表提供：

```env
DB_DIALECT=mysql                 # 目标环境切换为 dameng/openGauss 适配值
AI_PROVIDER=openai
AI_ENABLED=true
AI_BASE_URL=https://...
AI_MODEL=...
AI_API_KEY=...
TRANSFER_MIN_IDLE_DAYS=90
INSIGHT_MIN_SAMPLE=10
```

生产环境不在前端打包密钥；容器使用非 root 用户、独立日志卷和数据库备份卷。国产化验收前必须完成 openEuler/麒麟/统信至少一个目标环境的部署演练。

## 9. 阶段清单与验收

### Stage 0：数据核验

代码端任务：统计维修工单数量、费用、资产关联率、按品牌/型号分布和缺失字段；输出 SQL 或脚本及报告。

验收：随机抽取 10 个资产，维修次数和费用与源系统一致；确认 `10700` 口径。

### Stage 1：调拨闭环

代码端任务：新增模型、DDL、service、API、权限、审计和前端页面；实现状态机和并发校验。

验收：创建、确认、拒绝、执行、取消全部可用；执行后部门/位置/使用人更新；审计快照完整；并发冲突返回 409。

### Stage 2：品牌/型号表现

代码端任务：实现聚合接口、评分、风险标签、证据接口和两个页面。

验收：维修次数、维修费用、闲置率和样本量可由明细复算；样本不足不强推荐。

### Stage 3：采购建议

代码端任务：实现需求预览、闲置匹配、缺口计算、候选型号、预算和建议单。

验收：输入一个需求可得到调拨数量、采购缺口、候选型号和证据；不产生自动采购动作。

### Stage 4：AI 场景

代码端任务：扩展 AI 适配、结构化校验、解释组件和失败兜底。

验收：模型可用和不可用两种情况下均完成业务流程；页面展示模型状态和数据依据。

### Stage 5：国产化交付

代码端任务：完成目标 OS、数据库适配、容器、备份、日志、安全和回滚文档。

验收：在目标环境完成安装、启动、迁移、备份恢复和回滚。

## 10. 代码端提交前检查

- Python 编译、单元测试和 API 契约测试通过。
- 前端 `npm run build` 通过。
- `git diff --check` 通过。
- 不提交 API Key、数据库密码和生产数据。
- 返回本阶段修改文件清单、迁移命令、测试命令和已知限制。
