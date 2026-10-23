"""
Train a multi-class disaster prediction model.

Generates realistic synthetic weather scenarios labelled by disaster type,
trains a Random Forest classifier, evaluates it, and serialises the model
to ``ml/disaster_model.joblib``.

Run directly:
    python -m ml.train_disaster_model
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

# ── constants ────────────────────────────────────────────────────────────────

FEATURE_COLUMNS = [
    "temperature_c",
    "humidity_pct",
    "precipitation_mm",
    "rain_mm",
    "wind_speed_kmph",
    "pressure_hpa",
    "rain_6h_mm",
    "rain_12h_mm",
    "rain_24h_mm",
    "rain_48h_mm",
    "humidity_trend",
    "precip_trend",
    "pressure_delta_6h",
    "heat_index_c",
    "fire_weather_index",
    "soil_saturation_index",
]

DISASTER_TYPES = [
    "None",              # 0 — no disaster
    "Flood",             # 1
    "Landslide",         # 2
    "Fire",              # 3
    "Smoke",             # 4
    "Building Collapse", # 5
    "Road Blockage",     # 6
]

MODEL_DIR = Path(__file__).parent
MODEL_PATH = MODEL_DIR / "disaster_model.joblib"

RANDOM_SEED = 42
N_SAMPLES = 12_000  # total synthetic rows

# ── synthetic data generators ────────────────────────────────────────────────

def _rng() -> random.Random:
    return random.Random(RANDOM_SEED)


def _np_rng() -> np.random.Generator:
    return np.random.default_rng(RANDOM_SEED)


def _clip(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _generate_none(rng: np.random.Generator, n: int) -> list[dict]:
    """Normal weather — no disaster conditions."""
    rows: list[dict] = []
    for _ in range(n):
        temp = rng.normal(28, 4)
        hum = rng.normal(55, 12)
        precip = rng.exponential(1.0)
        wind = rng.normal(12, 5)
        pres = rng.normal(1013, 4)
        rain_6h = rng.exponential(3)
        rain_12h = rain_6h + rng.exponential(3)
        rain_24h = rain_12h + rng.exponential(4)
        rain_48h = rain_24h + rng.exponential(5)
        rows.append({
            "temperature_c": round(_clip(temp, 10, 42), 2),
            "humidity_pct": round(_clip(hum, 15, 85), 2),
            "precipitation_mm": round(_clip(precip, 0, 8), 2),
            "rain_mm": round(_clip(precip * 0.8, 0, 7), 2),
            "wind_speed_kmph": round(_clip(wind, 0, 35), 2),
            "pressure_hpa": round(_clip(pres, 995, 1025), 2),
            "rain_6h_mm": round(_clip(rain_6h, 0, 20), 2),
            "rain_12h_mm": round(_clip(rain_12h, 0, 35), 2),
            "rain_24h_mm": round(_clip(rain_24h, 0, 50), 2),
            "rain_48h_mm": round(_clip(rain_48h, 0, 70), 2),
            "humidity_trend": round(rng.normal(0, 0.3), 4),
            "precip_trend": round(rng.normal(0, 0.1), 4),
            "pressure_delta_6h": round(rng.normal(0, 1.5), 2),
            "heat_index_c": round(_clip(temp + rng.normal(0, 2), 10, 45), 2),
            "fire_weather_index": round(_clip(rng.normal(30, 10), 5, 55), 2),
            "soil_saturation_index": round(_clip(rng.normal(25, 12), 0, 55), 2),
            "label": "None",
        })
    return rows


def _generate_flood(rng: np.random.Generator, n: int) -> list[dict]:
    """Heavy rainfall, high humidity, saturated soil."""
    rows: list[dict] = []
    for _ in range(n):
        temp = rng.normal(27, 3)
        hum = rng.normal(88, 5)
        precip = rng.normal(25, 10)
        wind = rng.normal(20, 8)
        pres = rng.normal(1002, 5)
        rain_6h = rng.normal(40, 15)
        rain_12h = rain_6h + rng.normal(30, 12)
        rain_24h = rain_12h + rng.normal(40, 15)
        rain_48h = rain_24h + rng.normal(50, 20)
        rows.append({
            "temperature_c": round(_clip(temp, 18, 35), 2),
            "humidity_pct": round(_clip(hum, 75, 100), 2),
            "precipitation_mm": round(_clip(precip, 8, 60), 2),
            "rain_mm": round(_clip(precip * 0.9, 7, 55), 2),
            "wind_speed_kmph": round(_clip(wind, 5, 50), 2),
            "pressure_hpa": round(_clip(pres, 985, 1010), 2),
            "rain_6h_mm": round(_clip(rain_6h, 15, 80), 2),
            "rain_12h_mm": round(_clip(rain_12h, 30, 140), 2),
            "rain_24h_mm": round(_clip(rain_24h, 50, 250), 2),
            "rain_48h_mm": round(_clip(rain_48h, 80, 400), 2),
            "humidity_trend": round(_clip(rng.normal(0.8, 0.4), 0.1, 2.0), 4),
            "precip_trend": round(_clip(rng.normal(0.6, 0.3), 0.1, 1.5), 4),
            "pressure_delta_6h": round(_clip(rng.normal(-3, 2), -10, 0), 2),
            "heat_index_c": round(_clip(temp + rng.normal(2, 2), 18, 40), 2),
            "fire_weather_index": round(_clip(rng.normal(15, 8), 0, 35), 2),
            "soil_saturation_index": round(_clip(rng.normal(78, 12), 50, 100), 2),
            "label": "Flood",
        })
    return rows


def _generate_landslide(rng: np.random.Generator, n: int) -> list[dict]:
    """Sustained rainfall + saturated soil on steep terrain."""
    rows: list[dict] = []
    for _ in range(n):
        temp = rng.normal(22, 4)
        hum = rng.normal(90, 4)
        precip = rng.normal(18, 8)
        wind = rng.normal(15, 6)
        pres = rng.normal(1000, 5)
        rain_6h = rng.normal(30, 12)
        rain_12h = rain_6h + rng.normal(25, 10)
        rain_24h = rain_12h + rng.normal(35, 15)
        rain_48h = rain_24h + rng.normal(45, 18)
        rows.append({
            "temperature_c": round(_clip(temp, 12, 30), 2),
            "humidity_pct": round(_clip(hum, 80, 100), 2),
            "precipitation_mm": round(_clip(precip, 5, 45), 2),
            "rain_mm": round(_clip(precip * 0.85, 4, 40), 2),
            "wind_speed_kmph": round(_clip(wind, 3, 35), 2),
            "pressure_hpa": round(_clip(pres, 988, 1012), 2),
            "rain_6h_mm": round(_clip(rain_6h, 10, 65), 2),
            "rain_12h_mm": round(_clip(rain_12h, 25, 120), 2),
            "rain_24h_mm": round(_clip(rain_24h, 45, 200), 2),
            "rain_48h_mm": round(_clip(rain_48h, 70, 350), 2),
            "humidity_trend": round(_clip(rng.normal(0.6, 0.3), 0.0, 1.5), 4),
            "precip_trend": round(_clip(rng.normal(0.4, 0.2), 0.0, 1.2), 4),
            "pressure_delta_6h": round(_clip(rng.normal(-2.5, 1.8), -8, 0), 2),
            "heat_index_c": round(_clip(temp + rng.normal(1, 1.5), 12, 32), 2),
            "fire_weather_index": round(_clip(rng.normal(12, 6), 0, 30), 2),
            "soil_saturation_index": round(_clip(rng.normal(82, 10), 55, 100), 2),
            "label": "Landslide",
        })
    return rows


def _generate_fire(rng: np.random.Generator, n: int) -> list[dict]:
    """Hot, dry, windy — classic fire conditions."""
    rows: list[dict] = []
    for _ in range(n):
        temp = rng.normal(38, 4)
        hum = rng.normal(25, 8)
        precip = rng.exponential(0.3)
        wind = rng.normal(30, 10)
        pres = rng.normal(1015, 3)
        rain_6h = rng.exponential(0.5)
        rain_12h = rain_6h + rng.exponential(0.5)
        rain_24h = rain_12h + rng.exponential(1)
        rain_48h = rain_24h + rng.exponential(1.5)
        rows.append({
            "temperature_c": round(_clip(temp, 30, 48), 2),
            "humidity_pct": round(_clip(hum, 8, 40), 2),
            "precipitation_mm": round(_clip(precip, 0, 3), 2),
            "rain_mm": round(_clip(precip * 0.5, 0, 2), 2),
            "wind_speed_kmph": round(_clip(wind, 10, 60), 2),
            "pressure_hpa": round(_clip(pres, 1005, 1025), 2),
            "rain_6h_mm": round(_clip(rain_6h, 0, 3), 2),
            "rain_12h_mm": round(_clip(rain_12h, 0, 5), 2),
            "rain_24h_mm": round(_clip(rain_24h, 0, 8), 2),
            "rain_48h_mm": round(_clip(rain_48h, 0, 12), 2),
            "humidity_trend": round(_clip(rng.normal(-0.5, 0.3), -1.5, 0.0), 4),
            "precip_trend": round(_clip(rng.normal(-0.1, 0.08), -0.5, 0.0), 4),
            "pressure_delta_6h": round(rng.normal(0.5, 1.0), 2),
            "heat_index_c": round(_clip(temp + rng.normal(5, 3), 32, 55), 2),
            "fire_weather_index": round(_clip(rng.normal(78, 10), 55, 100), 2),
            "soil_saturation_index": round(_clip(rng.normal(10, 6), 0, 25), 2),
            "label": "Fire",
        })
    return rows


def _generate_smoke(rng: np.random.Generator, n: int) -> list[dict]:
    """Similar to fire but typically less extreme; often industrial."""
    rows: list[dict] = []
    for _ in range(n):
        temp = rng.normal(34, 4)
        hum = rng.normal(35, 10)
        precip = rng.exponential(0.5)
        wind = rng.normal(18, 8)
        pres = rng.normal(1012, 4)
        rain_6h = rng.exponential(1)
        rain_12h = rain_6h + rng.exponential(1)
        rain_24h = rain_12h + rng.exponential(1.5)
        rain_48h = rain_24h + rng.exponential(2)
        rows.append({
            "temperature_c": round(_clip(temp, 26, 44), 2),
            "humidity_pct": round(_clip(hum, 15, 55), 2),
            "precipitation_mm": round(_clip(precip, 0, 5), 2),
            "rain_mm": round(_clip(precip * 0.6, 0, 3), 2),
            "wind_speed_kmph": round(_clip(wind, 3, 40), 2),
            "pressure_hpa": round(_clip(pres, 1000, 1022), 2),
            "rain_6h_mm": round(_clip(rain_6h, 0, 6), 2),
            "rain_12h_mm": round(_clip(rain_12h, 0, 10), 2),
            "rain_24h_mm": round(_clip(rain_24h, 0, 15), 2),
            "rain_48h_mm": round(_clip(rain_48h, 0, 22), 2),
            "humidity_trend": round(_clip(rng.normal(-0.3, 0.25), -1.0, 0.2), 4),
            "precip_trend": round(_clip(rng.normal(-0.05, 0.06), -0.3, 0.1), 4),
            "pressure_delta_6h": round(rng.normal(0, 1.2), 2),
            "heat_index_c": round(_clip(temp + rng.normal(3, 2.5), 28, 50), 2),
            "fire_weather_index": round(_clip(rng.normal(62, 12), 40, 90), 2),
            "soil_saturation_index": round(_clip(rng.normal(18, 8), 0, 35), 2),
            "label": "Smoke",
        })
    return rows


def _generate_building_collapse(rng: np.random.Generator, n: int) -> list[dict]:
    """Extreme wind, heavy rain weakening structures, or very high soil saturation."""
    rows: list[dict] = []
    for _ in range(n):
        temp = rng.normal(30, 5)
        hum = rng.normal(65, 15)
        precip = rng.normal(12, 8)
        wind = rng.normal(45, 15)
        pres = rng.normal(998, 6)
        rain_6h = rng.normal(20, 10)
        rain_12h = rain_6h + rng.normal(18, 10)
        rain_24h = rain_12h + rng.normal(25, 12)
        rain_48h = rain_24h + rng.normal(30, 15)
        rows.append({
            "temperature_c": round(_clip(temp, 18, 42), 2),
            "humidity_pct": round(_clip(hum, 35, 95), 2),
            "precipitation_mm": round(_clip(precip, 2, 35), 2),
            "rain_mm": round(_clip(precip * 0.7, 1, 30), 2),
            "wind_speed_kmph": round(_clip(wind, 25, 90), 2),
            "pressure_hpa": round(_clip(pres, 980, 1010), 2),
            "rain_6h_mm": round(_clip(rain_6h, 5, 50), 2),
            "rain_12h_mm": round(_clip(rain_12h, 10, 90), 2),
            "rain_24h_mm": round(_clip(rain_24h, 20, 150), 2),
            "rain_48h_mm": round(_clip(rain_48h, 35, 250), 2),
            "humidity_trend": round(rng.normal(0.2, 0.4), 4),
            "precip_trend": round(rng.normal(0.2, 0.2), 4),
            "pressure_delta_6h": round(_clip(rng.normal(-4, 3), -12, 0), 2),
            "heat_index_c": round(_clip(temp + rng.normal(1, 2), 18, 45), 2),
            "fire_weather_index": round(_clip(rng.normal(28, 12), 5, 55), 2),
            "soil_saturation_index": round(_clip(rng.normal(55, 18), 20, 90), 2),
            "label": "Building Collapse",
        })
    return rows


def _generate_road_blockage(rng: np.random.Generator, n: int) -> list[dict]:
    """Moderate-to-heavy rain + wind; often accompanies storms."""
    rows: list[dict] = []
    for _ in range(n):
        temp = rng.normal(25, 5)
        hum = rng.normal(80, 8)
        precip = rng.normal(15, 7)
        wind = rng.normal(35, 12)
        pres = rng.normal(1001, 5)
        rain_6h = rng.normal(25, 10)
        rain_12h = rain_6h + rng.normal(20, 10)
        rain_24h = rain_12h + rng.normal(30, 12)
        rain_48h = rain_24h + rng.normal(35, 15)
        rows.append({
            "temperature_c": round(_clip(temp, 14, 38), 2),
            "humidity_pct": round(_clip(hum, 60, 98), 2),
            "precipitation_mm": round(_clip(precip, 3, 40), 2),
            "rain_mm": round(_clip(precip * 0.75, 2, 35), 2),
            "wind_speed_kmph": round(_clip(wind, 15, 70), 2),
            "pressure_hpa": round(_clip(pres, 985, 1015), 2),
            "rain_6h_mm": round(_clip(rain_6h, 8, 55), 2),
            "rain_12h_mm": round(_clip(rain_12h, 18, 100), 2),
            "rain_24h_mm": round(_clip(rain_24h, 30, 180), 2),
            "rain_48h_mm": round(_clip(rain_48h, 50, 280), 2),
            "humidity_trend": round(_clip(rng.normal(0.4, 0.3), -0.2, 1.2), 4),
            "precip_trend": round(_clip(rng.normal(0.3, 0.2), -0.1, 1.0), 4),
            "pressure_delta_6h": round(_clip(rng.normal(-3, 2), -10, 0), 2),
            "heat_index_c": round(_clip(temp + rng.normal(0, 2), 14, 40), 2),
            "fire_weather_index": round(_clip(rng.normal(20, 8), 5, 40), 2),
            "soil_saturation_index": round(_clip(rng.normal(65, 15), 30, 95), 2),
            "label": "Road Blockage",
        })
    return rows


# ── main training routine ────────────────────────────────────────────────────

def generate_dataset(n_total: int = N_SAMPLES) -> pd.DataFrame:
    """Create a balanced synthetic dataset."""
    rng = _np_rng()
    per_class = n_total // len(DISASTER_TYPES)
    extra = n_total - per_class * len(DISASTER_TYPES)

    generators = {
        "None": _generate_none,
        "Flood": _generate_flood,
        "Landslide": _generate_landslide,
        "Fire": _generate_fire,
        "Smoke": _generate_smoke,
        "Building Collapse": _generate_building_collapse,
        "Road Blockage": _generate_road_blockage,
    }

    all_rows: list[dict] = []
    for label, gen_fn in generators.items():
        count = per_class + (1 if extra > 0 else 0)
        extra -= 1
        all_rows.extend(gen_fn(rng, count))

    df = pd.DataFrame(all_rows)
    return df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)


def train_model() -> dict:
    """Generate data, train model, save to disk, return metrics."""
    print("=" * 60)
    print("  Multi-Disaster Prediction - Model Training")
    print("=" * 60)

    # 1. Generate dataset
    print(f"\n> Generating {N_SAMPLES} synthetic samples ...")
    df = generate_dataset(N_SAMPLES)
    print(f"  Classes: {df['label'].value_counts().to_dict()}")

    # 2. Split
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )
    print(f"  Train: {len(X_train)}  |  Test: {len(X_test)}")

    # 3. Train
    print("\n> Training Random Forest classifier ...")
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # 4. Evaluate
    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred, labels=DISASTER_TYPES)

    print("\n> Classification Report:")
    print(classification_report(y_test, y_pred))

    print("> Confusion Matrix:")
    print(pd.DataFrame(cm, index=DISASTER_TYPES, columns=DISASTER_TYPES))

    # 5. Feature importances
    importances = dict(zip(FEATURE_COLUMNS, clf.feature_importances_))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print("\n> Feature Importances:")
    for feat, imp in sorted_imp:
        bar = "#" * int(imp * 80)
        print(f"  {feat:>25s}  {imp:.4f}  {bar}")

    # 6. Save
    model_artifact = {
        "classifier": clf,
        "feature_columns": FEATURE_COLUMNS,
        "disaster_types": DISASTER_TYPES,
        "version": "disaster-multi-v1",
    }
    joblib.dump(model_artifact, MODEL_PATH)
    print(f"\n[OK] Model saved to {MODEL_PATH}  ({MODEL_PATH.stat().st_size / 1024:.0f} KB)")

    return {
        "accuracy": report["accuracy"],
        "per_class": {k: v for k, v in report.items() if k in DISASTER_TYPES},
        "feature_importances": importances,
    }


if __name__ == "__main__":
    metrics = train_model()
    print("\n" + "=" * 60)
    print(f"  Overall Accuracy: {metrics['accuracy']:.4f}")
    print("=" * 60)
