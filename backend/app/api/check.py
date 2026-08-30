"""智能盘点接口"""
from fastapi import APIRouter, Depends
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..services.check_service import CheckService

router = APIRouter()


@router.get("/tasks")
def check_tasks(user: AiUser = Depends(get_current_user)):
    svc = CheckService()
    data = svc.get_check_tasks()
    svc.close()
    return data


@router.get("/tasks/{check_bid}/detail")
def check_detail(check_bid: int, state: int = None, page: int = 1, size: int = 20, user: AiUser = Depends(get_current_user)):
    svc = CheckService()
    data = svc.get_check_detail(check_bid, state, page, size)
    svc.close()
    return data


@router.get("/tasks/{check_bid}/diagnosis")
def check_diagnosis(check_bid: int, user: AiUser = Depends(get_current_user)):
    svc = CheckService()
    data = svc.get_check_diagnosis(check_bid)
    svc.close()
    return data


@router.get("/optimized-path")
def optimized_path(user: AiUser = Depends(get_current_user)):
    svc = CheckService()
    data = svc.get_optimized_check_path()
    svc.close()
    return data
