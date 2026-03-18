import requests # pyre-ignore[21]
import time
import math
import random

API_URL = "http://localhost:8000/api/gps"

def generate_segment(start_lat, start_lon, end_lat, end_lon, steps):
    lats = [start_lat + (end_lat - start_lat) * i / steps for i in range(steps)]
    lons = [start_lon + (end_lon - start_lon) * i / steps for i in range(steps)]
    return list(zip(lats, lons))

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat/2)**2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(d_lon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

print("========================================")
print("  Live Vehicle Tracking Simulation      ")
print("========================================")
print("This script will hijack 'Ravi Kumar' (P001) on the dashboard")
print("and simulate him getting into a vehicle and speeding away.\n")

# Start near home, drive far away
start_coords = (17.4200, 78.3500)
end_coords = (17.5000, 78.4500)
steps = 60 # 60 seconds of driving

path = generate_segment(start_coords[0], start_coords[1], end_coords[0], end_coords[1], steps)

print(f"Starting engine... Driving from {start_coords} to {end_coords}")
for i in range(1, len(path)):
    prev_lat, prev_lon = path[i-1]
    curr_lat, curr_lon = path[i]
    
    # Calculate exact speed to inject
    dist_km = haversine(prev_lat, prev_lon, curr_lat, curr_lon)
    time_hrs = 1.0 / 3600.0  # 1 second between pings
    speed_kmh = dist_km / time_hrs
    
    # Add random GPS noise to speed
    speed_kmh += random.uniform(-2.0, 5.0)

    payload = {
        "person_id": "P001",
        "latitude": curr_lat,
        "longitude": curr_lon,
        "speed_kmh": round(float(speed_kmh), 2) # type: ignore
    }

    try:
        response = requests.post(API_URL, json=payload)
        risk = response.json().get("risk_level", "UNKNOWN")
        print(f"Ping {i}/{steps} | Speed: {speed_kmh:.1f} km/h | Target: P001 | Risk Alert: {risk}")
    except Exception as e:
        print(f"Error connecting to dashboard: {e}")
        
    time.sleep(1)

print("\nSimulation complete. Check the dashboard History tab!")
