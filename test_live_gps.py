"""
Test Live GPS — Simulates a phone sending GPS coordinates.
============================================================
Sends GPS readings to POST /api/location, starting at home
and gradually moving away to trigger increasing risk levels.

Usage:
    1. Start the server:  python -m app.api
    2. Run this script:   python test_live_gps.py
"""

import requests
import time
import math

API_URL = "http://localhost:8080/api/location"

# Home coordinates (Hyderabad area)
HOME_LAT = 17.4200
HOME_LON = 78.3500

# Simulate path: starting at home, walking away
waypoints = [
    # Phase 1: Inside safe zone (< 100m) → Risk 10
    (HOME_LAT + 0.0002, HOME_LON + 0.0003),
    (HOME_LAT + 0.0004, HOME_LON + 0.0005),
    (HOME_LAT + 0.0006, HOME_LON + 0.0007),

    # Phase 2: Slight drift (100m–300m) → Risk 30
    (HOME_LAT + 0.0015, HOME_LON + 0.0010),
    (HOME_LAT + 0.0020, HOME_LON + 0.0015),
    (HOME_LAT + 0.0025, HOME_LON + 0.0018),

    # Phase 3: Suspicious movement (300m–700m) → Risk 60
    (HOME_LAT + 0.0040, HOME_LON + 0.0030),
    (HOME_LAT + 0.0050, HOME_LON + 0.0040),
    (HOME_LAT + 0.0055, HOME_LON + 0.0045),

    # Phase 4: Wandering / Critical (> 700m) → Risk 90
    (HOME_LAT + 0.0070, HOME_LON + 0.0060),
    (HOME_LAT + 0.0090, HOME_LON + 0.0080),
    (HOME_LAT + 0.0120, HOME_LON + 0.0100),
    (HOME_LAT + 0.0150, HOME_LON + 0.0130),
    (HOME_LAT + 0.0200, HOME_LON + 0.0160),
]


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two GPS points."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


print("=" * 55)
print("  📱 Live GPS Test — Simulating Phone GPS Input")
print("=" * 55)
print(f"  Home: ({HOME_LAT}, {HOME_LON})")
print(f"  API:  {API_URL}")
print(f"  Sending {len(waypoints)} GPS points...\n")

for i, (lat, lon) in enumerate(waypoints):
    dist = haversine(HOME_LAT, HOME_LON, lat, lon)
    speed = round(3.5 + (i * 0.5), 1)  # Simulated walking speed

    payload = {
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "speed": speed,
        "heart_rate": 72 + (i * 3),
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        data = response.json()

        risk = data.get("risk_score", "?")
        level = data.get("risk_level", "?")
        dist_km = data.get("distance_km", "?")
        label = data.get("distance_label", "")

        # Color-coded output
        if level == "critical":
            icon = "🔴"
        elif level == "high":
            icon = "🟠"
        elif level == "warning":
            icon = "🟡"
        else:
            icon = "🟢"

        print(f"  {icon} Point {i+1:2d}/{len(waypoints)} | "
              f"Risk: {risk:3d} ({level:8s}) | "
              f"Dist: {dist_km} km | "
              f"{label}")

    except requests.exceptions.ConnectionError:
        print(f"  ❌ Connection failed — is the server running at {API_URL}?")
        break
    except Exception as e:
        print(f"  ❌ Error: {e}")

    time.sleep(1.5)

print(f"\n{'=' * 55}")
print("  ✅ Test complete!")
print("  → Check dashboard at http://localhost:5000")
print("  → Live data at http://localhost:5000/api/live-data")
print(f"{'=' * 55}")
