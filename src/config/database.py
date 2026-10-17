from src.models.Settings import SystemSettings
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.config.settings import get_settings
from src.core.logger import get_logger

from src.models.User import User
from src.models.Turbine import Turbine
from src.models.Telemetry import Telemetry
from src.models.Prediction import Prediction
from src.models.Incident import Incident

logger = get_logger(__name__)
settings = get_settings()

_client: AsyncIOMotorClient | None = None


async def connect_to_mongo():
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)
    db = _client[settings.mongo_db_name]

    # Tạo timeseries collection thủ công
    collections = await db.list_collection_names()


    await init_beanie(
        database=db,
        document_models=[
            User, Turbine, Telemetry, Prediction, Incident, SystemSettings,
        ],
    )
    logger.info(f"Connected to MongoDB: {settings.mongo_db_name}")


async def close_mongo_connection():
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")


async def ping_mongo() -> bool:
    """Check MongoDB connection health."""
    if _client is None:
        return False
    try:
        await _client.admin.command("ping")
        return True
    except Exception as e:
        logger.error(f"MongoDB ping failed: {e}")
        return False