from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime
from ..database import Base
class AiProcurementSuggestion(Base):
    __tablename__ = 'ai_procurement_suggestion'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    class_id = Column(Integer); quantity = Column(Integer, nullable=False); payload = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='draft', index=True); created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False); confirmed_by = Column(BigInteger); confirmed_at = Column(DateTime)
