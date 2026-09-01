from fastapi import APIRouter, Depends
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..services.insight_service import InsightService
from ..services.llm_service import LLMService
from pydantic import BaseModel
from ..core.ai_governance import outbound_payload
import json

router = APIRouter()

class ExplainRequest(BaseModel):
    metrics: dict
    evidence: dict = {}

@router.get('/brands')
def brands(class_id: int = None, dept_id: int = None, min_sample: int = 10, user: AiUser = Depends(get_current_user)):
    svc = InsightService()
    try: return {"list": svc.brands(user, class_id, dept_id, min_sample), "data_quality": {"brand_source": "ai_asset.brand", "repair_bill_type": 10700, **svc.quality_metadata()}}
    finally: svc.close()

@router.get('/models')
def models(brand: str = None, class_id: int = None, min_sample: int = 10, user: AiUser = Depends(get_current_user)):
    svc = InsightService()
    try: return {"list": svc.models(user, brand, class_id, min_sample), "data_quality": {"repair_bill_type": 10700, **svc.quality_metadata()}}
    finally: svc.close()

@router.get('/models/evidence')
def model_evidence(brand: str, model: str, class_id: int = None, user: AiUser = Depends(get_current_user)):
    svc = InsightService()
    try:
        rows = svc.models(user, brand, class_id, 1)
        return {'list': [r for r in rows if r.get('model') == model], 'evidence_query': '按品牌、型号和类别聚合资产台账，并关联 bill_type=10700 维修工单'}
    finally: svc.close()

@router.post('/explain')
async def explain(payload: ExplainRequest, user: AiUser = Depends(get_current_user)):
    safe = outbound_payload({"metrics": payload.metrics, "evidence": payload.evidence}, {"metrics", "evidence"})
    llm = LLMService(); text = await llm.chat(json.dumps(safe, ensure_ascii=False), '请用中文给出不超过120字的采购分析说明，只陈述数据支持的结论。', operation="insight_explain", user_id=user.user_id)
    return {'explanation': text or '当前模型不可用，请依据页面指标和证据判断。', 'ai_used': bool(text), 'provider': llm.provider, 'model': llm.model}
