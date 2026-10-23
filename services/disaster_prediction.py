"""
Multi-disaster prediction service.

Orchestrates: fetch live weather → engineer features → run ML model
→ return structured prediction results.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import joblib
import pandas as pd
from pathlib import Path

from services.feature_engineering import engineer_features
from services.weather_client import fetch_weather

logger = logging.getLogger(__name__)

# ── model loading ────────────────────────────────────────────────────────────

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "disaster_model.joblib"

_model_artifact: dict | None = None


def _load_model() -> dict:
    global _model_artifact
    if _model_artifact is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Disaster model not found at {MODEL_PATH}. "
                "Run `python -m ml.train_disaster_model` first."
            )
        _model_artifact = joblib.load(MODEL_PATH)
        logger.info("Loaded disaster model v%s", _model_artifact.get("version"))
    return _model_artifact


# ── risk thresholds ──────────────────────────────────────────────────────────

# Probability above which a disaster type is flagged
RISK_THRESHOLD_HIGH = 0.60
RISK_THRESHOLD_MEDIUM = 0.35
RISK_THRESHOLD_LOW = 0.15


def _risk_level(probability: float) -> str:
    if probability >= RISK_THRESHOLD_HIGH:
        return "Critical"
    elif probability >= RISK_THRESHOLD_MEDIUM:
        return "High"
    elif probability >= RISK_THRESHOLD_LOW:
        return "Medium"
    return "Low"


# ── severity mapping (aligned with existing codebase values) ─────────────────

def _severity_from_risk(risk_level: str) -> str:
    """Map ML risk level to the severity labels used in DisasterModel."""
    return {
        "Critical": "Critical",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
    }.get(risk_level, "Low")


# ── public API ───────────────────────────────────────────────────────────────

def predict_disasters(
    latitude: float,
    longitude: float,
    location_name: str = "Unknown",
    weather_payload: Optional[dict] = None,
) -> dict:
    """Run the full prediction pipeline for a location.

    Parameters
    ----------
    latitude, longitude : float
        Coordinates to fetch weather for (used only when *weather_payload*
        is ``None``).
    location_name : str
        Human-readable location label.
    weather_payload : dict, optional
        Pre-fetched Open-Meteo response.  If ``None``, the function will
        call the weather API directly.

    Returns
    -------
    dict
        ``predicted_class``: top predicted disaster type (or "None")
        ``risk_level``: overall risk assessment
        ``severity``: severity label compatible with DisasterModel
        ``confidence``: probability of the top class (0-1)
        ``probabilities``: dict of each disaster type → probability
        ``features``: the engineered feature dict used for prediction
        ``location``: location metadata
        ``timestamp``: ISO prediction timestamp
    """
    artifact = _load_model()
    clf = artifact["classifier"]
    feature_cols = artifact["feature_columns"]
    disaster_types = artifact["disaster_types"]

    # 1. Fetch weather if not provided
    if weather_payload is None:
        logger.info("Fetching weather for (%.4f, %.4f) …", latitude, longitude)
        weather_payload = fetch_weather(latitude, longitude)

    # 2. Engineer features
    features = engineer_features(weather_payload)

    # 3. Predict
    df = pd.DataFrame([features])[feature_cols]
    probabilities_array = clf.predict_proba(df)[0]

    # Build class → probability map
    proba_map: dict[str, float] = {}
    for cls_label, prob in zip(clf.classes_, probabilities_array):
        proba_map[cls_label] = round(float(prob), 4)

    # Top prediction
    predicted_class = clf.classes_[probabilities_array.argmax()]
    top_prob = float(probabilities_array.max())

    # If top class is "None" → no disaster predicted
    if predicted_class == "None":
        overall_risk = "Low"
        severity = "Low"
    else:
        overall_risk = _risk_level(top_prob)
        severity = _severity_from_risk(overall_risk)

    # Gather all high-risk types (above threshold)
    flagged_disasters = [
        {
            "type": dtype,
            "probability": proba_map.get(dtype, 0.0),
            "risk_level": _risk_level(proba_map.get(dtype, 0.0)),
        }
        for dtype in disaster_types
        if dtype != "None" and proba_map.get(dtype, 0.0) >= RISK_THRESHOLD_LOW
    ]
    flagged_disasters.sort(key=lambda x: x["probability"], reverse=True)

    return {
        "predicted_class": predicted_class,
        "risk_level": overall_risk,
        "severity": severity,
        "confidence": round(top_prob, 4),
        "probabilities": proba_map,
        "flagged_disasters": flagged_disasters,
        "features": features,
        "location": {
            "name": location_name,
            "latitude": latitude,
            "longitude": longitude,
        },
        "model_version": artifact.get("version", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
