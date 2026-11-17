import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, AsyncMock

@pytest.fixture
def client():
    # Patch init_db to avoid actual database connection during tests
    with patch("main.init_db", new_callable=AsyncMock):
        with TestClient(app) as c:
            yield c

@pytest.fixture
def admin_headers():
    return {"X-Role": "ADMIN"}

@pytest.fixture
def dba_headers():
    return {"X-Role": "DBA"}

@pytest.fixture
def operator_headers():
    return {"X-Role": "OPERATOR"}

@pytest.fixture
def viewer_headers():
    return {"X-Role": "VIEWER"}

@pytest.fixture
def invalid_role_headers():
    return {"X-Role": "INVALID"}

@pytest.fixture
def no_role_headers():
    return {}
