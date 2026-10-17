"""
DashboardController – class diagram:
    + get_overview()
    + get_turbine_detail(asset_id: Int)
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

from src.modules.Telemetry import telemetry_service
from src.modules.Incident import incident_service
from src.models.Turbine import TurbineStatus

router = APIRouter()


@router.get("/overview")
async def get_overview():
    turbines = await telemetry_service.get_all_latest()
    active_incidents = await incident_service.get_active()

    return {
        "turbines": [
            {
                "asset_id": t.asset_id,
                "name": t.name,
                "status": t.status.value,
                "is_online": t.is_online(),
            }
            for t in turbines
        ],
        "active_incident_count": len(active_incidents),
        "turbine_count": len(turbines),
        "fault_count": sum(
            1 for t in turbines if t.status == TurbineStatus.FAULT
        ),
    }


@router.get("/turbine/{asset_id}")
async def get_turbine_detail(
    asset_id: int,
    limit: int = Query(100, le=1000),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    history = await telemetry_service.get_history(
        asset_id, limit, start, end
    )
    incidents = await incident_service.get_all(asset_id=asset_id, limit=20)

    return {
        "asset_id": asset_id,
        "telemetry": [
            {
                "timestamp": t.timestamp.isoformat(),
                "wind_speed": t.wind_speed,
                "power": t.power,
                "rotor_speed": t.rotor_speed,
            }
            for t in history
        ],
        "incidents": incidents,
    }