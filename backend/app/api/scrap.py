"""报废决策接口"""
from fastapi import APIRouter, Depends, Query
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..services.scrap_service import ScrapService

router = APIRouter()


@router.get("/expire-list")
def expire_list(days: int = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200), user: AiUser = Depends(get_current_user)):
    svc = ScrapService()
    data = svc.get_expire_list(days, None, page, size)
    svc.close()
    return data


@router.post("/evaluate/{asset_id}")
def evaluate(asset_id: int, user: AiUser = Depends(get_current_user)):
    svc = ScrapService()
    data = svc.evaluate_asset(asset_id)
    svc.close()
    return data


@router.post("/batch-evaluate")
def batch_evaluate(asset_ids: list[int], user: AiUser = Depends(get_current_user)):
    svc = ScrapService()
    data = svc.batch_evaluate(asset_ids)
    svc.close()
    return data
