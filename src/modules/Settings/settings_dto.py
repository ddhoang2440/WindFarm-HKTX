from pydantic import BaseModel, Field, field_validator
from typing import Optional


class StreamSettingsDTO(BaseModel):
    interval_ms: int = Field(default=1000, ge=100, le=60000)
    enabled: bool = True
    dataset_path: Optional[str] = None


class AISettingsDTO(BaseModel):
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    enabled: bool = True
    model_path: Optional[str] = None

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not (0 <= v <= 1):
            raise ValueError("Threshold must be between 0 and 1")
        return v


class DatadogSettingsDTO(BaseModel):
    enabled: bool = True
    api_key: Optional[str] = None
    app_key: Optional[str] = None
    env: str = "development"
    alert_recipients: list[str] = []


class UpdateSettingsDTO(BaseModel):
    stream: Optional[StreamSettingsDTO] = None
    ai: Optional[AISettingsDTO] = None
    datadog: Optional[DatadogSettingsDTO] = None