from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from db.db import get_db
from db.models import UserModel
from models import Report, ReportCreate
from services import reports as report_service
from services.security import require_rescue_team_or_admin, require_authenticated_user
import logging
from services.notification_service import notify_rescue_team

logger = logging.getLogger(__name__)

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
    report_dict["submittedBy"] = current_user.username

    created_report = report_service.create(db, report_dict)

    try:
        message_id = notify_rescue_team(created_report)
        logger.info(
            "SNS notification published for report %s: %s",
            created_report["id"],
            message_id,
        )
    except Exception:
        logger.exception(
            "SNS notification failed for report %s",
            created_report["id"],
        )

    return created_report
