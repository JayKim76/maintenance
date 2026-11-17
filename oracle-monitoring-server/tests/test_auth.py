import pytest
from core.auth import get_current_role, Role, PERMISSIONS

@pytest.mark.asyncio
async def test_get_current_role_valid():
    assert await get_current_role("ADMIN") == Role.ADMIN
    assert await get_current_role("dba") == Role.DBA
    assert await get_current_role("OPERATOR") == Role.OPERATOR
    assert await get_current_role("Viewer") == Role.VIEWER

@pytest.mark.asyncio
async def test_get_current_role_invalid():
    assert await get_current_role("SUPERUSER") == Role.VIEWER
    assert await get_current_role(None) == Role.VIEWER

def test_permissions_mapping():
    assert "modify_settings" in PERMISSIONS[Role.ADMIN]
    assert "modify_settings" not in PERMISSIONS[Role.DBA]
    assert "execute_dml" in PERMISSIONS[Role.DBA]
    assert "execute_dml" not in PERMISSIONS[Role.OPERATOR]
    assert "execute_sql" in PERMISSIONS[Role.OPERATOR]
    assert "execute_sql" not in PERMISSIONS[Role.VIEWER]
    assert "view_metrics" in PERMISSIONS[Role.VIEWER]
