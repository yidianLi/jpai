"""Centralized stable permission and data-scope rules."""
from sqlalchemy.orm import Query
from ..models.dict import AiUser
from ..models.asset import AiAsset


def apply_data_scope(query: Query, user: AiUser, model=AiAsset) -> Query:
    if user.is_admin == 1:
        return query
    if user.company_id:
        query = query.filter(model.company_id == user.company_id)
    if user.dept_id:
        query = query.filter(model.dept_id == user.dept_id)
    return query


def permission_codes(user: AiUser) -> set[str]:
    if user.is_admin == 1:
        return {"asset.read.all", "report.read.all", "audit.read", "dictionary.read.all"}
    codes = {"asset.read.company", "report.read.own", "dictionary.read.scoped"}
    if user.dept_id:
        codes.add("asset.read.department")
    return codes


def has_permission(user: AiUser, code: str) -> bool:
    return code in permission_codes(user)
