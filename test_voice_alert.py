"""
test_voice_alert.py
-----------------
Run this script to simulate a person wandering 2 km from home.
This will trigger the Twilio Voice Call alert to your phone.

Usage:
    .\venv\Scripts\python.exe test_voice_alert.py
"""
import requests

# Your live Render URL
BASE_URL = "https://ai-missing-person-drift-detection.onrender.com"

# These coordinates are ~2 km from your house — definitely "wandering"
WANDERING_LAT = 17.3750  # ~2.5 km south of home
WANDERING_LON = 78.6100

payload = {
    "lat": WANDERING_LAT,
    "lon": WANDERING_LON,
    "speed": 3.2,
    "heart_rate": 95,
    "person_id": "P001"
}

print("Sending wandering GPS to Render server...")
print(f"  Location: {WANDERING_LAT}, {WANDERING_LON} (far from home)")
print(f"  URL: {BASE_URL}/api/location\n")

try:
    res = requests.post(f"{BASE_URL}/api/location", json=payload, timeout=15)
    data = res.json()
    print("Server response:")
    print(f"  Risk Level : {data.get('risk_level', data.get('level', '?'))}")
    print(f"  Distance   : {data.get('distance_km', '?')} km from home")
    print(f"  Risk Score : {data.get('risk_score', data.get('risk', '?'))}")
    print(f"\n✅ Done! Check your phone for a Voice Call from +1 478-429-7791")
    print("   (Call is initiated only if cooldown period of 5 mins has passed)")
except Exception as e:
    print(f"❌ Error: {e}")
