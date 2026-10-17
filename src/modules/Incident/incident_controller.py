"""
IncidentController – REST API for IncidentService.
Routes: /api/incidents
"""
from fastapi import APIRouter, Query, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional

from src.modules.Incident import incident_service
from src.models.User import User
from src.models.Incident import Incident, IncidentSeverity
from src.core.dependencies import get_current_user_dep, require_admin

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class CreateBody(BaseModel):
    asset_id: int
    label: str = "Fault"
    severity: IncidentSeverity = IncidentSeverity.WARNING


class ResolveBody(BaseModel):
    notes: str = ""


def _serialize_incident(inc: Incident) -> dict:
    return {
        "event_id": inc.event_id,
        "asset_id": inc.asset_id,
        "label": inc.label,
        "severity": inc.severity.value,
        "status": inc.status.value,
        "handled_by": str(inc.handled_by) if inc.handled_by else None,
        "resolved_by": str(inc.resolved_by) if inc.resolved_by else None,
        "created_at": inc.created_at.isoformat(),
        "acknowledged_at": (
            inc.acknowledged_at.isoformat() if inc.acknowledged_at else None
        ),
        "resolved_at": (
            inc.resolved_at.isoformat() if inc.resolved_at else None
        ),
        "notes": inc.notes,
        "duration_seconds": inc.duration_seconds(),
    }


@router.get("/active")
async def get_active(
    current_user: User = Depends(get_current_user_dep),
):
    incidents = await incident_service.get_active()
    return [_serialize_incident(i) for i in incidents]


@router.get("/")
async def get_all(
    asset_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user_dep),
):
    incidents = await incident_service.get_all(
        asset_id=asset_id, limit=limit
    )
    return [_serialize_incident(i) for i in incidents]


@router.post("/", status_code=201)
async def create(
    body: CreateBody,
    admin: User = Depends(require_admin),
):
    incident = await incident_service.create(
        body.asset_id, body.label, body.severity
    )
    return _serialize_incident(incident)


@router.patch("/{event_id}/acknowledge")
async def acknowledge(
    event_id: str,
    current_user: User = Depends(get_current_user_dep),
):
    incident = await incident_service.acknowledge(
        event_id, str(current_user.id)
    )
    return _serialize_incident(incident)


@router.patch("/{event_id}/resolve")
async def resolve(
    event_id: str,
    body: ResolveBody,
    current_user: User = Depends(get_current_user_dep),
):
    incident = await incident_service.resolve(
        event_id, str(current_user.id), body.notes
    )
    return _serialize_incident(incident)