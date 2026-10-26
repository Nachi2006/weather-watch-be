
import json
import logging

from services.weather_ingestion import ingest_all_locations

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Starting multi-location weather ingestion")

    results = ingest_all_locations()

    logger.info(
        "Weather ingestion results: %s",
        json.dumps(results, default=str),
    )

    failed = sum(
        result["status"] == "failed"
        for result in results
    )

    return {
        "statusCode": 200 if failed == 0 else 207,
        "body": json.dumps(results, default=str),
    }
