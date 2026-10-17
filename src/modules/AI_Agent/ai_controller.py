"""
AdminController – start_stream(), set_threshold().
Routes: /api/admin
"""
import asyncio
import csv
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.modules.AI_Agent import ai_service
from src.modules.Telemetry import telemetry_service
from src.core.dependencies import require_admin
from src.models.User import User
from src.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# ── Stream state ───────────────────────────────────────────────────────────────
_stream_task: asyncio.Task | None = None
_stream_running: bool = False


class ThresholdBody(BaseModel):
    threshold: float = Field(ge=0.0, le=1.0)


class StreamBody(BaseModel):
    asset_id: int = 0
    interval_ms: int = Field(default=1000, ge=100, le=60000)


async def _stream_worker(asset_id: int, interval_ms: int) -> None:
    """Background worker: read CSV → call TelemetryService.save() directly."""
    global _stream_running
    csv_path = Path(f"data/{asset_id}.csv")
    if not csv_path.exists():
        logger.error(f"[AdminController] CSV not found: {csv_path}")
        _stream_running = False
        return

    logger.info(f"[AdminController] Stream started: asset_id={asset_id}")

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not _stream_running:
                break

            payload = {"asset_id": asset_id}
            for k, v in row.items():
                try:
                    payload[k] = float(v)
                except (ValueError, TypeError):
                    payload[k] = v

            try:
                await telemetry_service.save(payload)
            except Exception as exc:
                logger.warning(f"[AdminController] Ingest error: {exc}")

            await asyncio.sleep(interval_ms / 1000)

    _stream_running = False
    logger.info("[AdminController] Stream finished.")


@router.post("/stream/start")
async def start_stream(
    body: StreamBody,
    admin: User = Depends(require_admin),
):
    global _stream_running, _stream_task
    if _stream_running:
        raise HTTPException(400, "Stream already running.")

    _stream_running = True
    _stream_task = asyncio.create_task(
        _stream_worker(body.asset_id, body.interval_ms)
    )
    return {"status": "started", "asset_id": body.asset_id}


@router.post("/stream/stop")
async def stop_stream(admin: User = Depends(require_admin)):
    global _stream_running, _stream_task
    _stream_running = False
    if _stream_task:
        _stream_task.cancel()
        _stream_task = None
    return {"status": "stopped"}


@router.get("/stream/status")
async def stream_status(admin: User = Depends(require_admin)):
    return {"running": _stream_running}


@router.put("/threshold")
async def set_threshold(
    body: ThresholdBody,
    admin: User = Depends(require_admin),
):
    try:
        await ai_service.update_threshold(body.threshold)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"threshold": body.threshold, "status": "updated"}


@router.get("/threshold")
async def get_threshold(admin: User = Depends(require_admin)):
    threshold = await ai_service.get_threshold()
    return {"threshold": threshold}