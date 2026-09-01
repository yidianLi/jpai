from types import SimpleNamespace
from backend.app.core.data_scope import permission_codes, has_permission


def test_admin_permissions_are_global():
    user = SimpleNamespace(is_admin=1, company_id=None, dept_id=None)
    assert has_permission(user, "dictionary.read.all")
    assert has_permission(user, "audit.read")


def test_scoped_user_permissions_are_stable():
    user = SimpleNamespace(is_admin=0, company_id=10, dept_id=20)
    codes = permission_codes(user)
    assert "asset.read.company" in codes
    assert "asset.read.department" in codes
    assert "dictionary.read.all" not in codes
