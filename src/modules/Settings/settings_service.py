"""
System Settings service (UC08, UC09).
"""
from datetime import datetime
from typing import Any, Dict, Optional

from src.models.Settings import SystemSettings
from src.core.logger import get_logger

logger = get_logger(__name__)


def _mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 4)


async def _get_or_create_settings() -> SystemSettings:
    """Singleton: 1 document duy nhất trong collection."""
    settings = await SystemSettings.find_one()
    if not settings:
        settings = SystemSettings()
        await settings.insert()
        logger.info("Created default SystemSettings document")
    return settings


async def get_settings_data() -> Dict[str, Any]:
    """Trả về settings đã mask secret."""
    settings = await _get_or_create_settings()

    stream = settings.stream or {}
    ai = settings.ai or {}
    dd = settings.datadog or {}

    return {
        "stream": {
            "interval_ms": stream.get("interval_ms", 1000),
            "enabled": stream.get("enabled", True),
            "dataset_path": stream.get("dataset_path"),
        },
        "ai": {
            "model_path": ai.get("model_path"),
            "threshold": ai.get("threshold", 0.5),
            "enabled": ai.get("enabled", True),
        },
        "datadog": {
            "enabled": dd.get("enabled", True),
            "api_key_masked": _mask_secret(dd.get("api_key", "")),
            "app_key_masked": _mask_secret(dd.get("app_key", "")),
            "env": dd.get("env", "development"),
            "alert_recipients": dd.get("alert_recipients", []),
        },
        "updated_at": settings.updated_at.isoformat(),
        "updated_by": settings.updated_by,
    }


async def update_settings_data(updates, admin_id: str) -> Dict[str, Any]:
    """
    Cập nhật settings. Gán lại dict để Beanie track thay đổi
    (không dùng .update() vì Beanie không detect nested mutation).
    """
    settings = await _get_or_create_settings()
    changed = False

    # --- Stream ---
    if updates.stream:
        patch = updates.stream.model_dump(exclude_unset=True)
        settings.stream = {**(settings.stream or {}), **patch}
        changed = True
        logger.info(f"Stream settings updated by {admin_id}: {patch}")

    # --- AI ---
    if updates.ai:
        patch = updates.ai.model_dump(exclude_unset=True)
        settings.ai = {**(settings.ai or {}), **patch}
        changed = True
        logger.info(f"AI settings updated by {admin_id}: {patch}")

        # Sync threshold sang AI service (best-effort)
        if updates.ai.threshold is not None:
            try:
                from src.modules.AI_Agent import ai_service
                await ai_service.update_threshold(updates.ai.threshold)
            except Exception as e:
                logger.error(f"Failed to sync AI threshold: {e}")

    # --- Datadog ---
    if updates.datadog:
        patch = updates.datadog.model_dump(exclude_unset=True)
        settings.datadog = {**(settings.datadog or {}), **patch}
        changed = True
        logger.info(f"Datadog settings updated by {admin_id}")

        # Sync sang Datadog client nếu có api_key mới
        if updates.datadog.api_key:
            try:
                from src.config import datadog as dd
                await dd.configure(
                    api_key=updates.datadog.api_key,
                    app_key=updates.datadog.app_key or "",
                    env=updates.datadog.env or "development",
                )
            except Exception as e:
                logger.error(f"Failed to sync Datadog: {e}")

    if changed:
        settings.updated_at = datetime.utcnow()
        settings.updated_by = admin_id
        await settings.save()

    return await get_settings_data()