import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import joblib
import time
from geopy.distance import geodesic
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
heatmap_data = df[["latitude","longitude"]].values.tolist()

map_center = [df["latitude"].mean(), df["longitude"].mean()]

heat_map = folium.Map(location=map_center, zoom_start=14)

HeatMap(heatmap_data).add_to(heat_map)

st.subheader("Risk Heatmap")

st_folium(heat_map, width=700)

map_placeholder = st.empty()
alert_placeholder = st.empty()
risk_placeholder = st.empty()


for i in range(len(df)):

    live_data = df.iloc[i:i+1]

    map_placeholder.map(live_data[["latitude","longitude"]])

    row = df.iloc[i]

    # anomaly model
    features = pd.DataFrame(
        [[row["speed"],row["heart_rate"]]],
        columns=["speed","heart_rate"]
    )

    prediction = model.predict(features)

    # geofence check
    outside, distance = check_geofence(
        row["latitude"],
        row["longitude"]
    )
    route_deviation = detect_route_deviation(i)

    # risk score
    risk = calculate_risk(
        row["speed"],
        row["heart_rate"],
        outside
    )

    if prediction == -1 or outside or route_deviation:
        alert_placeholder.error("⚠ WANDERING RISK DETECTED")
        location = f"{row['latitude']},{row['longitude']}"
        #send_alert(location, risk)

    else:
        alert_placeholder.success("SAFE")
    if route_deviation:
        st.warning("⚠ ROUTE DEVIATION DETECTED")

    risk_placeholder.write(f"Risk Score: {risk}/100")

    time.sleep(1)