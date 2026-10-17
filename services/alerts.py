from sqlalchemy.orm import Session
from datetime import timezone
import uuid

from db.models import AlertModel
from services.time_utils import format_time_ago, calculate_minutes_ago, parse_datetime_flexible

def format_alert(record: AlertModel) -> dict:
    minutes_ago = calculate_minutes_ago(record.timestamp) if record.timestamp else (record.reportedMinutesAgo or 0)
    time_ago = format_time_ago(record.timestamp) if record.timestamp else f"{minutes_ago} min ago"
    return {
        "id": record.id,
        "title": record.title,
        "disasterId": record.disasterId,
        "type": record.type,
        "severity": record.severity,
        "location": record.location,
        "affectedArea": record.affectedArea,
        "populationAtRisk": record.populationAtRisk,
        "reportedMinutesAgo": minutes_ago,
        "timestamp": record.timestamp,
        "timeAgo": time_ago,
        "acknowledged": record.acknowledged,
    }

def get_all(db: Session):
    records = db.query(AlertModel).all()
    return [format_alert(r) for r in records]

def acknowledge(db: Session, id: str):
    alert = db.query(AlertModel).filter(AlertModel.id == id).first()
    if alert:
        alert.acknowledged = True
        db.commit()
        db.refresh(alert)
        return format_alert(alert)
    return None

def create(db: Session, data: dict):
    if not data.get("id"):
        data["id"] = f"ALT-{uuid.uuid4().hex[:8].upper()}"
    raw_time = data.pop("timestamp", None)
    data.pop("timeAgo", None)
    if raw_time is None and data.get("reportedMinutesAgo") is not None:
        dt = parse_datetime_flexible(data["reportedMinutesAgo"])
    else:
        dt = parse_datetime_flexible(raw_time)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    data["timestamp"] = dt
    data["reportedMinutesAgo"] = calculate_minutes_ago(dt)
    record = AlertModel(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return format_alert(record)
