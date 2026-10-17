from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Any


class TelemetryIngestDTO(BaseModel):
    """Payload cho POST /api/telemetry/ingest."""
    asset_id: int = Field(..., ge=1)
    timestamp: Optional[datetime] = None

    wind_speed: Optional[float] = None
    power: Optional[float] = None
    rotor_speed: Optional[float] = None
    generator_speed: Optional[float] = None
    blade_pitch_angle: Optional[float] = None
    nacelle_temperature: Optional[float] = None
    gearbox_temperature: Optional[float] = None
    ambient_temperature: Optional[float] = None

    raw_payload: Optional[dict[str, Any]] = None

    @field_validator("wind_speed", "power", "rotor_speed", "generator_speed")
    @classmethod
    def non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("must be >= 0")
        return v

    @field_validator("blade_pitch_angle")
    @classmethod
    def pitch_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("blade_pitch_angle must be in [-180, 180]")
        return v


class TelemetryReadingDTO(BaseModel):
    """Response shape cho 1 reading."""
    timestamp: datetime
    asset_id: int
    wind_speed: Optional[float] = None
    power: Optional[float] = None
    rotor_speed: Optional[float] = None
    generator_speed: Optional[float] = None
    blade_pitch_angle: Optional[float] = None
    nacelle_temperature: Optional[float] = None
    gearbox_temperature: Optional[float] = None
    ambient_temperature: Optional[float] = None

    @classmethod
    def from_doc(cls, doc) -> "TelemetryReadingDTO":
        return cls(
            timestamp=doc.timestamp,
            asset_id=doc.asset_id,
            wind_speed=doc.wind_speed,
            power=doc.power,
            rotor_speed=doc.rotor_speed,
            generator_speed=doc.generator_speed,
            blade_pitch_angle=doc.blade_pitch_angle,
            nacelle_temperature=doc.nacelle_temperature,
            gearbox_temperature=doc.gearbox_temperature,
            ambient_temperature=doc.ambient_temperature,
        )