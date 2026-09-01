from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from ..database import Base


class AiJob(Base):
    __tablename__ = "ai_job"
    id = Column(String(64), primary_key=True)
    job_type = Column(String(64), nullable=False, index=True)
    idempotency_key = Column(String(255), nullable=False, unique=True)
    status = Column(String(16), nullable=False, default="queued", index=True)
    progress = Column(Integer, nullable=False, default=0)
    owner_user_id = Column(Integer, nullable=True, index=True)
    owner_name = Column(String(64), nullable=True)
    payload = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=2)
    timeout_seconds = Column(Integer, nullable=False, default=900)
    created_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False)

    __table_args__ = (Index("idx_ai_job_status_updated", "status", "updated_at"),)
