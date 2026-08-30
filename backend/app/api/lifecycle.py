"""资产生命周期档案接口"""
from fastapi import APIRouter, Depends
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
