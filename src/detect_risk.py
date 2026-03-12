import pandas as pd
import os
import joblib

model = joblib.load(os.path.join(os.path.dirname(__file__), "..", "models", "anomaly_model.pkl"))

df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "gps_data.csv"))

features = df[["speed", "heart_rate"]]

df["anomaly"] = model.predict(features)

df["risk"] = df["anomaly"].apply(
    lambda x: "HIGH RISK" if x == -1 else "NORMAL"
)

print(df[["timestamp", "latitude", "longitude", "speed", "heart_rate", "anomaly", "risk"]].head(20))