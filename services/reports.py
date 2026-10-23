from sqlalchemy.orm import Session
from datetime import timezone, datetime
import uuid

from db.models import ReportModel
from services.time_utils import format_time_ago, parse_datetime_flexible


def format_report(record: ReportModel) -> dict:
    return {
        "id": record.id,
        "disasterType": record.disasterType,
        "location": record.location,
        "submittedBy": record.submittedBy,
        "timeAgo": format_time_ago(record.timeAgo),
        "timestamp": record.timeAgo,
        "status": record.status,
        "severity": record.severity,
        "acknowledged": record.acknowledged,
        "acknowledgedBy": record.acknowledgedBy,
        "acknowledgedAt": record.acknowledgedAt,
    }


def get_all(db: Session):
    records = db.query(ReportModel).all()
    return [format_report(r) for r in records]

def create(db: Session, data: dict):
    if not data.get("id"):
        data["id"] = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    raw_time = data.pop("timeAgo", None)
    raw_timestamp = data.pop("timestamp", None)
    chosen_time = raw_time if raw_time is not None else raw_timestamp
    dt = parse_datetime_flexible(chosen_time)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    data["timeAgo"] = dt
    record = ReportModel(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return format_report(record)


def acknowledge_report(
    db: Session,
    report_id: str,
    username: str,
):
    record = (
        db.query(ReportModel)
        .filter(ReportModel.id == report_id)
        .first()
    )

    if record is None:
        return None

    if not record.acknowledged:
        record.acknowledged = True
        record.acknowledgedBy = username
        record.acknowledgedAt = datetime.utcnow()

        db.commit()
        db.refresh(record)

    return format_report(record)
