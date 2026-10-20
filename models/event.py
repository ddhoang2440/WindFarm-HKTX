from datetime import datetime, timezone
from pydantic import BaseModel, Field
from beanie import Document

class EventInput(BaseModel):
    event_id: int
    asset_id: int
    event_label: str
    event_start: datetime
    event_end: datetime
    event_description: str

class EventRecord(Document, EventInput):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "events"