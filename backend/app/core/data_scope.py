"""数据权限过滤：领导看全部，管理员看管辖单位/部门"""
from sqlalchemy.orm import Query
from ..models.dict import AiUser
from ..models.asset import AiAsset


def apply_data_scope(query: Query, user: AiUser, model=AiAsset) -> Query:
    """根据用户角色应用数据权限过滤"""
    if user.is_admin == 1:
        return query  # 管理员看全部
    # 普通用户看本单位
    if user.company_id:
        query = query.filter(model.company_id == user.company_id)
    # 如果有部门限制，看本部门
    if user.dept_id and user.role_name and "部门" in (user.role_name or ""):
        query = query.filter(model.dept_id == user.dept_id)
    return query
