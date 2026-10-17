from datetime import datetime
from typing import List, Optional

from src.models.Turbine import Turbine, TurbineStatus
from src.core.exceptions import NotFoundException
from src.core.logger import get_logger

logger = get_logger(__name__)


async def get_all_turbines() -> List[Turbine]:
    """Return all turbines sorted by asset_id."""
    return await Turbine.find_all().sort(Turbine.asset_id).to_list()


async def get_turbine_by_asset_id(asset_id: int) -> Turbine:
    """Find turbine by asset_id (CSV filename key)."""
    turbine = await Turbine.find_one(Turbine.asset_id == asset_id)
    if not turbine:
        raise NotFoundException(f"Turbine asset_id={asset_id} not found")
    return turbine


async def update_turbine_status(
    asset_id: int,
    status: TurbineStatus,
    updated_by: Optional[str] = None,
) -> Turbine:
    """Update turbine status and updated_at."""
    turbine = await get_turbine_by_asset_id(asset_id)
    turbine.status = status
    turbine.updated_at = datetime.utcnow()
    await turbine.save()
    logger.info(
        f"Turbine {asset_id} status → {status.value} "
        f"by user {updated_by or 'unknown'}"
    )
    return turbine