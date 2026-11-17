import pytest

def test_status_endpoint_no_auth(client):
    """Public endpoint should work without X-Role header"""
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "oracle-monitoring-server"}

def test_settings_status_viewer(client, viewer_headers):
    """GET /api/settings/status does not require special permissions (default access)"""
    response = client.get("/api/settings/status", headers=viewer_headers)
    assert response.status_code == 200

def test_test_connection_admin_success(client, admin_headers):
    """ADMIN has modify_settings permission"""
    payload = {
        "host": "localhost",
        "port": "1521",
        "service_name": "xe",
        "username": "system",
        "password": "mock",
        "mode": "SERVICE_NAME"
    }
    response = client.post("/api/settings/test-connection", json=payload, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_test_connection_dba_forbidden(client, dba_headers):
    """DBA does NOT have modify_settings permission"""
    payload = {
        "host": "localhost",
        "port": "1521",
        "service_name": "xe",
        "username": "system",
        "password": "mock",
        "mode": "SERVICE_NAME"
    }
    response = client.post("/api/settings/test-connection", json=payload, headers=dba_headers)
    assert response.status_code == 403
    assert "Permission denied" in response.json()["detail"]

def test_test_connection_no_role_forbidden(client):
    """No role defaults to VIEWER, which is forbidden"""
    payload = {
        "host": "localhost",
        "port": "1521",
        "service_name": "xe",
        "username": "system",
        "password": "mock",
        "mode": "SERVICE_NAME"
    }
    response = client.post("/api/settings/test-connection", json=payload)
    assert response.status_code == 403

def test_disconnect_admin(client, admin_headers):
    """ADMIN can disconnect"""
    response = client.post("/api/settings/disconnect", headers=admin_headers)
    assert response.status_code == 200

def test_disconnect_operator_forbidden(client, operator_headers):
    """OPERATOR cannot disconnect"""
    response = client.post("/api/settings/disconnect", headers=operator_headers)
    assert response.status_code == 403
