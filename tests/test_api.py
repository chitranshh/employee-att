from datetime import datetime, timezone
import mongomock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

@pytest.fixture()
def client():
    client_db = mongomock.MongoClient(tz_aware=True)["test_attendance"]
    client_db.attendance.create_index([("employee_id", 1), ("work_date", 1)], unique=True)
    app.dependency_overrides[get_db] = lambda: client_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def test_punch_in_and_duplicate(client):
    now = datetime.now(timezone.utc).isoformat()
    response = client.post("/attendance/punch-in", json={"employee_id": "EMP001", "occurred_at": now})
    assert response.status_code == 201
    assert response.json()["employee_id"] == "EMP001"
    duplicate = client.post("/attendance/punch-in", json={"employee_id": "EMP001", "occurred_at": now})
    assert duplicate.status_code == 409

def test_punch_out_requires_punch_in(client):
    response = client.post("/attendance/punch-out", json={"employee_id": "MISSING"})
    assert response.status_code == 404

def test_punch_out_completes_record(client):
    punch_in_time = datetime.now(timezone.utc).replace(microsecond=0)
    punch_out_time = punch_in_time.replace(hour=(punch_in_time.hour + 1) % 24)
    # Keep the interval valid even when the current hour is 23.
    from datetime import timedelta
    punch_out_time = punch_in_time + timedelta(hours=1)
    # Skip if generated punch-out is in the future; use a prior-day interval instead.
    if punch_out_time > datetime.now(timezone.utc):
        punch_in_time -= timedelta(days=1)
        punch_out_time = punch_in_time + timedelta(hours=1)
    client.post("/attendance/punch-in", json={"employee_id": "EMP002", "occurred_at": punch_in_time.isoformat()})
    response = client.post("/attendance/punch-out", json={"employee_id": "EMP002", "occurred_at": punch_out_time.isoformat()})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

def test_correction_creates_audit_log(client):
    from datetime import timedelta
    punch_in_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=8)
    punch_out_time = punch_in_time + timedelta(hours=8)
    created = client.post("/attendance/punch-in", json={"employee_id": "EMP003", "occurred_at": punch_in_time.isoformat()})
    record_id = created.json()["_id"]
    response = client.patch(f"/attendance/{record_id}/correction", json={
        "punch_out": punch_out_time.isoformat(),
        "reason": "Manager approved correction",
        "corrected_by": "manager@example.com"
    })
    assert response.status_code == 200
    assert response.json()["attendance"]["status"] == "completed"
    audit = client.get(f"/attendance/{record_id}/audit")
    assert audit.status_code == 200
    assert len(audit.json()["items"]) == 1
