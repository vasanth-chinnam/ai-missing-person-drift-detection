import pandas as pd
import time
import os

df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "gps_data.csv"))

for index, row in df.iterrows():

    gps_data = {
        "timestamp": row["timestamp"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "speed": row["speed"],
        "heart_rate": row["heart_rate"]
    }

    print(gps_data)

    time.sleep(1)