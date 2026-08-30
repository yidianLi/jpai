"""资产相关数据模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, SmallInteger, BigInteger, Text, Index
from ..database import Base


class AiAsset(Base):
    """资产主表（同步+清洗标注）"""
    __tablename__ = "ai_asset"

    asset_id = Column(Integer, primary_key=True, comment="对应fs_bom.BOMID")
    barcode = Column(String(32), index=True, comment="资产编号")
    asset_name = Column(String(128), comment="资产名称(原)")
    asset_name_clean = Column(String(128), comment="清洗后名称")
    model = Column(String(128), comment="型号")
    brand = Column(String(32), comment="品牌")
    sn = Column(String(32), comment="序列号")
    class_id = Column(Integer, index=True, comment="分类ID")
    class_path = Column(String(256), comment="分类全路径")
    state_id = Column(Integer, index=True, comment="状态ID")
    state_name = Column(String(32), comment="状态名称")
    company_id = Column(BigInteger, comment="使用单位ID")
    company_name = Column(String(128), comment="使用单位")
    dept_id = Column(Integer, index=True, comment="使用部门ID")
    dept_name = Column(String(64), comment="使用部门")
    warehouse_id = Column(Integer, comment="仓库ID")
    position = Column(String(128), comment="摆放位置")
    responsible = Column(String(64), comment="责任人")
    user_name = Column(String(64), comment="使用人")
    buy_price = Column(Float, comment="购置原值")
    buy_date = Column(Date, comment="购置日期")
    start_date = Column(Date, comment="入账日期")
    use_year = Column(Integer, comment="使用年限")
    expire_date = Column(Date, index=True, comment="到期日")
    current_value = Column(Float, comment="当前净值")
    change_date = Column(DateTime, comment="最后变更日期")
    over_date = Column(Date, comment="清理日期")
    status2 = Column(SmallInteger, comment="待报废标志")
    invoice_no = Column(String(64), comment="发票号")
    contract_no = Column(String(32), comment="合同号")
    supplier_name = Column(String(64), comment="供应商")
    # AI扩展
    idle_days = Column(Integer, comment="闲置天数")
    is_idle = Column(SmallInteger, default=0, index=True, comment="是否闲置")
    data_quality_score = Column(Integer, comment="数据质量分0-100")
    clean_status = Column(SmallInteger, default=0, comment="0未清洗1已清洗2异常")
    clean_remark = Column(String(256), comment="清洗备注")
    sync_time = Column(DateTime, comment="同步时间")


class AiAssetTransfer(Base):
    """资产流转记录"""
    __tablename__ = "ai_asset_transfer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, index=True, comment="资产ID")
    bill_no = Column(String(32), comment="工单编号")
    bill_type = Column(Integer, comment="操作类型SID")
    bill_type_name = Column(String(32), comment="操作类型名称")
    bill_date = Column(Date, index=True, comment="工单日期")
    handler = Column(String(64), comment="经办人")
    old_state = Column(Integer)
    new_state = Column(Integer)
    old_dept_id = Column(Integer)
    new_dept_id = Column(Integer)
    old_responsible = Column(String(64))
    new_responsible = Column(String(64))
    old_position = Column(String(128))
    new_position = Column(String(128))
    fee = Column(Float, comment="费用(维修)")
    remark = Column(String(255))


class AiCheckRecord(Base):
    """盘点记录"""
    __tablename__ = "ai_check_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    check_bid = Column(Integer, index=True, comment="盘点工单ID")
    check_title = Column(String(255), comment="盘点标题")
    check_date = Column(Date, comment="盘点日期")
    asset_id = Column(Integer, index=True)
    barcode = Column(String(64))
    check_state = Column(SmallInteger, index=True, comment="0未盘1正常2盘亏3不符")
    old_dept = Column(String(64))
    new_dept = Column(String(64))
    old_position = Column(String(128))
    new_position = Column(String(128))
    old_responsible = Column(String(64))
    new_responsible = Column(String(64))
    is_overdue = Column(SmallInteger, default=0, comment="是否超期未处理")
    handle_status = Column(SmallInteger, default=0, comment="处理状态")
    handle_remark = Column(String(255))
