"""
Synthetic GPS Dataset Generator
================================
Generates realistic movement patterns for missing person drift detection.
Data simulates a person with cognitive impairment (e.g., Alzheimer's) who
follows daily routines with occasional anomalous drift events.

Dataset rationale for recruiters:
- Real GPS data of vulnerable individuals is private/protected
- Synthetic data allows full control over anomaly injection
- Follows realistic patterns based on published research on wandering behavior
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import json
import math

# ── Anchor locations (Hyderabad-area coordinates, adjustable) ──────────────
HOME       = (17.4200, 78.3500)   # lat, lon
SCHOOL     = (17.4310, 78.3620)
PARK       = (17.4180, 78.3480)
HOSPITAL   = (17.4250, 78.3700)
MARKET     = (17.4150, 78.3550)

SAFE_ZONE_RADIUS_KM = 0.5          # Safe zone radius around home
WANDER_THRESHOLD_KM = 1.0          # Distance that triggers HIGH risk


def haversine(lat1, lon1, lat2, lon2):
    """Return distance in km between two GPS coordinates."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def meters_to_deg(meters):
    return meters / 111_000


def generate_segment(start, end, n_points, noise_m=15):
    """Interpolate GPS path between two points with realistic GPS noise."""
    lats = np.linspace(start[0], end[0], n_points)
    lons = np.linspace(start[1], end[1], n_points)
    noise = meters_to_deg(noise_m)
    lats += np.random.normal(0, noise, n_points)
    lons += np.random.normal(0, noise, n_points)
    return list(zip(lats, lons))


def daily_routine(date, person_id, is_anomaly=False):
    """
    Generate one day of GPS readings.
    Normal:  home → park → home → market → home
    Anomaly: home → park → [drift far away] → eventually home
    """
    records = []
    base_ts = datetime.combine(date, datetime.min.time())

    # Morning: 7:00 AM, walk to park
    morning_start = base_ts + timedelta(hours=7)
    path = generate_segment(HOME, PARK, 20)
    for i, (lat, lon) in enumerate(path):
        records.append({
            "person_id": person_id,
            "timestamp": morning_start + timedelta(minutes=i*2),
            "latitude": lat,
            "longitude": lon,
            "activity": "walking_to_park",
            "is_anomaly": False,
        })

    # Sit at park 30 min
    park_ts = morning_start + timedelta(minutes=40)
    for i in range(15):
        lat = PARK[0] + np.random.normal(0, meters_to_deg(5))
        lon = PARK[1] + np.random.normal(0, meters_to_deg(5))
        records.append({
            "person_id": person_id,
            "timestamp": park_ts + timedelta(minutes=i*2),
            "latitude": lat,
            "longitude": lon,
            "activity": "stationary_park",
            "is_anomaly": False,
        })

    if is_anomaly:
        # ANOMALY: person wanders in wrong direction
        drift_target = (
            HOME[0] + random.uniform(0.015, 0.030) * random.choice([-1, 1]),
            HOME[1] + random.uniform(0.015, 0.030) * random.choice([-1, 1]),
        )
        drift_start = park_ts + timedelta(minutes=30)
        path = generate_segment(PARK, drift_target, 30)
        for i, (lat, lon) in enumerate(path):
            records.append({
                "person_id": person_id,
                "timestamp": drift_start + timedelta(minutes=i*3),
                "latitude": lat,
                "longitude": lon,
                "activity": "wandering",
                "is_anomaly": True,
            })
        # Return path (slow, confused)
        return_start = drift_start + timedelta(minutes=90)
        path = generate_segment(drift_target, HOME, 40)
        for i, (lat, lon) in enumerate(path):
            records.append({
                "person_id": person_id,
                "timestamp": return_start + timedelta(minutes=i*4),
                "latitude": lat,
                "longitude": lon,
                "activity": "returning",
                "is_anomaly": True,
            })
    else:
        # Normal return home
        return_start = park_ts + timedelta(minutes=30)
        path = generate_segment(PARK, HOME, 20)
        for i, (lat, lon) in enumerate(path):
            records.append({
                "person_id": person_id,
                "timestamp": return_start + timedelta(minutes=i*2),
                "latitude": lat,
                "longitude": lon,
                "activity": "returning_home",
                "is_anomaly": False,
            })

    # Afternoon: 2 PM market visit (normal only)
    if not is_anomaly:
        afternoon_start = base_ts + timedelta(hours=14)
        path = generate_segment(HOME, MARKET, 15)
        for i, (lat, lon) in enumerate(path):
            records.append({
                "person_id": person_id,
                "timestamp": afternoon_start + timedelta(minutes=i*2),
                "latitude": lat,
                "longitude": lon,
                "activity": "market_trip",
                "is_anomaly": False,
            })
        path = generate_segment(MARKET, HOME, 15)
        for i, (lat, lon) in enumerate(path):
            records.append({
                "person_id": person_id,
                "timestamp": afternoon_start + timedelta(minutes=30 + i*2),
                "latitude": lat,
                "longitude": lon,
                "activity": "returning_home",
                "is_anomaly": False,
            })

    return records


def generate_dataset(n_days=30, n_persons=3, anomaly_rate=0.15):
    """Generate full synthetic dataset with multiple persons."""
    all_records = []
    start_date = datetime.now().date() - timedelta(days=n_days)

    for person_id in range(1, n_persons + 1):
        for day_offset in range(n_days):
            date = start_date + timedelta(days=day_offset)
            is_anomaly = random.random() < anomaly_rate
            records = daily_routine(date, f"P{person_id:03d}", is_anomaly)
            all_records.extend(records)

    df = pd.DataFrame(all_records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by=["person_id", "timestamp"]).reset_index(drop=True) # type: ignore

    # Compute derived features
    df["dist_from_home_km"] = df.apply(
        lambda r: haversine(r.latitude, r.longitude, HOME[0], HOME[1]), axis=1
    )
    df["in_safe_zone"] = df["dist_from_home_km"] <= SAFE_ZONE_RADIUS_KM
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek

    # Speed estimation (km/h between consecutive points per person)
    df["speed_kmh"] = 0.0
    for pid in df["person_id"].unique():
        mask = df["person_id"] == pid
        sub = df[mask].copy()
        dists = [0] + [
            haversine(sub.iloc[i-1]["latitude"], sub.iloc[i-1]["longitude"],
                      sub.iloc[i]["latitude"],   sub.iloc[i]["longitude"])
            for i in range(1, len(sub))
        ]
        time_hrs = [0] + [
            (sub.iloc[i]["timestamp"] - sub.iloc[i-1]["timestamp"]).seconds / 3600
            for i in range(1, len(sub))
        ]
        speeds = [d / max(t, 1e-6) for d, t in zip(dists, time_hrs)]
        df.loc[mask, "speed_kmh"] = speeds

    return df


def save_dataset(output_path="data/gps_dataset.csv"):
    """Generate and save the synthetic GPS dataset."""
    print("Generating synthetic GPS dataset...")
    df = generate_dataset(n_days=30, n_persons=3, anomaly_rate=0.20)
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df):,} records → {output_path}")

    # Summary stats
    summary = {
        "total_records": len(df),
        "persons": df["person_id"].nunique(),
        "date_range": [str(df["timestamp"].min().date()), str(df["timestamp"].max().date())],
        "anomaly_rate": round(df["is_anomaly"].mean(), 3),
        "home_coordinates": HOME,
        "safe_zone_radius_km": SAFE_ZONE_RADIUS_KM,
    }
    with open("data/dataset_info.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary: {summary}")
    return df


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    save_dataset()
