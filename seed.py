import json
from datetime import datetime, date
from db.db import SessionLocal
from db.models import DisasterModel, AlertModel, ReportModel, HistoryEntryModel, FacilityModel
from services.auth import seed_default_users

disasters_data = [
  {
    "id": "DIS-001",
    "type": "Flood",
    "location": "Chennai, Tamil Nadu",
    "latitude": 13.0827,
    "longitude": 80.2707,
    "severity": "Critical",
    "confidence": 96,
    "affectedArea": 48,
    "dryArea": 52,
    "populationAtRisk": 20000,
    "status": "Active",
    "timestamp": "2026-09-05T08:52:00+05:30",
    "reportedMinutesAgo": 8,
    "roadAccessibility": "Limited",
    "rainfall": "High",
    "temperature": 29,
    "humidity": 84,
    "waterLevel": "Danger",
    "image": "https://picsum.photos/seed/chennai-flood-1/800/500",
    "originalImage": "https://picsum.photos/seed/chennai-flood-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/chennai-flood-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/chennai-flood-overlay/800/500",
    "aiSummary": "AI analysis indicates significant flooding across a densely populated area. Multiple roads appear inaccessible and immediate evacuation assessment is recommended."
  },
  {
    "id": "DIS-002",
    "type": "Fire",
    "location": "Coimbatore, Tamil Nadu",
    "latitude": 11.0168,
    "longitude": 76.9558,
    "severity": "High",
    "confidence": 91,
    "affectedArea": 22,
    "dryArea": 78,
    "populationAtRisk": 4200,
    "status": "Active",
    "timestamp": "2026-09-05T08:25:00+05:30",
    "reportedMinutesAgo": 35,
    "roadAccessibility": "Moderate",
    "rainfall": "Low",
    "temperature": 34,
    "humidity": 41,
    "waterLevel": "Normal",
    "image": "https://picsum.photos/seed/coimbatore-fire-1/800/500",
    "originalImage": "https://picsum.photos/seed/coimbatore-fire-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/coimbatore-fire-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/coimbatore-fire-overlay/800/500",
    "aiSummary": "Thermal signature and smoke plume analysis suggest an active wildfire spreading along dry vegetation near residential outskirts. Wind direction favors northeast expansion."
  },
  {
    "id": "DIS-003",
    "type": "Flood",
    "location": "Madurai, Tamil Nadu",
    "latitude": 9.9252,
    "longitude": 78.1198,
    "severity": "Medium",
    "confidence": 89,
    "affectedArea": 19,
    "dryArea": 81,
    "populationAtRisk": 3100,
    "status": "Monitoring",
    "timestamp": "2026-09-05T07:58:00+05:30",
    "reportedMinutesAgo": 62,
    "roadAccessibility": "Open",
    "rainfall": "Medium",
    "temperature": 30,
    "humidity": 76,
    "waterLevel": "Elevated",
    "image": "https://picsum.photos/seed/madurai-flood-1/800/500",
    "originalImage": "https://picsum.photos/seed/madurai-flood-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/madurai-flood-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/madurai-flood-overlay/800/500",
    "aiSummary": "Rising water levels detected near low-lying riverbank zones. Current trend suggests moderate risk with potential to escalate if rainfall continues overnight."
  },
  {
    "id": "DIS-004",
    "type": "Landslide",
    "location": "Nilgiris, Tamil Nadu",
    "latitude": 11.4064,
    "longitude": 76.6932,
    "severity": "High",
    "confidence": 87,
    "affectedArea": 12,
    "dryArea": 88,
    "populationAtRisk": 850,
    "status": "Active",
    "timestamp": "2026-09-05T06:40:00+05:30",
    "reportedMinutesAgo": 140,
    "roadAccessibility": "Blocked",
    "rainfall": "High",
    "temperature": 21,
    "humidity": 91,
    "waterLevel": "N/A",
    "image": "https://picsum.photos/seed/nilgiris-landslide-1/800/500",
    "originalImage": "https://picsum.photos/seed/nilgiris-landslide-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/nilgiris-landslide-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/nilgiris-landslide-overlay/800/500",
    "aiSummary": "Slope instability detected following sustained heavy rainfall. Satellite imagery shows soil displacement along the primary access road, cutting off two hillside villages."
  },
  {
    "id": "DIS-005",
    "type": "Building Collapse",
    "location": "Trichy, Tamil Nadu",
    "latitude": 10.7905,
    "longitude": 78.7047,
    "severity": "Critical",
    "confidence": 94,
    "affectedArea": 6,
    "dryArea": 94,
    "populationAtRisk": 180,
    "status": "Active",
    "timestamp": "2026-09-05T09:05:00+05:30",
    "reportedMinutesAgo": 3,
    "roadAccessibility": "Limited",
    "rainfall": "None",
    "temperature": 32,
    "humidity": 58,
    "waterLevel": "N/A",
    "image": "https://picsum.photos/seed/trichy-collapse-1/800/500",
    "originalImage": "https://picsum.photos/seed/trichy-collapse-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/trichy-collapse-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/trichy-collapse-overlay/800/500",
    "aiSummary": "A partial structural collapse has been detected in a mixed residential-commercial block. Debris pattern analysis suggests possible trapped occupants on the lower floors."
  },
  {
    "id": "DIS-006",
    "type": "Smoke",
    "location": "Salem, Tamil Nadu",
    "latitude": 11.6643,
    "longitude": 78.146,
    "severity": "Medium",
    "confidence": 82,
    "affectedArea": 15,
    "dryArea": 85,
    "populationAtRisk": 2200,
    "status": "Monitoring",
    "timestamp": "2026-09-05T07:10:00+05:30",
    "reportedMinutesAgo": 110,
    "roadAccessibility": "Open",
    "rainfall": "None",
    "temperature": 33,
    "humidity": 46,
    "waterLevel": "N/A",
    "image": "https://picsum.photos/seed/salem-smoke-1/800/500",
    "originalImage": "https://picsum.photos/seed/salem-smoke-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/salem-smoke-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/salem-smoke-overlay/800/500",
    "aiSummary": "Dense smoke plume detected near an industrial zone, likely originating from a warehouse fire. Air quality sensors nearby report elevated particulate levels."
  },
  {
    "id": "DIS-007",
    "type": "Road Blockage",
    "location": "Tirunelveli, Tamil Nadu",
    "latitude": 8.7139,
    "longitude": 77.7567,
    "severity": "Low",
    "confidence": 78,
    "affectedArea": 4,
    "dryArea": 96,
    "populationAtRisk": 600,
    "status": "Resolved",
    "timestamp": "2026-09-04T18:20:00+05:30",
    "reportedMinutesAgo": 900,
    "roadAccessibility": "Cleared",
    "rainfall": "Low",
    "temperature": 31,
    "humidity": 63,
    "waterLevel": "N/A",
    "image": "https://picsum.photos/seed/tirunelveli-road-1/800/500",
    "originalImage": "https://picsum.photos/seed/tirunelveli-road-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/tirunelveli-road-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/tirunelveli-road-overlay/800/500",
    "aiSummary": "Fallen debris from heavy winds blocked a secondary access road. Local crews cleared the obstruction; route is now fully operational."
  },
  {
    "id": "DIS-008",
    "type": "Flood",
    "location": "Thanjavur, Tamil Nadu",
    "latitude": 10.787,
    "longitude": 79.1378,
    "severity": "High",
    "confidence": 93,
    "affectedArea": 34,
    "dryArea": 66,
    "populationAtRisk": 9800,
    "status": "Active",
    "timestamp": "2026-09-05T08:00:00+05:30",
    "reportedMinutesAgo": 60,
    "roadAccessibility": "Limited",
    "rainfall": "High",
    "temperature": 28,
    "humidity": 88,
    "waterLevel": "Danger",
    "image": "https://picsum.photos/seed/thanjavur-flood-1/800/500",
    "originalImage": "https://picsum.photos/seed/thanjavur-flood-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/thanjavur-flood-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/thanjavur-flood-overlay/800/500",
    "aiSummary": "Cauvery delta river gauges show rapid water level rise. Agricultural land and low-lying residential clusters are at immediate risk of inundation."
  },
  {
    "id": "DIS-009",
    "type": "Fire",
    "location": "Vellore, Tamil Nadu",
    "latitude": 12.9165,
    "longitude": 79.1325,
    "severity": "Medium",
    "confidence": 85,
    "affectedArea": 9,
    "dryArea": 91,
    "populationAtRisk": 1200,
    "status": "Monitoring",
    "timestamp": "2026-09-05T05:45:00+05:30",
    "reportedMinutesAgo": 195,
    "roadAccessibility": "Open",
    "rainfall": "None",
    "temperature": 33,
    "humidity": 50,
    "waterLevel": "N/A",
    "image": "https://picsum.photos/seed/vellore-fire-1/800/500",
    "originalImage": "https://picsum.photos/seed/vellore-fire-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/vellore-fire-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/vellore-fire-overlay/800/500",
    "aiSummary": "Small-scale agricultural field fire detected. Currently contained but proximity to a residential boundary warrants continued monitoring."
  },
  {
    "id": "DIS-010",
    "type": "Landslide",
    "location": "Kanyakumari, Tamil Nadu",
    "latitude": 8.0883,
    "longitude": 77.5385,
    "severity": "Low",
    "confidence": 74,
    "affectedArea": 5,
    "dryArea": 95,
    "populationAtRisk": 300,
    "status": "Resolved",
    "timestamp": "2026-09-04T14:10:00+05:30",
    "reportedMinutesAgo": 1200,
    "roadAccessibility": "Open",
    "rainfall": "Low",
    "temperature": 27,
    "humidity": 80,
    "waterLevel": "N/A",
    "image": "https://picsum.photos/seed/kanyakumari-landslide-1/800/500",
    "originalImage": "https://picsum.photos/seed/kanyakumari-landslide-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/kanyakumari-landslide-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/kanyakumari-landslide-overlay/800/500",
    "aiSummary": "Minor soil slippage recorded along a hillside footpath after light rainfall. No structural or population impact identified."
  },
  {
    "id": "DIS-011",
    "type": "Building Collapse",
    "location": "Erode, Tamil Nadu",
    "latitude": 11.341,
    "longitude": 77.7172,
    "severity": "Medium",
    "confidence": 80,
    "affectedArea": 3,
    "dryArea": 97,
    "populationAtRisk": 90,
    "status": "Monitoring",
    "timestamp": "2026-09-05T04:30:00+05:30",
    "reportedMinutesAgo": 250,
    "roadAccessibility": "Open",
    "rainfall": "None",
    "temperature": 30,
    "humidity": 55,
    "waterLevel": "N/A",
    "image": "https://picsum.photos/seed/erode-collapse-1/800/500",
    "originalImage": "https://picsum.photos/seed/erode-collapse-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/erode-collapse-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/erode-collapse-overlay/800/500",
    "aiSummary": "Structural crack widening detected on an aging commercial building facade. Precautionary evacuation of upper floors recommended pending inspection."
  },
  {
    "id": "DIS-012",
    "type": "Road Blockage",
    "location": "Ooty, Tamil Nadu",
    "latitude": 11.4102,
    "longitude": 76.695,
    "severity": "Medium",
    "confidence": 83,
    "affectedArea": 7,
    "dryArea": 93,
    "populationAtRisk": 450,
    "status": "Active",
    "timestamp": "2026-09-05T07:35:00+05:30",
    "reportedMinutesAgo": 85,
    "roadAccessibility": "Blocked",
    "rainfall": "Medium",
    "temperature": 18,
    "humidity": 89,
    "waterLevel": "N/A",
    "image": "https://picsum.photos/seed/ooty-road-1/800/500",
    "originalImage": "https://picsum.photos/seed/ooty-road-original/800/500",
    "segmentationImage": "https://picsum.photos/seed/ooty-road-seg/800/500",
    "overlayImage": "https://picsum.photos/seed/ooty-road-overlay/800/500",
    "aiSummary": "Mudflow across the ghat road has blocked the primary route connecting hillside settlements. Alternate route capacity is limited for heavy vehicles."
  }
]

alerts_data = [
  {"id": "ALT-2026-0091", "title": "CRITICAL FLOOD DETECTED", "disasterId": "DIS-001", "type": "Flood", "severity": "Critical", "location": "Chennai, Tamil Nadu", "affectedArea": 48.0, "populationAtRisk": 20000, "reportedMinutesAgo": 8, "acknowledged": False},
  {"id": "ALT-2026-0090", "title": "ACTIVE WILDFIRE SPREADING", "disasterId": "DIS-002", "type": "Fire", "severity": "High", "location": "Coimbatore, Tamil Nadu", "affectedArea": 22.0, "populationAtRisk": 4200, "reportedMinutesAgo": 35, "acknowledged": False},
  {"id": "ALT-2026-0089", "title": "RISING FLOOD RISK", "disasterId": "DIS-003", "type": "Flood", "severity": "Medium", "location": "Madurai, Tamil Nadu", "affectedArea": 19.0, "populationAtRisk": 3100, "reportedMinutesAgo": 62, "acknowledged": True},
  {"id": "ALT-2026-0088", "title": "STRUCTURAL COLLAPSE REPORTED", "disasterId": "DIS-005", "type": "Building Collapse", "severity": "Critical", "location": "Trichy, Tamil Nadu", "affectedArea": 6.0, "populationAtRisk": 180, "reportedMinutesAgo": 3, "acknowledged": False},
  {"id": "ALT-2026-0087", "title": "LANDSLIDE BLOCKING ACCESS ROAD", "disasterId": "DIS-004", "type": "Landslide", "severity": "High", "location": "Nilgiris, Tamil Nadu", "affectedArea": 12.0, "populationAtRisk": 850, "reportedMinutesAgo": 140, "acknowledged": True},
  {"id": "ALT-2026-0086", "title": "INDUSTRIAL SMOKE PLUME DETECTED", "disasterId": "DIS-006", "type": "Smoke", "severity": "Medium", "location": "Salem, Tamil Nadu", "affectedArea": 15.0, "populationAtRisk": 2200, "reportedMinutesAgo": 110, "acknowledged": False}
]

facilities_data = [
  {"id": "FAC-01", "name": "Rajiv Gandhi Govt Hospital", "type": "Hospital", "latitude": 13.0836, "longitude": 80.2751},
  {"id": "FAC-02", "name": "Chennai Central Relief Shelter", "type": "Shelter", "latitude": 13.0827, "longitude": 80.2785},
  {"id": "FAC-03", "name": "Coimbatore Rescue Center", "type": "Rescue Center", "latitude": 11.0093, "longitude": 76.9612},
  {"id": "FAC-04", "name": "Madurai Government Hospital", "type": "Hospital", "latitude": 9.9195, "longitude": 78.1258},
  {"id": "FAC-05", "name": "Trichy District Rescue Unit", "type": "Rescue Center", "latitude": 10.7952, "longitude": 78.7089},
  {"id": "FAC-06", "name": "Thanjavur Community Shelter", "type": "Shelter", "latitude": 10.7825, "longitude": 79.1315}
]

reports_data = [
  {"id": "RPT-2026-00124", "disasterType": "Flood", "location": "Chennai, Tamil Nadu", "submittedBy": "Field Agent K. Ramesh", "timeAgo": "8 min ago", "status": "Analyzing", "severity": "Critical"},
  {"id": "RPT-2026-00123", "disasterType": "Fire", "location": "Coimbatore, Tamil Nadu", "submittedBy": "Citizen Report", "timeAgo": "35 min ago", "status": "Verified", "severity": "High"},
  {"id": "RPT-2026-00122", "disasterType": "Flood", "location": "Madurai, Tamil Nadu", "submittedBy": "Field Agent S. Priya", "timeAgo": "1 hr ago", "status": "Verified", "severity": "Medium"},
  {"id": "RPT-2026-00121", "disasterType": "Landslide", "location": "Nilgiris, Tamil Nadu", "submittedBy": "District Officer", "timeAgo": "2 hr ago", "status": "Resolved", "severity": "High"},
  {"id": "RPT-2026-00120", "disasterType": "Building Collapse", "location": "Trichy, Tamil Nadu", "submittedBy": "Citizen Report", "timeAgo": "3 min ago", "status": "Pending", "severity": "Critical"},
  {"id": "RPT-2026-00119", "disasterType": "Smoke", "location": "Salem, Tamil Nadu", "submittedBy": "Field Agent M. Kumar", "timeAgo": "1.8 hr ago", "status": "Analyzing", "severity": "Medium"},
  {"id": "RPT-2026-00118", "disasterType": "Road Blockage", "location": "Tirunelveli, Tamil Nadu", "submittedBy": "Citizen Report", "timeAgo": "15 hr ago", "status": "Resolved", "severity": "Low"},
  {"id": "RPT-2026-00117", "disasterType": "Flood", "location": "Thanjavur, Tamil Nadu", "submittedBy": "Field Agent K. Ramesh", "timeAgo": "1 hr ago", "status": "Verified", "severity": "High"},
  {"id": "RPT-2026-00116", "disasterType": "Fire", "location": "Vellore, Tamil Nadu", "submittedBy": "Citizen Report", "timeAgo": "3.2 hr ago", "status": "Pending", "severity": "Medium"},
  {"id": "RPT-2026-00115", "disasterType": "Road Blockage", "location": "Ooty, Tamil Nadu", "submittedBy": "District Officer", "timeAgo": "1.4 hr ago", "status": "Analyzing", "severity": "Medium"}
]

history_data = [
  {"date": "2026-09-04", "disaster": "Road Blockage", "location": "Tirunelveli, Tamil Nadu", "severity": "Low", "affectedArea": 4.0, "status": "Resolved"},
  {"date": "2026-09-04", "disaster": "Landslide", "location": "Kanyakumari, Tamil Nadu", "severity": "Low", "affectedArea": 5.0, "status": "Resolved"},
  {"date": "2026-08-29", "disaster": "Flood", "location": "Nagapattinam, Tamil Nadu", "severity": "High", "affectedArea": 41.0, "status": "Resolved"},
  {"date": "2026-08-22", "disaster": "Fire", "location": "Dindigul, Tamil Nadu", "severity": "Medium", "affectedArea": 14.0, "status": "Resolved"},
  {"date": "2026-08-15", "disaster": "Building Collapse", "location": "Chennai, Tamil Nadu", "severity": "Critical", "affectedArea": 2.0, "status": "Resolved"},
  {"date": "2026-08-09", "disaster": "Flood", "location": "Cuddalore, Tamil Nadu", "severity": "Critical", "affectedArea": 55.0, "status": "Resolved"},
  {"date": "2026-08-02", "disaster": "Landslide", "location": "Nilgiris, Tamil Nadu", "severity": "High", "affectedArea": 9.0, "status": "Resolved"},
  {"date": "2026-07-27", "disaster": "Smoke", "location": "Salem, Tamil Nadu", "severity": "Medium", "affectedArea": 11.0, "status": "Resolved"},
  {"date": "2026-07-19", "disaster": "Road Blockage", "location": "Ooty, Tamil Nadu", "severity": "Medium", "affectedArea": 6.0, "status": "Resolved"},
  {"date": "2026-07-11", "disaster": "Flood", "location": "Thanjavur, Tamil Nadu", "severity": "High", "affectedArea": 37.0, "status": "Resolved"}
]

def seed_db():
    db = SessionLocal()
    try:
        for d in disasters_data:
            dt = datetime.fromisoformat(d["timestamp"])
            db_obj = DisasterModel(**d)
            db_obj.timestamp = dt
            if not db.query(DisasterModel).filter_by(id=d['id']).first():
                db.add(db_obj)
        
        for a in alerts_data:
            if not db.query(AlertModel).filter_by(id=a['id']).first():
                db.add(AlertModel(**a))

        for f in facilities_data:
            if not db.query(FacilityModel).filter_by(id=f['id']).first():
                db.add(FacilityModel(**f))

        for r in reports_data:
            if not db.query(ReportModel).filter_by(id=r['id']).first():
                db.add(ReportModel(**r))

        for h in history_data:
            db_h = HistoryEntryModel(**h)
            db_h.date = date.fromisoformat(h['date'])
            # Since history does not have a natural ID in the mock, we just add it
            db.add(db_h)

        seed_default_users(db)

        db.commit()
        print("Database successfully seeded with mock data.")
    except Exception as e:
        db.rollback()
        print("Failed to seed database:", e)
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
