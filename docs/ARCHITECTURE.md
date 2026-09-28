# Architecture Notes

## Runtime boundaries

1. **Sensor publisher**: `sensor_simulator/simulator.py` models one plant and sends a typed HTTPS JSON reading. The same contract can be implemented by ESP32 firmware.
2. **API boundary**: `backend/app.py` validates readings with Pydantic, authenticates an optional device key, and exposes device control endpoints.
3. **Persistence**: `backend/database.py` creates normalized device, reading, watering event, and alert tables. The reading table has a composite index for time-series retrieval.
4. **Decision engine**: `automation.py` enforces threshold, tank-level, auto-water, and cooldown guards before a watering event is recorded.
5. **Presentation**: `frontend/` is a static dashboard served by FastAPI. It polls the overview endpoint so the project remains dependency-free in a local classroom environment.

## Production evolution

- Replace polling with WebSockets or Firestore listeners.
- Replace SQLite with PostgreSQL, Firestore, DynamoDB, or TimescaleDB.
- Put API Gateway / WAF / rate limiting in front of the service.
- Use per-device signed credentials and a secrets manager.
- Move watering decisions to a queue-backed worker for high device counts.
- Store raw readings with retention policies and roll up daily aggregates for analytics.
- Require user authentication and device ownership authorization for every dashboard action.

## Failure behavior

- Invalid readings receive HTTP 422 and are never stored.
- Invalid device keys receive HTTP 401.
- Duplicate timestamps are ignored using a unique device/timestamp constraint.
- Simulator HTTP failures are logged and retried on the next cycle.
- Offline state is computed from `last_seen`; a production worker should create a dedicated offline alert after the expected heartbeat interval.
- Empty water tanks block automatic watering.
