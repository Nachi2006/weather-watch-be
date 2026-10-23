import joblib
import pandas as pd
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "flood_risk_model.joblib"

model = joblib.load(MODEL_PATH)


def predict_flood_risk(features: dict):
    data = pd.DataFrame([features])

    probability = model.predict_proba(data)[0][1]

    return {
        "flood_probability": round(float(probability), 4),
        "risk_level": (
            "High" if probability >= 0.7
            else "Medium" if probability >= 0.4
            else "Low"
        ),
        "model_version": "flood-v1"
    }