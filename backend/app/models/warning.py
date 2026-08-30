"""预警与决策模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, SmallInteger, Text
from ..database import Base


class AiWarning(Base):
    """预警表"""
    __tablename__ = "ai_warning"

    id = Column(Integer, primary_key=True, autoincrement=True)
    warning_type = Column(String(32), index=True, comment="expire/idle/overdue_borrow/loss/low_stock/duplicate_purchase/abnormal_scrap")
    warning_level = Column(SmallInteger, comment="1红2黄3蓝")
    asset_id = Column(Integer, index=True)
    asset_name = Column(String(128))
    barcode = Column(String(32))
    dept_name = Column(String(64))
    warning_date = Column(Date)
    warning_content = Column(String(512))
    status = Column(SmallInteger, default=0, index=True, comment="0未处理1已处理2已忽略")
    handle_user = Column(String(32))
    handle_time = Column(DateTime)
    handle_remark = Column(String(255))
    create_time = Column(DateTime)


class AiIdlePool(Base):
    """闲置资产池"""
    __tablename__ = "ai_idle_pool"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, unique=True)
    asset_name = Column(String(128))
    barcode = Column(String(32))
    model = Column(String(128))
    buy_price = Column(Float)
    idle_start_date = Column(Date)
    idle_days = Column(Integer)
    estimated_value = Column(Float, comment="估算价值")
    suggest_action = Column(String(32), comment="transfer/scrap/continue_use")
    dept_name = Column(String(64))
    position = Column(String(128))
    status = Column(SmallInteger, default=0, comment="0在池1已调拨2已报废3已移除")
    create_time = Column(DateTime)
    update_time = Column(DateTime)


class AiScrapEvaluation(Base):
    """报废评估表"""
    __tablename__ = "ai_scrap_evaluation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, index=True)
    asset_name = Column(String(128))
    barcode = Column(String(32))
    eval_date = Column(Date)
    eval_result = Column(SmallInteger, comment="1建议报废2建议维修3建议调拨")
    eval_reason = Column(String(512), comment="评估依据")
    used_year_ratio = Column(Float, comment="已用年限比例")
    repair_count = Column(Integer, default=0)
    current_value = Column(Float)
    residual_value = Column(Float, comment="残值估算")
    dispose_suggest = Column(String(32), comment="sell/donate/recycle/destroy")
    operator = Column(String(32))
