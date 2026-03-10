import pandas as pd
import time

df = pd.read_csv("data/gps_data.csv")

for index, row in df.iterrows():

    gps_data = {
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "speed": row["speed"],
        "heart_rate": row["heart_rate"]
    }

    print(gps_data)

    time.sleep(1)