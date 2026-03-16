"""
Daily Routine Learning & Movement History
==========================================
Learns normal movement patterns for each person and detects deviations.

Approach:
  1. Build a 24-hour "home profile" per person: (hour → cluster of lat/lon positions)
  2. At inference time: compare new position to expected cluster for that hour
  3. Score deviation using Mahalanobis distance from cluster centroid

Also provides movement history analysis:
  - Last N hours path
  - Frequent location clustering (K-Means)
  - Per-hour location heatmap grid
"""

import numpy as np
import pandas as pd
import json
import math
from collections import defaultdict
from pathlib import Path


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


class RoutineLearner:
    """
    Learns daily routine patterns from GPS history.
    Stores: for each (person, hour) → mean lat/lon + std deviation
    """

    def __init__(self):
        # {person_id: {hour: [(lat, lon), ...]}}
        self._hourly_positions: dict = defaultdict(lambda: defaultdict(list))
        self._hourly_stats: dict = {}   # computed after fit()

    def fit(self, df: pd.DataFrame):
        """Learn patterns from historical GPS data."""
        df = df.copy()
        df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

        for _, row in df.iterrows():
            pid  = row["person_id"]
            hour = row["hour"]
            self._hourly_positions[pid][hour].append(
                (row["latitude"], row["longitude"])
            )

        # Compute per-person, per-hour statistics
        self._hourly_stats = {}
        for pid, hours in self._hourly_positions.items():
            self._hourly_stats[pid] = {}
            for hour, positions in hours.items():
                lats = [p[0] for p in positions]
                lons = [p[1] for p in positions]
                self._hourly_stats[pid][hour] = {
                    "mean_lat":  float(np.mean(lats)),
                    "mean_lon":  float(np.mean(lons)),
                    "std_lat":   float(np.std(lats)) + 1e-6,
                    "std_lon":   float(np.std(lons)) + 1e-6,
                    "n_samples": len(positions),
                }
        return self

    def deviation_score(self, person_id: str, lat: float, lon: float,
                        hour: int) -> float:
        """
        Return [0, 1] deviation score for a new position.
        0 = typical for this hour, 1 = highly unusual.
        """
        stats = self._hourly_stats.get(person_id, {}).get(hour)
        if stats is None or stats["n_samples"] < 5:
            return 0.0   # insufficient history

        dist = haversine(lat, lon, stats["mean_lat"], stats["mean_lon"])
        # Typical std in km (~1 std = ~80m)
        typical_std_km = 0.08
        return float(min(dist / (3 * typical_std_km), 1.0))

    def get_routine_summary(self, person_id: str) -> dict:
        """Return human-readable routine summary for a person."""
        stats = self._hourly_stats.get(person_id, {})
        summary = {}
        for hour, s in sorted(stats.items()):
            summary[f"{hour:02d}:00"] = {
                "usual_location": (round(s["mean_lat"], 5), round(s["mean_lon"], 5)),
                "observations":   s["n_samples"],
            }
        return summary

    def save(self, path: str = "models/routine_model.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._hourly_stats, f, indent=2)

    def load(self, path: str = "models/routine_model.json"):
        with open(path) as f:
            raw = json.load(f)
        # JSON keys are strings; convert hour keys back to int
        self._hourly_stats = {
            pid: {int(h): s for h, s in hours.items()}
            for pid, hours in raw.items()
        }
        return self


class MovementHistoryAnalyzer:
    """Analyse movement history: recent path, frequent locations, heatmap data."""

    def get_recent_path(self, df: pd.DataFrame, person_id: str,
                         hours: int = 24) -> pd.DataFrame:
        """Return GPS rows from the last N hours for a person."""
        if df.empty:
            return df
        max_ts = df["timestamp"].max()
        cutoff = max_ts - pd.Timedelta(hours=hours)
        return (df[(df["person_id"] == person_id) &
                   (df["timestamp"] >= cutoff)]
                .sort_values(by="timestamp")) # type: ignore

    def frequent_locations(self, df: pd.DataFrame, person_id: str,
                           n_clusters: int = 5) -> list:
        """
        Use simple K-Means to find N frequent location clusters.
        Returns list of {lat, lon, visit_count, label}.
        """
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            return []

        sub = df[df["person_id"] == person_id][["latitude", "longitude"]].dropna() # type: ignore
        if len(sub) < n_clusters:
            return []

        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10) # type: ignore
        km.fit(sub)
        labels, counts = np.unique(km.labels_, return_counts=True) # type: ignore

        results = []
        for i, (lbl, cnt) in enumerate(zip(labels, counts)):
            center = km.cluster_centers_[lbl]
            results.append({
                "cluster_id":   int(lbl),
                "latitude":     round(float(center[0]), 5), # type: ignore
                "longitude":    round(float(center[1]), 5), # type: ignore
                "visit_count":  int(cnt),
                "label":        f"Location {i+1}",
            })
        return sorted(results, key=lambda x: -x["visit_count"])

    def hourly_heatmap_data(self, df: pd.DataFrame,
                             person_id: str) -> list[dict]:
        """
        Return heatmap data: list of {hour, lat, lon, weight}
        for use with Folium HeatMapWithTime or Plotly.
        """
        sub = df[df["person_id"] == person_id].copy()
        sub["hour"] = pd.to_datetime(sub["timestamp"]).dt.hour # type: ignore
        result = []
        for _, row in sub.iterrows():
            result.append({
                "hour":      int(row["hour"]),
                "latitude":  float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "weight":    1.0,
            })
        return result

    def stats_summary(self, df: pd.DataFrame, person_id: str) -> dict:
        """Overall movement statistics for a person."""
        sub = df[df["person_id"] == person_id].sort_values(by="timestamp") # type: ignore
        if sub.empty:
            return {}

        total_dist = sum(
            haversine(sub.iloc[i-1]["latitude"], sub.iloc[i-1]["longitude"],
                      sub.iloc[i]["latitude"],   sub.iloc[i]["longitude"])
            for i in range(1, len(sub))
        )
        return {
            "person_id":          person_id,
            "total_records":      len(sub),
            "date_range": [
                str(sub["timestamp"].min()),
                str(sub["timestamp"].max()),
            ],
            "total_distance_km":  round(float(total_dist), 2), # type: ignore
            "avg_speed_kmh":      round(float(sub["speed_kmh"].mean()), 2) if "speed_kmh" in sub else None, # type: ignore
            "anomaly_count":      int(sub["is_anomaly"].sum()) if "is_anomaly" in sub else None,
            "time_in_safe_zone_pct": round(
                float(sub["in_safe_zone"].mean()) * 100, 1
            ) if "in_safe_zone" in sub else None, # type: ignore
        }
