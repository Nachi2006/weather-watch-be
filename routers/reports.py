from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from db.db import get_db
from db.models import UserModel
from models import Report, ReportCreate
from services import reports as report_service
from services.security import require_rescue_team_or_admin, require_authenticated_user

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("", response_model=List[Report])
def get_reports(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_rescue_team_or_admin)
):
    return report_service.get_all(db)

@router.post("", response_model=Report, status_code=201)
def create_report(
    body: ReportCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_authenticated_user)
):
    report_dict = body.model_dump()
    if not report_dict.get("submittedBy") or report_dict.get("submittedBy") == "Anonymous":
        report_dict["submittedBy"] = current_user.username
    return report_service.create(db, report_dict)
