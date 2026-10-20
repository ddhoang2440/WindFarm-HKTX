from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config.settings import settings
from models.telemetry import TelemetryRecord
from models.event import EventRecord

async def init_db():
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(
        database=client[settings.DATABASE_NAME],
        document_models=[TelemetryRecord, EventRecord]
    )