# AI 资产管理系统架构审计报告

审计日期：2026-08-31  
范围：数据结构、索引、缓存、队列、Session、SSL、日志、审计架构、交互设计、代码结构、API、数据安全、项目运维。  
审计方式：代码静态检查、OpenAPI 路由扫描、后端编译、前端生产构建、未授权接口探测。未使用或猜测管理员凭据，因此本报告不宣称已完成带权限的端到端业务验收。

## 1. 结论摘要

- 后端 `python -m compileall -q backend/app` 通过；前端 `npm run build` 通过；`GET /health` 返回 200。
- 受保护业务路由均声明 OAuth2 Bearer 依赖，未授权请求返回 401；登录接口和健康接口为公开接口。
- 当前最大风险不是编译错误，而是生产安全基线和任务执行模型：默认密钥/密码、宽松 CORS、无 TLS、root 数据库账号、同步执行长任务、无统一审计与可观测性。
- 条件筛选和采购预测卡顿与当前设计一致：大表 `COUNT`、聚合、全量 `.all()`、同步预测/报告/同步任务共用 Web 进程；在真实数据量和并发下容易再次出现 30 秒超时。
- 国产数据库兼容目前停留在设计层面。代码直接使用 MySQL 方言/连接驱动和 `AUTO_INCREMENT`、`ON DUPLICATE KEY UPDATE`，尚未完成达梦/openGauss 实测矩阵。

## 2. 分级问题清单

### P0 / 必须在生产前修复

1. **默认数据库密码和固定 JWT 密钥**（🔴）  
   证据：`backend/app/config.py:12-21,37-39` 默认使用 root、`aiasset2026` 和固定 `SECRET_KEY`；`docker-compose.yml` 中又写入 root/`123456`。泄露配置即可伪造令牌或直接读写数据库。  
   整改：启动时拒绝默认值；改用环境变量/密钥管理器；AI 库使用最小权限专用账号，源库保持只读；执行密钥轮换并使旧令牌失效。

2. **CORS 任意来源与凭据同时开启**（🔴）  
   证据：`backend/app/main.py:40-46` 为 `allow_origins=["*"]`、`allow_credentials=True`。生产环境会扩大跨站调用面。  
   整改：使用显式前端域名白名单；开发和生产分配置；补充安全响应头和可信代理配置。

3. **无 SSL/TLS 终止方案**（🔴）  
   证据：`frontend/nginx.conf:1-3` 仅监听 80；compose 未挂载证书或配置 HTTPS。Bearer token、密码和 AI 请求可能明文传输。  
   整改：由 Nginx/国产网关统一 TLS，HTTP 重定向 HTTPS，启用 HSTS；证书续期和回滚纳入运维手册。内网也应按部署边界决定是否强制 TLS。

4. **长任务在 Web 请求线程同步执行**（🔴）  
   证据：`backend/app/api/query.py:128-133` 同步计算预测；`backend/app/api/dashboard.py:70-75` 同步生成 Word/图表；`backend/app/api/system.py:23-43` 同步触发全量同步；`backend/app/core/scheduler.py:10-46` 使用 APScheduler 直接运行任务。  
   影响：数据库连接和 worker 被占满，前端出现 `timeout of 30000ms exceeded`，任务失败后也缺少可重试状态。  
   整改：引入 Redis + 国产化可接受的任务队列（Celery/RQ/Arq 需先做适配验证，或实现数据库任务表 + 独立 worker）；API 只返回 job_id；增加进度、超时、重试、幂等和取消。

5. **迁移治理不完整且启动时吞掉建表异常**（🔴）  
   证据：`backend/app/main.py:20-27` 可选 `create_all`，采购表又在启动时 `create(... checkfirst=True)` 并裸 `except Exception: pass`；compose 只挂载 `backend/sql/init.sql`，迁移目录不会自动执行。  
   影响：环境间 schema 漂移，真实错误被隐藏，导致接口 500。  
   整改：选定 Alembic 或受控 SQL migration runner；启动只做版本检查，不自动改生产 schema；迁移失败阻断部署并输出明确日志。

### P1 / 应尽快整改

6. **密码兼容 MD5**（🔴）  
   证据：`backend/app/core/auth.py:17-29` 对 32 位 MD5 直接校验。MD5 不适合密码存储。  
   整改：登录成功后透明升级为 Argon2id/bcrypt；设置迁移截止期，禁用新账号 MD5；增加失败次数限制、锁定和登录审计。

7. **Session/事务管理不统一**（🟡）  
   证据：依赖注入的 session 有 finally close，但多个 service 直接创建 `AiSessionLocal()`；如 `query.py:68-116`、`procurement.py:30-46` 手工 close，异常路径和事务边界不一致。  
   整改：统一 `Depends(get_ai_db)` 或 service context manager；写操作统一 `commit/rollback`；避免请求内创建多个独立 session；增加连接池耗尽监控。

8. **查询性能缺少分页上限、索引验证和关键集成索引**（🔴）  
   证据：`query.py:23-47` 对模糊关键词使用 `%...%`，默认执行 `COUNT`；多个 service 使用 `.all()` 和 `count()`；`AiAssetTransfer` 仅有 `asset_id`、`bill_date` 单列索引，预测/维修聚合涉及 `bill_type + bill_date + asset_id`。  
   影响：条件筛选和采购预测在数据增长后会再次卡顿。  
   整改：所有 `page/size` 用 Pydantic 校验并设最大值；首屏与总数解耦；基于实际 SQL `EXPLAIN` 建立联合索引（候选：`ai_asset_transfer(asset_id,bill_type,bill_date)`、按实际过滤组合补充 `ai_asset(class_id,state_id,dept_id,is_idle,asset_id)`）；关键词改前缀/全文检索或搜索表；为统计建立日/小时汇总表。

9. **无缓存层、无队列层、无任务状态表**（🟡）  
   证据：依赖中无 Redis/Celery/RQ/Arq；预测、报表、部门统计直接查库。  
   整改：短 TTL 缓存仪表盘和字典；缓存键包含数据版本/权限范围；写操作主动失效；长任务使用 job 表/队列，禁止把缓存当唯一事实源。

10. **审计日志不完整且未统一抽象**（🔴）  
    已有：调拨 `ai_transfer_audit` 保存前后快照。缺失：采购保存/确认、部门人数修改、AI 配置、报告生成/下载、同步任务、登录和权限失败审计。现有审计字段也没有 request id、IP、user-agent、失败原因。  
    整改：建立统一 `audit_event`（actor、action、resource、before/after、result、request_id、ip、user_agent、created_at）；敏感字段脱敏；审计表只追加、按时间分区/归档并限制查询权限。

11. **日志不可观测、未证明脱敏**（🟡）  
    证据：`scheduler.py`、`llm_service.py` 等使用普通文本 logger；无统一 logging config、JSON、request id、轮转和保留策略；异常消息直接写入日志。  
    整改：结构化日志字段（时间、级别、request_id、用户、路由、耗时、结果）；Authorization、API key、密码、完整用户输入和 SQL 参数必须脱敏；配置 uvicorn access log、轮转、集中采集和告警。

12. **AI 配置密钥以明文存储/可写，AI 调用缺少治理**（🔴）  
    证据：`AiConfig.config_value` 为 Text；`system.py:101-136` 允许管理员写入 AI key，`llm_service.py` 直接读取并发起外部请求；请求超时约 60 秒，缺少配额、重试上限、审计和数据脱敏策略。  
    整改：密钥使用 KMS/环境密钥引用或加密列；读取接口只返回 configured；按 provider allowlist 限制 URL，禁止 SSRF；统一超时、熔断、限流、重试和费用/调用量审计；明确哪些资产字段可发送到外部模型。

13. **权限范围存在一致性风险**（🟡）  
    证据：`data_scope.py:7-16` 仅按 company/dept 和 role_name 中文字符串判断；`system.py:47-83` 部门、公司、分类、状态列表对普通用户返回全量；部分报告/采购接口按创建人过滤，部分统计依赖服务内 scope，规则不统一。  
    整改：以稳定 role/permission code 替代名称匹配；统一 scope dependency；逐接口定义可见字段和操作权限；对导出、报告、调拨审计做越权测试。

14. **报告月份口径不真实**（🟡）  
    证据：`report_service.py:34-46` 用当前数据生成任意指定月份报告，页面也提示当前快照。  
    影响：历史月报不能作为历史时点事实。  
    整改：选择“当前快照报告”或建立按月快照/事实表；报告元数据记录数据截止时间、算法版本和是否 AI 润色。

15. **下载路径虽做 basename 限制，但缺少资源级授权和生命周期治理**（🟡）  
    证据：`dashboard.py:85-92` 仅验证文件名存在，未校验该文件是否属于当前用户可见报告；`reports` 目录长期累积。  
    整改：先查 `ai_report` 记录再下载；使用不可猜测 ID/短时签名；限制文件大小和 MIME；增加过期清理与病毒扫描策略。

### P2 / 暂记与验证项

16. **国产数据库兼容未实测**（🟡）
    当前依赖 `mysql+pymysql`；DDL 使用 MySQL 语法。需在达梦/openGauss 建立 schema、分页、日期、JSON/Text、事务和索引兼容性测试矩阵，再决定 SQLAlchemy 方言和迁移策略。

17. **前端 token 存 localStorage**（🟡）
    证据：`frontend/src/utils/request.js:11`、`store/index.js:5-19`。一旦发生 XSS，token 可被读取。短期应加强 CSP、依赖审计和输入渲染约束；长期改为 HttpOnly Secure SameSite cookie，并配合 CSRF 防护。

18. **前端构建包偏大、交互错误治理不足**（🟡）
    本次构建出现约 1.0MB 和 1.2MB 的 JS chunk；请求层统一 30 秒超时，但未按接口区分读/写/AI 超时，也没有全局 loading、重试和任务进度模型。应做路由级懒加载、ECharts/Element 按需拆分，并将长任务改为异步状态展示。

19. **测试体系缺失**（🔴）
    未发现 pytest 测试目录或 API contract test；本次只能验证编译、构建、健康接口和未授权 401。需要补充认证、权限、分页边界、迁移、并发状态机、下载授权、AI 降级、超时取消、国产数据库兼容测试。

## 3. 按主题审计结论

| 主题 | 当前状态 | 结论 |
|---|---|---|
| 数据结构 | 资产/字典/预测/报告/调拨表已分离 | 缺统一审计、任务、快照、版本字段；部分金额用 Float |
| 索引 | 主键及少量单列索引 | 聚合和筛选缺少 EXPLAIN 驱动的联合索引 |
| 缓存 | 无 | 仪表盘、字典、统计重复查库 |
| 队列 | APScheduler 进程内 | 不适合长任务、扩容和失败重试 |
| Session | 有依赖注入，但 service 自建 session | 事务/异常关闭不一致 |
| SSL | 无 HTTPS 配置 | 生产阻断项 |
| 日志 | 普通 Python logger | 缺结构化、追踪、脱敏、轮转 |
| 审计架构 | 仅调拨较完整 | 业务写操作覆盖不足 |
| 交互设计 | 菜单二级化、请求取消已有 | 卡顿时缺任务进度和可解释错误状态 |
| 代码结构 | API/service/model 分层 | 连接、事务、错误处理和权限策略尚未统一 |
| API | OpenAPI 可生成，保护路由有 Bearer | 缺 schema 版本、统一错误码、分页约束和完整 E2E |
| 数据安全 | 有基础 JWT/管理员依赖 | 默认密钥、MD5、明文 AI key、localStorage 风险高 |
| 运维 | Docker Compose 可启动 | 缺 healthcheck、资源限制、备份恢复、迁移、监控、TLS |

## 4. 整改路线与验收标准

### P0（上线前）

1. 密钥/密码移出代码与 compose，启动拒绝默认值；验证：配置扫描无明文秘密，旧 JWT 全部失效。
2. TLS、CORS 白名单、安全头；验证：HTTP 自动跳 HTTPS，跨域仅允许配置域名。
3. 迁移工具和版本表；验证：空库、升级库、回滚/失败场景均可重复执行。
4. 长任务 job 化；验证：请求在 1 秒内返回 job_id，任务可查询进度、失败、重试和取消。
5. 最小权限数据库账号；验证：源库账号执行写 SQL 被拒绝，应用账号无建库/建用户权限。

### P1（稳定性）

1. 统一 session/事务/错误码和分页校验。
2. 基于生产 SQL 采样执行 `EXPLAIN`，补联合索引和汇总表。
3. 统一审计事件与结构化日志；验证可按 request_id 还原一次请求及其写操作。
4. AI 密钥加密/引用、URL allowlist、超时熔断和调用审计。
5. 端到端 API 测试和权限矩阵测试，覆盖普通用户、部门用户、管理员。

### P2（优化与国产化验证）

1. Redis 缓存与失效策略、路由级前端拆包。
2. 达梦/openGauss 双数据库 CI 或至少每版本兼容性回归。
3. 报告月度快照、文件保留和灾备演练。

## 5. 本次验证记录

- `python -m compileall -q backend/app`：通过。
- `npm.cmd run build`：通过；存在大 chunk 警告风险，未阻断构建。
- `GET http://127.0.0.1:8000/health`：200，`{"status":"ok"}`。
- `GET /openapi.json`：200，共扫描到认证、仪表盘、查询、预测、采购、调拨、系统等路由。
- 未带 token 请求受保护业务接口：401。
- 未完成项：带有效管理员 token 的业务 E2E、真实数据库 EXPLAIN/慢查询、TLS 握手、备份恢复、压力测试、达梦/openGauss 实测。

## 6. 建议的下一份执行清单

优先创建“P0 安全与任务治理阶段清单”，明确环境变量命名、密钥注入方式、CORS/HTTPS 拓扑、job 状态机、迁移工具和验收脚本；该清单评审通过后再改代码。审计报告中的 P1/P2 项不应在没有接口契约和数据口径确认时直接散改。
