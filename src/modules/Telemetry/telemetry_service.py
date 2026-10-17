"""
TelemetryService – class diagram:
    + save(data) -> (Telemetry, Prediction)
    + get_history(asset_id) -> List[Telemetry]
    + get_all_latest() -> List[Turbine]
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from beanie.operators import And

from src.models.Telemetry import Telemetry
from src.models.Prediction import Prediction, PredictionClass
from src.models.Turbine import Turbine, TurbineStatus
from src.models.Incident import Incident, IncidentStatus
from src.modules.AI_Agent import ai_service
from src.modules.Incident import incident_service
from src.core.exceptions import BadRequestException
from src.core.logger import get_logger
from src.config import datadog as dd

logger = get_logger(__name__)

_broadcast_callback = None


def set_broadcast_callback(fn) -> None:
    global _broadcast_callback
    _broadcast_callback = fn


def _parse_timestamp(ts: Any) -> datetime:
    """Parse timestamp from various formats, fallback to utcnow()."""
    if ts is None:
        return datetime.utcnow()
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            logger.warning(f"Invalid timestamp: {ts}, using utcnow()")
            return datetime.utcnow()
    return datetime.utcnow()


async def save(data: Dict[str, Any]) -> Tuple[Telemetry, Prediction]:
    """save(data) – diagram method."""
    # 1. Validate
    if "asset_id" not in data:
        raise BadRequestException("asset_id is required")

    asset_id = int(data["asset_id"])
    ts = _parse_timestamp(data.get("timestamp"))

    # 2. AI predict
    prediction_class, confidence = await ai_service.predict(data)

    # 3. Insert raw telemetry
    reading = Telemetry(
        asset_id=asset_id,
        timestamp=ts,
        wind_speed=data.get("wind_speed"),
        power=data.get("power"),
        rotor_speed=data.get("rotor_speed"),
        generator_speed=data.get("generator_speed"),
        blade_pitch_angle=data.get("blade_pitch_angle"),
        nacelle_temperature=data.get("nacelle_temperature"),
        gearbox_temperature=data.get("gearbox_temperature"),
        ambient_temperature=data.get("ambient_temperature"),
    )
    await reading.insert()

    # 4. Insert prediction
    pred = Prediction(
        asset_id=asset_id,
        timestamp=ts,
        telemetry_id=reading.id,
        prediction=prediction_class,
        confidence=confidence,
        model_version=getattr(ai_service, "model_version", None),
    )
    await pred.insert()

    # 5. Update turbine
    turbine = await Turbine.find_one(Turbine.asset_id == asset_id)
    if turbine:
        turbine.last_seen_at = datetime.utcnow()
        turbine.updated_at = datetime.utcnow()

        if prediction_class == PredictionClass.FAULT:
            turbine.status = TurbineStatus.FAULT
        elif (prediction_class == PredictionClass.NORMAL
              and turbine.status == TurbineStatus.FAULT):
            # Reset only if no active incidents
            active = await Incident.find(
                Incident.asset_id == asset_id,
                Incident.status != IncidentStatus.RESOLVED,
            ).count()
            if active == 0:
                turbine.status = TurbineStatus.NORMAL

        await turbine.save()

    # 6. Push Datadog (non-blocking)
    tags = [f"asset_id:{asset_id}"]
    try:
        if reading.power is not None:
            await dd.push_metric("turbine.power", reading.power, tags)
        if reading.wind_speed is not None:
            await dd.push_metric("turbine.wind_speed", reading.wind_speed, tags)
        await dd.push_metric(
            "turbine.anomaly_score",
            confidence if prediction_class == PredictionClass.FAULT else 0.0,
            tags,
        )
    except Exception as e:
        logger.error(f"Datadog push failed: {e}")

    # 7. Auto-create incident
    if prediction_class == PredictionClass.FAULT:
        await incident_service.create(
            asset_id=asset_id,
            label="AI-detected fault",
            telemetry_snapshot=data,
        )

    # 8. Broadcast via WebSocket
    if _broadcast_callback:
        try:
            await _broadcast_callback({
                "asset_id": asset_id,
                "prediction": prediction_class.value,
                "confidence": confidence,
                "wind_speed": reading.wind_speed,
                "power": reading.power,
                "timestamp": reading.timestamp.isoformat(),
            })
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")

    logger.info(
        f"Saved telemetry for asset_id={asset_id}: "
        f"{prediction_class.value} (conf={confidence:.2f})"
    )
    return reading, pred


async def get_history(
    asset_id: int,
    limit: int = 100,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Telemetry]:
    """get_history(asset_id) – diagram method."""
    conditions = [Telemetry.asset_id == asset_id]
    if start:
        conditions.append(Telemetry.timestamp >= start)
    if end:
        conditions.append(Telemetry.timestamp <= end)

    query = Telemetry.find(And(*conditions))
    return await query.sort(-Telemetry.timestamp).limit(limit).to_list()


async def get_all_latest() -> List[Turbine]:
    """get_all_latest() – diagram method."""
    return await Turbine.find_all().sort(Turbine.asset_id).to_list()