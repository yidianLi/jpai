# AI数智化资产管理系统

基于现有固定资产管理系统（简普科技 jpsoft_db4）数据库，构建的AI智能分析与决策辅助平台。与原系统并行运行，只读原库，AI做分析、预警、决策辅助。

## 系统架构

```
原系统(简普B/S) ──只读同步──> AI分析库(MySQL) ──> AI服务(FastAPI) ──> 前端(Vue3蓝色科技风)
                                      │
                                      └──> 本地大模型(Ollama + Qwen2.5)
```

## 六大功能模块

| 模块 | 功能 |
|------|------|
| 领导驾驶舱 | 资产总览大屏、关键指标、分类/状态/趋势图表、部门排名、实时预警、报告生成 |
| 智能盘点 | 盘点任务管理、结果智能诊断、盘亏/不符定位、整改建议、高价值盘亏预警 |
| 闲置盘活 | 闲置资产自动识别、闲置池管理、重复采购预警、调拨跟踪、盘活成效统计 |
| 资产档案 | 资产身份证、全生命周期时间轴、维修/盘点历史、数据质量检测与清洗标注 |
| 报废决策 | 到期分级预警、AI三档评估（报废/维修/调拨）、残值估算、处置建议、批量评估 |
| 智能查询 | 多维度筛选、自然语言查询（本地大模型）、采购需求预测、耗材预警、导出 |

## 技术栈

- **后端**: Python 3.11 + FastAPI + SQLAlchemy 2.0 + APScheduler
- **前端**: Vue3 + Element Plus + ECharts 5 + Pinia
- **数据库**: MySQL 8.0（AI库）+ 原系统MySQL（只读）
- **大模型**: Ollama + Qwen2.5-7B（本地部署，内网运行）
- **部署**: Docker Compose，支持信创环境（ARM64/AMD64）

## 快速开始

### 1. 配置数据库连接

编辑 `backend/.env` 或修改 `backend/app/config.py`：
- AI库配置（新建数据库）
- 原系统库配置（只读账号）

### 2. 启动服务

```bash
docker-compose up -d
```

服务启动后：
- 前端: http://localhost:8080
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 3. 拉取大模型

```bash
docker exec -it ai-asset-ollama ollama pull qwen2.5:7b
```

### 4. 初始化数据

登录系统后，进入「系统管理」→「数据同步」，点击「全量同步」。

默认管理员账号与原系统一致。

## 目录结构

```
ai-asset-management/
├── backend/
│   ├── app/
│   │   ├── api/           # API路由（6模块+认证+系统）
│   │   ├── core/          # 认证、数据权限、定时任务
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务逻辑（同步/分析/预警/闲置/报废/报告/预测/LLM）
│   │   ├── config.py      # 配置
│   │   ├── database.py    # 数据库连接
│   │   └── main.py        # 入口
│   ├── sql/init.sql       # 数据库初始化
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/         # 6个模块页面
│   │   ├── api/           # API封装
│   │   ├── router/        # 路由
│   │   ├── store/         # 状态管理
│   │   └── assets/styles/ # 蓝色科技风样式
│   ├── nginx.conf
│   └── package.json
├── docs/                   # 文档（代码完成后归档）
├── docker-compose.yml
└── README.md
```

## 信创环境适配

- CPU: 支持鲲鹏(ARM64)、飞腾(ARM64)、海光(x86)
- OS: 统信UOS V20、银河麒麟V10
- 数据库: MySQL（默认），可切换达梦DM8（通过SQLAlchemy抽象层）
- 大模型: Ollama原生支持ARM64，Q4量化可纯CPU运行
- 浏览器: 兼容奇安信、360安全浏览器等信创浏览器

## 政绩指标

系统自动计算并展示以下可量化指标：
- 资产盘点效率提升率
- 账实相符率
- 闲置资产盘活率
- 节约采购资金（重复采购拦截）
- 资产周转率
- 报废处置合规率
- 预警响应及时率

## 开发流程

讨论 → 出方案 → 改代码 → 更新文档 → git同步

代码完成后再更新文档，文档与代码并行。
