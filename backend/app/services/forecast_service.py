"""采购需求预测服务：规则驱动 + 移动平均（数据量小，暂不上复杂模型）"""
from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import func
from ..database import AiSessionLocal
from ..models.asset import AiAsset, AiAssetTransfer
from ..models.dict import AiAssetClass
from ..models.report import AiPurchaseForecast


class ForecastService:
    def __init__(self, db=None):
        self.db = db or AiSessionLocal(); self._owns_db = db is None

    def close(self):
        if self._owns_db: self.db.close()

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

        # 预测不能只依赖流转记录。历史同步数据可能没有近 12 个月的入库单，
        # 此时仍应按现有资产类别生成可解释的替换/调剂预测。
        transfer_map = {r[0]: (r[1], round((r[2] or 0) / 12, 1)) for r in rows}
        asset_rows = self.db.query(
            AiAsset.class_id, AiAsset.class_path
        ).filter(AiAsset.class_id.isnot(None)).group_by(
            AiAsset.class_id, AiAsset.class_path
        ).all()
        class_map = {class_id: class_path for class_id, class_path in asset_rows}
        for class_id, class_path, _ in expire_rows:
            class_map.setdefault(class_id, class_path)
        for class_id, class_path in transfer_map.items():
            class_map.setdefault(class_id, class_path[0])

        # 清除旧预测
        self.db.query(AiPurchaseForecast).delete()

        results = []
        for class_id, class_path in class_map.items():
            monthly_avg = transfer_map.get(class_id, (class_path, 0))[1]
            expire_qty = expire_map.get(class_id, 0)
            idle_qty = idle_map.get(class_id, 0)
            # 预测需求 = 月均消耗 * 预测月数 + 到期替换 - 闲置可调剂
            forecast = max(0, monthly_avg * months + expire_qty * 0.7 - idle_qty * 0.5)
            basis = f"月均入库{monthly_avg}台×{months}月 + 到期{expire_qty}台×70%替换率 - 闲置{idle_qty}台×50%调剂率"
            # 使用完整分类路径作为预测维度，避免所有末级资产都被压扁为“设备”。
            top_class = class_path or "未分类"
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
        # 展示按可读的上级类别合并，避免多个末级分类都显示为“设备”造成重复行。
        merged = {}
        category_counts = defaultdict(int)
        for item in results:
            category_counts[item["class_name"]] += 1
        for item in results:
            key = item["class_name"]
            if key not in merged:
                merged[key] = {**item}
            else:
                for field in ("monthly_avg", "expire_qty", "idle_qty", "forecast_qty"):
                    merged[key][field] = round(merged[key][field] + item[field], 1)
                merged[key]["basis"] = f"合并{category_counts[key]}个分类：月均入库{merged[key]['monthly_avg']}台×{months}月 + 到期{merged[key]['expire_qty']}台×70%替换率 - 闲置{merged[key]['idle_qty']}台×50%调剂率"
        return sorted(merged.values(), key=lambda x: -x["forecast_qty"])[:20]

    def get_forecast(self):
        rows = self.db.query(AiPurchaseForecast).order_by(AiPurchaseForecast.forecast_qty.desc()).all()
        merged = {}
        for r in rows:
            if r.class_name not in merged:
                merged[r.class_name] = {"class_name": r.class_name, "forecast_qty": float(r.forecast_qty or 0), "basis": r.forecast_basis}
            else:
                merged[r.class_name]["forecast_qty"] += float(r.forecast_qty or 0)
        return sorted(merged.values(), key=lambda x: -x["forecast_qty"])[:20]
