import json
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import or_
from ..database import AiSessionLocal
from ..models.asset import AiAsset
from ..models.dict import AiDepartment
from ..models.transfer import AiTransferSuggestion, AiTransferAudit
from ..core.data_scope import apply_data_scope

ACTIVE = {"draft", "pending_receiver", "confirmed"}


def snapshot(asset):
    return {"company_id": asset.company_id, "dept_id": asset.dept_id, "dept_name": asset.dept_name,
            "position": asset.position, "user_name": asset.user_name, "state_id": asset.state_id,
            "state_name": asset.state_name, "sync_time": str(asset.sync_time) if asset.sync_time else None}


class TransferService:
    def __init__(self, db=None):
        self.db = db or AiSessionLocal()
        self.owns_db = db is None

    def close(self):
        if self.owns_db:
            self.db.close()

    def get_item(self, suggestion_id, user):
        item = self.db.query(AiTransferSuggestion).filter(AiTransferSuggestion.id == suggestion_id).first()
        if not item:
            raise HTTPException(404, "调拨建议不存在")
        if not apply_data_scope(self.db.query(AiAsset), user).filter(AiAsset.asset_id == item.asset_id).first():
            raise HTTPException(403, "无权访问该资产")
        return item

    def audit(self, item, user, action, before=None, after=None, remark=None):
        self.db.add(AiTransferAudit(suggestion_id=item.id, asset_id=item.asset_id, action=action,
            operator_user_id=user.user_id, before_snapshot=json.dumps(before, ensure_ascii=False) if before else None,
            after_snapshot=json.dumps(after, ensure_ascii=False) if after else None, remark=remark, created_at=datetime.now()))

    def as_dict(self, item):
        return {"id": item.id, "asset_id": item.asset_id, "source_dept_name": item.source_dept_name,
            "source_position": item.source_position, "source_user_name": item.source_user_name,
            "target_dept_id": item.target_dept_id, "target_dept_name": item.target_dept_name,
            "target_position": item.target_position, "target_user_name": item.target_user_name,
            "reason": item.reason, "estimated_saving": float(item.estimated_saving) if item.estimated_saving is not None else None,
            "status": item.status, "receiver_remark": item.receiver_remark, "receiver_time": item.receiver_time,
            "operator_time": item.operator_time, "created_at": item.created_at}

    def list(self, user, status=None, page=1, size=20):
        q = self.db.query(AiTransferSuggestion).join(AiAsset, AiAsset.asset_id == AiTransferSuggestion.asset_id)
        if user.is_admin != 1:
            q = q.filter(or_(AiAsset.company_id == user.company_id, AiTransferSuggestion.target_dept_id == user.dept_id))
        if status: q = q.filter(AiTransferSuggestion.status == status)
        size = min(max(size, 1), 100)
        total = q.count()
        rows = q.order_by(AiTransferSuggestion.updated_at.desc()).offset((page - 1) * size).limit(size).all()
        return {"total": total, "page": page, "size": size, "list": [self.as_dict(row) for row in rows]}

    def create(self, payload, user):
        asset = apply_data_scope(self.db.query(AiAsset), user).filter(AiAsset.asset_id == payload.asset_id).first()
        if not asset: raise HTTPException(404, "资产不存在或无权访问")
        if asset.is_idle != 1: raise HTTPException(422, "只有闲置资产可以发起调拨建议")
        if self.db.query(AiTransferSuggestion).filter(AiTransferSuggestion.asset_id == asset.asset_id, AiTransferSuggestion.status.in_(ACTIVE)).first():
            raise HTTPException(409, "该资产已有未完成调拨建议")
        dept = self.db.query(AiDepartment).filter(AiDepartment.dept_id == payload.target_dept_id).first()
        if not dept: raise HTTPException(422, "目标部门不存在")
        now = datetime.now()
        item = AiTransferSuggestion(asset_id=asset.asset_id, source_company_id=asset.company_id, source_dept_id=asset.dept_id,
            source_dept_name=asset.dept_name, source_position=asset.position, source_user_name=asset.user_name,
            target_company_id=payload.target_company_id or asset.company_id, target_dept_id=dept.dept_id,
            target_dept_name=dept.dept_name, target_position=payload.target_position, target_user_name=payload.target_user_name,
            reason=payload.reason, estimated_saving=payload.estimated_saving, status="pending_receiver",
            asset_sync_time=asset.sync_time, created_by=user.user_id, created_at=now, updated_at=now)
        self.db.add(item); self.db.flush(); self.audit(item, user, "created", snapshot(asset), None, payload.reason)
        self.db.commit(); self.db.refresh(item)
        return self.as_dict(item)

    def decide(self, suggestion_id, user, accept, remark=None):
        item = self.get_item(suggestion_id, user)
        if item.status != "pending_receiver": raise HTTPException(409, "当前状态不可确认或拒绝")
        if user.is_admin != 1 and user.dept_id != item.target_dept_id: raise HTTPException(403, "只有接收部门可以处理该建议")
        item.status = "confirmed" if accept else "rejected"; item.receiver_user_id = user.user_id
        item.receiver_remark = remark; item.receiver_time = item.updated_at = datetime.now()
        self.audit(item, user, "receiver_confirm" if accept else "receiver_reject", remark=remark)
        self.db.commit(); return self.as_dict(item)

    def execute(self, suggestion_id, user):
        if user.is_admin != 1: raise HTTPException(403, "只有资产管理员可以执行调拨")
        item = self.get_item(suggestion_id, user)
        if item.status != "confirmed": raise HTTPException(409, "只有接收部门确认后才能执行")
        asset = self.db.query(AiAsset).filter(AiAsset.asset_id == item.asset_id).with_for_update().first()
        if not asset or asset.sync_time != item.asset_sync_time or asset.is_idle != 1:
            self.db.rollback(); raise HTTPException(409, "资产已发生变化，请刷新后重新处理")
        before = snapshot(asset)
        asset.company_id = item.target_company_id or asset.company_id; asset.dept_id = item.target_dept_id
        asset.dept_name = item.target_dept_name; asset.position = item.target_position; asset.user_name = item.target_user_name
        asset.is_idle = 0; item.status = "completed"; item.operator_user_id = user.user_id; item.operator_time = item.updated_at = datetime.now()
        self.audit(item, user, "execute", before, snapshot(asset), "调拨执行")
        self.db.commit(); return self.as_dict(item)

    def cancel(self, suggestion_id, user, remark=None):
        item = self.get_item(suggestion_id, user)
        if item.status not in ACTIVE: raise HTTPException(409, "当前状态不可取消")
        if user.is_admin != 1 and item.created_by != user.user_id: raise HTTPException(403, "只有发起人或管理员可以取消")
        item.status = "cancelled"; item.updated_at = datetime.now(); self.audit(item, user, "cancel", remark=remark)
        self.db.commit(); return self.as_dict(item)

    def get(self, suggestion_id, user):
        return self.as_dict(self.get_item(suggestion_id, user))

    def audits(self, suggestion_id, user):
        item = self.get_item(suggestion_id, user)
        rows = self.db.query(AiTransferAudit).filter(AiTransferAudit.suggestion_id == item.id).order_by(AiTransferAudit.created_at).all()
        return [{"id": row.id, "action": row.action, "operator_user_id": row.operator_user_id,
            "before": json.loads(row.before_snapshot) if row.before_snapshot else None,
            "after": json.loads(row.after_snapshot) if row.after_snapshot else None,
            "remark": row.remark, "created_at": row.created_at} for row in rows]
