from sqlalchemy import case, func
from datetime import datetime
from ..database import AiSessionLocal
from ..models.asset import AiAsset, AiAssetTransfer, AiCheckRecord
from ..core.data_scope import apply_data_scope


class InsightService:
    def __init__(self): self.db = AiSessionLocal()
    def close(self): self.db.close()

    def quality_metadata(self):
        cutoff = self.db.query(func.max(AiAsset.sync_time)).scalar()
        return {"ai_used": False, "data_cutoff": cutoff.isoformat() if cutoff else None,
                "sample_definition": "按权限范围内资产台账去重统计，维修工单类型=10700",
                "rules_version": "insight-v1", "generated_at": datetime.now().isoformat()}

    def brands(self, user, class_id=None, dept_id=None, min_sample=10):
        q = apply_data_scope(self.db.query(AiAsset), user).filter(AiAsset.brand.isnot(None), AiAsset.brand != "")
        if class_id: q = q.filter(AiAsset.class_id == class_id)
        if dept_id: q = q.filter(AiAsset.dept_id == dept_id)
        repair = AiAssetTransfer.bill_type == 10700
        rows = q.outerjoin(AiAssetTransfer, (AiAssetTransfer.asset_id == AiAsset.asset_id) & repair).group_by(AiAsset.brand).with_entities(
            AiAsset.brand, func.count(func.distinct(AiAsset.asset_id)).label('assets'), func.count(AiAssetTransfer.id).label('repairs'),
            func.coalesce(func.sum(AiAssetTransfer.fee), 0).label('repair_fee'), func.sum(case((AiAsset.is_idle == 1, 1), else_=0)).label('idle')) .order_by(func.count(func.distinct(AiAsset.asset_id)).desc()).all()
        return [self._row(r, min_sample) for r in rows]

    def models(self, user, brand=None, class_id=None, min_sample=10):
        q = apply_data_scope(self.db.query(AiAsset), user).filter(AiAsset.model.isnot(None), AiAsset.model != "")
        if brand: q = q.filter(AiAsset.brand == brand)
        if class_id: q = q.filter(AiAsset.class_id == class_id)
        repair = AiAssetTransfer.bill_type == 10700
        rows = q.outerjoin(AiAssetTransfer, (AiAssetTransfer.asset_id == AiAsset.asset_id) & repair).group_by(AiAsset.brand, AiAsset.model, AiAsset.class_id).with_entities(
            AiAsset.brand, AiAsset.model, AiAsset.class_id, func.count(func.distinct(AiAsset.asset_id)).label('assets'), func.count(AiAssetTransfer.id).label('repairs'),
            func.coalesce(func.sum(AiAssetTransfer.fee), 0).label('repair_fee'), func.sum(case((AiAsset.is_idle == 1, 1), else_=0)).label('idle')).order_by(func.count(func.distinct(AiAsset.asset_id)).desc()).all()
        return [self._row(r, min_sample, model=True) for r in rows]

    @staticmethod
    def _row(r, min_sample, model=False):
        assets = int(r[3] if model else r[1] or 0); repairs = int(r[4] if model else r[2] or 0); idle = int(r[6] if model else r[4] or 0)
        brand = r[0]; item = {"brand": brand, "assets": assets, "repairs": repairs, "repair_fee": float(r[5] if model else r[3] or 0), "idle": idle,
                "idle_rate": round(idle / assets * 100, 2) if assets else 0, "repair_rate": round(repairs / assets, 3) if assets else None,
                "sample_size": assets, "confidence": "sufficient" if assets >= min_sample else "insufficient",
                "risk_tags": [] if assets >= min_sample else ["样本不足"],
                "evidence": {"asset_count": assets, "repair_work_orders": repairs, "repair_fee": float(r[5] if model else r[3] or 0), "idle_asset_count": idle},
                "recommendation": "可作为采购候选" if assets >= min_sample and repairs == 0 else ("需补充维修数据" if repairs == 0 else "建议关注维修表现")}
        if model: item.update({"model": r[1], "class_id": r[2]})
        return item
