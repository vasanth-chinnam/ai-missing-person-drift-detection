import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

df = pd.read_csv("data/gps_data.csv")

features = df[["speed", "heart_rate"]]

model = IsolationForest(
    n_estimators=200,
    contamination=0.02, # type: ignore
    random_state=42
)

model.fit(features)

joblib.dump(model, "models/anomaly_model.pkl")

print("Model trained successfully")