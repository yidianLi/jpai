"""预警引擎服务"""
from datetime import datetime, date, timedelta
from sqlalchemy import and_
from ..database import AiSessionLocal
from ..models.asset import AiAsset
from ..models.warning import AiWarning
from ..config import settings


class WarningService:
    def __init__(self):
        self.db = AiSessionLocal()

    def close(self):
        self.db.close()

    def compute_expire_warnings(self):
        """计算到期预警"""
        today = date.today()
        red_date = today + timedelta(days=settings.EXPIRE_RED_DAYS)
        yellow_date = today + timedelta(days=settings.EXPIRE_YELLOW_DAYS)
        # 清除旧的到期预警
        self.db.query(AiWarning).filter(AiWarning.warning_type == "expire").delete()
        assets = self.db.query(AiAsset).filter(
            AiAsset.expire_date.isnot(None),
            AiAsset.state_id.notin_([15000, 15100, 15200, 19900]),
            AiAsset.expire_date <= yellow_date
        ).all()
        batch = []
        for a in assets:
            level = 1 if a.expire_date <= red_date else 2
            days_left = (a.expire_date - today).days
            batch.append(AiWarning(
                warning_type="expire", warning_level=level, asset_id=a.asset_id,
                asset_name=a.asset_name, barcode=a.barcode, dept_name=a.dept_name,
                warning_date=today,
                warning_content=f"资产{a.asset_name}({a.barcode})将于{a.expire_date}到期，剩余{days_left}天",
                status=0, create_time=datetime.now()
            ))
        self.db.add_all(batch)
        self.db.commit()
        return len(batch)

    def compute_idle_warnings(self):
        """计算闲置预警"""
        today = date.today()
        self.db.query(AiWarning).filter(AiWarning.warning_type == "idle").delete()
        assets = self.db.query(AiAsset).filter(
            AiAsset.is_idle == 1, AiAsset.idle_days >= settings.IDLE_THRESHOLD_DAYS
        ).all()
        batch = []
        for a in assets:
            level = 1 if a.idle_days >= 180 else 2
            batch.append(AiWarning(
                warning_type="idle", warning_level=level, asset_id=a.asset_id,
                asset_name=a.asset_name, barcode=a.barcode, dept_name=a.dept_name,
                warning_date=today,
                warning_content=f"资产{a.asset_name}({a.barcode})已闲置{a.idle_days}天，建议调拨或处置",
                status=0, create_time=datetime.now()
            ))
        self.db.add_all(batch)
        self.db.commit()
        return len(batch)

    def compute_overdue_warnings(self):
        """计算超期借用/盘亏未处理预警"""
        today = date.today()
        self.db.query(AiWarning).filter(AiWarning.warning_type.in_(["overdue_borrow", "loss"])).delete()
        # 超期借用：状态=借用(10410)且变更日期超过30天
        borrow_assets = self.db.query(AiAsset).filter(
            AiAsset.state_id == 10410,
            AiAsset.change_date < datetime.combine(today - timedelta(days=30), datetime.min.time())
        ).all()
        batch = []
        for a in borrow_assets:
            batch.append(AiWarning(
                warning_type="overdue_borrow", warning_level=1, asset_id=a.asset_id,
                asset_name=a.asset_name, barcode=a.barcode, dept_name=a.dept_name,
                warning_date=today,
                warning_content=f"资产{a.asset_name}({a.barcode})借用超期未归还",
                status=0, create_time=datetime.now()
            ))
        self.db.add_all(batch)
        self.db.commit()
        return len(batch)

    def get_warning_list(self, warning_type=None, level=None, status=None, page=1, size=20):
        """获取预警列表"""
        q = self.db.query(AiWarning)
        if warning_type: q = q.filter(AiWarning.warning_type == warning_type)
        if level: q = q.filter(AiWarning.warning_level == level)
        if status is not None: q = q.filter(AiWarning.status == status)
        total = q.count()
        rows = q.order_by(AiWarning.warning_level.asc(), AiWarning.create_time.desc()).offset((page-1)*size).limit(size).all()
        return {
            "total": total, "page": page, "size": size,
            "list": [{
                "id": r.id, "type": r.warning_type, "level": r.warning_level,
                "asset_id": r.asset_id, "asset_name": r.asset_name, "barcode": r.barcode,
                "dept_name": r.dept_name, "date": str(r.warning_date),
                "content": r.warning_content, "status": r.status
            } for r in rows]
        }

    def handle_warning(self, warning_id, status, remark, user):
        """处理预警"""
        w = self.db.query(AiWarning).filter(AiWarning.id == warning_id).first()
        if not w:
            return None
        w.status = status
        w.handle_user = user
        w.handle_time = datetime.now()
        w.handle_remark = remark
        self.db.commit()
        return w
