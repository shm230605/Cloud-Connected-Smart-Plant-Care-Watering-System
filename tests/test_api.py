import os
os.environ["DATABASE_PATH"] = "data/test.db"

from fastapi.testclient import TestClient
from backend.app import app
from backend.database import init_db

client = TestClient(app)


def setup_module():
    if os.path.exists("data/test.db"):
        os.remove("data/test.db")
    init_db()


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_and_overview():
    response = client.post("/api/sensors/data", json={"device_id":"TEST-001","soil_moisture":55,"temperature":24,"humidity":60,"light_level":75,"water_tank_level":90})
    assert response.status_code == 200
    overview = client.get("/api/devices/TEST-001/overview")
    assert overview.status_code == 200
    assert overview.json()["latest"]["soil_moisture"] == 55


def test_validation_rejects_invalid_reading():
    response = client.post("/api/sensors/data", json={"device_id":"TEST-002","soil_moisture":150,"temperature":24,"humidity":60,"light_level":75})
    assert response.status_code == 422


def test_low_moisture_triggers_automation():
    response = client.post("/api/sensors/data", json={"device_id":"TEST-003","soil_moisture":20,"temperature":24,"humidity":60,"light_level":75,"water_tank_level":90})
    assert response.status_code == 200
    assert response.json()["watering_triggered"] is True


def test_manual_watering():
    response = client.post("/api/devices/TEST-001/water", json={"duration_seconds":3})
    assert response.status_code == 200
    assert response.json()["queued"] is True
