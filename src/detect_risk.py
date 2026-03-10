import pandas as pd
import joblib

model = joblib.load("models/anomaly_model.pkl")

df = pd.read_csv("data/gps_data.csv")

features = df[["speed", "heart_rate"]]

df["anomaly"] = model.predict(features)

df["risk"] = df["anomaly"].apply(
    lambda x: "HIGH RISK" if x == -1 else "NORMAL"
)

print(df.head(20))