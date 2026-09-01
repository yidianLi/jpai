"""闲置资产盘活接口"""
from fastapi import APIRouter, Depends, Query
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..services.idle_service import IdleService

router = APIRouter()


@router.get("/pool")
def idle_pool(dept: str = None, min_days: int = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200), user: AiUser = Depends(get_current_user)):
    svc = IdleService()
    data = svc.get_idle_list(dept, None, min_days, page, size)
    svc.close()
    return data


@router.get("/stats")
def idle_stats(user: AiUser = Depends(get_current_user)):
    svc = IdleService()
    data = svc.get_idle_stats()
    svc.close()
    return data


@router.post("/refresh")
def refresh_idle(user: AiUser = Depends(get_current_user)):
    svc = IdleService()
    count = svc.refresh_idle_pool()
    svc.close()
    return {"message": f"闲置池已刷新，共{count}台闲置资产"}


@router.post("/{idle_id}/transfer")
def mark_transfer(idle_id: int, user: AiUser = Depends(get_current_user)):
    svc = IdleService()
    svc.mark_transferred(idle_id, user.user_name)
    svc.close()
    return {"message": "已标记为调拨"}
