"""智能查询与分析接口"""
from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from typing import Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from ..database import get_ai_db
from ..models.dict import AiUser
from ..models.asset import AiAsset
from ..core.auth import get_current_user
from ..core.data_scope import apply_data_scope
from ..services.forecast_service import ForecastService
from ..services.llm_service import LLMService
import csv, io

router = APIRouter()

ASSET_FIELD_ALIASES = {
    "asset_id": ["asset_id", "资产ID", "资产编号"], "barcode": ["barcode", "资产编码", "条码", "资产编号"],
    "asset_name": ["asset_name", "资产名称", "名称"], "model": ["model", "型号", "规格型号"],
    "brand": ["brand", "品牌"], "sn": ["sn", "序列号", "SN"], "class_path": ["class_path", "资产类别", "分类"],
    "state_name": ["state_name", "资产状态", "状态"], "company_name": ["company_name", "单位", "使用单位"],
    "dept_name": ["dept_name", "部门", "使用部门"], "position": ["position", "位置", "存放位置"],
    "responsible": ["responsible", "责任人"], "user_name": ["user_name", "使用人"],
    "buy_price": ["buy_price", "购置原值", "原值", "金额"], "supplier_name": ["supplier_name", "供应商"],
}

@router.post("/import-file")
async def import_file(file: UploadFile = File(...), commit: bool = False,
                      db: Session = Depends(get_ai_db), user: AiUser = Depends(get_current_user)):
    """解析资产 CSV/XLSX；默认仅预览，commit=true 才写入资产库。"""
    raw = await file.read()
    name = (file.filename or "").lower()
    if name.endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    elif name.endswith((".xlsx", ".xls")):
        try:
            from openpyxl import load_workbook
            ws = load_workbook(io.BytesIO(raw), read_only=True, data_only=True).active
            values = list(ws.values)
            rows = [dict(zip(values[0], row)) for row in values[1:] if any(row)] if values else []
        except Exception as exc:
            raise HTTPException(400, f"Excel解析失败: {exc}")
    else:
        raise HTTPException(400, "仅支持 CSV 或 XLSX 文件")
    headers = list(rows[0].keys()) if rows else []
    mapping = {}
    for field, aliases in ASSET_FIELD_ALIASES.items():
        header = next((h for h in headers if str(h).strip().lower() in {a.lower() for a in aliases}), None)
        if header: mapping[field] = header
    preview = [{field: row.get(header) for field, header in mapping.items()} for row in rows[:20]]
    if commit:
        inserted = 0
        for item in preview:
            if not item.get("asset_name") and not item.get("barcode"): continue
            db.add(AiAsset(**{k: v for k, v in item.items() if hasattr(AiAsset, k) and v not in (None, "")}))
            inserted += 1
        db.commit()
        return {"filename": file.filename, "mapping": mapping, "preview": preview, "rows": len(rows), "inserted": inserted}
    return {"filename": file.filename, "mapping": mapping, "preview": preview, "rows": len(rows), "inserted": 0}


@router.get("/assets")
def query_assets(
    keyword: str = None, class_id: int = None, state_id: int = None,
    dept_id: int = None, company_id: int = None,
    min_price: float = None, max_price: float = None,
    start_date: str = None, end_date: str = None,
    is_idle: int = None,
    page: int = 1, size: int = 20, include_total: bool = True,
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
    # 首屏预览可跳过 COUNT，避免大表筛选时先阻塞在总数统计上。
    total = None
    if include_total:
        try:
            total = q.count()
        except Exception:
            # 总数统计失败不应阻断当前页数据返回。
            db.rollback()
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
async def nl_query(payload: dict = Body(default=None), query: Optional[str] = None, user: AiUser = Depends(get_current_user)):
    """自然语言查询：模型负责理解，后端以受控查询执行统计。"""
    payload = payload or {}
    query = (payload.get("query") or query or "").strip()
    history = payload.get("history") or []
    if not query:
        raise HTTPException(status_code=422, detail="查询内容不能为空")
    if not isinstance(history, list):
        history = []
    history = [item for item in history[-10:] if isinstance(item, dict)]
    llm = LLMService()
    # 上下文：可用分类、部门、状态
    from ..database import AiSessionLocal
    db = AiSessionLocal()
    from ..models.dict import AiAssetClass, AiDepartment, AiAssetState
    try:
        classes = [c.class_name for c in db.query(AiAssetClass).filter(AiAssetClass.is_lowest == 1).limit(50).all()]
        depts = [d.dept_name for d in db.query(AiDepartment).limit(30).all()]
        states = [s.state_name for s in db.query(AiAssetState).limit(20).all()]
        result = await llm.nl_query(query, {"classes": classes, "depts": depts, "states": states, "conversation": history})

        # 模型返回异常或格式不稳定时，仍为常用资产问法提供受控兜底。
        lowered = query.lower()
        intent = result.get("intent")
        if intent not in {"count", "list", "rank", "trend", "value"}:
            intent = "rank" if any(word in query for word in ["哪个部门", "排名", "最多"]) else ("list" if any(word in query for word in ["哪些", "列出", "明细"]) else ("value" if any(word in query for word in ["价值", "金额", "净值"]) else "count"))
        filters = result.get("filters") or {}
        asset_query = apply_data_scope(db.query(AiAsset), user)
        if "闲置" in query or filters.get("闲置") in (True, "是", "闲置"):
            asset_query = asset_query.filter(AiAsset.is_idle == 1)
        matched_class = next((name for name in classes if name and name in query), None)
        matched_dept = next((name for name in depts if name and name in query), None)
        matched_state = next((name for name in states if name and name in query), None)
        if matched_class:
            asset_query = asset_query.filter(AiAsset.class_path.like(f"%{matched_class}%"))
        if matched_dept:
            asset_query = asset_query.filter(AiAsset.dept_name == matched_dept)
        if matched_state:
            asset_query = asset_query.filter(AiAsset.state_name == matched_state)
        applied = {key: value for key, value in {"分类": matched_class, "部门": matched_dept, "状态": matched_state, "闲置": "是" if "闲置" in query else None}.items() if value}

        if intent == "rank":
            rows = asset_query.with_entities(AiAsset.dept_name, func.count(AiAsset.asset_id).label("count"), func.coalesce(func.sum(AiAsset.current_value), 0).label("value")).group_by(AiAsset.dept_name).order_by(func.count(AiAsset.asset_id).desc()).limit(5).all()
            data = [{"name": row[0] or "未分配部门", "count": row[1], "value": float(row[2] or 0)} for row in rows]
            answer = "资产数量排名：" + "；".join(f"{item['name']} {item['count']} 台" for item in data) if data else "未找到符合条件的资产。"
        elif intent == "value":
            count, value = asset_query.with_entities(func.count(AiAsset.asset_id), func.coalesce(func.sum(AiAsset.current_value), 0)).one()
            data = {"count": count, "value": float(value or 0)}
            answer = f"共 {count} 台资产，当前净值合计 {float(value or 0):,.2f} 元。"
        elif intent == "list":
            rows = asset_query.order_by(AiAsset.asset_id.desc()).limit(10).all()
            data = [{"asset_id": row.asset_id, "barcode": row.barcode, "asset_name": row.asset_name, "dept_name": row.dept_name, "state_name": row.state_name} for row in rows]
            answer = f"找到 {asset_query.count()} 条记录，已展示前 {len(data)} 条。" if data else "未找到符合条件的资产。"
        else:
            count = asset_query.count()
            data = {"count": count}
            answer = f"查询到 {count} 台符合条件的资产。"
        return {"intent": intent, "filters": applied, "answer": answer, "data": data,
                "ai_used": result.get("model_used", False), "provider": llm.provider, "model": llm.model,
                "ai_error": result.get("model_error", "")}
    finally:
        db.close()


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
    return LLMService().check_health()


@router.get("/llm-status")
def llm_status(user: AiUser = Depends(get_current_user)):
    """向业务页面提供非敏感的当前 AI 配置状态。"""
    llm = LLMService()
    return {"enabled": llm.enabled, "provider": llm.provider, "model": llm.model,
            "configured": bool(llm.api_key) if llm.provider == "openai" else True}
