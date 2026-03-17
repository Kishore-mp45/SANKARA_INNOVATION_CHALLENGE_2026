"""
Integration tests for PatientPath AI API endpoints.
Uses FastAPI TestClient to exercise the full request/response cycle.
Run with: pytest tests/test_api_integration.py -v
"""
import os
import sys
import pytest

# Add backend directory to path
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_TESTS_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def auth_token(client):
    """Obtain an admin auth token for protected endpoint tests."""
    resp = client.post("/auth/login", json={"user_id": "admin001", "password": "Admin@123"})
    if resp.status_code == 200:
        return resp.json().get("token")
    return None


# --- Auth endpoints ---

def test_login_valid_credentials(client):
    resp = client.post("/auth/login", json={"user_id": "admin001", "password": "Admin@123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["role"] == "admin"


def test_login_invalid_credentials(client):
    resp = client.post("/auth/login", json={"user_id": "admin001", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/auth/login", json={"user_id": "nobody", "password": "Abc@1234"})
    assert resp.status_code == 401


def test_demo_users_endpoint(client):
    resp = client.get("/auth/demo-users")
    assert resp.status_code == 200
    data = resp.json()
    assert "demo_credentials" in data
    assert len(data["demo_credentials"]) >= 4


def test_me_endpoint_requires_auth(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_endpoint_with_token(client, auth_token):
    if not auth_token:
        pytest.skip("Could not obtain auth token")
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "admin001"


# --- System endpoints ---

def test_health_check(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")


# --- Zones endpoints ---

def test_zones_list(client):
    resp = client.get("/zones/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, (list, dict))


# --- Alerts endpoints ---

def test_alerts_list(client):
    resp = client.get("/alerts/")
    assert resp.status_code == 200


# --- Prediction endpoints ---

def test_prediction_arrival_rate(client):
    resp = client.get("/prediction/arrival-rate")
    assert resp.status_code == 200
    data = resp.json()
    assert "predicted_arrival_rate" in data
    assert data["predicted_arrival_rate"] >= 0


def test_prediction_bottleneck(client):
    resp = client.get("/prediction/bottleneck")
    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 7  # All 7 departments


def test_prediction_exit_rate(client):
    resp = client.get("/prediction/exit-rate")
    assert resp.status_code in (200, 503)  # 503 if model not loaded


def test_ml_models_no_500(client):
    """All prediction endpoints should respond without 500 errors."""
    for endpoint in ["/prediction/arrival-rate", "/prediction/exit-rate", "/prediction/bottleneck"]:
        resp = client.get(endpoint)
        assert resp.status_code != 500, f"{endpoint} returned 500"


# --- Patient endpoints ---

def test_patient_enter_missing_zone(client):
    resp = client.post("/patients/enter", json={
        "tracking_id": "TEST-EDGE-001",
        "name": "Edge Case Patient",
        "zone_name": "nonexistent_zone_xyz"
    })
    assert resp.status_code == 404


def test_negative_occupancy_prevention(client):
    """Exit for a non-existent patient should not crash the server."""
    resp = client.post("/patients/exit", json={"tracking_id": "NONEXISTENT-99999"})
    assert resp.status_code in (200, 404, 422), f"Unexpected status: {resp.status_code}"
    assert resp.status_code != 500


# --- Export endpoints require auth ---

def test_export_occupancy_requires_auth(client):
    resp = client.get("/export/occupancy/csv")
    assert resp.status_code == 401


def test_export_patients_requires_auth(client):
    resp = client.get("/export/patients/csv")
    assert resp.status_code == 401


def test_export_with_auth(client, auth_token):
    if not auth_token:
        pytest.skip("Could not obtain auth token")
    resp = client.get("/export/occupancy/csv", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


# --- Admin export requires auth ---

def test_admin_export_requires_auth(client):
    resp = client.get("/admin/export")
    assert resp.status_code == 401


# --- Reports endpoint requires auth ---

def test_reports_requires_auth(client):
    resp = client.get("/reports/management-summary")
    assert resp.status_code == 401


def test_reports_pdf_with_auth(client, auth_token):
    if not auth_token:
        pytest.skip("Could not obtain auth token")
    resp = client.get("/reports/management-summary", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers.get("content-type", "")
