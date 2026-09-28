from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/plantcare.db"))


def connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                plant_name TEXT NOT NULL,
                plant_type TEXT NOT NULL,
                location TEXT NOT NULL,
                threshold REAL NOT NULL DEFAULT 30,
                auto_water INTEGER NOT NULL DEFAULT 1,
                last_seen TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                soil_moisture REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                light_level REAL NOT NULL,
                water_tank_level REAL NOT NULL,
                timestamp TEXT NOT NULL,
                UNIQUE(device_id, timestamp),
                FOREIGN KEY(device_id) REFERENCES devices(device_id)
            );
            CREATE TABLE IF NOT EXISTS watering_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                moisture_before REAL NOT NULL,
                duration_seconds INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(device_id) REFERENCES devices(device_id)
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                level TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(device_id) REFERENCES devices(device_id)
            );
            CREATE INDEX IF NOT EXISTS idx_readings_device_time ON readings(device_id, timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_alerts_device_time ON alerts(device_id, created_at DESC);
            """
        )
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None
