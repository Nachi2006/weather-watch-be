from sqlalchemy.orm import Session
from typing import Optional
from datetime import timezone
import uuid

from db.models import DisasterModel
from services.time_utils import format_time_ago, calculate_minutes_ago, parse_datetime_flexible

def format_disaster(record: DisasterModel) -> dict:
    minutes_ago = calculate_minutes_ago(record.timestamp) if record.timestamp else (record.reportedMinutesAgo or 0)
    time_ago = format_time_ago(record.timestamp) if record.timestamp else f"{minutes_ago} min ago"
    return {
        "id": record.id,
        "type": record.type,
        "location": record.location,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "severity": record.severity,
        "confidence": record.confidence,
        "affectedArea": record.affectedArea,
        "dryArea": record.dryArea,
        "populationAtRisk": record.populationAtRisk,
        "status": record.status,
        "timestamp": record.timestamp,
        "image": record.image,
        "reportedMinutesAgo": minutes_ago,
        "timeAgo": time_ago,
        "roadAccessibility": record.roadAccessibility,
        "rainfall": record.rainfall,
        "temperature": record.temperature,
        "humidity": record.humidity,
        "waterLevel": record.waterLevel,
        "originalImage": record.originalImage,
        "segmentationImage": record.segmentationImage,
        "overlayImage": record.overlayImage,
        "aiSummary": record.aiSummary,
    }

def get_all(db: Session, severity: Optional[str], type: Optional[str], status: Optional[str]):
    query = db.query(DisasterModel)
    if severity:
        query = query.filter(DisasterModel.severity == severity)
    if type:
        query = query.filter(DisasterModel.type == type)
    if status:
        query = query.filter(DisasterModel.status == status)
    return [format_disaster(r) for r in query.all()]

def get_by_id(db: Session, id: str):
    record = db.query(DisasterModel).filter(DisasterModel.id == id).first()
    return format_disaster(record) if record else None

def create(db: Session, data: dict):
    if not data.get("id"):
        data["id"] = f"DIS-{uuid.uuid4().hex[:8].upper()}"
    raw_time = data.pop("timestamp", None)
    dt = parse_datetime_flexible(raw_time)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    data["timestamp"] = dt
    data["reportedMinutesAgo"] = calculate_minutes_ago(dt)
    # strip fields not on the ORM model (e.g. recommendations list, timeAgo)
    data.pop("recommendations", None)
    data.pop("timeAgo", None)
    record = DisasterModel(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return format_disaster(record)

def update_status(db: Session, id: str, status: str):
    record = db.query(DisasterModel).filter(DisasterModel.id == id).first()
    if record:
        record.status = status
        db.commit()
        db.refresh(record)
        return format_disaster(record)
    return None

def delete(db: Session, id: str):
    record = db.query(DisasterModel).filter(DisasterModel.id == id).first()
    if record:
        db.delete(record)
        db.commit()
    return record
