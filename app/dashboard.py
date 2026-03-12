import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import joblib
import time
from src.geofence import check_geofence
from src.risk_engine import calculate_risk
from src.trajectory_predictor import detect_route_deviation
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from src.notification import send_alert

st.title("AI Missing Person Early Drift Detection System")

df = pd.read_csv("data/gps_data.csv")

model = joblib.load("models/anomaly_model.pkl")
heatmap_data = df[["latitude", "longitude"]].values.tolist()

map_center = [df["latitude"].mean(), df["longitude"].mean()]

heat_map = folium.Map(location=map_center, zoom_start=14)

HeatMap(heatmap_data).add_to(heat_map)

st.subheader("Risk Heatmap")

st_folium(heat_map, width=700)

map_placeholder = st.empty()
alert_placeholder = st.empty()
risk_placeholder = st.empty()


for i in range(len(df)):

    row = df.iloc[i]

    live_data = df.iloc[:i + 1]

    map_placeholder.map(
        pd.DataFrame({
            "lat": [row["latitude"]],
            "lon": [row["longitude"]]
        })
    )

    # Use speed & heart_rate for anomaly detection (matches training features)
    features = pd.DataFrame(
        [[row["speed"], row["heart_rate"]]],
        columns=["speed", "heart_rate"]
    )

    prediction = int(model.predict(features)[0])

    outside, distance = check_geofence(row["latitude"], row["longitude"])

    route_deviation = detect_route_deviation(i)

    risk = calculate_risk(prediction, outside, route_deviation)
    risk_placeholder.write(f"Risk Score: {risk}/100")

    if risk > 60:
        alert_placeholder.error("⚠ WANDERING RISK DETECTED")
        try:
            send_alert(
                f"{row['latitude']}, {row['longitude']}",
                risk
            )
        except Exception as e:
            st.warning(f"Email alert failed: {e}")

    elif risk > 30:
        alert_placeholder.warning("⚠ Suspicious Movement")

    else:
        alert_placeholder.success("✅ SAFE")

    time.sleep(1)