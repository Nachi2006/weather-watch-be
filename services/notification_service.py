import json
import os

import boto3


AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
SNS_TOPIC_ARN = os.getenv("SNS_DISASTER_TOPIC_ARN")

sns = boto3.client("sns", region_name=AWS_REGION)


def notify_rescue_team(report: dict) -> str:
    if not SNS_TOPIC_ARN:
        raise RuntimeError(
            "SNS_DISASTER_TOPIC_ARN is not configured"
        )

    message = {
        "event": "NEW_DISASTER_REPORT",
        "report_id": report["id"],
        "disaster_type": report.get("disasterType"),
        "location": report.get("location"),
        "severity": report.get("severity"),
        "status": report.get("status"),
        "submitted_by": report.get("submittedBy"),
        "message": (
            "A new disaster report has been submitted. "
            "Please review it in the Weather Watch application."
        ),
    }

    response = sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Weather Watch: New Disaster Report",
        Message=json.dumps(message, indent=2),
    )

    return response["MessageId"]
