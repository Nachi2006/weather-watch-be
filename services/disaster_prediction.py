
"""
Multi-disaster prediction service.

Orchestrates:
fetch weather -> engineer features -> run ML model -> return prediction.

Supports an optional randomized-demo override without retraining.
The model's actual probabilities are preserved in demo mode.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd

from services.feature_engineering import engineer_features
from services.weather_client import fetch_weather

logger = logging.getLogger(__name__)

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "ml"
    / "disaster_model.joblib"
)

_model_artifact: dict | None = None

# Demo classes supported by the existing trained model.
DEMO_DISASTER_TYPES = [
    "Flood",
    "Landslide",
    "Fire",
    "Smoke",
    "Building Collapse",
    "Road Blockage",
]


def _load_model() -> dict:
    global _model_artifact

    if _model_artifact is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Disaster model not found at {MODEL_PATH}. "
                "Run `python -m ml.train_disaster_model` first."
            )

        _model_artifact = joblib.load(MODEL_PATH)
        logger.info(
            "Loaded disaster model v%s",
            _model_artifact.get("version", "unknown"),
        )

    return _model_artifact


# Risk thresholds for actual model probabilities.
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


def _severity_from_risk(risk_level: str) -> str:
    return {
        "Critical": "Critical",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
    }.get(risk_level, "Low")


def predict_disasters(
    latitude: float,
    longitude: float,
    location_name: str = "Unknown",
    weather_payload: Optional[dict] = None,
    demo_disaster: Optional[str] = None,
) -> dict:
    """
    Predict disaster risks for a location.

    demo_disaster:
        Optional demo-only override. When supplied, the displayed class
        is overridden, but the actual model probabilities and confidence
        remain unchanged. The result is marked with is_demo=True.
    """
    artifact = _load_model()

    clf = artifact["classifier"]
    feature_cols = artifact["feature_columns"]
    disaster_types = list(artifact["disaster_types"])

    if demo_disaster is not None:
        if demo_disaster not in DEMO_DISASTER_TYPES:
            raise ValueError(
                f"Unsupported demo disaster: {demo_disaster!r}. "
                f"Supported demo classes: {DEMO_DISASTER_TYPES}"
            )

        if demo_disaster not in disaster_types:
            raise ValueError(
                f"Demo class {demo_disaster!r} is not supported "
                "by the loaded model."
            )

    # 1. Fetch weather only if no stored payload was provided.
    if weather_payload is None:
        logger.info(
            "Fetching weather for (%.4f, %.4f)",
            latitude,
            longitude,
        )
        weather_payload = fetch_weather(latitude, longitude)

    # 2. Engineer features.
    features = engineer_features(weather_payload)

    # 3. Run the original trained classifier.
    df = pd.DataFrame([features])[feature_cols]
    probabilities_array = clf.predict_proba(df)[0]

    # Preserve actual model probabilities.
    proba_map: dict[str, float] = {
        str(class_label): round(float(probability), 4)
        for class_label, probability in zip(
            clf.classes_,
            probabilities_array,
        )
    }

    logger.info(
        "Class probabilities for %s: %s",
        location_name,
        sorted(
            proba_map.items(),
            key=lambda item: item[1],
            reverse=True,
        ),
    )

    model_predicted_class = str(
        clf.classes_[probabilities_array.argmax()]
    )
    top_probability = float(probabilities_array.max())

    # 4. Choose the displayed class.
    is_demo = demo_disaster is not None

    if is_demo:
        predicted_class = demo_disaster

        # This is a demo display label, not a model risk assessment.
        overall_risk = "High"
        severity = "High"

        logger.warning(
            "DEMO OVERRIDE: location=%s, model_class=%s, "
            "display_class=%s. Not a real disaster prediction.",
            location_name,
            model_predicted_class,
            predicted_class,
        )
    else:
        predicted_class = model_predicted_class

        if predicted_class == "None":
            overall_risk = "Low"
            severity = "Low"
        else:
            overall_risk = _risk_level(top_probability)
            severity = _severity_from_risk(overall_risk)

    # 5. Keep flagged disasters based on genuine model probabilities.
    flagged_disasters = [
        {
            "type": disaster_type,
            "probability": proba_map.get(disaster_type, 0.0),
            "risk_level": _risk_level(
                proba_map.get(disaster_type, 0.0)
            ),
        }
        for disaster_type in disaster_types
        if (
            disaster_type != "None"
            and proba_map.get(disaster_type, 0.0)
            >= RISK_THRESHOLD_LOW
        )
    ]

    flagged_disasters.sort(
        key=lambda item: item["probability"],
        reverse=True,
    )

    return {
        "predicted_class": predicted_class,
        "model_predicted_class": model_predicted_class,
        "risk_level": overall_risk,
        "severity": severity,
        # Genuine confidence of the model's top class.
        "confidence": round(top_probability, 4),
        "probabilities": proba_map,
        "flagged_disasters": flagged_disasters,
        "features": features,
        "is_demo": is_demo,
        "demo_disaster": demo_disaster if is_demo else None,
        "notification_allowed": not is_demo,
        "location": {
            "name": location_name,
            "latitude": latitude,
            "longitude": longitude,
        },
        "model_version": artifact.get("version", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
