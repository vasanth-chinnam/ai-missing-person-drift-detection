import sys
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables (mostly for local use)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Add the root directory to sys.path so that 'src' can be imported natively
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify, request, send_from_directory # pyre-ignore[21]
from flask_cors import CORS # pyre-ignore[21]
import pandas as pd # pyre-ignore[21]
import joblib # pyre-ignore[21]

from src.geofence import check_geofence, SAFE_LOCATION, SAFE_RADIUS # pyre-ignore[21]
from src.risk_engine import calculate_risk, calculate_risk_from_distance # pyre-ignore[21]
from src.trajectory_predictor import detect_route_deviation # pyre-ignore[21]
from src.notification import send_sms_alert # pyre-ignore[21]

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# ── Load data & models ──────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "gps_data.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "anomaly_model.pkl")

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("WARNING: Supabase credentials not found in env.")
    supabase = None

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

# Auth token store (in-memory for simplicity)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "missing2026")
active_tokens: set = set()

alert_history = []


def _compute_risk_row(row, idx):
    """Compute risk score and metadata for a single GPS row."""
    features = [[row["speed"], row["heart_rate"]]]
    feat_df = pd.DataFrame(features, columns=["speed", "heart_rate"]) # type: ignore
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
    folder = app.static_folder or "../frontend"
    return send_from_directory(folder, "index.html")


@app.route("/api/login", methods=["POST"])
def login():
    body = request.json or {}
    password = body.get("password", "")
    if password == ADMIN_PASSWORD:
        token = str(uuid.uuid4())
        active_tokens.add(token)
        return jsonify({"token": token})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    active_tokens.discard(token)
    return jsonify({"status": "logged out"})


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
    avg_risk = float(round(sum(p["risk"] for p in computed) / total, 1)) if total else 0.0
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
    global next_person_id
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
    import src.risk_engine as re_module # pyre-ignore[21]
    body = request.json
    geofence_config["lat"] = body.get("lat", geofence_config["lat"])
    geofence_config["lon"] = body.get("lon", geofence_config["lon"])
    geofence_config["radius"] = body.get("radius", geofence_config["radius"])
    # Sync the live risk engine so new GPS calculations use the updated home
    re_module.HOME_LOCATION = (geofence_config["lat"], geofence_config["lon"])
    return jsonify(geofence_config)


# ── Live GPS Endpoints ───────────────────────────────────────

@app.route("/api/location", methods=["POST"])
def receive_location():
    """
    Receive live GPS from a phone / Postman / wearable device.
    Body: { "lat": float, "lon": float, "speed": float (optional), "heart_rate": int (optional) }
    """
    data = request.json
    if not data or "lat" not in data or "lon" not in data:
        return jsonify({"error": "lat and lon are required"}), 400

    lat = float(data["lat"])
    lon = float(data["lon"])
    speed = float(data.get("speed", 0))
    heart_rate = int(data.get("heart_rate", 72))
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Compute real km-based risk
    risk_result = calculate_risk_from_distance(lat, lon)

    person_id = data.get("person_id", "P001")

    # 🚨 Fire SMS alert if wandering detected
    if risk_result["risk_level"] == "critical":
        send_sms_alert(person_id, risk_result["distance_km"], risk_result["distance_label"])

    if supabase:
        try:
            supabase.table("locations").insert({
                "latitude": lat,
                "longitude": lon,
                "person_id": person_id
            }).execute()
        except Exception as e:
            print(f"Supabase error: {e}")

    return jsonify({
        "status": "success",
        "timestamp": ts,
        "latitude": lat,
        "longitude": lon,
        "speed": speed,
        "heart_rate": heart_rate,
        **risk_result,
    })


@app.route("/api/live-data")
def get_live_data():
    """
    Returns all live GPS readings with computed risk scores.
    The frontend polls this endpoint every few seconds.
    """
    if not supabase:
        return jsonify([])

    try:
        # Fetch more locations (up to 300) to ensure we get a good trail for multiple users
        response = supabase.table("locations").select("*").order("created_at", desc=True).limit(300).execute()
        data = response.data
        if data:
            # Reverse the list so it's OLD->NEW (for the map path trail in frontend)
            data.reverse()
    except Exception as e:
        print(f"Supabase error reading: {e}")
        return jsonify([])

    if not data:
        return jsonify([])

    results = []
    for idx, row in enumerate(data):
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        risk_result = calculate_risk_from_distance(lat, lon)
        
        # We synthesize speed and heart_rate since we don't store them in DB
        # This keeps the dashboard UI fully packed with data
        results.append({
            "index": idx,
            "person_id": row.get("person_id", "P001"),
            "timestamp": row.get("created_at", ""),
            "latitude": lat,
            "longitude": lon,
            "speed": 4.5, # Placeholder speed
            "heartRate": 80, # Placeholder heart rate
            "risk": risk_result["risk_score"],
            "level": risk_result["risk_level"],
            "distance_km": risk_result["distance_km"],
            "distance_label": risk_result["distance_label"],
        })

    return jsonify(results)


@app.route("/api/history/<person_id>")
def get_person_history(person_id):
    """Returns the full historical path for a specific person."""
    if not supabase:
        return jsonify({"path": []})
    try:
        response = (
            supabase.table("locations")
            .select("latitude, longitude, created_at")
            .eq("person_id", person_id)
            .order("created_at", desc=False)
            .execute()
        )
        return jsonify({"path": response.data})
    except Exception as e:
        print(f"History fetch error: {e}")
        return jsonify({"path": []})


@app.route("/api/heatmap-data/<person_id>")
def get_heatmap_data(person_id):
    """Returns points formatted for Leaflet.heat intensity layer."""
    if not supabase:
        return jsonify({"heatmap_points": []})
    try:
        response = (
            supabase.table("locations")
            .select("latitude, longitude")
            .eq("person_id", person_id)
            .execute()
        )
        # Intensity = 1 for each point
        points = [[p["latitude"], p["longitude"], 1.0] for p in response.data]
        return jsonify({"heatmap_points": points})
    except Exception as e:
        print(f"Heatmap fetch error: {e}")
        return jsonify({"heatmap_points": []})


@app.route("/api/live-reset", methods=["POST"])
def reset_live_data():
    """Clear all live GPS data (for demo resets)."""
    if supabase:
        try:
            # Delete all locations from the table
            supabase.table("locations").delete().neq("id", -1).execute()
        except Exception as e:
            print(f"Supabase error resetting: {e}")
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    print("\n  🚀  API running at http://localhost:8080")
    print("  📡  Frontend at   http://localhost:8080\n")
    # Using port 8080 as it's often more reliable than 5000
    app.run(debug=True, port=8080, host="0.0.0.0")
