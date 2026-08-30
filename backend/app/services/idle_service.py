"""闲置资产识别与盘活服务"""
from datetime import datetime, date
from sqlalchemy import and_
from ..database import AiSessionLocal
from ..models.asset import AiAsset
from ..models.warning import AiIdlePool
from ..config import settings


class IdleService:
    def __init__(self):
        self.db = AiSessionLocal()

    def close(self):
        self.db.close()

    def refresh_idle_pool(self):
        """刷新闲置资产池：状态=归还回库(10500)且变更日期超过阈值"""
        today = date.today()
        # 先更新资产表的闲置标记
        assets = self.db.query(AiAsset).filter(AiAsset.state_id == 10500).all()
        idle_ids = []
        for a in assets:
            if a.change_date:
                idle_days = (today - a.change_date.date()).days
                a.idle_days = idle_days
                a.is_idle = 1 if idle_days >= settings.IDLE_THRESHOLD_DAYS else 0
                if a.is_idle:
                    idle_ids.append(a.asset_id)
            else:
                a.idle_days = 0
                a.is_idle = 0
        self.db.commit()

        # 重建闲置池
        self.db.query(AiIdlePool).delete()
        idle_assets = self.db.query(AiAsset).filter(AiAsset.is_idle == 1).all()
        batch = []
        for a in idle_assets:
            suggest = "transfer"
            if a.use_year and a.buy_date:
                used_ratio = (today - a.buy_date).days / (a.use_year * 365) if a.use_year else 0
                if used_ratio > 0.8:
                    suggest = "scrap"
            batch.append(AiIdlePool(
                asset_id=a.asset_id, asset_name=a.asset_name, barcode=a.barcode,
                model=a.model, buy_price=a.buy_price, idle_start_date=a.change_date.date() if a.change_date else today,
                idle_days=a.idle_days, estimated_value=a.current_value,
                suggest_action=suggest, dept_name=a.dept_name, position=a.position,
                status=0, create_time=datetime.now(), update_time=datetime.now()
            ))
        self.db.add_all(batch)
        self.db.commit()
        return len(batch)

    def get_idle_list(self, dept=None, class_path=None, min_days=None, page=1, size=20):
        """获取闲置资产列表"""
        q = self.db.query(AiIdlePool).filter(AiIdlePool.status == 0)
        if dept: q = q.filter(AiIdlePool.dept_name == dept)
        if min_days: q = q.filter(AiIdlePool.idle_days >= min_days)
        total = q.count()
        rows = q.order_by(AiIdlePool.idle_days.desc()).offset((page-1)*size).limit(size).all()
        return {
            "total": total, "page": page, "size": size,
            "list": [{
                "id": r.id, "asset_id": r.asset_id, "asset_name": r.asset_name,
                "barcode": r.barcode, "model": r.model, "buy_price": r.buy_price,
                "idle_days": r.idle_days, "estimated_value": r.estimated_value,
                "suggest_action": r.suggest_action, "dept_name": r.dept_name,
                "position": r.position, "idle_start_date": str(r.idle_start_date)
            } for r in rows]
        }

    def get_idle_stats(self):
        """闲置统计"""
        total = self.db.query(AiIdlePool).filter(AiIdlePool.status == 0).count()
        total_value = self.db.query(AiIdlePool.estimated_value).filter(AiIdlePool.status == 0).all()
        total_val = sum(r[0] or 0 for r in total_value)
        transferred = self.db.query(AiIdlePool).filter(AiIdlePool.status == 1).count()
        return {
            "idle_count": total,
            "idle_value": round(total_val, 2),
            "transferred_count": transferred,
            "avg_idle_days": round(self.db.query(AiIdlePool.idle_days).filter(AiIdlePool.status == 0).all() and sum(r[0] for r in self.db.query(AiIdlePool.idle_days).filter(AiIdlePool.status == 0).all()) / max(total, 1), 1)
        }

    def mark_transferred(self, idle_id, user):
        """标记为已调拨"""
        item = self.db.query(AiIdlePool).filter(AiIdlePool.id == idle_id).first()
        if item:
            item.status = 1
            item.update_time = datetime.now()
            # 同时更新资产表
            asset = self.db.query(AiAsset).filter(AiAsset.asset_id == item.asset_id).first()
            if asset:
                asset.is_idle = 0
            self.db.commit()
        return item
