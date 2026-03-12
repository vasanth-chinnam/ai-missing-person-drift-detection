import sys
import os
import json
from datetime import datetime

# Add the root directory to sys.path so that 'src' can be imported natively
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify, request, send_from_directory # pyre-ignore[21]
from flask_cors import CORS # pyre-ignore[21]
import pandas as pd # pyre-ignore[21]
import joblib # pyre-ignore[21]

from src.geofence import check_geofence, SAFE_LOCATION, SAFE_RADIUS # pyre-ignore[21]
from src.risk_engine import calculate_risk # pyre-ignore[21]
from src.trajectory_predictor import detect_route_deviation # pyre-ignore[21]

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# ── Load data & models ──────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "gps_data.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "anomaly_model.pkl")

df = pd.read_csv(DATA_PATH)
model = joblib.load(MODEL_PATH)

# In-memory stores
persons = [
    {"id": 1, "name": "Rajesh Kumar", "age": 72, "condition": "Alzheimer's", "status": "active",
     "lastSeen": "2026-03-12T09:30:00", "avatar": "RK"},
    {"id": 2, "name": "Meera Devi", "age": 68, "condition": "Dementia", "status": "active",
     "lastSeen": "2026-03-12T08:45:00", "avatar": "MD"},
]
next_person_id: int = 3

geofence_config = {
    "lat": SAFE_LOCATION[0],
    "lon": SAFE_LOCATION[1],
    "radius": SAFE_RADIUS,
}

alert_history = []


def _compute_risk_row(row, idx):
    """Compute risk score and metadata for a single GPS row."""
    features = [[row["speed"], row["heart_rate"]]]
    feat_df = pd.DataFrame(features, columns=["speed", "heart_rate"])
    prediction = int(model.predict(feat_df)[0])

    outside, distance = check_geofence(row["latitude"], row["longitude"])
    route_dev = detect_route_deviation(idx)
    risk = calculate_risk(prediction, outside, route_dev)

    level = "critical" if risk >= 60 else ("warning" if risk >= 30 else "safe")
    return {
        "index": idx,
        "timestamp": row.get("timestamp", ""),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "speed": float(row["speed"]),
        "heartRate": float(row["heart_rate"]),
        "risk": risk,
        "level": level,
        "outside": outside,
        "distance": distance, # pyre-ignore[6]: Incompatible parameter type
        "anomaly": prediction == -1,
    }


# Pre-compute all rows
computed = [_compute_risk_row(df.iloc[i], i) for i in range(len(df))]

# Build alert history from high-risk points
for point in computed:
    if point["level"] in ("critical", "warning"):
        alert_history.append({
            "id": len(alert_history) + 1,
            "timestamp": point["timestamp"],
            "latitude": point["latitude"],
            "longitude": point["longitude"],
            "risk": point["risk"],
            "level": point["level"],
            "message": "Wandering risk detected — subject outside safe zone"
            if point["outside"]
            else "Abnormal behavior detected — elevated risk score",
            "personId": 1,
        })


# ── Routes ───────────────────────────────────────────────────────────

@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/gps-data")
def get_gps_data():
    return jsonify(computed)


@app.route("/api/live-status")
def get_live_status():
    idx = int(request.args.get("index", len(computed) - 1))
    idx = max(0, min(idx, len(computed) - 1))
    return jsonify(computed[idx])


@app.route("/api/alerts")
def get_alerts():
    level = request.args.get("level")
    if level:
        filtered = [a for a in alert_history if a["level"] == level]
        return jsonify(filtered)
    return jsonify(alert_history)


@app.route("/api/stats")
def get_stats():
    total = len(computed)
    high = sum(1 for p in computed if p["level"] == "critical")
    warn = sum(1 for p in computed if p["level"] == "warning")
    safe = sum(1 for p in computed if p["level"] == "safe")
    avg_risk = round(float(sum(p["risk"] for p in computed) / total), 1) if total else 0.0
    drift_count = sum(1 for p in computed if p["outside"])

    return jsonify({
        "totalPoints": total,
        "highRisk": high,
        "warning": warn,
        "safe": safe,
        "avgRisk": avg_risk,
        "driftCount": drift_count,
        "alertCount": len(alert_history),
        "activePersons": len(persons),
    })


@app.route("/api/persons", methods=["GET"])
def get_persons(): # type: ignore
    return jsonify(persons)


@app.route("/api/persons", methods=["POST"])
def add_person():
    global next_person_id # pyre-ignore[8]: Not mutable from this scope
    body = request.json
    person = {
        "id": next_person_id,
        "name": body.get("name", "Unknown"),
        "age": body.get("age", 0),
        "condition": body.get("condition", ""),
        "status": "active",
        "lastSeen": datetime.now().isoformat(),
        "avatar": "".join(w[0].upper() for w in body.get("name", "U").split()[:2]),
    }
    persons.append(person)
    next_person_id += 1
    return jsonify(person), 201


@app.route("/api/geofence", methods=["GET"])
def get_geofence():
    return jsonify(geofence_config)


@app.route("/api/geofence", methods=["POST"])
def update_geofence():
    body = request.json
    geofence_config["lat"] = body.get("lat", geofence_config["lat"])
    geofence_config["lon"] = body.get("lon", geofence_config["lon"])
    geofence_config["radius"] = body.get("radius", geofence_config["radius"])
    return jsonify(geofence_config)


if __name__ == "__main__":
    print("\n  🚀  API running at http://localhost:5000")
    print("  📡  Frontend at   http://localhost:5000\n")
    app.run(debug=True, port=5000)
