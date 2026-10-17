from beanie import Document, PydanticObjectId
from pydantic import Field
from datetime import datetime
from typing import Optional
from enum import Enum
from uuid import uuid4
from pymongo import IndexModel, ASCENDING


class IncidentStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class IncidentSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Incident(Document):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    asset_id: int
    label: str
    severity: IncidentSeverity = IncidentSeverity.WARNING
    status: IncidentStatus = IncidentStatus.OPEN
    handled_by: Optional[PydanticObjectId] = None
    resolved_by: Optional[PydanticObjectId] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None
    telemetry_snapshot: Optional[dict] = None

    class Settings:
        name = "incidents"
        indexes = [
            "asset_id",
            "status",
            "event_id",
            "created_at",
            # Partial unique: mỗi asset chỉ có 1 incident chưa resolved
            IndexModel(
                [("asset_id", ASCENDING)],
                unique=True,
                partialFilterExpression={
                    "status": {"$in": ["open", "acknowledged"]}
                },
                name="uniq_active_incident_per_asset",
            ),
        ]

    def duration_seconds(self) -> Optional[float]:
        if not self.resolved_at:
            return None
        return (self.resolved_at - self.created_at).total_seconds()

    def is_active(self) -> bool:
        return self.status != IncidentStatus.RESOLVED