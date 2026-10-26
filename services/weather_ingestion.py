
import hashlib
import json
import logging
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from db.db import SessionLocal
from db.models import WeatherObservation
from services.weather_client import fetch_weather

logger = logging.getLogger(__name__)

LOCATIONS = [
    {
        "id": "chennai",
        "latitude": 13.0827,
        "longitude": 80.2707,
    },
    {
        "id": "vellore",
        "latitude": 12.9165,
        "longitude": 79.1325,
    },
    {
        "id": "coimbatore",
        "latitude": 11.0168,
        "longitude": 76.9558,
    },
    {
        "id": "bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
    },
    {
        "id": "hyderabad",
        "latitude": 17.3850,
        "longitude": 78.4867,
    },
    {
        "id": "mumbai",
        "latitude": 19.0760,
        "longitude": 72.8777,
    },
    {
        "id": "delhi",
        "latitude": 28.6139,
        "longitude": 77.2090,
    },
    {
        "id": "kolkata",
        "latitude": 22.5726,
        "longitude": 88.3639,
    },
]


def ingest_weather(location: dict) -> dict:
    location_id = location["id"]

    payload = fetch_weather(
        location["latitude"],
        location["longitude"],
    )

    current = payload["current"]
    observed_at = datetime.fromisoformat(current["time"])

    stable_data = json.dumps(
        {
            "location": location_id,
            "time": current["time"],
            "data": current,
        },
        sort_keys=True,
    )

    record_hash = hashlib.sha256(
        stable_data.encode("utf-8")
    ).hexdigest()

    with SessionLocal() as session:
        try:
            existing = (
                session.query(WeatherObservation)
                .filter_by(record_hash=record_hash)
                .first()
            )

            if existing:
                logger.info(
                    "Duplicate observation: %s at %s",
                    location_id,
                    current["time"],
                )
                return {
                    "location": location_id,
                    "status": "duplicate",
                    "observed_at": current["time"],
                }

            observation = WeatherObservation(
                source="Open-Meteo",
                station_id=location_id,
                station_name=location_id,
                observed_at=observed_at,
                temperature_c=current.get("temperature_2m"),
                rainfall_mm=current.get("precipitation"),
                humidity_pct=current.get("relative_humidity_2m"),
                wind_speed_kmph=current.get("wind_speed_10m"),
                pressure_hpa=current.get("surface_pressure"),
                raw_data=payload,
                record_hash=record_hash,
            )

            session.add(observation)
            session.commit()

            logger.info("Inserted weather for %s", location_id)

            return {
                "location": location_id,
                "status": "inserted",
                "observed_at": current["time"],
            }

        except SQLAlchemyError:
            session.rollback()
            logger.exception(
                "Database error for location %s",
                location_id,
            )
            raise


def ingest_all_locations() -> list:
    results = []

    for location in LOCATIONS:
        try:
            result = ingest_weather(location)
            results.append(result)

        except Exception:
            logger.exception(
                "Weather ingestion failed for %s",
                location["id"],
            )
            results.append({
                "location": location["id"],
                "status": "failed",
            })

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(ingest_all_locations(), indent=2))
