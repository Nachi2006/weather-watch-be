"""
Flood prediction wrapper.

Provides backward compatibility with the original flood-only prediction
by wrapping the new multi-disaster prediction service.
"""

from __future__ import annotations

from services.disaster_prediction import predict_disasters


def predict_flood_risk(
    latitude: float = 13.0827,
    longitude: float = 80.2707,
    location_name: str = "Chennai, Tamil Nadu",
) -> dict:
    """Return flood-specific risk from the multi-disaster model."""
    result = predict_disasters(latitude, longitude, location_name)
    flood_prob = result["probabilities"].get("Flood", 0.0)

    risk_level = (
        "High" if flood_prob >= 0.7
        else "Medium" if flood_prob >= 0.4
        else "Low"
    )

    return {
        "flood_probability": round(flood_prob, 4),
        "risk_level": risk_level,
        "model_version": result.get("model_version", "unknown"),
        "all_predictions": result,
    }
