from collections import Counter, defaultdict
from datetime import datetime
from sqlalchemy.orm import Session
from models import Analytics, DashboardSummary, LabelData, TelemetryInsights, WeatherReading
from db.models import DisasterModel, AlertModel, HistoryEntryModel

def get_summary(db: Session) -> DashboardSummary:
    disasters = db.query(DisasterModel).all()
    active = [d for d in disasters if d.status != "Resolved"]

    return DashboardSummary(
        activeDisasters=len(active),
        critical=sum(1 for d in active if d.severity == "Critical"),
        high=sum(1 for d in active if d.severity == "High"),
        medium=sum(1 for d in active if d.severity == "Medium"),
        populationAtRisk=sum(int(d.populationAtRisk or 0) for d in active),
    )

def get_analytics(db: Session) -> Analytics:
    disasters = db.query(DisasterModel).all()
    history = db.query(HistoryEntryModel).all()

    # 1. Disasters by Category
    type_counter = Counter(d.type for d in disasters if d.type)
    default_order = ["Flood", "Fire", "Smoke", "Landslide", "Building Collapse", "Road Blockage"]
    all_types = sorted(type_counter.keys(), key=lambda t: default_order.index(t) if t in default_order else 99)
    type_labels = all_types if all_types else ["None"]
    type_data = [float(type_counter[t]) for t in type_labels]

    # 2. Severity Distribution
    severity_order = ["Critical", "High", "Medium", "Low"]
    severity_counter = Counter(d.severity for d in disasters if d.severity)
    sev_labels = severity_order
    sev_data = [float(severity_counter.get(s, 0)) for s in sev_labels]

    # 3. Incidents Timeline
    monthly_counts = defaultdict(int)
    for h in history:
        if h.date:
            m_str = h.date.strftime("%b")
            monthly_counts[m_str] += 1
    for d in disasters:
        if d.timestamp:
            m_str = d.timestamp.strftime("%b")
            monthly_counts[m_str] += 1
    
    month_order = ["Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"]
    timeline_labels = [m for m in month_order if m in monthly_counts]
    if not timeline_labels:
        timeline_labels = list(monthly_counts.keys()) or ["Sep", "Oct"]
    timeline_data = [float(monthly_counts.get(m, 0)) for m in timeline_labels]

    # 4. Population at risk by region
    pop_by_region = defaultdict(int)
    for d in disasters:
        if d.location:
            city = d.location.split(",")[0].strip()
            pop_by_region[city] += int(d.populationAtRisk or 0)
    
    sorted_pop = sorted(pop_by_region.items(), key=lambda item: item[1], reverse=True)[:6]
    if sorted_pop:
        pop_labels = [k for k, _ in sorted_pop]
        pop_data = [float(v) for _, v in sorted_pop]
    else:
        pop_labels = ["No Data"]
        pop_data = [0.0]

    # 5. Response Status
    status_order = ["Active", "Monitoring", "Resolved"]
    status_counter = Counter(d.status for d in disasters if d.status)
    status_labels = status_order
    status_data = [float(status_counter.get(s, 0)) for s in status_labels]

    return Analytics(
        disastersByType=LabelData(labels=type_labels, data=type_data),
        severityDistribution=LabelData(labels=sev_labels, data=sev_data),
        incidentsOverTime=LabelData(labels=timeline_labels, data=timeline_data),
        populationAtRisk=LabelData(labels=pop_labels, data=pop_data),
        responseStatus=LabelData(labels=status_labels, data=status_data),
    )

def get_telemetry_insights(db: Session) -> TelemetryInsights:
    disasters = db.query(DisasterModel).all()

    temps = [d.temperature for d in disasters if d.temperature is not None]
    humidities = [d.humidity for d in disasters if d.humidity is not None]
    
    avg_temp = round(sum(temps) / len(temps), 1) if temps else 28.5
    avg_hum = round(sum(humidities) / len(humidities), 1) if humidities else 70.0

    high_rain_count = sum(1 for d in disasters if (d.rainfall or "").lower() in ["high", "extreme"])
    danger_water_count = sum(1 for d in disasters if (d.waterLevel or "").lower() in ["danger", "elevated"])

    locations = set(d.location for d in disasters if d.location)

    hazard_counter = Counter(d.type for d in disasters if d.type)
    most_frequent = hazard_counter.most_common(1)[0][0] if hazard_counter else "Flood"

    pop_counter = defaultdict(int)
    for d in disasters:
        if d.location:
            pop_counter[d.location] += int(d.populationAtRisk or 0)
    top_region = max(pop_counter.items(), key=lambda x: x[1])[0] if pop_counter else "Chennai, Tamil Nadu"

    readings = [
        WeatherReading(
            location=d.location or "Unknown",
            temperature=d.temperature,
            humidity=d.humidity,
            rainfall=d.rainfall,
            waterLevel=d.waterLevel,
            roadAccessibility=d.roadAccessibility,
            severity=d.severity,
        )
        for d in disasters
        if d.temperature is not None or d.humidity is not None or d.rainfall or d.waterLevel
    ]

    return TelemetryInsights(
        avgTemperature=avg_temp,
        avgHumidity=avg_hum,
        highRiskRainfallCount=high_rain_count,
        dangerWaterLevelCount=danger_water_count,
        sensorLocationsMonitored=len(locations),
        mostFrequentHazard=most_frequent,
        topVulnerableRegion=top_region,
        weatherReadings=readings,
    )
