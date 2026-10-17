"""
IncidentService – class diagram:
    + create(asset_id, label) -> Incident
    + acknowledge(event_id, user_id)
    + resolve(event_id, notes)
    + get_active() -> List[Incident]
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
from pymongo.errors import DuplicateKeyError

from beanie import PydanticObjectId

from src.models.Incident import (
    Incident,
    IncidentStatus,
    IncidentSeverity,
)
from src.models.Turbine import Turbine, TurbineStatus
from src.core.exceptions import (
    NotFoundException,
    ConflictException,
)
from src.core.logger import get_logger
from src.config import datadog as dd

logger = get_logger(__name__)


async def create(
    asset_id: int,
    label: str = "Fault",
    severity: IncidentSeverity = IncidentSeverity.WARNING,
    telemetry_snapshot: Optional[Dict[str, Any]] = None,
) -> Incident:
    """create(asset_id, label) – diagram method."""
    try:
        await incident.insert()
    except DuplicateKeyError:
        existing = await Incident.find_one(
            Incident.asset_id == asset_id,
            Incident.status != IncidentStatus.RESOLVED,
        )
        if existing:
            logger.info(
                f"Active incident already exists for asset_id={asset_id}, "
                f"skipping creation (event_id={existing.event_id})"
            )
            return existing

    incident = Incident(
        event_id=str(uuid4()),
        asset_id=asset_id,
        label=label,
        severity=severity,
        telemetry_snapshot=telemetry_snapshot,
    )
    await incident.insert()
    logger.info(
        f"[IncidentService] Created incident event_id={incident.event_id} "
        f"for asset_id={asset_id}"
    )

    # Update turbine status → fault
    turbine = await Turbine.find_one(Turbine.asset_id == asset_id)
    if turbine:
        turbine.status = TurbineStatus.FAULT
        turbine.updated_at = datetime.utcnow()
        await turbine.save()

    # Sync Datadog (non-blocking)
    try:
        await dd.trigger_alert(incident)
        await dd.push_metric(
            "incident.created",
            1.0,
            tags=[f"asset_id:{asset_id}", f"severity:{severity.value}"],
        )
    except Exception as e:
        logger.error(f"Datadog sync failed: {e}")

    return incident


async def acknowledge(event_id: str, user_id: str) -> Incident:
    """acknowledge(event_id, user_id) – diagram method."""
    incident = await Incident.find_one(Incident.event_id == event_id)
    if not incident:
        raise NotFoundException(f"Incident event_id={event_id} not found")

    if incident.status == IncidentStatus.RESOLVED:
        raise ConflictException("Cannot acknowledge a resolved incident")

    if incident.status == IncidentStatus.ACKNOWLEDGED:
        if str(incident.handled_by) == user_id:
            raise ConflictException(
                "You have already acknowledged this alert"
            )
        raise ConflictException(
            "This alert is being handled by another user"
        )

    incident.status = IncidentStatus.ACKNOWLEDGED
    incident.handled_by = PydanticObjectId(user_id)
    incident.acknowledged_at = datetime.utcnow()
    await incident.save()

    logger.info(
        f"[IncidentService] Acknowledged event_id={event_id} by {user_id}"
    )

    try:
        await dd.push_metric(
            "incident.acknowledged",
            1.0,
            tags=[f"asset_id:{incident.asset_id}"],
        )
    except Exception as e:
        logger.error(f"Datadog sync failed: {e}")

    return incident


async def resolve(
    event_id: str, user_id: str, notes: str = ""
) -> Incident:
    """resolve(event_id, notes) – diagram method."""
    incident = await Incident.find_one(Incident.event_id == event_id)
    if not incident:
        raise NotFoundException(f"Incident event_id={event_id} not found")

    if incident.status == IncidentStatus.RESOLVED:
        raise ConflictException("Incident is already resolved")

    incident.status = IncidentStatus.RESOLVED
    incident.resolved_by = PydanticObjectId(user_id)
    incident.notes = notes
    incident.resolved_at = datetime.utcnow()
    await incident.save()

    logger.info(f"[IncidentService] Resolved event_id={event_id}")

    # Check if there are still open incidents for this turbine
    still_open = await Incident.find(
        Incident.asset_id == incident.asset_id,
        Incident.status != IncidentStatus.RESOLVED,
    ).count()

    if still_open == 0:
        turbine = await Turbine.find_one(
            Turbine.asset_id == incident.asset_id
        )
        if turbine:
            turbine.status = TurbineStatus.NORMAL
            turbine.updated_at = datetime.utcnow()
            await turbine.save()

    try:
        await dd.push_metric(
            "incident.resolved",
            1.0,
            tags=[f"asset_id:{incident.asset_id}"],
        )
    except Exception as e:
        logger.error(f"Datadog sync failed: {e}")

    return incident


async def get_active() -> List[Incident]:
    """get_active() – diagram method."""
    return await Incident.find(
        Incident.status != IncidentStatus.RESOLVED
    ).sort(-Incident.created_at).to_list()


async def get_all(
    asset_id: Optional[int] = None, limit: int = 50
) -> List[Incident]:
    """Extended: paginated history with optional asset filter."""
    if asset_id is not None:
        query = Incident.find(Incident.asset_id == asset_id)
    else:
        query = Incident.find()
    return await query.sort(-Incident.created_at).limit(limit).to_list()