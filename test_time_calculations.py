from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app import app
from services.time_utils import format_time_ago, calculate_minutes_ago, parse_datetime_flexible

client = TestClient(app)

def test_time_calculations():
    print("=== Testing Date & Time Columns and Dynamic Elapsed Time Calculation ===")

    # 1. Login as Rescue Team and Admin
    r_rescue = client.post("/auth/login", json={"username": "rescueteam", "password": "RescuePassword123!"})
    assert r_rescue.status_code == 200
    rescue_auth = {"Authorization": f"Bearer {r_rescue.json()['access_token']}"}

    r_admin = client.post("/auth/login", json={"username": "admin", "password": "AdminPassword123!"})
    assert r_admin.status_code == 200
    admin_auth = {"Authorization": f"Bearer {r_admin.json()['access_token']}"}

    # 2. Test Report Creation with Date and Time
    now = datetime.now(timezone.utc)
    ten_mins_ago = now - timedelta(minutes=10)

    print("\n--- 1. Testing Report creation with specific DateTime ---")
    payload = {
        "disasterType": "Flood",
        "location": "Guindy, Chennai",
        "severity": "High",
        "timeAgo": ten_mins_ago.isoformat()
    }
    r = client.post("/reports", json=payload, headers=rescue_auth)
    assert r.status_code == 201, f"Failed: {r.text}"
    report_data = r.json()
    print("Created report response:", report_data)
    assert "timeAgo" in report_data
    assert "timestamp" in report_data
    assert "min ago" in report_data["timeAgo"], f"Expected 'X min ago', got {report_data['timeAgo']}"
    print(f"[PASS] Report created. Calculated timeAgo: '{report_data['timeAgo']}', timestamp: '{report_data['timestamp']}'")

    # Test Report creation defaulting to now
    r_now = client.post("/reports", json={"disasterType": "Fire", "location": "Anna Nagar", "severity": "Medium"}, headers=rescue_auth)
    assert r_now.status_code == 201
    now_report = r_now.json()
    assert now_report["timeAgo"] == "just now"
    print(f"[PASS] Recent report dynamically calculated as '{now_report['timeAgo']}'")

    # 3. Test GET /reports calculates time elapsed for all reports
    print("\n--- 2. Testing GET /reports dynamic calculations ---")
    r_reports = client.get("/reports", headers=rescue_auth)
    assert r_reports.status_code == 200
    reports = r_reports.json()
    assert len(reports) > 0
    for rep in reports[:5]:
        print(f"  Report {rep['id']}: timeAgo='{rep['timeAgo']}', timestamp='{rep.get('timestamp')}'")
        assert isinstance(rep['timeAgo'], str)
        assert any(unit in rep['timeAgo'] for unit in ["min ago", "hr ago", "day", "just now", "month"])
    print("[PASS] All reports dynamically compute time elapsed!")

    # 4. Test Alert dynamic time calculations
    print("\n--- 3. Testing Alert dynamic time calculations ---")
    alert_payload = {
        "title": "URGENT FLOOD ALERT",
        "disasterId": "DIS-001",
        "type": "Flood",
        "severity": "Critical",
        "location": "Marina Beach, Chennai",
        "affectedArea": 5.0,
        "populationAtRisk": 300,
        "timestamp": (now - timedelta(minutes=25)).isoformat()
    }
    r_alert = client.post("/alerts", json=alert_payload, headers=admin_auth)
    assert r_alert.status_code == 201
    alert_data = r_alert.json()
    print("Created alert response:", alert_data)
    assert alert_data["reportedMinutesAgo"] >= 24 and alert_data["reportedMinutesAgo"] <= 26
    assert alert_data["timeAgo"] is not None
    assert "min ago" in alert_data["timeAgo"]
    print(f"[PASS] Alert dynamically calculated minutes: {alert_data['reportedMinutesAgo']} min, timeAgo: '{alert_data['timeAgo']}'")

    # 5. Test Disaster dynamic time calculations
    print("\n--- 4. Testing Disaster dynamic time calculations ---")
    disaster_payload = {
        "type": "Flood",
        "location": "Mylapore, Chennai",
        "latitude": 13.0368,
        "longitude": 80.2676,
        "severity": "High",
        "timestamp": (now - timedelta(hours=2)).isoformat()
    }
    r_disaster = client.post("/disasters", json=disaster_payload, headers=admin_auth)
    assert r_disaster.status_code == 201
    disaster_data = r_disaster.json()
    print("Created disaster response:", disaster_data)
    assert disaster_data["reportedMinutesAgo"] >= 118 and disaster_data["reportedMinutesAgo"] <= 122
    assert "hr ago" in disaster_data["timeAgo"]
    print(f"[PASS] Disaster dynamically calculated minutes: {disaster_data['reportedMinutesAgo']} min, timeAgo: '{disaster_data['timeAgo']}'")

    print("\nALL TIME CALCULATION TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_time_calculations()
