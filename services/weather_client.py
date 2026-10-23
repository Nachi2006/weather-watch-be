import requests
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
def fetch_weather(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "wind_speed_10m",
            "surface_pressure",
        ],
        "hourly": [
            "precipitation",
            "rain",
            "relative_humidity_2m",
            "soil_moisture_0_to_7cm",
        ],
        "forecast_days": 2,
        "timezone": "Asia/Kolkata",
    }

    response = requests.get(
        OPEN_METEO_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    data = fetch_weather(13.0827, 80.2707)
    print(data.get("current", {}))
