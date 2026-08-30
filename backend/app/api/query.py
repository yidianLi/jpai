"""智能查询与分析接口"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from ..database import get_ai_db
from ..models.dict import AiUser
from ..models.asset import AiAsset
from ..core.auth import get_current_user
from ..core.data_scope import apply_data_scope
from ..services.forecast_service import ForecastService
from ..services.llm_service import LLMService

router = APIRouter()


@router.get("/assets")
def query_assets(
    keyword: str = None, class_id: int = None, state_id: int = None,
    dept_id: int = None, company_id: int = None,
    min_price: float = None, max_price: float = None,
    start_date: str = None, end_date: str = None,
    is_idle: int = None,
    page: int = 1, size: int = 20,
    db: Session = Depends(get_ai_db),
    user: AiUser = Depends(get_current_user)
):
    """多维度资产查询"""
    q = db.query(AiAsset)
    if keyword:
        q = q.filter(or_(AiAsset.asset_name.like(f"%{keyword}%"), AiAsset.barcode.like(f"%{keyword}%"), AiAsset.model.like(f"%{keyword}%")))
    if class_id: q = q.filter(AiAsset.class_id == class_id)
    if state_id: q = q.filter(AiAsset.state_id == state_id)
    if dept_id: q = q.filter(AiAsset.dept_id == dept_id)
    if company_id: q = q.filter(AiAsset.company_id == company_id)
    if min_price is not None: q = q.filter(AiAsset.buy_price >= min_price)
    if max_price is not None: q = q.filter(AiAsset.buy_price <= max_price)
    if start_date: q = q.filter(AiAsset.buy_date >= start_date)
    if end_date: q = q.filter(AiAsset.buy_date <= end_date)
    if is_idle is not None: q = q.filter(AiAsset.is_idle == is_idle)
    q = apply_data_scope(q, user)
    total = q.count()
    rows = q.order_by(AiAsset.asset_id.desc()).offset((page-1)*size).limit(size).all()
    return {
        "total": total, "page": page, "size": size,
        "list": [{
            "asset_id": r.asset_id, "barcode": r.barcode, "asset_name": r.asset_name,
            "model": r.model, "brand": r.brand, "class_path": r.class_path,
            "state_name": r.state_name, "dept_name": r.dept_name,
            "company_name": r.company_name, "position": r.position,
            "responsible": r.responsible, "user_name": r.user_name,
            "buy_price": r.buy_price, "buy_date": str(r.buy_date) if r.buy_date else None,
            "current_value": r.current_value, "is_idle": r.is_idle,
            "expire_date": str(r.expire_date) if r.expire_date else None,
        } for r in rows]
    }


@router.post("/nl-query")
async def nl_query(query: str, user: AiUser = Depends(get_current_user)):
    """自然语言查询（本地大模型意图识别 + 模板执行）"""
    llm = LLMService()
    # 上下文：可用分类、部门、状态
    from ..database import AiSessionLocal
    db = AiSessionLocal()
    from ..models.dict import AiAssetClass, AiDepartment, AiAssetState
    classes = [c.class_name for c in db.query(AiAssetClass).filter(AiAssetClass.is_lowest == 1).limit(50).all()]
    depts = [d.dept_name for d in db.query(AiDepartment).limit(30).all()]
    states = [s.state_name for s in db.query(AiAssetState).limit(20).all()]
    db.close()

    result = await llm.nl_query(query, {"classes": classes, "depts": depts, "states": states})
    # 根据意图执行查询（简化版，实际可扩展更多模板）
    answer = ""
    if result.get("intent") == "count":
        answer = f"系统理解您的问题为统计类查询。请使用上方筛选条件查看具体数量，或提供更精确的分类/部门信息。"
    elif result.get("intent") == "value":
        answer = f"系统理解您的问题为价值统计类查询。当前资产总价值可在驾驶舱页面查看。"
    else:
        answer = result.get("answer_hint", "已记录您的查询，建议使用多维度筛选功能查看结果。")
    return {"intent": result.get("intent"), "filters": result.get("filters", {}), "answer": answer}


@router.get("/forecast")
def purchase_forecast(user: AiUser = Depends(get_current_user)):
    """采购需求预测"""
    svc = ForecastService()
    data = svc.get_forecast()
    svc.close()
    return data


@router.post("/forecast/compute")
def compute_forecast(months: int = 6, user: AiUser = Depends(get_current_user)):
    svc = ForecastService()
    data = svc.compute_forecast(months)
    svc.close()
    return data


@router.get("/llm-health")
def llm_health(user: AiUser = Depends(get_current_user)):
    """检查大模型状态"""
    from ..services.llm_service import llm_service
    return llm_service.check_health()
