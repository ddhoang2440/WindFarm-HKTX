from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional
from enum import Enum


class TurbineStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    FAULT = "fault"
    OFFLINE = "offline"


class Turbine(Document):
    asset_id: int
    name: str = ""
    status: TurbineStatus = TurbineStatus.NORMAL
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    capacity_kw: Optional[float] = None
    manufacturer: Optional[str] = None
    commissioned_date: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "turbines"
        indexes = ["asset_id", "status"]

    def is_online(self) -> bool:
        if not self.last_seen_at:
            return False
        return (datetime.utcnow() - self.last_seen_at).total_seconds() < 300