from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from src.config.database import connect_to_mongo, close_mongo_connection
from src.config.settings import get_settings
from src.core.logger import get_logger

# ── Routers ────────────────────────────────────────────────────────────────────
from src.modules.Auth.auth_controller import router as auth_router
from src.modules.Turbine.turbine_controller import router as turbine_router
from src.modules.Telemetry.telemetry_ingest_controller import router as telemetry_router
from src.modules.Telemetry.telemetry_controller import router as dashboard_router
from src.modules.AI_Agent.ai_controller import router as admin_router
from src.modules.Incident.incident_controller import router as incident_router
from src.modules.Settings.settings_controller import router as settings_router

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    await connect_to_mongo()
    logger.info("Application started")
    yield
    logger.info("Shutting down...")
    await close_mongo_connection()
    logger.info("Application stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "WindFarm Real-time Monitoring API\n\n"
        "**Controllers (class diagram)**\n"
        "- `AuthController` → `/api/auth`\n"
        "- `DashboardController` → `/api/dashboard`\n"
        "- `AdminController` → `/api/admin`\n"
        "- `IncidentService` REST → `/api/incidents`\n"
        "- `TelemetryService` REST + WS → `/api/telemetry`\n"
        "- `Settings` → `/api/settings`\n"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # false khi dùng ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers ──────────────────────────────────────────────────────────────
app.include_router(auth_router,      prefix="/api/auth",       tags=["AuthController"])
app.include_router(turbine_router,   prefix="/api/turbines",   tags=["Turbine"])
app.include_router(telemetry_router, prefix="/api/telemetry",  tags=["TelemetryService"])
app.include_router(dashboard_router, prefix="/api/dashboard",  tags=["DashboardController"])
app.include_router(admin_router,     prefix="/api/admin",      tags=["AdminController"])
app.include_router(incident_router,  prefix="/api/incidents",  tags=["IncidentService"])
app.include_router(settings_router,  prefix="/api/settings",   tags=["Settings"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.app_version}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled error at {request.method} {request.url}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )