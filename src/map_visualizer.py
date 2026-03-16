"""
Map Visualization Module
=========================
Generates interactive Folium maps for:
  - Live person location with risk color coding
  - Safe zone circle overlay
  - Movement path (last 24h / all time)
  - Heatmap of frequent locations
  - Multi-person monitoring dashboard
"""

import folium
from folium.plugins import HeatMap, AntPath, MarkerCluster
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

HOME = (17.4200, 78.3500)
SAFE_ZONE_RADIUS_M = 500   # metres for folium circle

RISK_COLORS = {
    "LOW":    "#22c55e",
    "MEDIUM": "#f59e0b",
    "HIGH":   "#ef4444",
}


def build_live_tracking_map(df: pd.DataFrame,
                             output_path: str = "frontend/map_live.html",
                             last_n_hours: int = 24) -> str:
    """
    Build a live tracking map for all persons in df.
    Shows: safe zone, current position, path, risk level badge.
    """
    m = folium.Map(location=[float(HOME[0]), float(HOME[1])], zoom_start=15, # type: ignore
                   tiles="CartoDB positron")

    # ── Safe zone circle ────────────────────────────────────────────────────
    folium.Circle(
        location=HOME,
        radius=SAFE_ZONE_RADIUS_M,
        color="#22c55e",
        weight=2,
        fill=True,
        fill_color="#22c55e",
        fill_opacity=0.08,
        tooltip="Safe Zone (500m radius)",
    ).add_to(m)

    # Home marker
    folium.Marker(
        location=HOME,
        icon=folium.Icon(color="green", icon="home", prefix="fa"),
        tooltip="Home",
    ).add_to(m)

    if df.empty:
        return output_path
    
    max_ts = df["timestamp"].max()
    cutoff = max_ts - pd.Timedelta(hours=last_n_hours)
    
    colors = ["blue", "red", "purple", "orange", "darkred"]
    for idx, person_id in enumerate(df["person_id"].unique()):
        sub = df[
            (df["person_id"] == person_id) &
            (df["timestamp"] >= cutoff)
        ].sort_values(by="timestamp") # type: ignore

        if sub.empty:
            continue

        # Movement path
        path_coords = list(zip(sub["latitude"], sub["longitude"]))
        if len(path_coords) >= 2:
            AntPath(
                locations=path_coords,
                color=colors[idx % len(colors)],
                weight=3,
                opacity=0.7,
                delay=1000,
                tooltip=f"{person_id} movement path",
            ).add_to(m)

        # Latest position
        latest = sub.iloc[-1]
        risk_level = latest.get("risk_level", "LOW")
        risk_color = RISK_COLORS.get(risk_level, "#888")
        dist_km = latest.get("distance_from_home_km", 0)

        popup_html = f"""
        <div style='font-family:sans-serif;min-width:200px'>
          <h4 style='margin:0 0 8px'>{person_id}</h4>
          <span style='background:{risk_color};color:#fff;padding:3px 10px;
                border-radius:12px;font-size:12px;font-weight:600'>
            {risk_level} RISK
          </span>
          <table style='margin-top:10px;font-size:13px;width:100%'>
            <tr><td><b>Distance from home</b></td><td>{dist_km:.2f} km</td></tr>
            <tr><td><b>Last seen</b></td>
                <td>{pd.to_datetime(latest['timestamp']).strftime('%H:%M:%S')}</td></tr>
            <tr><td><b>Speed</b></td>
                <td>{latest.get('speed_kmh', 0):.1f} km/h</td></tr>
          </table>
        </div>
        """

        folium.CircleMarker(
            location=(latest["latitude"], latest["longitude"]),
            radius=10,
            color=risk_color,
            fill=True,
            fill_color=risk_color,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{person_id} – {risk_level}",
        ).add_to(m)

    # ── Legend ──────────────────────────────────────────────────────────────
    legend_html = """
    <div style='position:fixed;bottom:30px;left:30px;z-index:1000;
                background:#fff;padding:14px 18px;border-radius:10px;
                box-shadow:0 2px 12px rgba(0,0,0,0.15);font-family:sans-serif'>
      <p style='margin:0 0 8px;font-weight:600;font-size:14px'>Risk Level</p>
      <p style='margin:4px 0'><span style='color:#22c55e'>●</span> LOW</p>
      <p style='margin:4px 0'><span style='color:#f59e0b'>●</span> MEDIUM</p>
      <p style='margin:4px 0'><span style='color:#ef4444'>●</span> HIGH</p>
      <p style='margin:8px 0 0;font-size:12px;color:#888'>Updated live</p>
    </div>
    """
    m.get_root().add_child(folium.Element(legend_html)) # type: ignore

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)
    return output_path


def build_heatmap(df: pd.DataFrame,
                  output_path: str = "frontend/map_heatmap.html") -> str:
    """Generate a heatmap of frequent locations for a person."""
    m = folium.Map(location=[float(HOME[0]), float(HOME[1])], zoom_start=15, # type: ignore
                   tiles="CartoDB dark_matter")

    heat_data = [[r["latitude"], r["longitude"]]
                 for _, r in df.iterrows()]
    HeatMap(heat_data, radius=12, blur=18, min_opacity=0.4).add_to(m)

    folium.Marker(
        location=HOME,
        icon=folium.Icon(color="white", icon="home", prefix="fa"),
        tooltip="Home",
    ).add_to(m)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)
    return output_path


def build_history_map(df: pd.DataFrame,
                      person_id: str,
                      output_path: str = "frontend/map_history.html") -> str:
    """
    Show full movement history for one person with color-coded risk segments.
    """
    sub = df[df["person_id"] == person_id].sort_values(by="timestamp") # type: ignore
    if sub.empty:
        raise ValueError(f"No data for person {person_id}")

    m = folium.Map(location=[float(HOME[0]), float(HOME[1])], zoom_start=14, # type: ignore
                   tiles="CartoDB positron")

    # Safe zone
    folium.Circle(HOME, radius=SAFE_ZONE_RADIUS_M,
                  color="#22c55e", weight=1.5,
                  fill=True, fill_opacity=0.07).add_to(m)

    # Color-coded path segments
    for i in range(1, len(sub)):
        prev = sub.iloc[i-1]
        curr = sub.iloc[i]
        risk = curr.get("risk_level", "LOW")
        folium.PolyLine(
            locations=[(float(prev["latitude"]), float(prev["longitude"])), # type: ignore
                       (float(curr["latitude"]), float(curr["longitude"]))], # type: ignore
            color=RISK_COLORS.get(risk, "#888"),
            weight=3,
            opacity=0.8,
        ).add_to(m)

    # Anomaly markers
    anomalies = sub[sub.get("is_anomaly", pd.Series(False, index=sub.index)) == True]
    for _, row in anomalies.iterrows():
        folium.Marker(
            location=(float(row["latitude"]), float(row["longitude"])), # type: ignore
            icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa"),
            tooltip=f"Anomaly at {pd.to_datetime(row['timestamp']).strftime('%H:%M')}",
        ).add_to(m)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)
    return output_path
