"""资产生命周期档案接口"""
from fastapi import APIRouter, Depends, HTTPException
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..services.lifecycle_service import LifecycleService

router = APIRouter()


@router.get("/asset/{asset_id}")
def asset_detail(asset_id: int, user: AiUser = Depends(get_current_user)):
    svc = LifecycleService()
    data = svc.get_asset_detail(asset_id)
    svc.close()
    if not data:
        return {"error": "资产不存在"}
    return data


@router.get("/data-quality")
def data_quality(user: AiUser = Depends(get_current_user)):
    svc = LifecycleService()
    data = svc.get_data_quality_report()
    svc.close()
    return data

@router.get("/quality-issues")
def quality_issues(status: str = None, issue_type: str = None, page: int = 1, size: int = 20, user: AiUser = Depends(get_current_user)):
    svc = LifecycleService()
    try: return svc.list_quality_issues(status, issue_type, page, min(size, 100))
    finally: svc.close()

@router.post("/quality-issues/{issue_id}/action")
def quality_issue_action(issue_id: int, action: str, assignee: str = None, remark: str = None, user: AiUser = Depends(get_current_user)):
    svc = LifecycleService()
    try:
        result = svc.update_quality_issue(issue_id, action, user.user_name, assignee, remark)
        if not result: raise HTTPException(404, "质量问题不存在")
        return {"message": "操作成功", "status": result.status}
    except ValueError as exc: raise HTTPException(400, str(exc))
    finally: svc.close()


@router.get("/abnormal-assets")
def abnormal_assets(issue_type: str = None, page: int = 1, size: int = 20, user: AiUser = Depends(get_current_user)):
    svc = LifecycleService()
    data = svc.get_abnormal_assets(issue_type, page, size)
    svc.close()
    return data


@router.post("/asset/{asset_id}/clean")
def clean_asset(asset_id: int, field: str, value: str, reason: str, user: AiUser = Depends(get_current_user)):
    svc = LifecycleService()
    data = svc.clean_asset(asset_id, field, value, reason, user.user_name)
    svc.close()
    return {"message": "清洗标注已保存", "data": data}
