from fastapi import APIRouter, File, UploadFile, Body, Depends
from typing import List
from pydantic import BaseModel, HttpUrl

from db.models import UserModel
from services.security import require_rescue_team_or_admin

router = APIRouter(tags=["AI Pipeline"])

class DetectRequest(BaseModel):
    imageUrl: str

class SegmentRequest(BaseModel):
    imageUrl: str

class PredictSeverityRequest(BaseModel):
    imageUrl: str
    affectedArea: float
    populationAtRisk: int
    rainfall: str = None
    humidity: int = None

class RecommendationsRequest(BaseModel):
    disasterType: str = None
    severity: str = None
    location: str = None
    populationAtRisk: int = None
    aiSummary: str = None

@router.post("/upload")
def upload_images(
    images: List[UploadFile] = File(...),
    current_user: UserModel = Depends(require_rescue_team_or_admin)
):
    # Mock implementation
    return {"urls": [f"http://mock-s3.com/{image.filename}" for image in images], "reportId": "RPT-MOCK"}

@router.post("/detect")
def detect_hazards(
    req: DetectRequest,
    current_user: UserModel = Depends(require_rescue_team_or_admin)
):
    return {"detections": []}

@router.post("/segment")
def segment_flood(
    req: SegmentRequest,
    current_user: UserModel = Depends(require_rescue_team_or_admin)
):
    return {"maskUrl": "http://mock.com/mask.png", "affectedArea": 50.0, "dryArea": 50.0}

@router.post("/predict-severity")
def predict_severity(
    req: PredictSeverityRequest,
    current_user: UserModel = Depends(require_rescue_team_or_admin)
):
    return {"severity": "High", "confidence": 95.0}

@router.post("/recommendations")
def generate_recommendations(
    req: RecommendationsRequest,
    current_user: UserModel = Depends(require_rescue_team_or_admin)
):
    return {"recommendations": ["Evacuate immediately", "Deploy rescue boats"]}
