from beanie import Document, PydanticObjectId
from pydantic import Field
from datetime import datetime
from typing import Optional
from enum import Enum


class PredictionClass(str, Enum):
    NORMAL = "normal"
    FAULT = "fault"
    UNCERTAIN = "uncertain"


class Prediction(Document):
    asset_id: int
    timestamp: datetime
    telemetry_id: PydanticObjectId
    prediction: PredictionClass = PredictionClass.NORMAL
    confidence: Optional[float] = None
    model_version: Optional[str] = None
    is_processed: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "predictions"
        indexes = ["asset_id", "timestamp", "telemetry_id"]

    def is_uncertain(self) -> bool:
        return self.prediction == PredictionClass.UNCERTAIN