"""字典表模型（同步自原系统）"""
from sqlalchemy import Column, Integer, String, SmallInteger, BigInteger, DateTime
from ..database import Base


class AiCompany(Base):
    __tablename__ = "ai_company"
    company_id = Column(BigInteger, primary_key=True, comment="单位ID")
    parent_id = Column(BigInteger, comment="上级ID")
    company_code = Column(String(32))
    company_name = Column(String(128))
    state = Column(SmallInteger, default=1)


class AiDepartment(Base):
    __tablename__ = "ai_department"
    dept_id = Column(Integer, primary_key=True, comment="部门ID")
    company_id = Column(BigInteger, comment="单位ID")
    parent_id = Column(Integer, comment="上级部门")
    dept_code = Column(String(32))
    dept_name = Column(String(64))
    headcount = Column(Integer, default=0, comment="部门人数(手动维护)")
    state = Column(SmallInteger, default=1)


class AiUser(Base):
    __tablename__ = "ai_user"
    user_id = Column(Integer, primary_key=True, comment="用户ID")
    user_code = Column(String(32), index=True, comment="账号")
    user_name = Column(String(32), comment="姓名")
    password = Column(String(128), comment="密码(MD5)")
    company_id = Column(BigInteger)
    dept_id = Column(Integer)
    role_id = Column(Integer, comment="角色ID")
    role_name = Column(String(64), comment="角色名称")
    mobile = Column(String(32))
    email = Column(String(50))
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    token_version = Column(Integer, default=1, nullable=False)
    state = Column(SmallInteger, default=1)
    is_admin = Column(SmallInteger, default=0, comment="是否管理员")


class AiAssetClass(Base):
    __tablename__ = "ai_asset_class"
    class_id = Column(Integer, primary_key=True, comment="分类ID")
    parent_id = Column(Integer, comment="上级分类")
    class_code = Column(String(32))
    class_name = Column(String(64))
    use_year = Column(Integer, comment="使用年限")
    is_lowest = Column(SmallInteger, default=0, comment="是否末级")
    state = Column(SmallInteger, default=1)


class AiAssetState(Base):
    __tablename__ = "ai_asset_state"
    state_id = Column(Integer, primary_key=True, comment="状态ID")
    state_name = Column(String(32), comment="状态名称")
    state_label = Column(String(32), comment="显示标签")
    state_idx = Column(Integer, comment="排序")
    is_valid = Column(SmallInteger, default=1, comment="是否有效")
