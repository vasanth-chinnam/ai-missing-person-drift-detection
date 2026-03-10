import pandas as pd
import joblib
import time

# Load anomaly model
model = joblib.load("models/anomaly_model.pkl")

df = pd.read_csv("data/gps_data.csv")

for index, row in df.iterrows():
    features = pd.DataFrame(
    [[row["speed"], row["heart_rate"]]],
    columns=["speed","heart_rate"])

    prediction = model.predict(features)

    if prediction == -1:
        print("⚠ HIGH RISK: abnormal behavior detected")

    else:
        print("SAFE")

    time.sleep(1)