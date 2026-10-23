from predict import predict_flood_risk

sample = {
    "Rainfall (mm)": 120,
    "Temperature (°C)": 28,
    "Humidity (%)": 85,
    "River Discharge (m³/s)": 500,
    "Water Level (m)": 4.5,
    "Elevation (m)": 10,
    "Land Cover": "Urban",
    "Soil Type": "Clay",
    "Population Density": 5000,
    "Infrastructure": 7,
    "Historical Floods": 2,
    "Latitude": 13.08,
    "Longitude": 80.27
}

print(predict_flood_risk(sample))