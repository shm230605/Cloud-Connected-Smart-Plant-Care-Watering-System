from __future__ import annotations

import argparse
import logging
import math
import random
import time
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def run(base_url: str, device_id: str, interval: float, offline: bool) -> None:
    soil, temperature, humidity = 58.0, 25.0, 62.0
    client = httpx.Client(timeout=5)
    logging.info("Starting virtual sensor %s", device_id)
    while True:
        minute = datetime.now().minute + datetime.now().hour * 60
        daylight = max(0, math.sin((minute - 360) / 720 * math.pi))
        soil = max(0, min(100, soil - random.uniform(0.5, 1.3)))
        temperature = max(15, min(40, temperature + random.uniform(-0.5, 0.5)))
        humidity = max(30, min(90, humidity + random.uniform(-1.5, 1.5)))
        payload = {"device_id": device_id, "soil_moisture": round(soil, 1), "temperature": round(temperature, 1), "humidity": round(humidity, 1), "light_level": round(daylight * 100, 1), "water_tank_level": 82, "timestamp": datetime.now(timezone.utc).isoformat()}
        if not offline:
            try:
                response = client.post(f"{base_url}/api/sensors/data", json=payload, headers={"x-api-key": "demo-device-key"})
                response.raise_for_status()
                result = response.json()
                if result.get("watering_triggered"):
                    logging.info("Automatic watering triggered at %.1f%%", soil)
                    soil = min(100, soil + 15)
                logging.info("reading soil=%s%% temp=%sC humidity=%s%% light=%s%%", payload["soil_moisture"], payload["temperature"], payload["humidity"], payload["light_level"])
            except httpx.HTTPError as exc:
                logging.warning("API unavailable, retrying next cycle: %s", exc)
        else:
            logging.info("offline reading soil=%.1f%% temp=%.1fC humidity=%.1f%%", soil, temperature, humidity)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Realistic virtual plant sensor")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--device-id", default="PLANT-001")
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    run(args.base_url, args.device_id, args.interval, args.offline)
