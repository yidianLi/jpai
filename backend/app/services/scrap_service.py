"""报废与处置智能决策服务"""
from datetime import datetime, date
from sqlalchemy import func
from ..database import AiSessionLocal
from ..models.asset import AiAsset, AiAssetTransfer
from ..models.warning import AiScrapEvaluation
from ..config import settings


class ScrapService:
    def __init__(self):
        self.db = AiSessionLocal()

    def close(self):
        self.db.close()

    def evaluate_asset(self, asset_id):
        """对单台资产进行报废评估"""
        asset = self.db.query(AiAsset).filter(AiAsset.asset_id == asset_id).first()
        if not asset:
            return None
        today = date.today()
        # 已用年限比例
        used_ratio = 0
        if asset.buy_date and asset.use_year:
            used_days = (today - asset.buy_date).days
            used_ratio = min(1.0, used_days / (asset.use_year * 365)) if asset.use_year else 0
        # 维修次数
        repair_count = self.db.query(func.count(AiAssetTransfer.id)).filter(
            AiAssetTransfer.asset_id == asset_id,
            AiAssetTransfer.bill_type == 10700
        ).scalar() or 0
        # 评估逻辑
        eval_result = 2  # 默认建议维修继续使用
        reasons = []
        if used_ratio >= 1.0:
            eval_result = 1  # 建议报废
            reasons.append("已达到使用年限")
        elif used_ratio >= 0.8:
            eval_result = 1
            reasons.append(f"已使用{used_ratio*100:.0f}%设计寿命")
        elif repair_count >= 3:
            eval_result = 1
            reasons.append(f"累计维修{repair_count}次，维修成本高")
        elif used_ratio >= 0.6 and repair_count >= 2:
            eval_result = 1
            reasons.append("使用率较高且维修频繁")
        elif asset.is_idle == 1 and (asset.idle_days or 0) >= 180:
            eval_result = 3  # 建议调拨
            reasons.append("长期闲置，建议调拨给有需求的部门")
        else:
            eval_result = 2
            reasons.append("状态良好，建议继续使用")
        # 异常报废标记
        abnormal = used_ratio < 0.33 and eval_result == 1
        if abnormal:
            reasons.append("注意：使用不足1/3年限即报废，需重点审核")
        # 残值估算
        residual = asset.current_value or 0
        if used_ratio >= 1.0:
            residual = round((asset.buy_price or 0) * settings.RESIDUAL_RATE, 2)
        # 处置建议
        dispose = "recycle"
        if residual > 1000:
            dispose = "sell"
        elif used_ratio >= 1.0:
            dispose = "recycle"
        eval_record = AiScrapEvaluation(
            asset_id=asset.asset_id, asset_name=asset.asset_name, barcode=asset.barcode,
            eval_date=today, eval_result=eval_result, eval_reason="；".join(reasons),
            used_year_ratio=round(used_ratio, 2), repair_count=repair_count,
            current_value=asset.current_value, residual_value=residual,
            dispose_suggest=dispose, operator="system"
        )
        self.db.add(eval_record)
        self.db.commit()
        return {
            "asset_id": asset.asset_id, "asset_name": asset.asset_name,
            "eval_result": eval_result, "eval_result_text": {1: "建议报废", 2: "建议继续使用", 3: "建议调拨"}.get(eval_result),
            "reasons": reasons, "used_ratio": round(used_ratio * 100, 1),
            "repair_count": repair_count, "current_value": asset.current_value,
            "residual_value": residual, "dispose_suggest": dispose,
            "abnormal": abnormal
        }

    def batch_evaluate(self, asset_ids):
        """批量评估"""
        results = []
        for aid in asset_ids:
            r = self.evaluate_asset(aid)
            if r:
                results.append(r)
        return results

    def get_expire_list(self, days=None, level=None, page=1, size=20):
        """获取到期资产清单"""
        today = date.today()
        q = self.db.query(AiAsset).filter(AiAsset.expire_date.isnot(None))
        if days:
            from datetime import timedelta
            q = q.filter(AiAsset.expire_date <= today + timedelta(days=days))
        q = q.filter(AiAsset.state_id.notin_([15000, 15100, 15200, 19900]))
        total = q.count()
        rows = q.order_by(AiAsset.expire_date.asc()).offset((page-1)*size).limit(size).all()
        return {
            "total": total, "page": page, "size": size,
            "list": [{
                "asset_id": r.asset_id, "barcode": r.barcode, "asset_name": r.asset_name,
                "model": r.model, "buy_date": str(r.buy_date) if r.buy_date else None,
                "use_year": r.use_year, "expire_date": str(r.expire_date) if r.expire_date else None,
                "days_left": (r.expire_date - today).days if r.expire_date else None,
                "buy_price": r.buy_price, "current_value": r.current_value,
                "dept_name": r.dept_name, "state_name": r.state_name
            } for r in rows]
        }
