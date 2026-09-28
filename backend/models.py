from datetime import datetime
from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    soil_moisture: float = Field(ge=0, le=100)
    temperature: float = Field(ge=-20, le=70)
    humidity: float = Field(ge=0, le=100)
    light_level: float = Field(ge=0, le=100)
    water_tank_level: float = Field(default=100, ge=0, le=100)
    timestamp: datetime | None = None


class ThresholdUpdate(BaseModel):
    threshold: float = Field(ge=5, le=95)


class WaterRequest(BaseModel):
    duration_seconds: int = Field(default=4, ge=1, le=30)
