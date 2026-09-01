from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..services.procurement_service import ProcurementService
from ..services.llm_service import LLMService
import re
import json
from datetime import datetime
from ..models.procurement import AiProcurementSuggestion

router = APIRouter()

class AiPreviewRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=2000)

class SaveSuggestionRequest(BaseModel):
    class_id: int | None = None
    quantity: int = Field(..., ge=1, le=100000)
    preview: dict

@router.post('/preview')
def preview(class_id: int = None, quantity: int = 1, dept_id: int = None, user: AiUser = Depends(get_current_user)):
    if quantity < 1 or quantity > 100000: raise HTTPException(422, '需求数量必须在1到100000之间')
    svc = ProcurementService()
    try: return svc.preview(user, class_id, quantity, dept_id)
    finally: svc.close()

@router.post('/suggestions')
def save_suggestion(payload: SaveSuggestionRequest, user: AiUser = Depends(get_current_user)):
    db = ProcurementService().db
    row = AiProcurementSuggestion(class_id=payload.class_id, quantity=payload.quantity, payload=json.dumps(payload.preview, ensure_ascii=False), created_by=user.user_id, created_at=datetime.now())
    db.add(row); db.commit(); db.refresh(row); result={'id': row.id, 'status': row.status}; db.close(); return result

@router.get('/suggestions')
def list_suggestions(user: AiUser = Depends(get_current_user)):
    db = ProcurementService().db
    rows = db.query(AiProcurementSuggestion).filter(AiProcurementSuggestion.created_by == user.user_id).order_by(AiProcurementSuggestion.id.desc()).limit(100).all()
    result=[{'id':r.id,'class_id':r.class_id,'quantity':r.quantity,'status':r.status,'created_at':r.created_at} for r in rows]; db.close(); return {'list': result}

@router.post('/suggestions/{suggestion_id}/confirm')
def confirm_suggestion(suggestion_id: int, user: AiUser = Depends(get_current_user)):
    db = ProcurementService().db; row = db.query(AiProcurementSuggestion).filter(AiProcurementSuggestion.id == suggestion_id, AiProcurementSuggestion.created_by == user.user_id).first()
    if not row: db.close(); raise HTTPException(404, '采购建议不存在')
    if row.status != 'draft': db.close(); raise HTTPException(409, '采购建议当前状态不可确认')
    row.status='confirmed'; row.confirmed_by=user.user_id; row.confirmed_at=datetime.now(); db.commit(); db.close(); return {'id': suggestion_id, 'status': 'confirmed'}

@router.post('/ai-preview')
async def ai_preview(payload: AiPreviewRequest, user: AiUser = Depends(get_current_user)):
    request = payload.request.strip()
    llm = LLMService()
    raw = await llm.chat(request, '请仅返回JSON：{"quantity":整数,"class_id":整数或null}。无法识别时quantity为1。')
    quantity, class_id = 1, None
    try:
        import json
        value = json.loads(raw[raw.find('{'):raw.rfind('}') + 1])
        quantity, class_id = int(value.get('quantity', 1)), value.get('class_id')
    except Exception:
        match = re.search(r'(\d+)\s*(台|件|套|个)', request)
        if match: quantity = int(match.group(1))
    svc = ProcurementService()
    try:
        data = svc.preview(user, class_id, min(max(quantity, 1), 100000))
        data.update({"ai_used": bool(raw), "provider": llm.provider, "model": llm.model})
        return data
    finally: svc.close()
