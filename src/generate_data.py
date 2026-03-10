import pandas as pd
import numpy as np

rows = 5000

data = {
    "timestamp": range(rows),
    "latitude": np.random.normal(12.9716, 0.01, rows),
    "longitude": np.random.normal(77.5946, 0.01, rows),
    "speed": np.random.normal(2.5, 0.8, rows),
    "heart_rate": np.random.normal(75, 10, rows)
}

df = pd.DataFrame(data)

# create abnormal wandering cases
for i in range(100):
    df.loc[np.random.randint(rows), "speed"] = np.random.uniform(8,12)
    df.loc[np.random.randint(rows), "heart_rate"] = np.random.uniform(110,140)

df.to_csv("data/gps_data.csv", index=False)

print("Dataset created")