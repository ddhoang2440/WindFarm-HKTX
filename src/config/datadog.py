"""
DatadogIntegration – async wrapper for Datadog API.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

from src.config.settings import get_settings

if TYPE_CHECKING:
    from src.models.Incident import Incident

settings = get_settings()
logger = logging.getLogger(__name__)

try:
    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v2.api.metrics_api import MetricsApi
    from datadog_api_client.v2.model.metric_payload import MetricPayload
    from datadog_api_client.v2.model.metric_series import MetricSeries
    from datadog_api_client.v2.model.metric_point import MetricPoint
    from datadog_api_client.v1.api.events_api import EventsApi
    from datadog_api_client.v1.model.event_create_request import EventCreateRequest
    import time as _time
    _DD_AVAILABLE = True
except ImportError:
    _DD_AVAILABLE = False
    logger.warning("datadog-api-client not installed – disabled.")


def _get_config() -> "Configuration | None":
    if not _DD_AVAILABLE:
        return None
    cfg = Configuration()
    cfg.api_key["apiKeyAuth"] = settings.dd_api_key
    cfg.server_variables["site"] = "datadoghq.com"
    return cfg


# ── push_metric ────────────────────────────────────────────────────────────────

async def push_metric(
    name: str, value: float, tags: list[str] | None = None
) -> None:
    if not _DD_AVAILABLE or not settings.dd_api_key:
        logger.debug(f"[Datadog] push_metric skipped: {name}={value}")
        return
    await asyncio.to_thread(_push_metric_sync, name, value, tags)


def _push_metric_sync(
    name: str, value: float, tags: list[str] | None
) -> None:
    cfg = _get_config()
    try:
        with ApiClient(cfg) as client:
            api = MetricsApi(client)
            payload = MetricPayload(
                series=[
                    MetricSeries(
                        metric=f"windfarm.{name}",
                        points=[MetricPoint(
                            timestamp=int(_time.time()),
                            value=value,
                        )],
                        tags=tags or [
                            f"env:{settings.dd_env}",
                            f"service:{settings.dd_service}",
                        ],
                    )
                ]
            )
            api.submit_metrics(body=payload)
            logger.debug(f"[Datadog] metric sent: {name}={value}")
    except Exception as exc:
        logger.error(f"[Datadog] push_metric failed: {exc}")


# ── trigger_alert ──────────────────────────────────────────────────────────────

async def trigger_alert(incident: "Incident") -> None:
    if not _DD_AVAILABLE or not settings.dd_api_key:
        logger.debug(f"[Datadog] trigger_alert skipped: {incident.event_id}")
        return
    await asyncio.to_thread(_trigger_alert_sync, incident)


def _trigger_alert_sync(incident: "Incident") -> None:
    cfg = _get_config()
    try:
        with ApiClient(cfg) as client:
            api = EventsApi(client)
            body = EventCreateRequest(
                title=f"WindFarm Fault – Turbine {incident.asset_id}",
                text=(
                    f"event_id: {incident.event_id}\n"
                    f"asset_id: {incident.asset_id}\n"
                    f"label: {incident.label}\n"
                    f"status: {incident.status}"
                ),
                alert_type="error",
                tags=[
                    f"asset_id:{incident.asset_id}",
                    f"event_id:{incident.event_id}",
                    f"env:{settings.dd_env}",
                ],
            )
            api.create_event(body=body)
            logger.info(f"[Datadog] alert for {incident.event_id}")
    except Exception as exc:
        logger.error(f"[Datadog] trigger_alert failed: {exc}")


# ── configure (UC08) ───────────────────────────────────────────────────────────

async def configure(
    api_key: str,
    app_key: str = "",
    env: str = "development",
) -> bool:
    """Test connection + save config."""
    if not _DD_AVAILABLE:
        raise RuntimeError("datadog-api-client not installed")

    cfg = Configuration()
    cfg.api_key["apiKeyAuth"] = api_key
    cfg.server_variables["site"] = "datadoghq.com"

    try:
        await asyncio.to_thread(_test_connection_sync, cfg)
    except Exception as e:
        logger.error(f"[Datadog] Test failed: {e}")
        return False

    settings.dd_api_key = api_key
    settings.dd_env = env
    logger.info(f"[Datadog] Configured: env={env}")
    return True


def _test_connection_sync(cfg: Configuration) -> None:
    with ApiClient(cfg) as client:
        api = MetricsApi(client)
        api.submit_metrics(body=MetricPayload(series=[]))