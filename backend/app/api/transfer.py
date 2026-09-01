from fastapi import APIRouter, Depends
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..schemas.transfer import TransferCreate, TransferDecision
from ..services.transfer_service import TransferService

router = APIRouter()

def run(method, *args):
    svc = TransferService()
    try: return getattr(svc, method)(*args)
    finally: svc.close()

@router.get("/suggestions")
def list_suggestions(status: str = None, page: int = 1, size: int = 20, user: AiUser = Depends(get_current_user)):
    return run("list", user, status, page, size)

@router.post("/suggestions")
def create_suggestion(payload: TransferCreate, user: AiUser = Depends(get_current_user)):
    return run("create", payload, user)

@router.get("/suggestions/{suggestion_id}")
def get_suggestion(suggestion_id: int, user: AiUser = Depends(get_current_user)):
    return run("get", suggestion_id, user)

@router.post("/suggestions/{suggestion_id}/receiver-confirm")
def receiver_confirm(suggestion_id: int, payload: TransferDecision = TransferDecision(), user: AiUser = Depends(get_current_user)):
    return run("decide", suggestion_id, user, True, payload.remark)

@router.post("/suggestions/{suggestion_id}/receiver-reject")
def receiver_reject(suggestion_id: int, payload: TransferDecision = TransferDecision(), user: AiUser = Depends(get_current_user)):
    return run("decide", suggestion_id, user, False, payload.remark)

@router.post("/suggestions/{suggestion_id}/execute")
def execute_suggestion(suggestion_id: int, user: AiUser = Depends(get_current_user)):
    return run("execute", suggestion_id, user)

@router.post("/suggestions/{suggestion_id}/cancel")
def cancel_suggestion(suggestion_id: int, payload: TransferDecision = TransferDecision(), user: AiUser = Depends(get_current_user)):
    return run("cancel", suggestion_id, user, payload.remark)

@router.get("/suggestions/{suggestion_id}/audit")
def get_audit(suggestion_id: int, user: AiUser = Depends(get_current_user)):
    return run("audits", suggestion_id, user)
