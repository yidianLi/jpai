"""资产全生命周期档案服务"""
from datetime import datetime
from sqlalchemy import func
from ..database import AiSessionLocal
from ..models.asset import AiAsset, AiAssetTransfer, AiCheckRecord
from ..models.report import AiDataClean


class LifecycleService:
    def __init__(self):
        self.db = AiSessionLocal()

    def close(self):
        self.db.close()

    def get_asset_detail(self, asset_id):
        """资产身份证详情"""
        asset = self.db.query(AiAsset).filter(AiAsset.asset_id == asset_id).first()
        if not asset:
            return None
        # 流转记录
        transfers = self.db.query(AiAssetTransfer).filter(
            AiAssetTransfer.asset_id == asset_id
        ).order_by(AiAssetTransfer.bill_date.asc()).all()
        # 盘点记录
        checks = self.db.query(AiCheckRecord).filter(
            AiCheckRecord.asset_id == asset_id
        ).order_by(AiCheckRecord.check_date.desc()).all()
        # 维修次数
        repair_count = sum(1 for t in transfers if t.bill_type == 10700)
        state_map = {0: "未盘", 1: "正常", 2: "盘亏", 3: "不符"}
        return {
            "basic": {
                "asset_id": asset.asset_id, "barcode": asset.barcode,
                "asset_name": asset.asset_name, "asset_name_clean": asset.asset_name_clean,
                "model": asset.model, "brand": asset.brand, "sn": asset.sn,
                "class_path": asset.class_path, "state_name": asset.state_name,
                "company_name": asset.company_name, "dept_name": asset.dept_name,
                "position": asset.position, "responsible": asset.responsible,
                "user_name": asset.user_name, "invoice_no": asset.invoice_no,
                "contract_no": asset.contract_no, "supplier_name": asset.supplier_name,
            },
            "value": {
                "buy_price": asset.buy_price, "buy_date": str(asset.buy_date) if asset.buy_date else None,
                "start_date": str(asset.start_date) if asset.start_date else None,
                "use_year": asset.use_year, "expire_date": str(asset.expire_date) if asset.expire_date else None,
                "current_value": asset.current_value,
            },
            "timeline": [{
                "date": str(t.bill_date) if t.bill_date else None,
                "type": t.bill_type_name, "bill_no": t.bill_no,
                "handler": t.handler, "fee": t.fee,
                "detail": f"{t.old_dept or '-'} → {t.new_dept or '-'}" if t.old_dept != t.new_dept else t.bill_type_name
            } for t in transfers],
            "check_history": [{
                "date": str(r.check_date) if r.check_date else None,
                "state": state_map.get(r.check_state, "未知"),
                "position": r.new_position or r.old_position
            } for r in checks],
            "stats": {
                "transfer_count": len(transfers),
                "repair_count": repair_count,
                "check_count": len(checks),
                "data_quality_score": asset.data_quality_score,
            }
        }

    def get_data_quality_report(self):
        """数据质量报告"""
        total = self.db.query(func.count(AiAsset.asset_id)).scalar() or 0
        abnormal = self.db.query(func.count(AiAsset.asset_id)).filter(AiAsset.clean_status == 2).scalar() or 0
        # 各类异常统计
        no_name = self.db.query(func.count(AiAsset.asset_id)).filter(
            AiAsset.asset_name.is_(None) | (AiAsset.asset_name.in_(["*", "1", "2", "3", "11"]))
        ).scalar() or 0
        no_dept = self.db.query(func.count(AiAsset.asset_id)).filter(AiAsset.dept_id.is_(None)).scalar() or 0
        no_price = self.db.query(func.count(AiAsset.asset_id)).filter(AiAsset.buy_price.is_(None)).scalar() or 0
        no_date = self.db.query(func.count(AiAsset.asset_id)).filter(AiAsset.buy_date.is_(None)).scalar() or 0
        return {
            "total": total, "abnormal": abnormal,
            "abnormal_rate": round(abnormal / total * 100, 1) if total else 0,
            "issues": {
                "名称异常": no_name, "部门缺失": no_dept,
                "价值缺失": no_price, "日期缺失": no_date
            },
            "avg_quality_score": round(
                self.db.query(func.avg(AiAsset.data_quality_score)).scalar() or 0, 1
            )
        }

    def get_abnormal_assets(self, issue_type=None, page=1, size=20):
        """获取异常资产列表"""
        q = self.db.query(AiAsset).filter(AiAsset.clean_status == 2)
        if issue_type == "name":
            q = q.filter(AiAsset.asset_name.is_(None) | (AiAsset.asset_name.in_(["*", "1", "2", "3", "11"])))
        elif issue_type == "dept":
            q = q.filter(AiAsset.dept_id.is_(None))
        total = q.count()
        rows = q.offset((page-1)*size).limit(size).all()
        return {
            "total": total, "page": page, "size": size,
            "list": [{
                "asset_id": r.asset_id, "barcode": r.barcode, "asset_name": r.asset_name,
                "dept_name": r.dept_name, "buy_price": r.buy_price,
                "data_quality_score": r.data_quality_score, "clean_status": r.clean_status
            } for r in rows]
        }

    def clean_asset(self, asset_id, field, clean_value, reason, user):
        """数据清洗标注（不改原库，只在AI库标注）"""
        asset = self.db.query(AiAsset).filter(AiAsset.asset_id == asset_id).first()
        if not asset:
            return None
        old_value = getattr(asset, field, "")
        setattr(asset, field, clean_value)
        asset.clean_status = 1
        record = AiDataClean(
            table_name="ai_asset", record_id=asset_id, field_name=field,
            old_value=str(old_value), clean_value=clean_value,
            clean_reason=reason, clean_user=user, clean_time=datetime.now(), status=1
        )
        self.db.add(record)
        self.db.commit()
        return {"asset_id": asset_id, "field": field, "old": old_value, "new": clean_value}
