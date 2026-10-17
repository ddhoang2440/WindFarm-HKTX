from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from typing import Optional, List
from datetime import datetime

from src.modules.Telemetry import telemetry_service
from src.modules.Telemetry.telemetry_dto import (
    TelemetryIngestDTO,
    TelemetryReadingDTO,
)

router = APIRouter()

_connections: list[WebSocket] = []


async def _broadcast(data: dict) -> None:
    dead = []
    for ws in _connections:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _connections:
            _connections.remove(ws)


telemetry_service.set_broadcast_callback(_broadcast)


@router.websocket("/ws")
async def ws_telemetry(websocket: WebSocket):
    await websocket.accept()
    _connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _connections:
            _connections.remove(websocket)


@router.post(
    "/ingest",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest one telemetry row",
)
async def ingest(payload: TelemetryIngestDTO):
    reading, pred = await telemetry_service.save(payload.model_dump())
    return {
        "asset_id": reading.asset_id,
        "prediction": pred.prediction.value,
        "confidence": pred.confidence,
        "timestamp": reading.timestamp.isoformat(),
    }


@router.get("/{asset_id}", response_model=List[TelemetryReadingDTO])
async def get_history(
    asset_id: int,
    limit: int = Query(100, le=1000),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    rows = await telemetry_service.get_history(asset_id, limit, start, end)
    return [TelemetryReadingDTO.from_doc(r) for r in rows]