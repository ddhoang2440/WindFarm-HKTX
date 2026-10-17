# src/models/Settings.py
from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional


class SystemSettings(Document):
    """
    Singleton document storing all system settings.
    Only 1 document exists in the collection.
    """
    stream: dict = Field(default_factory=lambda: {
        "interval_ms": 1000,
        "enabled": True,
        "dataset_path": None,
    })
    ai: dict = Field(default_factory=lambda: {
        "model_path": "src/modules/AI_Agent/model_weights/fault_classifier.pkl",
        "threshold": 0.5,
        "enabled": True,
    })
    datadog: dict = Field(default_factory=lambda: {
        "enabled": True,
        "api_key": "",
        "app_key": "",
        "env": "development",
        "alert_recipients": [],
    })
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None

    class Settings:
        name = "system_settings"