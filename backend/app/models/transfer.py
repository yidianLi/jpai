from sqlalchemy import Column, DateTime, BigInteger, Integer, String, Text, Numeric, Index
from ..database import Base


class AiTransferSuggestion(Base):
    __tablename__ = "ai_transfer_suggestion"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_id = Column(BigInteger, nullable=False)
    source_company_id = Column(BigInteger)
    source_dept_id = Column(Integer)
    source_dept_name = Column(String(128))
    source_position = Column(String(128))
    source_user_name = Column(String(64))
    target_company_id = Column(BigInteger)
    target_dept_id = Column(Integer, nullable=False)
    target_dept_name = Column(String(128), nullable=False)
    target_position = Column(String(128))
    target_user_name = Column(String(64))
    reason = Column(String(512))
    estimated_saving = Column(Numeric(18, 2))
    status = Column(String(32), nullable=False, default="draft", index=True)
    receiver_user_id = Column(BigInteger)
    receiver_remark = Column(String(512))
    receiver_time = Column(DateTime)
    operator_user_id = Column(BigInteger)
    operator_time = Column(DateTime)
    version_no = Column(Integer, nullable=False, default=1)
    asset_sync_time = Column(DateTime)
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    __table_args__ = (Index("idx_transfer_asset_status", "asset_id", "status"),)


class AiTransferAudit(Base):
    __tablename__ = "ai_transfer_audit"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    suggestion_id = Column(BigInteger, nullable=False, index=True)
    asset_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(32), nullable=False)
    operator_user_id = Column(BigInteger, nullable=False)
    before_snapshot = Column(Text)
    after_snapshot = Column(Text)
    remark = Column(String(512))
    created_at = Column(DateTime, nullable=False)
