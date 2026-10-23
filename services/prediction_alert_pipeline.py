"""
Prediction → Alert pipeline.

When the ML model flags a disaster risk above threshold, this module:
1. Creates a Disaster record in the DB
2. Creates a matching Alert record in the DB
3. Sends an SNS notification via the existing notification_service
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import DisasterModel, AlertModel
from services.disaster_prediction import predict_disasters, RISK_THRESHOLD_MEDIUM

logger = logging.getLogger(__name__)

# Minimum probability to trigger an alert
ALERT_THRESHOLD = RISK_THRESHOLD_MEDIUM  # 0.35


def _generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _severity_to_population_estimate(severity: str) -> int:
    """Rough population-at-risk estimate based on severity for seed values."""
    return {
        "Critical": 15000,
        "High": 5000,
        "Medium": 1500,
        "Low": 200,
    }.get(severity, 500)


def run_prediction_pipeline(
    db: Session,
    latitude: float,
    longitude: float,
    location_name: str = "Unknown",
    weather_payload: dict | None = None,
    send_sns: bool = True,
) -> dict:
    """Run prediction and create alerts for flagged disasters.

    Returns
    -------
    dict
        ``prediction``: full prediction result
        ``alerts_created``: list of alert dicts that were persisted
        ``disasters_created``: list of disaster dicts that were persisted
        ``sns_results``: list of SNS message IDs (empty if SNS disabled)
    """
    # 1. Run prediction
    prediction = predict_disasters(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        weather_payload=weather_payload,
    )

    alerts_created: list[dict] = []
    disasters_created: list[dict] = []
    sns_results: list[str] = []

    flagged = prediction.get("flagged_disasters", [])

    if not flagged:
        logger.info("No disaster risks above threshold for %s", location_name)
        return {
            "prediction": prediction,
            "alerts_created": alerts_created,
            "disasters_created": disasters_created,
            "sns_results": sns_results,
        }

    now = datetime.now(timezone.utc)

    for disaster_info in flagged:
        prob = disaster_info["probability"]
        if prob < ALERT_THRESHOLD:
            continue

        disaster_type = disaster_info["type"]
        risk_level = disaster_info["risk_level"]
        severity = risk_level  # Already aligned with DB labels

        disaster_id = _generate_id("DIS")
        alert_id = _generate_id("ALT")
        pop_at_risk = _severity_to_population_estimate(severity)

        # 2a. Create Disaster record
        features = prediction.get("features", {})
        disaster_record = DisasterModel(
            id=disaster_id,
            type=disaster_type,
            location=location_name,
            latitude=latitude,
            longitude=longitude,
            severity=severity,
            confidence=round(prob * 100, 1),
            affectedArea=0.0,  # unknown until satellite analysis
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

        db.add(disaster_record)

        disaster_dict = {
            "id": disaster_id,
            "type": disaster_type,
            "severity": severity,
            "confidence": round(prob * 100, 1),
            "location": location_name,
        }
        disasters_created.append(disaster_dict)

        # 2b. Create Alert record
        alert_record = AlertModel(
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

        db.add(alert_record)

        alert_dict = {
            "id": alert_id,
            "title": alert_record.title,
            "disasterId": disaster_id,
            "type": disaster_type,
            "severity": severity,
            "location": location_name,
        }
        alerts_created.append(alert_dict)

        logger.warning(
            "ALERT: %s risk (%s) at %s — prob=%.2f — disaster=%s alert=%s",
            disaster_type, risk_level, location_name, prob, disaster_id, alert_id,
        )

        # 2c. SNS notification
        if send_sns:
            try:
                from services.notification_service import notify_rescue_team

                report_payload = {
                    "id": disaster_id,
                    "disasterType": disaster_type,
                    "location": location_name,
                    "severity": severity,
                    "status": "Predicted",
                    "submittedBy": "ML Prediction Pipeline",
                }
                msg_id = notify_rescue_team(report_payload)
                sns_results.append(msg_id)
                logger.info("SNS notification sent: %s", msg_id)
            except Exception as exc:
                logger.warning("SNS notification failed (non-fatal): %s", exc)

    # Commit all records
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to commit prediction records")
        raise

    return {
        "prediction": prediction,
        "alerts_created": alerts_created,
        "disasters_created": disasters_created,
        "sns_results": sns_results,
    }


# ── label helpers ────────────────────────────────────────────────────────────

def _rainfall_label(rain_24h_mm: float) -> str:
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
    if soil_saturation >= 80:
        return "Danger"
    elif soil_saturation >= 55:
        return "Elevated"
    elif soil_saturation >= 30:
        return "Normal"
    return "Low"
