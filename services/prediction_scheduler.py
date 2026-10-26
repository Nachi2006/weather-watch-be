
"""
Background scheduler for periodic multi-location disaster predictions.

Reads the latest stored weather observations from Aurora PostgreSQL.
Does not fetch weather directly from Open-Meteo.

When DEMO_MODE is enabled, some locations receive randomly selected
demo scenarios. These are stored separately from normal ML detections.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random

from datetime import datetime, timezone

from services.disaster_prediction import DEMO_DISASTER_TYPES

logger = logging.getLogger(__name__)

# Scheduler configuration.
PREDICTION_INTERVAL_SECONDS = int(
    os.getenv("PREDICTION_INTERVAL_SECONDS", "7200")
)

# Demo mode is enabled by default for this prototype.
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {
    "true",
    "1",
    "yes",
}

# Probability that a location receives a demo override on each run.
DEMO_OVERRIDE_PROBABILITY = float(
    os.getenv("DEMO_OVERRIDE_PROBABILITY", "0.60")
)

if not 0.0 <= DEMO_OVERRIDE_PROBABILITY <= 1.0:
    raise ValueError(
        "DEMO_OVERRIDE_PROBABILITY must be between 0.0 and 1.0"
    )

LOCATIONS = [
    {"id": "chennai", "latitude": 13.0827, "longitude": 80.2707},
    {"id": "vellore", "latitude": 12.9165, "longitude": 79.1325},
    {"id": "coimbatore", "latitude": 11.0168, "longitude": 76.9558},
    {"id": "bengaluru", "latitude": 12.9716, "longitude": 77.5946},
    {"id": "hyderabad", "latitude": 17.3850, "longitude": 78.4867},
    {"id": "mumbai", "latitude": 19.0760, "longitude": 72.8777},
    {"id": "delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"id": "kolkata", "latitude": 22.5726, "longitude": 88.3639},
]


def _run_location_prediction(location: dict) -> dict:
    """Predict using the latest weather observation stored in Aurora."""

    from db.db import SessionLocal
    from db.models import WeatherObservation
    from services.prediction_alert_pipeline import (
        run_prediction_pipeline,
    )

    location_id = location["id"]

    try:
        with SessionLocal() as db:
            observation = (
                db.query(WeatherObservation)
                .filter(
                    WeatherObservation.station_id == location_id
                )
                .order_by(WeatherObservation.fetched_at.desc())
                .first()
            )

            if observation is None:
                logger.warning(
                    "No stored weather observation for %s; skipping",
                    location_id,
                )
                return {
                    "location": location_id,
                    "status": "no_observation",
                }

            weather_payload = observation.raw_data

            # Support older rows containing only the current weather object.
            if "current" not in weather_payload:
                weather_payload = {"current": weather_payload}

            logger.info(
                "Using stored observation: location=%s observed_at=%s "
                "fetched_at=%s",
                location_id,
                observation.observed_at,
                observation.fetched_at,
            )

            # Randomly decide whether this location gets a demo scenario.
            demo_disaster = None

            if (
                DEMO_MODE
                and random.random() < DEMO_OVERRIDE_PROBABILITY
            ):
                demo_disaster = random.choice(DEMO_DISASTER_TYPES)

                logger.info(
                    "Random demo scenario selected: location=%s class=%s",
                    location_id,
                    demo_disaster,
                )

            result = run_prediction_pipeline(
                db=db,
                latitude=location["latitude"],
                longitude=location["longitude"],
                location_name=location_id,
                weather_payload=weather_payload,
                # Send SNS messages for predictions.
                send_sns=True,
                demo_disaster=demo_disaster,
            )

            prediction = result.get("prediction", {})
            alerts = result.get("alerts_created", [])
            disasters = result.get("disasters_created", [])

            logger.info(
                "Prediction completed: location=%s class=%s "
                "model_class=%s risk=%s confidence=%s "
                "demo=%s alerts=%d disasters=%d",
                location_id,
                prediction.get("predicted_class", "?"),
                prediction.get("model_predicted_class", "?"),
                prediction.get("risk_level", "?"),
                prediction.get("confidence", 0),
                prediction.get("is_demo", False),
                len(alerts),
                len(disasters),
            )

            return {
                "location": location_id,
                "status": "success",
                "observation_id": observation.id,
                "observed_at": str(observation.observed_at),
                "predicted_class": prediction.get("predicted_class"),
                "model_predicted_class": prediction.get(
                    "model_predicted_class"
                ),
                "risk_level": prediction.get("risk_level"),
                "confidence": prediction.get("confidence"),
                "is_demo": prediction.get("is_demo", False),
                "alerts_created": len(alerts),
                "disasters_created": len(disasters),
            }

    except Exception:
        logger.exception(
            "Prediction failed for location %s",
            location_id,
        )
        return {
            "location": location_id,
            "status": "failed",
        }


async def _run_prediction_cycle() -> None:
    """Process all configured locations sequentially."""

    logger.info(
        "Starting prediction cycle for %d locations using Aurora data",
        len(LOCATIONS),
    )

    logger.info(
        "Prediction mode: %s; demo override probability: %.0f%%",
        "DEMO" if DEMO_MODE else "NORMAL ML",
        DEMO_OVERRIDE_PROBABILITY * 100,
    )

    loop = asyncio.get_running_loop()

    for location in LOCATIONS:
        result = await loop.run_in_executor(
            None,
            _run_location_prediction,
            location,
        )
        logger.info("Location result: %s", result)


async def prediction_scheduler() -> None:
    """Run predictions periodically while FastAPI is running."""

    logger.info(
        "Prediction scheduler started; interval=%d seconds",
        PREDICTION_INTERVAL_SECONDS,
    )

    await asyncio.sleep(10)

    while True:
        logger.info(
            "Running prediction cycle at %s",
            datetime.now(timezone.utc).isoformat(),
        )

        try:
            await _run_prediction_cycle()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Prediction cycle failed")

        await asyncio.sleep(PREDICTION_INTERVAL_SECONDS)


_scheduler_task: asyncio.Task | None = None


def start_scheduler() -> None:
    """Start the background scheduler during FastAPI startup."""

    global _scheduler_task

    if _scheduler_task is not None and not _scheduler_task.done():
        logger.warning("Prediction scheduler is already running")
        return

    _scheduler_task = asyncio.create_task(prediction_scheduler())
    logger.info("Background prediction scheduler task created")


def stop_scheduler() -> None:
    """Stop the background scheduler during FastAPI shutdown."""

    global _scheduler_task

    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("Background prediction scheduler stopped")


# Compatibility with existing imports, if your application uses these names.
start_schedule = start_scheduler
stop_schedule = stop_scheduler
