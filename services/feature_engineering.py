"""
Feature engineering for multi-disaster prediction.

Transforms raw Open-Meteo current + hourly weather data into a flat
feature dict that the disaster-prediction model consumes.
"""

from __future__ import annotations

import math
from typing import Any


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convert *val* to float; return *default* on failure."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _mean(values: list[float | None]) -> float:
    """Return mean of non-None values, or 0.0 if empty."""
    nums = [v for v in values if v is not None]
    return sum(nums) / len(nums) if nums else 0.0


def _slope(values: list[float | None]) -> float:
    """Simple linear-regression slope over sequential hourly values.

    A positive slope means the quantity is *increasing* over time.
    """
    nums = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(nums) < 2:
        return 0.0
    n = len(nums)
    sum_x = sum(x for x, _ in nums)
    sum_y = sum(y for _, y in nums)
    sum_xy = sum(x * y for x, y in nums)
    sum_x2 = sum(x * x for x, _ in nums)
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom


# ── derived indices ──────────────────────────────────────────────────────────

def _heat_index(temp_c: float, humidity_pct: float) -> float:
    """Simplified Rothfusz heat-index (°C).

    High values correlate with fire / smoke risk.
    """
    if temp_c < 27:
        return temp_c
    t = temp_c * 9 / 5 + 32  # to °F for the standard formula
    rh = humidity_pct
    hi = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t * t
        - 0.05481717 * rh * rh
        + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )
    return (hi - 32) * 5 / 9  # back to °C


def _fire_weather_index(temp_c: float, humidity_pct: float,
                        wind_kmph: float, rain_mm: float) -> float:
    """Simplified Fire Weather Index (0-100 scale).

    Combines dryness (low humidity, low rain) with heat and wind.
    Higher ⇒ greater fire risk.
    """
    dryness = max(0.0, 100.0 - humidity_pct) / 100.0
    heat_factor = min(temp_c / 50.0, 1.0)
    wind_factor = min(wind_kmph / 80.0, 1.0)
    rain_suppression = max(0.0, 1.0 - rain_mm / 20.0)
    return round(
        (0.35 * dryness + 0.25 * heat_factor + 0.20 * wind_factor + 0.20 * rain_suppression) * 100,
        2,
    )


def _soil_saturation_index(soil_moisture_vals: list[float | None],
                           rain_mm_cumulative: float) -> float:
    """0-100 index: high ⇒ ground is saturated (flood / landslide risk)."""
    avg_sm = _mean(soil_moisture_vals)
    # soil_moisture_0_to_7cm is in m³/m³ (0-0.5 typical)
    sm_component = min(avg_sm / 0.45, 1.0)
    rain_component = min(rain_mm_cumulative / 150.0, 1.0)
    return round((0.6 * sm_component + 0.4 * rain_component) * 100, 2)


# ── public API ───────────────────────────────────────────────────────────────

def engineer_features(weather_payload: dict) -> dict:
    """Return a flat feature dict from a raw Open-Meteo response.

    Parameters
    ----------
    weather_payload : dict
        Full JSON response from the Open-Meteo API (must include
        ``current`` and ``hourly`` sections).

    Returns
    -------
    dict
        Feature names → float values, ready for ``pd.DataFrame([features])``.
    """
    current = weather_payload.get("current", {})
    hourly = weather_payload.get("hourly", {})

    # ── current scalars ──────────────────────────────────────────────────
    temperature = _safe_float(current.get("temperature_2m"))
    humidity = _safe_float(current.get("relative_humidity_2m"))
    precipitation = _safe_float(current.get("precipitation"))
    rain = _safe_float(current.get("rain"))
    wind_speed = _safe_float(current.get("wind_speed_10m"))
    pressure = _safe_float(current.get("surface_pressure"))

    # ── hourly series (up to 48 h forecast) ──────────────────────────────
    h_precip: list = hourly.get("precipitation", [])
    h_rain: list = hourly.get("rain", [])
    h_humidity: list = hourly.get("relative_humidity_2m", [])
    h_soil: list = hourly.get("soil_moisture_0_to_7cm", [])

    # Cumulative / rolling metrics
    rain_6h = sum(_safe_float(v) for v in h_precip[:6])
    rain_12h = sum(_safe_float(v) for v in h_precip[:12])
    rain_24h = sum(_safe_float(v) for v in h_precip[:24])
    rain_48h = sum(_safe_float(v) for v in h_precip[:48])

    humidity_trend = _slope([_safe_float(v) for v in h_humidity[:24]])
    precip_trend = _slope([_safe_float(v) for v in h_precip[:24]])

    pressure_delta = 0.0
    # If the hourly block also carries pressure we can compute Δ
    h_pressure = hourly.get("surface_pressure", [])
    if len(h_pressure) >= 6:
        pressure_delta = _safe_float(h_pressure[5]) - _safe_float(h_pressure[0])

    # ── derived indices ──────────────────────────────────────────────────
    heat_idx = _heat_index(temperature, humidity)
    fwi = _fire_weather_index(temperature, humidity, wind_speed, precipitation)
    ssi = _soil_saturation_index(
        [_safe_float(v) for v in h_soil[:24]],
        rain_24h,
    )

    return {
        # Raw current
        "temperature_c": round(temperature, 2),
        "humidity_pct": round(humidity, 2),
        "precipitation_mm": round(precipitation, 2),
        "rain_mm": round(rain, 2),
        "wind_speed_kmph": round(wind_speed, 2),
        "pressure_hpa": round(pressure, 2),
        # Cumulative rainfall
        "rain_6h_mm": round(rain_6h, 2),
        "rain_12h_mm": round(rain_12h, 2),
        "rain_24h_mm": round(rain_24h, 2),
        "rain_48h_mm": round(rain_48h, 2),
        # Trends (slope per hour)
        "humidity_trend": round(humidity_trend, 4),
        "precip_trend": round(precip_trend, 4),
        "pressure_delta_6h": round(pressure_delta, 2),
        # Derived indices
        "heat_index_c": round(heat_idx, 2),
        "fire_weather_index": fwi,
        "soil_saturation_index": ssi,
    }
