from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from automation import should_water
from backend.database import connection, init_db, row_to_dict
from backend.models import SensorReading, ThresholdUpdate, WaterRequest

ROOT = Path(__file__).resolve().parent.parent
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "demo-device-key")
app = FastAPI(title="Verdant Cloud Plant Care API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init_db()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_device(conn, device_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO devices(device_id, plant_name, plant_type, location, threshold, last_seen, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (device_id, "Tomato No. 1", "Tomato", "Window ledge", 30, now(), now()),
    )


def last_event(conn, device_id: str):
    return conn.execute("SELECT * FROM watering_events WHERE device_id=? ORDER BY timestamp DESC LIMIT 1", (device_id,)).fetchone()


def create_alert(conn, device_id: str, level: str, alert_type: str, message: str) -> None:
    existing = conn.execute("SELECT id FROM alerts WHERE device_id=? AND alert_type=? AND acknowledged=0", (device_id, alert_type)).fetchone()
    if not existing:
        conn.execute("INSERT INTO alerts(device_id, level, alert_type, message, created_at) VALUES (?, ?, ?, ?, ?)", (device_id, level, alert_type, message, now()))


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "verdant-api", "timestamp": now()}


@app.post("/api/sensors/data")
def ingest(reading: SensorReading, x_api_key: str | None = Header(default=None)):
    if x_api_key and x_api_key != DEVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid device API key")
    recorded_at = (reading.timestamp or datetime.now(timezone.utc)).isoformat()
    with connection() as conn:
        ensure_device(conn, reading.device_id)
        device = conn.execute("SELECT * FROM devices WHERE device_id=?", (reading.device_id,)).fetchone()
        conn.execute("INSERT OR IGNORE INTO readings(device_id, soil_moisture, temperature, humidity, light_level, water_tank_level, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)", (reading.device_id, reading.soil_moisture, reading.temperature, reading.humidity, reading.light_level, reading.water_tank_level, recorded_at))
        conn.execute("UPDATE devices SET last_seen=? WHERE device_id=?", (recorded_at, reading.device_id))
        if reading.soil_moisture < device["threshold"]:
            create_alert(conn, reading.device_id, "warning", "LOW_SOIL", f"{device['plant_name']} moisture dropped to {reading.soil_moisture:.0f}%.")
        if reading.temperature > 35:
            create_alert(conn, reading.device_id, "critical", "HIGH_TEMPERATURE", f"Temperature reached {reading.temperature:.1f} C.")
        event = last_event(conn, reading.device_id)
        if should_water(reading.soil_moisture, device["threshold"], reading.water_tank_level, bool(device["auto_water"]), event["timestamp"] if event else None):
            conn.execute("INSERT INTO watering_events(device_id, trigger_type, moisture_before, duration_seconds, timestamp) VALUES (?, ?, ?, ?, ?)", (reading.device_id, "automatic", reading.soil_moisture, 4, now()))
            return {"accepted": True, "watering_triggered": True, "pump_duration_seconds": 4}
    return {"accepted": True, "watering_triggered": False}


@app.get("/api/devices")
def devices():
    with connection() as conn:
        rows = conn.execute("SELECT * FROM devices ORDER BY created_at").fetchall()
        return [row_to_dict(row) for row in rows]


@app.get("/api/devices/{device_id}/overview")
def overview(device_id: str):
    with connection() as conn:
        device = conn.execute("SELECT * FROM devices WHERE device_id=?", (device_id,)).fetchone()
        if not device:
            raise HTTPException(404, "Device not found")
        latest = conn.execute("SELECT * FROM readings WHERE device_id=? ORDER BY timestamp DESC LIMIT 1", (device_id,)).fetchone()
        readings = conn.execute("SELECT * FROM readings WHERE device_id=? ORDER BY timestamp DESC LIMIT 36", (device_id,)).fetchall()
        events = conn.execute("SELECT * FROM watering_events WHERE device_id=? ORDER BY timestamp DESC LIMIT 8", (device_id,)).fetchall()
        alerts = conn.execute("SELECT * FROM alerts WHERE device_id=? AND acknowledged=0 ORDER BY created_at DESC LIMIT 8", (device_id,)).fetchall()
        last_seen = datetime.fromisoformat(device["last_seen"]) if device["last_seen"] else datetime.min.replace(tzinfo=timezone.utc)
        status = "online" if datetime.now(timezone.utc) - last_seen < timedelta(minutes=2) else "offline"
        return {"device": {**row_to_dict(device), "status": status}, "latest": row_to_dict(latest), "history": [row_to_dict(row) for row in reversed(readings)], "watering_history": [row_to_dict(row) for row in events], "alerts": [row_to_dict(row) for row in alerts]}


@app.put("/api/devices/{device_id}/threshold")
def threshold(device_id: str, payload: ThresholdUpdate):
    with connection() as conn:
        if not conn.execute("SELECT 1 FROM devices WHERE device_id=?", (device_id,)).fetchone():
            raise HTTPException(404, "Device not found")
        conn.execute("UPDATE devices SET threshold=? WHERE device_id=?", (payload.threshold, device_id))
    return {"device_id": device_id, "threshold": payload.threshold}


@app.put("/api/devices/{device_id}/automation")
def automation(device_id: str, enabled: bool = Query(...)):
    with connection() as conn:
        conn.execute("UPDATE devices SET auto_water=? WHERE device_id=?", (int(enabled), device_id))
    return {"device_id": device_id, "auto_water": enabled}


@app.post("/api/devices/{device_id}/water")
def water(device_id: str, payload: WaterRequest):
    with connection() as conn:
        device = conn.execute("SELECT * FROM devices WHERE device_id=?", (device_id,)).fetchone()
        if not device:
            raise HTTPException(404, "Device not found")
        latest = conn.execute("SELECT soil_moisture FROM readings WHERE device_id=? ORDER BY timestamp DESC LIMIT 1", (device_id,)).fetchone()
        moisture = latest["soil_moisture"] if latest else 0
        conn.execute("INSERT INTO watering_events(device_id, trigger_type, moisture_before, duration_seconds, timestamp) VALUES (?, ?, ?, ?, ?)", (device_id, "manual", moisture, payload.duration_seconds, now()))
    return {"queued": True, "duration_seconds": payload.duration_seconds}


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: int):
    with connection() as conn:
        conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))
    return {"acknowledged": True}


@app.get("/")
def frontend():
    return FileResponse(ROOT / "frontend" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
