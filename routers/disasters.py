from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from db.db import get_db
from db.models import UserModel
from models import Disaster, DisasterCreate, DisasterStatusUpdate, Error
from services import disasters as disaster_service
from services.security import require_admin

router = APIRouter(prefix="/disasters", tags=["Disasters"])

@router.get("", response_model=List[Disaster])
def get_disasters(
    severity: Optional[str] = Query(None, enum=["Critical", "High", "Medium", "Low"]),
    type: Optional[str] = Query(None, enum=["Flood", "Fire", "Smoke", "Landslide", "Building Collapse", "Road Blockage"]),
    status: Optional[str] = Query(None, enum=["Active", "Monitoring", "Resolved"]),
    db: Session = Depends(get_db)
):
    return disaster_service.get_all(db, severity, type, status)

@router.post("", response_model=Disaster, status_code=201)
def create_disaster(
    body: DisasterCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin)
):
    return disaster_service.create(db, body.model_dump())

@router.get("/{id}", response_model=Disaster, responses={404: {"model": Error}})
def get_disaster(id: str, db: Session = Depends(get_db)):
    disaster = disaster_service.get_by_id(db, id)
    if not disaster:
        raise HTTPException(status_code=404, detail="Disaster not found")
    return disaster

@router.patch("/{id}/status", response_model=Disaster, responses={404: {"model": Error}})
def update_disaster_status(
    id: str,
    body: DisasterStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin)
):
    disaster = disaster_service.update_status(db, id, body.status)
    if not disaster:
        raise HTTPException(status_code=404, detail="Disaster not found")
    return disaster

@router.delete("/{id}", responses={404: {"model": Error}})
def delete_disaster(
    id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin)
):
    disaster = disaster_service.delete(db, id)
    if not disaster:
        raise HTTPException(status_code=404, detail="Disaster not found")
    return {"success": True, "id": id}
