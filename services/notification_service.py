import os
import boto3


AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
SNS_TOPIC_ARN = os.getenv("SNS_DISASTER_TOPIC_ARN")

sns = boto3.client("sns", region_name=AWS_REGION)


def notify_rescue_team(report: dict) -> str:
    if not SNS_TOPIC_ARN:
        raise RuntimeError("SNS_DISASTER_TOPIC_ARN is not configured")

    report_id = report.get("id", "N/A")
    disaster_type = report.get("disasterType", "Unknown")
    location = report.get("location", "Unknown")
    severity = report.get("severity", "Unspecified")
    status = report.get("status", "Pending")
    submitted_by = report.get("submittedBy", "Unknown")

    subject = f"Weather Watch Alert: {disaster_type} - {severity}"

    message = f"""
WEATHER WATCH
NEW DISASTER REPORT
========================================

Report ID:       {report_id}
Disaster Type:   {disaster_type}
Location:        {location}
Severity:        {severity}
Current Status:  {status}
Reported By:     {submitted_by}

ACTION REQUIRED
Please review this report in the Weather Watch application
and acknowledge it if your team is responding.

========================================
This is an automatically generated notification.
Report ID: {report_id}
""".strip()

    response = sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject[:100],
        Message=message,
    )

    return response["MessageId"]
