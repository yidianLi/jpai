# Stage 1：闲置资产调拨闭环开发清单

## 目标

实现资产管理员发起调拨建议、接收部门确认或拒绝、管理员执行调拨、资产字段更新和全量审计。该阶段不依赖品牌和维修数据质量。

## 固定业务规则

- 参与角色：资产管理员、接收部门用户。
- 接收部门只能处理目标部门为本人数据范围内的建议。
- 只有资产管理员可以执行已确认建议。
- 执行时修改 `ai_asset.company_id`（如填写）、`dept_id`、`dept_name`、`position`、`user_name`。
- 执行前必须校验资产仍存在、仍处于可调拨状态、没有其他未完成建议，且字段版本未变化。
- 任何拒绝、取消和执行都必须填写或保留操作备注。

## 后端实现

1. 新增 `backend/app/models/transfer.py`，实现 `AiTransferSuggestion` 和 `AiTransferAudit`，字段以 `docs/execution-plan.md` 为准。
2. 新增 Pydantic schema，禁止客户端提交状态、原始字段快照或操作人字段。
3. 新增 `backend/app/services/transfer_service.py`，集中实现创建、确认、拒绝、执行、取消、详情和审计查询。
4. 新增 `backend/app/api/transfer.py` 并在 `main.py` 注册 `/api/transfer`。
5. 执行操作使用事务；更新资产时带上原始 `change_date` 或 `sync_time` 条件，发生 0 行更新返回 HTTP 409。
6. 执行成功后写入 before/after JSON 快照；目标数据库不支持 JSON 时使用 TEXT 序列化。
7. 所有列表接口分页，默认 20 条，最大 100 条；详情和审计接口只返回当前用户有权访问的数据。
8. 不修改源系统，不自动调用采购流程。

## 状态迁移

```text
draft -> pending_receiver -> confirmed -> completed
                         \-> rejected
draft/pending_receiver/confirmed -> cancelled
```

非法迁移返回 HTTP 409。完成、拒绝和取消为终态。

## 前端实现

1. 新增 `frontend/src/views/transfer/Index.vue`。
2. 增加“待我处理、我发起的、已完成”三个视图。
3. 创建建议时展示资产当前部门、位置、使用人和状态；目标部门必填。
4. 接收部门提供确认/拒绝操作；管理员在确认后提供执行按钮。
5. 详情抽屉展示原值、目标值、状态时间线、操作人和审计记录。
6. 409 冲突时提示“资产已发生变化，请刷新后重新处理”，不得自动覆盖。
7. 不在前端决定权限；按钮隐藏仅作为交互优化。

## API 验收

- 创建草稿和提交确认各成功一次。
- 接收部门确认后状态为 `confirmed`，拒绝后状态为 `rejected`。
- 管理员执行后状态为 `completed`，资产四个字段正确更新。
- 执行后审计记录包含完整 before/after 快照。
- 重复执行、非法状态迁移、无权限执行和并发变更分别返回明确错误。
- 普通用户不能读取其他数据范围的调拨建议。

## 测试与交付

- 增加 service 层状态机和并发冲突测试。
- 增加 API 权限、分页、409 和事务回滚测试。
- 前端执行 `npm run build`。
- 后端执行编译和测试。
- 执行 `git diff --check`。

## 代码端完成后返回

1. 修改/新增文件清单。
2. DDL 或迁移命令。
3. 测试命令和结果。
4. 手工端到端操作步骤和结果。
5. 已知限制及对 Stage 2 的影响。

## 实施记录（2026-08-31）

- 已新增调拨建议与审计模型、Pydantic 请求模型、服务层和 `/api/transfer` 路由。
- 已创建 `ai_transfer_suggestion`、`ai_transfer_audit` 数据表。
- 已接入前端 `/transfer` 页面、路由和 API 方法。
- 后端编译、路由注册检查和前端生产构建通过；服务重启后 `/health` 返回 `ok`。
- 已完成真实登录用户的端到端创建/确认/执行测试，详见下方验收记录。

## 真实登录端到端验收（2026-08-31）

已使用运行中的服务通过真实 HTTP 登录完成闭环，测试账号为 `admin`（管理员权限），目标部门为 `dept_id=3`：

1. `POST /api/auth/login` 登录成功，取得 Bearer token。
2. `POST /api/idle/refresh` 刷新闲置池，共识别 26 台闲置资产。
3. 选取闲置资产 `asset_id=244137`（闲置 1035 天），创建调拨建议，返回 `id=1`、状态 `pending_receiver`。
4. 使用登录 token 调用接收确认，状态变为 `confirmed`。
5. 使用管理员 token 调用执行，状态变为 `completed`。
6. 审计接口返回 3 条记录（`created`、`receiver_confirm`、`execute`）；资产回读确认部门、位置和使用人已更新，`is_idle` 已清零。

注意：调拨创建校验 `ai_asset.is_idle`，因此验收前必须先刷新闲置池，使闲置池记录与资产主表标记保持一致。
