"""采购需求预测服务：规则驱动 + 移动平均（数据量小，暂不上复杂模型）"""
from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import func
from ..database import AiSessionLocal
from ..models.asset import AiAsset, AiAssetTransfer
from ..models.dict import AiAssetClass
from ..models.report import AiPurchaseForecast


class ForecastService:
    def __init__(self):
        self.db = AiSessionLocal()

    def close(self):
        self.db.close()

    def compute_forecast(self, months=6):
        """
        采购需求预测逻辑：
        1. 统计近12个月各类资产月均入库量（移动平均）
        2. 加上未来N个月到期资产数量
        3. 减去当前闲置池中同类资产数量
        """
        today = date.today()
        # 近12个月入库按分类统计
        start_date = today - timedelta(days=365)
        rows = self.db.query(
            AiAsset.class_id, AiAsset.class_path,
            func.count(AiAssetTransfer.id).label("cnt")
        ).join(AiAssetTransfer, AiAsset.asset_id == AiAssetTransfer.asset_id).filter(
            AiAssetTransfer.bill_type.in_([10100, 10300]),
            AiAssetTransfer.bill_date >= start_date
        ).group_by(AiAsset.class_id, AiAsset.class_path).all()

        # 到期资产按分类统计（未来months个月）
        end_date = today + timedelta(days=30 * months)
        expire_rows = self.db.query(
            AiAsset.class_id, AiAsset.class_path,
            func.count(AiAsset.asset_id).label("cnt")
        ).filter(
            AiAsset.expire_date >= today, AiAsset.expire_date <= end_date,
            AiAsset.state_id.notin_([15000, 15100, 15200, 19900])
        ).group_by(AiAsset.class_id, AiAsset.class_path).all()
        expire_map = {r[0]: r[2] for r in expire_rows}

        # 闲置资产按分类
        idle_rows = self.db.query(
            AiAsset.class_id, func.count(AiAsset.asset_id)
        ).filter(AiAsset.is_idle == 1).group_by(AiAsset.class_id).all()
        idle_map = {r[0]: r[1] for r in idle_rows}

        # 清除旧预测
        self.db.query(AiPurchaseForecast).delete()

        results = []
        for r in rows:
            class_id, class_path, monthly_avg = r[0], r[1], round((r[2] or 0) / 12, 1)
            expire_qty = expire_map.get(class_id, 0)
            idle_qty = idle_map.get(class_id, 0)
            # 预测需求 = 月均消耗 * 预测月数 + 到期替换 - 闲置可调剂
            forecast = max(0, monthly_avg * months + expire_qty * 0.7 - idle_qty * 0.5)
            basis = f"月均入库{monthly_avg}台×{months}月 + 到期{expire_qty}台×70%替换率 - 闲置{idle_qty}台×50%调剂率"
            top_class = class_path.split(" > ")[0] if class_path else "未分类"
            record = AiPurchaseForecast(
                class_id=class_id, class_name=top_class,
                forecast_month=end_date, forecast_qty=round(forecast, 1),
                forecast_basis=basis, create_time=datetime.now()
            )
            self.db.add(record)
            results.append({
                "class_name": top_class, "monthly_avg": monthly_avg,
                "expire_qty": expire_qty, "idle_qty": idle_qty,
                "forecast_qty": round(forecast, 1), "basis": basis
            })
        self.db.commit()
        return sorted(results, key=lambda x: -x["forecast_qty"])[:20]

    def get_forecast(self):
        rows = self.db.query(AiPurchaseForecast).order_by(AiPurchaseForecast.forecast_qty.desc()).all()
        return [{"class_name": r.class_name, "forecast_qty": r.forecast_qty,
                 "basis": r.forecast_basis} for r in rows]
