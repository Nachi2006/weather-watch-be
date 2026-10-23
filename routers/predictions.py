"""
API router for disaster predictions.

Endpoints:
    POST /predictions/run         — manual trigger for a specific location
    POST /predictions/run-default — manual trigger for the default location
    GET  /predictions/latest      — most recent prediction result (in-memory)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.db import get_db
from db.models import UserModel
from services.disaster_prediction import predict_disasters
from services.prediction_alert_pipeline import run_prediction_pipeline
from services.security import require_rescue_team_or_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])

# ── In-memory cache of the latest prediction ─────────────────────────────────

_latest_prediction: dict | None = None


# ── Request / Response schemas ───────────────────────────────────────────────

class PredictionRequest(BaseModel):
    latitude: float
    longitude: float
    location_name: str = "Custom Location"
    send_sns: bool = False  # opt-in for SNS during manual runs


class PredictionResponse(BaseModel):
    predicted_class: str
    risk_level: str
    severity: str
    confidence: float
    probabilities: dict
    flagged_disasters: list
    features: dict
    location: dict
    model_version: str
    timestamp: str
    alerts_created: list = []
    disasters_created: list = []


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/run", response_model=PredictionResponse)
def run_prediction(
    req: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_rescue_team_or_admin),
):
    """Run the disaster prediction pipeline for a custom location."""
    global _latest_prediction

    try:
        result = run_prediction_pipeline(
            db=db,
            latitude=req.latitude,
            longitude=req.longitude,
            location_name=req.location_name,
            send_sns=req.send_sns,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Prediction pipeline failed")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    prediction = result["prediction"]
    prediction["alerts_created"] = result.get("alerts_created", [])
    prediction["disasters_created"] = result.get("disasters_created", [])

    _latest_prediction = prediction
    return prediction


@router.post("/run-default", response_model=PredictionResponse)
def run_default_prediction(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_rescue_team_or_admin),
):
    """Run prediction for the default configured location (env vars)."""
    global _latest_prediction

    latitude = float(os.getenv("WEATHER_LATITUDE", "13.0827"))
    longitude = float(os.getenv("WEATHER_LONGITUDE", "80.2707"))
    location_name = os.getenv("WEATHER_LOCATION_ID", "Chennai, Tamil Nadu")

    try:
        result = run_prediction_pipeline(
            db=db,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            send_sns=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Prediction pipeline failed")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    prediction = result["prediction"]
    prediction["alerts_created"] = result.get("alerts_created", [])
    prediction["disasters_created"] = result.get("disasters_created", [])

    _latest_prediction = prediction
    return prediction


@router.get("/latest")
def get_latest_prediction(
    current_user: UserModel = Depends(require_rescue_team_or_admin),
):
    """Return the most recent prediction result (from in-memory cache)."""
    if _latest_prediction is None:
        raise HTTPException(
            status_code=404,
            detail="No prediction has been run yet. Call POST /predictions/run first.",
        )
    return _latest_prediction


@router.post("/predict-only")
def predict_only(
    req: PredictionRequest,
    current_user: UserModel = Depends(require_rescue_team_or_admin),
):
    """Run prediction WITHOUT creating alerts or DB records.

    Useful for testing / previewing what the model would predict.
    """
    try:
        prediction = predict_disasters(
            latitude=req.latitude,
            longitude=req.longitude,
            location_name=req.location_name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    return prediction
