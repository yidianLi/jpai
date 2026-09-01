"""系统管理接口：数据同步、字典、部门人数维护、配置"""
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..database import get_ai_db
from ..models.dict import AiUser, AiDepartment, AiCompany, AiAssetClass, AiAssetState
from ..models.report import AiConfig
from ..models.audit import AiAuditEvent
from ..models.ai_governance import AiUsageLog
from sqlalchemy import func
from ..core.auth import get_current_user, require_admin
from ..services.sync_service import SyncService
from ..core.audit import record as record_audit
from ..core.data_scope import has_permission

router = APIRouter()

@router.get("/ai-usage")
def ai_usage(days: int = 30, db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin)):
    """AI调用量、失败率和成本汇总（管理员）。"""
    days = min(max(days, 1), 365)
    since = datetime.now() - timedelta(days=days)
    q = db.query(AiUsageLog).filter(AiUsageLog.created_at >= since)
    total = q.count(); failed = q.filter(AiUsageLog.status == "failed").count(); blocked = q.filter(AiUsageLog.status == "blocked").count()
    summary = db.query(func.coalesce(func.sum(AiUsageLog.cost), 0), func.coalesce(func.sum(AiUsageLog.input_tokens), 0), func.coalesce(func.sum(AiUsageLog.output_tokens), 0)).filter(AiUsageLog.created_at >= since).first()
    by_operation = db.query(AiUsageLog.operation, func.count(AiUsageLog.id), func.coalesce(func.sum(AiUsageLog.cost), 0)).filter(AiUsageLog.created_at >= since).group_by(AiUsageLog.operation).all()
    return {"days": days, "total": total, "failed": failed, "blocked": blocked, "failure_rate": round(failed / total, 4) if total else 0,
            "cost": float(summary[0] or 0), "input_tokens": int(summary[1] or 0), "output_tokens": int(summary[2] or 0),
            "by_operation": [{"operation": op, "calls": n, "cost": float(cost or 0)} for op, n, cost in by_operation]}

@router.get("/ai-usage/logs")
def ai_usage_logs(page: int = 1, size: int = 50, operation: str = None, result: str = None,
                  db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin)):
    if page < 1 or size < 1 or size > 200: raise HTTPException(422, "invalid pagination")
    query = db.query(AiUsageLog)
    if operation: query = query.filter(AiUsageLog.operation == operation)
    if result: query = query.filter(AiUsageLog.status == result)
    total = query.count(); rows = query.order_by(AiUsageLog.created_at.desc(), AiUsageLog.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "list": [
        {"id": row.id, "user_id": row.user_id, "provider": row.provider, "model": row.model,
         "operation": row.operation, "request_id": row.request_id, "status": row.status,
         "input_tokens": row.input_tokens, "output_tokens": row.output_tokens, "cost": row.cost,
         "latency_ms": row.latency_ms, "error_code": row.error_code,
         "redacted_input": row.redacted_input, "created_at": row.created_at} for row in rows]}

@router.get("/audit-events")
def list_audit_events(page: int = 1, size: int = 50, db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin)):
    if page < 1 or size < 1 or size > 200:
        raise HTTPException(422, "page must be >= 1 and size must be between 1 and 200")
    query = db.query(AiAuditEvent).order_by(AiAuditEvent.created_at.desc(), AiAuditEvent.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "list": [
        {"id": row.id, "actor_user_id": row.actor_user_id, "actor_name": row.actor_name,
         "action": row.action, "resource": row.resource, "result": row.result,
         "request_id": row.request_id, "ip": row.ip, "created_at": row.created_at}
        for row in rows
    ]}

@router.get("/performance/explain")
def explain_asset_query(db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin)):
    from sqlalchemy import text
    statement = text("EXPLAIN SELECT asset_id FROM ai_asset WHERE company_id = :company_id AND dept_id = :dept_id AND state_id IS NOT NULL AND is_idle = :is_idle ORDER BY asset_id DESC LIMIT 200")
    try:
        rows = db.execute(statement, {"company_id": user.company_id or 0, "dept_id": user.dept_id or 0, "is_idle": 1}).mappings().all()
        return {"query": "asset_scope_state_idle", "plan": [dict(row) for row in rows]}
    except Exception as exc:
        db.rollback()
        raise HTTPException(503, f"EXPLAIN unavailable: {exc}")


class AiRuntimeConfig(BaseModel):
    enabled: bool = True
    provider: str = Field(default="openai", pattern="^(openai|ollama)$")
    base_url: str = ""
    api_key: str = ""
    model: str = ""


@router.post("/sync/all")
def sync_all(user: AiUser = Depends(require_admin)):
    """手动触发全量同步"""
    svc = SyncService()
    result = svc.sync_all()
    return result


@router.post("/sync/dictionaries")
def sync_dict(user: AiUser = Depends(require_admin)):
    svc = SyncService()
    svc.sync_dictionaries()
    svc.close()
    return {"message": "字典同步完成"}


@router.post("/sync/assets")
def sync_assets(user: AiUser = Depends(require_admin)):
    svc = SyncService()
    svc.sync_assets()
    svc.close()
    return {"message": "资产同步完成"}


@router.get("/departments")
def list_departments(db: Session = Depends(get_ai_db), user: AiUser = Depends(get_current_user)):
    query = db.query(AiDepartment)
    if not has_permission(user, "dictionary.read.all"):
        if user.company_id: query = query.filter(AiDepartment.company_id == user.company_id)
        if user.dept_id: query = query.filter(AiDepartment.dept_id == user.dept_id)
    rows = query.all()
    return [{"dept_id": r.dept_id, "dept_name": r.dept_name, "company_id": r.company_id,
             "headcount": r.headcount, "headcount_source": "同步用户（在职）" if r.headcount else "未配置", "parent_id": r.parent_id} for r in rows]


@router.put("/departments/{dept_id}/headcount")
def update_headcount(dept_id: int, headcount: int, db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin)):
    dept = db.query(AiDepartment).filter(AiDepartment.dept_id == dept_id).first()
    if not dept:
        raise HTTPException(404, "部门不存在")
    dept.headcount = headcount
    db.commit()
    return {"message": "部门人数已更新"}


@router.get("/companies")
def list_companies(db: Session = Depends(get_ai_db), user: AiUser = Depends(get_current_user)):
    query = db.query(AiCompany)
    if not has_permission(user, "dictionary.read.all") and user.company_id:
        query = query.filter(AiCompany.company_id == user.company_id)
    rows = query.all()
    return [{"company_id": r.company_id, "company_name": r.company_name, "parent_id": r.parent_id} for r in rows]


@router.get("/asset-classes")
def list_classes(db: Session = Depends(get_ai_db), user: AiUser = Depends(get_current_user)):
    rows = db.query(AiAssetClass).all()
    return [{"class_id": r.class_id, "class_name": r.class_name, "parent_id": r.parent_id,
             "class_code": r.class_code, "use_year": r.use_year, "is_lowest": r.is_lowest} for r in rows]


@router.get("/asset-states")
def list_states(db: Session = Depends(get_ai_db), user: AiUser = Depends(get_current_user)):
    rows = db.query(AiAssetState).all()
    return [{"state_id": r.state_id, "state_name": r.state_name, "state_label": r.state_label} for r in rows]


@router.get("/config")
def get_config(db: Session = Depends(get_ai_db), user: AiUser = Depends(get_current_user)):
    rows = db.query(AiConfig).all()
    return {r.config_key: r.config_value for r in rows}


@router.put("/config/{key}")
def update_config(key: str, value: str, db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin)):
    cfg = db.query(AiConfig).filter(AiConfig.config_key == key).first()
    if cfg:
        cfg.config_value = value
    else:
        cfg = AiConfig(config_key=key, config_value=value)
        db.add(cfg)
    db.commit()
    return {"message": "配置已更新"}


@router.get("/ai-config")
def get_ai_config(db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin)):
    keys = ["ai_enabled", "ai_provider", "ai_base_url", "ai_api_key", "ai_model"]
    values = {row.config_key: row.config_value for row in db.query(AiConfig).filter(AiConfig.config_key.in_(keys)).all()}
    api_key = values.get("ai_api_key", "")
    return {
        "enabled": values.get("ai_enabled", "true").lower() == "true",
        "provider": values.get("ai_provider", "openai"),
        "base_url": values.get("ai_base_url", ""),
        "model": values.get("ai_model", ""),
        "api_key_configured": bool(api_key),
    }


@router.put("/ai-config")
def update_ai_config(payload: AiRuntimeConfig, request: Request, db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin)):
    if payload.provider == "openai" and (not payload.base_url or not payload.model):
        raise HTTPException(422, "线上AI需要填写接口地址和模型名称")
    updates = {
        "ai_enabled": str(payload.enabled).lower(), "ai_provider": payload.provider,
        "ai_base_url": payload.base_url.strip(), "ai_model": payload.model.strip(),
    }
    # 空密钥代表不修改既有密钥，避免回读时暴露敏感配置。
    if payload.api_key.strip():
        updates["ai_api_key"] = payload.api_key.strip()
    existing = {row.config_key: row for row in db.query(AiConfig).filter(AiConfig.config_key.in_(updates)).all()}
    for key, value in updates.items():
        if key in existing:
            existing[key].config_value = value
        else:
            db.add(AiConfig(config_key=key, config_value=value, description="AI运行配置"))
    record_audit(db, user, "system.ai_config.update", "ai_config", after={"enabled": payload.enabled, "provider": payload.provider, "model": payload.model}, request=request)
    db.commit()
    return {"message": "AI配置已保存并立即生效"}
