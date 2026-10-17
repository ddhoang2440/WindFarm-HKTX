from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional


class Telemetry(Document):
    asset_id: int
    timestamp: datetime

    # Core fields
    wind_speed: Optional[float] = None
    power: Optional[float] = None

    # Extended sensor readings
    rotor_speed: Optional[float] = None
    generator_speed: Optional[float] = None
    blade_pitch_angle: Optional[float] = None
    nacelle_temperature: Optional[float] = None
    gearbox_temperature: Optional[float] = None
    ambient_temperature: Optional[float] = None

    # Raw payload for debugging
    raw_payload: Optional[dict] = None

    class Settings:
        name = "telemetry"
        timeseries = {
            "time_field": "timestamp",
            "meta_field": "asset_id",
            "granularity": "seconds",
        }