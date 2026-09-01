from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, BigInteger
from ..database import Base


class AiUsageLog(Base):
    __tablename__ = "ai_usage_log"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    provider = Column(String(32), nullable=False)
    model = Column(String(128), nullable=True)
    operation = Column(String(64), nullable=False, index=True)
    request_id = Column(String(64), nullable=True, index=True)
    status = Column(String(16), nullable=False, index=True)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cost = Column(Numeric(12, 6), nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
    error_code = Column(String(64), nullable=True)
    redacted_input = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, index=True)
