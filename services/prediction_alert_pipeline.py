from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import DisasterModel, AlertModel
from services.disaster_prediction import (
    predict_disasters,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MEDIUM,
    RISK_THRESHOLD_LOW,
)

logger = logging.getLogger(__name__)

# Keep existing threshold configuration.
ALERT_THRESHOLD = RISK_THRESHOLD_HIGH  # 0.60


def _generate_id(prefix: str) -> str:
    """Generate a unique identifier for a disaster, alert, or SNS message."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _severity_to_population_estimate(severity: str) -> int:
    """Return a rough population estimate based on severity."""
    estimates = {
        "Low": 200,
        "Medium": 1500,
        "High": 5000,
        "Critical": 15000,
    }
    return estimates.get(severity, 500)


def _rainfall_label(rain_24h_mm: float) -> str:
    """Convert rainfall in mm to a readable label."""
    if rain_24h_mm >= 100:
        return "Extreme"
    elif rain_24h_mm >= 50:
        return "High"
    elif rain_24h_mm >= 15:
        return "Medium"
    elif rain_24h_mm >= 2:
        return "Low"
    return "None"


def _water_level_label(soil_saturation: float) -> str:
    """Approximate a water-risk label from soil saturation."""
    if soil_saturation >= 80:
        return "Danger"
    elif soil_saturation >= 55:
        return "Elevated"
    elif soil_saturation >= 30:
        return "Normal"
    return "Low"


def _send_prediction_sns(
    prediction: dict,
    location_name: str,
    disaster_id: str | None = None,
) -> list[str]:
    """
    Send one SNS notification for the final predicted class.

    Demo predictions are allowed. A prediction whose final class is
    missing or 'None' must never send an SNS notification.
    """
    predicted_class = prediction.get("predicted_class")

    if not predicted_class or predicted_class == "None":
        logger.info(
            "SNS skipped for %s: final predicted class is None",
            location_name,
        )
        return []

    try:
        from services.notification_service import notify_rescue_team

        payload = {
            "id": disaster_id or _generate_id("SNS"),
            "disasterType": predicted_class,
            "location": location_name,
            "severity": prediction.get("severity", "High"),
            "status": "Predicted",
            "submittedBy": (
                "ML Demo Prediction"
                if prediction.get("is_demo", False)
                else "ML Prediction Pipeline"
            ),
        }

        message_id = notify_rescue_team(payload)

        logger.info(
            "SNS notification sent: class=%s location=%s demo=%s message_id=%s",
            predicted_class,
            location_name,
            prediction.get("is_demo", False),
            message_id,
        )

        return [message_id] if message_id else []

    except Exception as exc:
        logger.warning(
            "SNS notification failed (non-fatal) for location=%s class=%s: %s",
            location_name,
            predicted_class,
            exc,
        )
        return []


def run_prediction_pipeline(
    db: Session,
    latitude: float,
    longitude: float,
    location_name: str = "Unknown",
    weather_payload: dict | None = None,
    send_sns: bool = True,
    demo_disaster: str | None = None,
) -> dict:
    """
    Run disaster prediction, persist results, and optionally send SNS.

    SNS behavior:
      - Send once for the final predicted class.
      - Send for demo classes as well.
      - Never send when the final predicted class is 'None'.

    Database alerts continue to be created according to ALERT_THRESHOLD.
    """
    prediction = predict_disasters(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        weather_payload=weather_payload,
        demo_disaster=demo_disaster,
    )

    predicted_class = prediction.get("predicted_class", "None")
    is_demo = prediction.get("is_demo", False)
    features = prediction.get("features", {})
    now = datetime.now(timezone.utc)

    alerts_created: list[dict] = []
    disasters_created: list[dict] = []
    sns_results: list[str] = []

    try:
        # ---------------------------------------------------------
        # DEMO PATH
        # ---------------------------------------------------------
        if is_demo:
            severity = prediction.get("severity", "High")
            demo_title = f"⚠ [DEMO] {predicted_class.upper()} SCENARIO"
            disaster_id = _generate_id("DIS")
            alert_id = _generate_id("ALT")
            pop_at_risk = _severity_to_population_estimate(severity)
            conf = round(prediction.get("confidence", 0.0) * 100, 1)

            disaster = DisasterModel(
                id=disaster_id,
                type=predicted_class,
                location=location_name,
                latitude=latitude,
                longitude=longitude,
                severity=severity,
                confidence=conf,
                affectedArea=0.0,
                dryArea=100.0,
                populationAtRisk=pop_at_risk,
                status="Predicted",
                timestamp=now.replace(tzinfo=None),
                image="",
                reportedMinutesAgo=0,
                roadAccessibility="Unknown",
                rainfall=_rainfall_label(features.get("rain_24h_mm", 0)),
                temperature=features.get("temperature_c"),
                humidity=features.get("humidity_pct"),
                waterLevel=_water_level_label(features.get("soil_saturation_index", 0)),
                aiSummary=(
                    f"SIMULATED DEMO SCENARIO: {predicted_class} at {location_name}. "
                    f"This is a demonstration scenario, not a confirmed real-world disaster."
                ),
            )
            db.add(disaster)
            disasters_created.append({
                "id": disaster_id,
                "type": predicted_class,
                "severity": severity,
                "confidence": conf,
                "location": location_name,
            })

            alert = AlertModel(
                id=alert_id,
                title=demo_title,
                disasterId=disaster_id,
                type=predicted_class,
                severity=severity,
                location=location_name,
                affectedArea=0.0,
                populationAtRisk=pop_at_risk,
                timestamp=now.replace(tzinfo=None),
                reportedMinutesAgo=0,
                acknowledged=False,
            )
            db.add(alert)
            alerts_created.append({
                "id": alert_id,
                "title": alert.title,
                "disasterId": disaster_id,
                "type": predicted_class,
                "severity": severity,
                "location": location_name,
            })

        # ---------------------------------------------------------
        # NORMAL ML PREDICTION PATH
        # ---------------------------------------------------------
        else:
            flagged = prediction.get("flagged_disasters", [])

            for disaster_info in flagged:
                if isinstance(disaster_info, dict):
                    prob = disaster_info.get("probability", 0.0)
                    disaster_type = disaster_info.get("type") or disaster_info.get("disaster")
                    risk_level = disaster_info.get("risk_level", "Medium")
                else:
                    disaster_type = str(disaster_info)
                    prob = prediction.get("probabilities", {}).get(disaster_type, 0.0)
                    risk_level = "Medium"

                if not disaster_type or prob < ALERT_THRESHOLD:
                    continue

                severity = risk_level
                disaster_id = _generate_id("DIS")
                alert_id = _generate_id("ALT")
                pop_at_risk = _severity_to_population_estimate(severity)
                conf = round(prob * 100, 1)

                disaster = DisasterModel(
                    id=disaster_id,
                    type=disaster_type,
                    location=location_name,
                    latitude=latitude,
                    longitude=longitude,
                    severity=severity,
                    confidence=conf,
                    affectedArea=0.0,
                    dryArea=100.0,
                    populationAtRisk=pop_at_risk,
                    status="Predicted",
                    timestamp=now.replace(tzinfo=None),
                    image="",
                    reportedMinutesAgo=0,
                    roadAccessibility="Unknown",
                    rainfall=_rainfall_label(features.get("rain_24h_mm", 0)),
                    temperature=features.get("temperature_c"),
                    humidity=features.get("humidity_pct"),
                    waterLevel=_water_level_label(features.get("soil_saturation_index", 0)),
                    aiSummary=(
                        f"ML model predicts {disaster_type} risk ({risk_level}) with "
                        f"{prob:.0%} confidence based on current weather conditions. "
                        f"Key indicators: rainfall {features.get('rain_24h_mm', 0):.1f}mm/24h, "
                        f"temperature {features.get('temperature_c', 0):.1f}°C, "
                        f"humidity {features.get('humidity_pct', 0):.1f}%, "
                        f"wind {features.get('wind_speed_kmph', 0):.1f}km/h."
                    ),
                )
                db.add(disaster)
                disasters_created.append({
                    "id": disaster_id,
                    "type": disaster_type,
                    "severity": severity,
                    "confidence": conf,
                    "location": location_name,
                })

                alert = AlertModel(
                    id=alert_id,
                    title=f"⚠ PREDICTED: {disaster_type.upper()} RISK — {risk_level.upper()}",
                    disasterId=disaster_id,
                    type=disaster_type,
                    severity=severity,
                    location=location_name,
                    affectedArea=0.0,
                    populationAtRisk=pop_at_risk,
                    timestamp=now.replace(tzinfo=None),
                    reportedMinutesAgo=0,
                    acknowledged=False,
                )
                db.add(alert)
                alerts_created.append({
                    "id": alert_id,
                    "title": alert.title,
                    "disasterId": disaster_id,
                    "type": disaster_type,
                    "severity": severity,
                    "location": location_name,
                })

                logger.warning(
                    "ALERT: %s risk (%s) at %s — prob=%.2f — disaster=%s alert=%s",
                    disaster_type, risk_level, location_name, prob, disaster_id, alert_id,
                )

        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "Prediction pipeline database operation failed for %s",
            location_name,
        )
        raise

    # -------------------------------------------------------------
    # SNS: send ONCE for the final predicted class, not once per alert.
    # This is independent of the database ALERT_THRESHOLD.
    # -------------------------------------------------------------
    if send_sns:
        first_disaster_id = (
            disasters_created[0]["id"] if disasters_created else None
        )
        sns_results = _send_prediction_sns(
            prediction=prediction,
            location_name=location_name,
            disaster_id=first_disaster_id,
        )

    return {
        "prediction": prediction,
        "alerts_created": alerts_created,
        "disasters_created": disasters_created,
        "created_alerts": alerts_created,
        "created_disasters": disasters_created,
        "sns_results": sns_results,
        "location": location_name,
        "predicted_class": predicted_class,
        "model_predicted_class": prediction.get("model_predicted_class"),
        "risk_level": prediction.get("risk_level"),
        "severity": prediction.get("severity"),
        "confidence": prediction.get("confidence"),
        "probabilities": prediction.get("probabilities", {}),
        "flagged_disasters": prediction.get("flagged_disasters", []),
        "is_demo": is_demo,
    }