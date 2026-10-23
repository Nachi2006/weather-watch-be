
import hashlib
import json
import logging
import os
from datetime import datetime

import boto3
from sqlalchemy.exc import SQLAlchemyError

from db.db import SessionLocal
from db.models import WeatherObservation
from services.weather_client import fetch_weather

logger = logging.getLogger(__name__)

REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET = os.getenv("WEATHER_S3_BUCKET")

LATITUDE = float(os.getenv("WEATHER_LATITUDE", "13.0827"))
LONGITUDE = float(os.getenv("WEATHER_LONGITUDE", "80.2707"))
LOCATION_ID = os.getenv("WEATHER_LOCATION_ID", "chennai")

s3 = boto3.client("s3", region_name=REGION)


def ingest_weather():
    payload = fetch_weather(LATITUDE, LONGITUDE)
    current = payload["current"]

    observed_at = datetime.fromisoformat(current["time"])

    stable_data = json.dumps(
        {
            "location": LOCATION_ID,
            "time": current["time"],
            "data": current,
        },
        sort_keys=True,
    )
    record_hash = hashlib.sha256(
        stable_data.encode("utf-8")
    ).hexdigest()

    s3_key = None

    if S3_BUCKET:
        fetched_at = datetime.now().astimezone()
        s3_key = (
            f"weather/raw/{LOCATION_ID}/"
            f"{fetched_at:%Y/%m/%d}/"
            f"{fetched_at:%Y%m%dT%H%M%S%z}.json"
        )

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )

    with SessionLocal() as session:
        try:
            existing = (
                session.query(WeatherObservation)
                .filter_by(record_hash=record_hash)
                .first()
            )

            if existing:
                return {
                    "status": "duplicate",
                    "location": LOCATION_ID,
                    "observed_at": current["time"],
                }

            observation = WeatherObservation(
                source="Open-Meteo",
                station_id=LOCATION_ID,
                station_name=LOCATION_ID,
                observed_at=observed_at,
                temperature_c=current.get("temperature_2m"),
                rainfall_mm=current.get("precipitation"),
                humidity_pct=current.get("relative_humidity_2m"),
                wind_speed_kmph=current.get("wind_speed_10m"),
                pressure_hpa=current.get("surface_pressure"),
                raw_data=current,
                record_hash=record_hash,
            )

            session.add(observation)
            session.commit()

            return {
                "status": "inserted",
                "location": LOCATION_ID,
                "observed_at": current["time"],
                "s3_key": s3_key,
            }

        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to store weather observation")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(ingest_weather())
