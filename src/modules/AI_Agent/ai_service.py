"""
AIService – class diagram:
    - threshold: Float
    + predict(data: Dict) -> (PredictionClass, Float)
    + update_threshold(t: Float)
    + get_threshold() -> Float

Lazy-loads a scikit-learn Pipeline from disk.
"""
import asyncio
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple

from src.config.settings import get_settings
from src.core.logger import get_logger
from src.config import datadog as dd
from src.models.Prediction import PredictionClass

settings = get_settings()
logger = get_logger(__name__)

# ── Singleton state ────────────────────────────────────────────────────────────
_model = None
_threshold: float = 0.5
_uncertain_band: float = 0.1   # ±10% around threshold

FEATURE_COLUMNS = [
    "wind_speed",
    "power",
    "rotor_speed",
    "generator_speed",
    "blade_pitch_angle",
    "nacelle_temperature",
    "gearbox_temperature",
    "ambient_temperature",
]

MODEL_VERSION = "v1.0"


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def _extract_features(data: Dict[str, Any]) -> np.ndarray:
    """Extract features in correct order, with normalization."""
    normalized = {_normalize_key(k): v for k, v in data.items()}
    features = []
    for col in FEATURE_COLUMNS:
        val = normalized.get(col)
        if val is None or val == "":
            features.append(0.0)
        else:
            try:
                features.append(float(val))
            except (ValueError, TypeError):
                features.append(0.0)
    return np.array([features])


def load_model() -> None:
    """Load model from disk (sync). Call via asyncio.to_thread if needed."""
    global _model
    path = Path(settings.model_path)
    if not path.exists():
        logger.warning(f"[AIService] Model not found at {path} – dummy mode.")
        _model = None
        return
    with open(path, "rb") as f:
        _model = pickle.load(f)
    logger.info(f"[AIService] Model loaded from {path}")


async def predict(data: Dict[str, Any]) -> Tuple[PredictionClass, float]:
    """
    predict(data) -> (PredictionClass, confidence)

    Returns:
        - FAULT if P(fault) >= threshold + band
        - NORMAL if P(fault) <= threshold - band
        - UNCERTAIN otherwise
    """
    global _model
    if _model is None:
        # Load model in thread pool to avoid blocking event loop
        await asyncio.to_thread(load_model)

    if _model is None:
        # Dummy fallback: always normal, zero confidence
        return PredictionClass.NORMAL, 0.0

    features = _extract_features(data)

    try:
        if hasattr(_model, "predict_proba"):
            proba = float(_model.predict_proba(features)[0][1])
        else:
            proba = float(_model.predict(features)[0])

        # Classify với uncertain band
        if proba >= _threshold + _uncertain_band:
            prediction_class = PredictionClass.FAULT
            confidence = proba
        elif proba <= _threshold - _uncertain_band:
            prediction_class = PredictionClass.NORMAL
            confidence = 1.0 - proba
        else:
            prediction_class = PredictionClass.UNCERTAIN
            confidence = proba

        # Push metric (non-blocking)
        asset_id = data.get("asset_id", -1)
        try:
            await dd.push_metric(
                "ai.confidence",
                proba,
                tags=[f"asset_id:{asset_id}"],
            )
        except Exception as e:
            logger.error(f"[AIService] Datadog push failed: {e}")

    except Exception as exc:
        logger.error(f"[AIService] Prediction error: {exc}", exc_info=True)
        prediction_class, confidence = PredictionClass.NORMAL, 0.0

    return prediction_class, confidence


async def update_threshold(t: float) -> None:
    """
    update_threshold(t) – persist to Settings + update runtime.
    """
    global _threshold
    if not 0.0 <= t <= 1.0:
        raise ValueError(f"Threshold must be in [0, 1], got {t}")

    _threshold = t
    logger.info(f"[AIService] Threshold updated to {t}")

    # Persist to Settings
    try:
        from src.models.Settings import SystemSettings
        from datetime import datetime
        s = await SystemSettings.find_one()
        if not s:
            s = SystemSettings()
            await s.insert()
        s.ai["threshold"] = t
        s.updated_at = datetime.utcnow()
        await s.save()
    except Exception as e:
        logger.error(f"[AIService] Failed to persist threshold: {e}")

    # Push metric
    try:
        await dd.push_metric("ai.threshold", t)
    except Exception as e:
        logger.error(f"[AIService] Datadog push failed: {e}")


async def get_threshold() -> float:
    """Get threshold from Settings, fallback to runtime value."""
    try:
        from src.models.Settings import SystemSettings
        s = await SystemSettings.find_one()
        if s:
            return s.ai.get("threshold", _threshold)
    except Exception as e:
        logger.error(f"[AIService] Failed to read threshold: {e}")
    return _threshold


def get_model_version() -> str:
    return MODEL_VERSION