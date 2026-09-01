from sqlalchemy import func
from ..database import AiSessionLocal
from ..models.asset import AiAsset, AiAssetTransfer
from ..core.data_scope import apply_data_scope


class ProcurementService:
    def __init__(self): self.db = AiSessionLocal()
    def close(self): self.db.close()
    def preview(self, user, class_id, quantity, dept_id=None):
        base = apply_data_scope(self.db.query(AiAsset), user)
        if class_id: base = base.filter(AiAsset.class_id == class_id)
        idle_q = base.filter(AiAsset.is_idle == 1).order_by(AiAsset.current_value.desc())
        idle = idle_q.limit(max(quantity, 0)).all()
        repairable = base.filter(AiAsset.is_idle != 1, AiAsset.state_id.in_([15000, 15100])).order_by(AiAsset.current_value.desc()).limit(max(quantity - len(idle), 0)).all()
        candidates = base.filter(AiAsset.model.isnot(None), AiAsset.model != '').with_entities(
            AiAsset.brand, AiAsset.model, func.count(AiAsset.asset_id).label('count'), func.avg(AiAsset.buy_price).label('avg_price')
        ).group_by(AiAsset.brand, AiAsset.model).order_by(func.count(AiAsset.asset_id).desc()).limit(10).all()
        gap = max(quantity - len(idle) - len(repairable), 0)
        avg_price = float(candidates[0].avg_price or 0) if candidates else 0
        return {"requested_quantity": quantity, "available_transfer": len(idle), "purchase_gap": gap,
                "repairable_available": len(repairable), "estimated_budget": round(gap * avg_price, 2),
                "transfer_assets": [{"asset_id": a.asset_id, "asset_name": a.asset_name, "brand": a.brand, "model": a.model, "current_value": a.current_value, "dept_name": a.dept_name} for a in idle],
                "repairable_assets": [{"asset_id": a.asset_id, "asset_name": a.asset_name, "brand": a.brand, "model": a.model, "current_value": a.current_value} for a in repairable],
                "candidates": [{"brand": r.brand, "model": r.model, "asset_count": r.count, "sample_size": r.count, "confidence": "sufficient" if r.count >= 5 else "limited", "average_price": round(float(r.avg_price or 0), 2), "evidence": "历史资产购置均价与库存数量"} for r in candidates],
                "disclaimer": "当前为规则化采购预览，品牌/型号数据不足时不生成可靠性结论。"}
