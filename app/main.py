"""
Enhanced API Backend
=====================
FastAPI app integrating:
  - Live GPS ingestion + risk scoring
  - Alert dispatch
  - Movement history
  - Routine learning
  - Map generation
  - Model evaluation
  - Multi-person dashboard
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, BackgroundTasks # pyre-ignore[21]
from fastapi.middleware.cors import CORSMiddleware # pyre-ignore[21]
from fastapi.staticfiles import StaticFiles # pyre-ignore[21]
from pydantic import BaseModel # pyre-ignore[21]
from typing import Optional
import pandas as pd # pyre-ignore[21]
import os
from pathlib import Path
from datetime import datetime

# Local modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.data_generator import generate_dataset, HOME, SAFE_ZONE_RADIUS_KM # pyre-ignore[21]
from src.risk_scorer import RiskScorer, evaluate_model # pyre-ignore[21]
from src.alerts import AlertSystem # pyre-ignore[21]
from src.map_visualizer import build_live_tracking_map, build_heatmap, build_history_map # pyre-ignore[21]
from src.routine_learner import RoutineLearner, MovementHistoryAnalyzer # pyre-ignore[21]
from src.wearable_simulator import get_or_create_devices, get_all_device_status # pyre-ignore[21]

app = FastAPI(title="AI Missing Person Drift Detection", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global state ────────────────────────────────────────────────────────────
scorer   = RiskScorer()
alerts   = AlertSystem()
learner  = RoutineLearner()
analyzer = MovementHistoryAnalyzer()

# In-memory GPS buffer (replace with DB in production)
_gps_buffer: list[dict] = []
_df_cache: Optional[pd.DataFrame] = None

# Owner settings file
OWNER_SETTINGS_PATH = Path("data/owner_settings.json")

def _load_owner_settings() -> dict:
    if OWNER_SETTINGS_PATH.exists():
        import json
        return json.loads(OWNER_SETTINGS_PATH.read_text())
    return {"phone": "", "email": ""}

def _save_owner_settings(settings: dict):
    import json
    OWNER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    OWNER_SETTINGS_PATH.write_text(json.dumps(settings, indent=2))

# Track which persons already had emergency alerts sent (prevents spam)
_emergency_sent: set = set()


def _get_df() -> pd.DataFrame:
    global _df_cache
    if _df_cache is None or len(_df_cache) == 0:
        # Load or generate dataset
        csv_path = Path("data/gps_dataset.csv")
        if csv_path.exists():
            _df_cache = pd.read_csv(csv_path, parse_dates=["timestamp"])
        else:
            _df_cache = generate_dataset(n_days=30, n_persons=3)
        # Fit routine learner on historic data
        learner.fit(_df_cache)
    return _df_cache

import time
SIMULATION_START_TIME = time.time()

def _get_live_df() -> pd.DataFrame:
    """Return a progressively growing slice of df to simulate live streaming."""
    df = _get_df()
    elapsed_seconds = time.time() - SIMULATION_START_TIME
    steps = int(elapsed_seconds * 1.0) # 1 row per second
    
    counts = df["person_id"].value_counts()
    if counts.empty:
        return df
        
    max_per_person = counts.min()
    if max_per_person <= 50:
        return df
        
    end_idx = (steps % (max_per_person - 50)) + 50
    live_df = df.groupby("person_id").head(end_idx).copy()
    
    # Calculate live speed for the last recorded step
    from src.data_generator import haversine # pyre-ignore[21]
    for pid in live_df["person_id"].unique():
        mask = live_df["person_id"] == pid
        sub = live_df[mask]
        if len(sub) >= 2:
            prev = sub.iloc[-2]
            curr = sub.iloc[-1]
            dist = haversine(prev["latitude"], prev["longitude"], curr["latitude"], curr["longitude"])
            time_hrs = (curr["timestamp"] - prev["timestamp"]).seconds / 3600
            speed = dist / max(time_hrs, 1e-6)
            # Update the last row's speed
            live_df.loc[sub.index[-1], "speed_kmh"] = speed

    return live_df


# ── Pydantic models ─────────────────────────────────────────────────────────

class GPSReading(BaseModel):
    person_id: str
    latitude: float
    longitude: float
    speed_kmh: float = 0.0
    timestamp: Optional[str] = None


class PersonInfo(BaseModel):
    person_id: str
    name: str = ""
    caregiver_phone: str = ""
    caregiver_email: str = ""


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"message": "AI Missing Person Drift Detection v2.0", "status": "running"}


@app.post("/api/gps")
async def ingest_gps(reading: GPSReading, background_tasks: BackgroundTasks):
    """
    Receive a live GPS reading, score it, and dispatch alerts if needed.
    """
    ts = pd.Timestamp(reading.timestamp) if reading.timestamp else pd.Timestamp.now()
    if pd.isna(ts): # type: ignore
        ts = pd.Timestamp.now()
    dt_val = ts.to_pydatetime() # type: ignore
    import datetime
    if not isinstance(dt_val, datetime.datetime):
        raise ValueError("Invalid timestamp")
    
    result = scorer.score(
        lat=reading.latitude,
        lon=reading.longitude,
        speed_kmh=reading.speed_kmh,
        timestamp=dt_val,
    )

    # Append to buffer
    record = {**reading.dict(), "timestamp": str(ts), **result}
    _gps_buffer.append(record)

    # Dispatch alert in background (non-blocking)
    if result["risk_level"] in ("MEDIUM", "HIGH"):
        background_tasks.add_task(
            alerts.send,
            person_id=reading.person_id,
            risk_level=result["risk_level"],
            dist_km=result["distance_from_home_km"],
            lat=reading.latitude,
            lon=reading.longitude,
        )

    return result


@app.get("/api/dashboard")
def dashboard(background_tasks: BackgroundTasks):
    """
    Multi-person monitoring dashboard summary.
    Returns latest risk status for all tracked persons.
    """
    df = _get_live_df()
    persons = df["person_id"].unique()
    summaries = []

    for pid in persons:
        sub = df[df["person_id"] == pid].sort_values(by="timestamp") # type: ignore
        latest = sub.iloc[-1]
        result = scorer.score(
            lat=float(latest["latitude"]),
            lon=float(latest["longitude"]),
            speed_kmh=float(latest.get("speed_kmh", 0)),
            timestamp=pd.to_datetime(latest["timestamp"]).to_pydatetime(),
        )
        summaries.append({
            "person_id":   pid,
            "risk_level":  result["risk_level"],
            "risk_score":  result["composite_score"],
            "dist_km":     result["distance_from_home_km"],
            "speed":       float(latest.get("speed_kmh", 0)),
            "in_safe_zone": result["in_safe_zone"],
            "last_seen":   str(latest["timestamp"]),
            "latitude":    float(latest["latitude"]),
            "longitude":   float(latest["longitude"]),
            "sub_scores":  result["sub_scores"],
        })

        if result["risk_level"] in ("MEDIUM", "HIGH"):
            background_tasks.add_task(
                alerts.send,
                person_id=pid,
                risk_level=result["risk_level"],
                dist_km=result["distance_from_home_km"],
                lat=float(latest["latitude"]),
                lon=float(latest["longitude"]),
            )

        # 🚨 AUTO-EMERGENCY: when risk score hits 100%
        if result["composite_score"] >= 1.0 and pid not in _emergency_sent:
            owner = _load_owner_settings()
            background_tasks.add_task(
                alerts.send_emergency,
                person_id=pid,
                dist_km=result["distance_from_home_km"],
                lat=float(latest["latitude"]),
                lon=float(latest["longitude"]),
                owner_phone=owner.get("phone", ""),
                owner_email=owner.get("email", ""),
            )
            _emergency_sent.add(pid)

    # Initialize wearable simulators for all tracked persons
    for pid in persons:
        get_or_create_devices(str(pid))

    return {
        "persons": summaries,
        "home":    {"lat": HOME[0], "lon": HOME[1]},
        "safe_zone_km": SAFE_ZONE_RADIUS_KM,
        "updated_at": datetime.now().isoformat(),
    }


@app.get("/api/history/{person_id}")
def movement_history(person_id: str, hours: int = 24):
    """Return movement history for a person over the last N hours."""
    df = _get_live_df()
    path_df = analyzer.get_recent_path(df, person_id, hours=hours)
    if path_df.empty:
        raise HTTPException(404, f"No data for {person_id}")
    
    records = path_df.to_dict(orient="records")
    stats   = analyzer.stats_summary(df, person_id)
    freq    = analyzer.frequent_locations(df, person_id)

    return {
        "person_id":          person_id,
        "hours_requested":    hours,
        "path":               records,
        "stats":              stats,
        "frequent_locations": freq,
    }


@app.get("/api/alerts")
def get_alerts(n: int = 20):
    """Return recent alerts."""
    return {"alerts": alerts.get_recent_alerts(n)}


@app.get("/api/map/{map_type}")
def generate_map(map_type: str, person_id: Optional[str] = None):
    """
    Generate and return path to an HTML map.
    map_type: 'live' | 'heatmap' | 'history'
    """
    df = _get_df()
    # Score all records for map coloring
    df = df.copy()
    df["risk_level"] = "LOW"
    df["distance_from_home_km"] = 0.0

    if map_type == "live":
        path = build_live_tracking_map(df, "frontend/map_live.html")
    elif map_type == "heatmap":
        if person_id:
            df_p = df[df["person_id"] == person_id]
        else:
            df_p = df
        if isinstance(df_p, pd.Series):
            df_p = df_p.to_frame()
        path = build_heatmap(df_p, "frontend/map_heatmap.html")
    elif map_type == "history":
        if not person_id:
            person_id = str(df["person_id"].iloc[0])
        path = build_history_map(df, person_id, "frontend/map_history.html")
    else:
        raise HTTPException(400, "map_type must be: live | heatmap | history")

    return {"map_path": path, "status": "generated"}


@app.get("/api/evaluate")
def model_evaluation():
    """Run model evaluation and return precision, recall, accuracy, F1."""
    df = _get_df()
    if "is_anomaly" not in df.columns:
        raise HTTPException(400, "Dataset missing 'is_anomaly' ground truth column")

    # Score a representative slice so we get actual anomalies
    scorer_eval = RiskScorer()
    sample_size = min(1000, len(df))
    df_sample = df.sample(n=sample_size, random_state=42)
    df_scored = scorer_eval.score_dataframe(df_sample)
    metrics = evaluate_model(df_scored)
    return metrics


@app.get("/api/routine/{person_id}")
def get_routine(person_id: str):
    """Return learned daily routine summary for a person."""
    df = _get_df()
    summary = learner.get_routine_summary(person_id)
    if not summary:
        raise HTTPException(404, f"No routine learned for {person_id}")
    return {"person_id": person_id, "routine": summary}


@app.get("/api/heatmap-data/{person_id}")
def get_heatmap_data(person_id: str):
    """Return heatmap data points for frontend chart rendering."""
    df = _get_df()
    data = analyzer.hourly_heatmap_data(df, person_id)
    return {"person_id": person_id, "heatmap_points": data[:1000]}



# ── Wearable Device Endpoints ────────────────────────────────────────────────

@app.get("/api/wearable/status")
def wearable_status():
    """Return current telemetry from all simulated wearable devices."""
    devices = get_all_device_status()
    return {"devices": devices, "updated_at": datetime.now().isoformat()}


class OwnerSettings(BaseModel):
    phone: str = ""
    email: str = ""

@app.post("/api/settings/owner")
def save_owner(settings: OwnerSettings):
    """Save owner contact info for emergency alerts."""
    data = {"phone": settings.phone, "email": settings.email}
    _save_owner_settings(data)
    return {"status": "saved", "settings": data}

@app.get("/api/settings/owner")
def get_owner():
    """Get current owner contact settings."""
    return _load_owner_settings()


# ── Static files (MUST be last – catches all unmatched routes) ───────────────
frontend_dir = Path("react-dashboard/dist")
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory="react-dashboard/dist", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn # pyre-ignore[21]
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
