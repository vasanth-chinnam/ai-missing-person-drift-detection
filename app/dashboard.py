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

    row = df.iloc[i]

    live_data = df.iloc[:i+1]

    map_placeholder.map(live_data.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat","lon"]])

    features = [[row["latitude"], row["longitude"]]]

    prediction = model.predict(features)

    outside, distance = check_geofence(row["latitude"], row["longitude"])

    route_deviation = detect_route_deviation(i)

    risk = calculate_risk(prediction, outside, route_deviation)

    risk_placeholder.write(f"Risk Score: {risk}/100")

    if prediction == -1 or outside or route_deviation:

        alert_placeholder.error("⚠ WANDERING RISK DETECTED")

    else:

        alert_placeholder.success("SAFE")

    time.sleep(1)