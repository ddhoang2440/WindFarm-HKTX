# src/models/__init__.py
from .User import User, UserRole, UserStatus
from .Turbine import Turbine, TurbineStatus
from .Telemetry import Telemetry
from .Prediction import Prediction, PredictionClass
from .Incident import Incident, IncidentStatus, IncidentSeverity
from .Settings import SystemSettings   # ← Đổi về SystemSettings

__all__ = [
    "User", "UserRole", "UserStatus",
    "Turbine", "TurbineStatus",
    "Telemetry",
    "Prediction", "PredictionClass",
    "Incident", "IncidentStatus", "IncidentSeverity",
    "SystemSettings",   # ← Đổi
]