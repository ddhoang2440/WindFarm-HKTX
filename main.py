from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.database import init_db
from modules.telemetry.telemetry_router import router as telemetry_router
from modules.event.event_router import router as event_router
from modules.telemetry.stats_router import router as stats_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="WindFarm Backend (Hoàng)", lifespan=lifespan)

app.include_router(telemetry_router)
app.include_router(event_router)
app.include_router(stats_router)

@app.get("/")
def root():
    return {"message": "Backend is running"}