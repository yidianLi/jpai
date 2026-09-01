"""报告、清洗、日志、配置模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, SmallInteger, Text, BigInteger
from ..database import Base


class AiReport(Base):
    __tablename__ = "ai_report"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(32), index=True, comment="monthly/quarterly/yearly/check/idle")
    title = Column(String(200))
    period = Column(String(32))
    content = Column(Text, comment="报告内容JSON")
    file_path = Column(String(255), comment="Word文件路径")
    create_user = Column(String(32))
    create_time = Column(DateTime)


class AiDataClean(Base):
    __tablename__ = "ai_data_clean"
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(32))
    record_id = Column(Integer)
    field_name = Column(String(32))
    old_value = Column(String(255))
    clean_value = Column(String(255))
    clean_reason = Column(String(255))
    clean_user = Column(String(32))
    clean_time = Column(DateTime)
    status = Column(SmallInteger, default=1, comment="1生效0撤销")


class AiQualityIssue(Base):
    __tablename__ = "ai_quality_issue"
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, nullable=False, index=True)
    issue_type = Column(String(32), nullable=False)
    issue_title = Column(String(128), nullable=False)
    status = Column(String(16), nullable=False, default="open", index=True)
    assignee = Column(String(64))
    due_date = Column(Date)
    fix_remark = Column(String(512))
    created_by = Column(String(64), default="system")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    verified_by = Column(String(64))
    verified_at = Column(DateTime)


class AiNlQueryLog(Base):
    __tablename__ = "ai_nl_query_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_query = Column(String(512))
    intent = Column(String(64))
    matched_template = Column(String(128))
    query_result = Column(Text)
    is_success = Column(SmallInteger)
    query_time = Column(DateTime)
    response_ms = Column(Integer)


class AiPurchaseForecast(Base):
    __tablename__ = "ai_purchase_forecast"
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer)
    class_name = Column(String(64))
    forecast_month = Column(Date)
    forecast_qty = Column(Float)
    forecast_basis = Column(String(255))
    create_time = Column(DateTime)


class AiConfig(Base):
    __tablename__ = "ai_config"
    config_key = Column(String(64), primary_key=True)
    config_value = Column(Text)
    description = Column(String(255))
