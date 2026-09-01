"""
AI数智化资产管理系统 - 主入口
支持信创环境部署
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .database import ai_engine, Base
from .core.scheduler import start_scheduler
from .core.migrations import run_migrations
from .api import dashboard, check, idle, lifecycle, scrap, query, system, auth, transfer, insight, procurement, orchestration, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表、启动定时任务
    # Avoid blocking the server on every restart when the database is unavailable.
    if settings.CREATE_TABLES_ON_STARTUP:
        Base.metadata.create_all(bind=ai_engine)
    if settings.ENVIRONMENT.lower() in {"production", "prod"}:
        run_migrations(ai_engine, settings.MIGRATIONS_DIR)
    if settings.SYNC_ENABLED:
        start_scheduler()
    yield
    # 关闭


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["认证"])
app.include_router(dashboard.router, prefix=f"{settings.API_PREFIX}/dashboard", tags=["领导驾驶舱"])
app.include_router(check.router, prefix=f"{settings.API_PREFIX}/check", tags=["智能盘点"])
app.include_router(idle.router, prefix=f"{settings.API_PREFIX}/idle", tags=["闲置盘活"])
app.include_router(lifecycle.router, prefix=f"{settings.API_PREFIX}/lifecycle", tags=["生命周期档案"])
app.include_router(scrap.router, prefix=f"{settings.API_PREFIX}/scrap", tags=["报废决策"])
app.include_router(query.router, prefix=f"{settings.API_PREFIX}/query", tags=["智能查询"])
app.include_router(system.router, prefix=f"{settings.API_PREFIX}/system", tags=["系统管理"])


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(transfer.router, prefix=f"{settings.API_PREFIX}/transfer", tags=["资产调拨"])
app.include_router(insight.router, prefix=f"{settings.API_PREFIX}/insight", tags=["品牌型号分析"])
app.include_router(procurement.router, prefix=f"{settings.API_PREFIX}/procurement", tags=["采购建议"])
app.include_router(orchestration.router, prefix=f"{settings.API_PREFIX}/orchestration", tags=["多智能体编排"])

app.include_router(jobs.router, prefix=f'{settings.API_PREFIX}/jobs', tags=['jobs'])
