from modules.telemetry.telemetry_service import process_telemetry
from fastapi import APIRouter, Depends
from core.security import verify_token
from models.telemetry import TelemetryInput
from modules.telemetry.telemetry_service import process_telemetry  

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])

@router.post("", dependencies=[Depends(verify_token)])
async def post_telemetry(payload: TelemetryInput):
    # Gọi service thật
    record = await process_telemetry(payload)
    return {"status": "success", "id": str(record.id)}
    