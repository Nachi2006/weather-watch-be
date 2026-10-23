"""
Background scheduler for periodic disaster predictions.

Uses ``asyncio`` tasks that run alongside the FastAPI event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Default interval: every 30 minutes
PREDICTION_INTERVAL_SECONDS = int(os.getenv("PREDICTION_INTERVAL_SECONDS", "1800"))


async def _run_prediction_cycle() -> None:
    """Execute one prediction cycle (runs in a thread to avoid blocking)."""
    from db.db import SessionLocal
    from services.prediction_alert_pipeline import run_prediction_pipeline

    latitude = float(os.getenv("WEATHER_LATITUDE", "13.0827"))
    longitude = float(os.getenv("WEATHER_LONGITUDE", "80.2707"))
    location_name = os.getenv("WEATHER_LOCATION_ID", "Chennai, Tamil Nadu")

    loop = asyncio.get_event_loop()

    def _sync_run():
        with SessionLocal() as db:
            try:
                result = run_prediction_pipeline(
                    db=db,
                    latitude=latitude,
                    longitude=longitude,
                    location_name=location_name,
                    send_sns=True,
                )
                n_alerts = len(result.get("alerts_created", []))
                pred = result.get("prediction", {})
                logger.info(
                    "Scheduled prediction complete: class=%s risk=%s confidence=%.2f alerts=%d",
                    pred.get("predicted_class", "?"),
                    pred.get("risk_level", "?"),
                    pred.get("confidence", 0),
                    n_alerts,
                )
                return result
            except Exception:
                logger.exception("Scheduled prediction cycle failed")
                return None

    return await loop.run_in_executor(None, _sync_run)


async def prediction_scheduler() -> None:
    """Long-running async task that periodically invokes the prediction pipeline."""
    logger.info(
        "Prediction scheduler started — interval=%ds",
        PREDICTION_INTERVAL_SECONDS,
    )

    # Wait a short time after startup to let the app fully initialise
    await asyncio.sleep(10)

    while True:
        ts = datetime.now(timezone.utc).isoformat()
        logger.info("Running scheduled prediction cycle at %s", ts)

        try:
            await _run_prediction_cycle()
        except Exception:
            logger.exception("Unhandled error in prediction scheduler")

        await asyncio.sleep(PREDICTION_INTERVAL_SECONDS)


# ── lifecycle helpers for FastAPI ────────────────────────────────────────────

_scheduler_task: asyncio.Task | None = None


def start_scheduler() -> None:
    """Start the background prediction scheduler (call during app startup)."""
    global _scheduler_task
    if _scheduler_task is not None:
        logger.warning("Scheduler already running")
        return

    _scheduler_task = asyncio.create_task(prediction_scheduler())
    logger.info("Background prediction scheduler task created")


def stop_scheduler() -> None:
    """Cancel the background scheduler (call during app shutdown)."""
    global _scheduler_task
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("Background prediction scheduler stopped")
