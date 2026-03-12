import pandas as pd
import joblib
import time
import os

# Load anomaly model
model = joblib.load(os.path.join(os.path.dirname(__file__), "..", "models", "anomaly_model.pkl"))

df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "gps_data.csv"))

for index, row in df.iterrows():
    features = pd.DataFrame(
        [[row["speed"], row["heart_rate"]]],
        columns=["speed", "heart_rate"]
    )

    prediction = model.predict(features)

    if prediction[0] == -1:
        print(f"⚠ HIGH RISK: abnormal behavior at index {index} "
              f"(speed={row['speed']:.1f}, hr={row['heart_rate']})")
    else:
        print(f"✅ SAFE at index {index}")

    time.sleep(1)