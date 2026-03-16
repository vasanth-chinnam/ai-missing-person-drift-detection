"""
Enhanced Risk Scoring Engine
=============================
Multi-factor weighted risk scoring system for missing person drift detection.

Risk Score Formula:
  risk = 0.40 * distance_score
       + 0.25 * speed_anomaly_score
       + 0.20 * pattern_deviation_score
       + 0.15 * time_of_day_score

Each sub-score is normalised to [0, 1] before weighting.
Final risk is mapped to: LOW (<0.35) | MEDIUM (0.35–0.65) | HIGH (>0.65)
"""

import numpy as np
import pandas as pd
import math
import json
from datetime import datetime


# ── Constants ──────────────────────────────────────────────────────────────
HOME = (17.4200, 78.3500)
SAFE_ZONE_KM   = 0.5      # Radius considered safe
HIGH_RISK_KM   = 1.5      # Distance that gives max distance score
MAX_NORMAL_SPEED_KMH = 6  # Walking speed; above this is anomalous
NIGHT_HOURS    = list(range(22, 24)) + list(range(0, 6))  # 10 PM – 6 AM

# ── Weights (must sum to 1.0) ───────────────────────────────────────────────
W_DISTANCE  = 0.40
W_SPEED     = 0.25
W_PATTERN   = 0.20
W_TIME      = 0.15


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


class RiskScorer:
    """
    Computes risk scores for GPS readings.
    
    Parameters
    ----------
    home : tuple (lat, lon)  – home location anchor
    safe_zone_km : float     – safe radius in km
    history_window : int     – # recent readings used for pattern baseline
    """

    def __init__(self, home=HOME, safe_zone_km=SAFE_ZONE_KM, history_window=50):
        self.home = home
        self.safe_zone_km = safe_zone_km
        self.history_window = history_window
        self._location_history: list = []   # (lat, lon, hour)

    # ── Sub-score methods ──────────────────────────────────────────────────

    def distance_score(self, lat, lon) -> float:
        """
        0.0 = within safe zone
        1.0 = at HIGH_RISK_KM or beyond
        """
        dist = haversine(lat, lon, self.home[0], self.home[1])
        if dist <= self.safe_zone_km:
            return 0.0
        return min((dist - self.safe_zone_km) / (HIGH_RISK_KM - self.safe_zone_km), 1.0)

    def speed_anomaly_score(self, speed_kmh: float) -> float:
        """
        0.0 = stationary or normal walking speed
        1.0 = very high speed (vehicle? lost? running?)
        Also flags unusually fast speed as potentially disoriented running.
        """
        if speed_kmh <= MAX_NORMAL_SPEED_KMH:
            return 0.0
        return min((speed_kmh - MAX_NORMAL_SPEED_KMH) / 10.0, 1.0)

    def pattern_deviation_score(self, lat, lon, hour) -> float:
        """
        Compares current location to learned location history for the same
        hour-of-day. Returns 0 if near historical positions, 1 if novel location.
        Uses a simple nearest-neighbour distance in (lat, lon) space.
        """
        if len(self._location_history) < 10:
            return 0.0   # Not enough history to judge
        
        # Filter history to ±2 hours of current hour
        nearby = [(lt, lg) for lt, lg, h in self._location_history
                  if abs(h - hour) <= 2]
        if not nearby:
            return 0.5   # Uncertain – no data for this time of day

        dists = [haversine(lat, lon, lt, lg) for lt, lg in nearby]
        min_dist = min(dists)
        # Score: 0 if < 100m from a known location, 1 if > 800m
        return min(max(min_dist - 0.1, 0) / 0.7, 1.0)

    def time_of_day_score(self, hour: int) -> float:
        """
        Higher risk at night (10 PM – 6 AM).
        Twilight hours get partial score.
        """
        if hour in NIGHT_HOURS:
            return 1.0
        if hour in [6, 7, 20, 21]:
            return 0.4
        return 0.0

    # ── Main scoring method ────────────────────────────────────────────────

    def score(self, lat: float, lon: float, speed_kmh: float = 0,
              timestamp: datetime = None) -> dict: # type: ignore
        """
        Compute composite risk score for a single GPS reading.
        Returns a dict with all sub-scores and the composite risk level.
        """
        hour = timestamp.hour if timestamp else datetime.now().hour

        d_score = self.distance_score(lat, lon)
        s_score = self.speed_anomaly_score(speed_kmh)
        p_score = self.pattern_deviation_score(lat, lon, hour)
        t_score = self.time_of_day_score(hour)

        composite = (
            W_DISTANCE * d_score +
            W_SPEED    * s_score +
            W_PATTERN  * p_score +
            W_TIME     * t_score
        )
        composite = round(float(min(composite, 1.0)), 4) # type: ignore

        if composite < 0.35:
            level = "LOW"
        elif composite < 0.65:
            level = "MEDIUM"
        else:
            level = "HIGH"

        dist_km = haversine(lat, lon, self.home[0], self.home[1])

        result = {
            "composite_score": composite,
            "risk_level": level,
            "distance_from_home_km": round(float(dist_km), 3), # type: ignore
            "in_safe_zone": dist_km <= self.safe_zone_km,
            "sub_scores": {
                "distance":          round(float(d_score), 4), # type: ignore
                "speed_anomaly":     round(float(s_score), 4), # type: ignore
                "pattern_deviation": round(float(p_score), 4), # type: ignore
                "time_of_day":       round(float(t_score), 4), # type: ignore
            },
            "weights": {
                "distance": W_DISTANCE,
                "speed_anomaly": W_SPEED,
                "pattern_deviation": W_PATTERN,
                "time_of_day": W_TIME,
            },
            "timestamp": str(timestamp),
            "lat": lat,
            "lon": lon,
        }

        # Update location history
        self._location_history.append((lat, lon, hour))
        if len(self._location_history) > self.history_window:
            self._location_history.pop(0)

        return result

    def score_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Batch-score a GPS DataFrame. Expected cols: latitude, longitude, speed_kmh, timestamp."""
        results = []
        for _, row in df.iterrows():
            r = self.score(
                lat=float(row["latitude"]), # type: ignore
                lon=float(row["longitude"]), # type: ignore
                speed_kmh=float(row.get("speed_kmh", 0)), # type: ignore
                timestamp=pd.to_datetime(row["timestamp"]).to_pydatetime() if not pd.isna(row["timestamp"]) else None, # type: ignore
            )
            results.append(r)
        scores_df = pd.DataFrame(results)
        return pd.concat([df.reset_index(drop=True), scores_df], axis=1)


# ── Evaluation metrics ─────────────────────────────────────────────────────

def evaluate_model(df_scored: pd.DataFrame) -> dict:
    """
    Compute precision, recall, accuracy, and F1 for anomaly detection.
    Requires 'is_anomaly' ground truth and 'risk_level' prediction columns.
    """
    y_true = df_scored["is_anomaly"].astype(int)
    y_pred = (df_scored["risk_level"].isin(["HIGH", "MEDIUM"])).astype(int)

    tp = int(((y_true == 1) & (y_pred == 1)).sum()) # type: ignore
    fp = int(((y_true == 0) & (y_pred == 1)).sum()) # type: ignore
    fn = int(((y_true == 1) & (y_pred == 0)).sum()) # type: ignore
    tn = int(((y_true == 0) & (y_pred == 0)).sum()) # type: ignore

    precision = tp / max(tp + fp, 1)
    recall    = tp / max(tp + fn, 1)
    accuracy  = (tp + tn) / len(y_true)
    f1        = 2 * precision * recall / max(precision + recall, 1e-9)

    return {
        "precision":    round(float(precision), 4), # type: ignore
        "recall":       round(float(recall), 4), # type: ignore
        "accuracy":     round(float(accuracy), 4), # type: ignore
        "f1_score":     round(float(f1), 4), # type: ignore
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "total_samples": len(y_true),
        "anomaly_rate":  round(float(y_true.mean()), 4), # type: ignore
    }


if __name__ == "__main__":
    # Quick smoke test
    scorer = RiskScorer()
    
    # Inside safe zone
    r1 = scorer.score(17.420, 78.350, speed_kmh=3, timestamp=datetime(2024, 1, 1, 10, 0))
    print(f"In safe zone: {r1['risk_level']} ({r1['composite_score']})")

    # Far outside, night time
    r2 = scorer.score(17.435, 78.370, speed_kmh=8, timestamp=datetime(2024, 1, 1, 2, 0))
    print(f"Far + night:  {r2['risk_level']} ({r2['composite_score']})")
