import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Base location (home)
base_lat = 12.9716
base_lon = 77.5946

data = []
start_time = datetime(2026, 3, 12, 8, 0, 0)

for i in range(100):

    timestamp = start_time + timedelta(minutes=i)

    # Normal walking pattern
    if i < 60:
        lat = base_lat + np.random.normal(0, 0.0003)
        lon = base_lon + np.random.normal(0, 0.0003)
        speed = np.random.uniform(2.5, 5.0)        # Normal walking speed km/h
        heart_rate = np.random.randint(65, 85)       # Normal resting/walking HR

    # Wandering / drift behaviour
    else:
        lat = base_lat + np.random.normal(0.01, 0.001)
        lon = base_lon + np.random.normal(0.01, 0.001)
        speed = np.random.uniform(0.5, 9.0)          # Erratic speed
        heart_rate = np.random.randint(85, 130)       # Elevated HR

    data.append([timestamp.isoformat(), lat, lon, speed, heart_rate])

df = pd.DataFrame(data, columns=["timestamp", "latitude", "longitude", "speed", "heart_rate"])

df.to_csv("data/gps_data.csv", index=False)

print("GPS data generated with wandering behaviour, speed, heart_rate, and timestamps")