"""系统管理接口：数据同步、字典、部门人数维护、配置"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_ai_db
from ..models.dict import AiUser, AiDepartment, AiCompany, AiAssetClass, AiAssetState
from ..models.report import AiConfig
from ..core.auth import get_current_user, require_admin
from ..services.sync_service import SyncService

router = APIRouter()


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
    rows = db.query(AiDepartment).all()
    return [{"dept_id": r.dept_id, "dept_name": r.dept_name, "company_id": r.company_id,
             "headcount": r.headcount, "parent_id": r.parent_id} for r in rows]


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
    rows = db.query(AiCompany).all()
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
