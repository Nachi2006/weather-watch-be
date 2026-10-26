from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.db import get_db
from models import Analytics, DashboardSummary, TelemetryInsights
from services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("", response_model=Analytics)
def get_analytics(db: Session = Depends(get_db)):
    """Return aggregated database analytics across categories, severities, timelines, and regions."""
    return dashboard_service.get_analytics(db)

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Return real-time active incident counts and population at risk from the database."""
    return dashboard_service.get_summary(db)

@router.get("/telemetry", response_model=TelemetryInsights)
def get_telemetry_insights(db: Session = Depends(get_db)):
    """Return meteorological sensor telemetry and regional risk insights from the database."""
    return dashboard_service.get_telemetry_insights(db)
