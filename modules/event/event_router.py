from fastapi import APIRouter, Depends, BackgroundTasks
from core.security import verify_token
from models.event import EventInput, EventRecord

router = APIRouter(prefix="/api/v1/events", tags=["Events"])

@router.post("", dependencies=[Depends(verify_token)])
async def log_event(payload: EventInput):
    record = EventRecord(**payload.model_dump())
    await record.insert()
    
    
    return {"status": "success", "event_id": payload.event_id}