from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.modules.Turbine import turbine_service
from src.core.dependencies import get_current_user_dep
from src.models.User import User
from src.models.Turbine import TurbineStatus

router = APIRouter()


class UpdateStatusBody(BaseModel):
    status: TurbineStatus


@router.get("/")
async def list_turbines(
    current_user: User = Depends(get_current_user_dep),
):
    turbines = await turbine_service.get_all_turbines()
    return [
        {
            "asset_id": t.asset_id,
            "name": t.name,
            "status": t.status.value,
            "location_lat": t.location_lat,
            "location_lng": t.location_lng,
            "capacity_kw": t.capacity_kw,
            "manufacturer": t.manufacturer,
            "is_online": t.is_online(),
            "last_seen_at": (
                t.last_seen_at.isoformat() if t.last_seen_at else None
            ),
        }
        for t in turbines
    ]


@router.get("/{asset_id}")
async def get_turbine(
    asset_id: int,
    current_user: User = Depends(get_current_user_dep),
):
    turbine = await turbine_service.get_turbine_by_asset_id(asset_id)
    return {
        "asset_id": turbine.asset_id,
        "name": turbine.name,
        "status": turbine.status.value,
        "location_lat": turbine.location_lat,
        "location_lng": turbine.location_lng,
        "capacity_kw": turbine.capacity_kw,
        "manufacturer": turbine.manufacturer,
        "commissioned_date": (
            turbine.commissioned_date.isoformat()
            if turbine.commissioned_date
            else None
        ),
        "is_online": turbine.is_online(),
        "last_seen_at": (
            turbine.last_seen_at.isoformat()
            if turbine.last_seen_at
            else None
        ),
    }


@router.patch("/{asset_id}/status")
async def update_status(
    asset_id: int,
    body: UpdateStatusBody,
    current_user: User = Depends(get_current_user_dep),
):
    turbine = await turbine_service.update_turbine_status(
        asset_id, body.status, updated_by=str(current_user.id)
    )
    return {
        "asset_id": turbine.asset_id,
        "status": turbine.status.value,
        "updated_at": turbine.updated_at.isoformat(),
    }