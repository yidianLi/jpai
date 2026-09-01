"""Append-only audit events for sensitive business operations."""
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..database import Base


class AiAuditEvent(Base):
    __tablename__ = "ai_audit_event"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_user_id = Column(Integer, nullable=True, index=True)
    actor_name = Column(String(64), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    resource = Column(String(128), nullable=True)
    result = Column(String(16), nullable=False, default="success")
    before_snapshot = Column(Text, nullable=True)
    after_snapshot = Column(Text, nullable=True)
    request_id = Column(String(64), nullable=True, index=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, index=True)
