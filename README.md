# 🧭 AI Missing Person Drift Detection — v2.0

Real-time GPS tracking and anomaly detection system for monitoring vulnerable individuals (elderly, Alzheimer's patients, children) with multi-factor risk scoring, alert notifications, and interactive map visualization.

---

## ✨ What's New in v2.0

| Feature | Status | Details |
|---|---|---|
| 🗺️ Live Map Tracking | ✅ | Folium + Leaflet with safe zone overlay |
| 🚨 Alert System | ✅ | Email (SMTP) + SMS (Twilio) + In-app |
| 📊 Movement History | ✅ | 24h path, heatmap, frequent locations |
| 🧮 Enhanced Risk Scoring | ✅ | 4-factor weighted formula |
| 🤖 Synthetic GPS Dataset | ✅ | Realistic wandering simulation |
| 📈 Model Evaluation | ✅ | Precision, Recall, Accuracy, F1 |
| 🔄 Routine Learning | ✅ | Daily pattern baseline per person |
| 👥 Multi-Person Dashboard | ✅ | Monitor multiple people simultaneously |

---

## 🏗️ Project Structure

```
ai-missing-person-drift-detection/
├── src/
│   ├── data_generator.py      # Synthetic GPS dataset (Feature 5)
│   ├── risk_scorer.py         # Multi-factor risk scoring (Feature 4)
│   ├── alerts.py              # Email + SMS alert system (Feature 2)
│   ├── map_visualizer.py      # Folium map generation (Feature 1)
│   └── routine_learner.py     # Pattern learning + history (Features 3 & ⭐1)
├── app/
│   └── main.py                # FastAPI backend
├── frontend/
│   └── index.html             # Multi-person monitoring dashboard
├── data/
│   └── gps_dataset.csv        # Generated synthetic GPS data
├── models/
│   └── routine_model.json     # Learned daily routine model
└── requirements.txt
```

---

## 📡 Feature 1: Real Map Visualization

The system uses **Folium** (Python) and **Leaflet.js** (frontend) to render:
- **Live GPS position** of each monitored person (color-coded by risk)
- **Safe zone circle** (500m radius from home)
- **Movement path** (last 24h animated trail)
- **Heatmap** of frequently visited locations
- **Anomaly markers** where drift was detected

**API endpoint:** `GET /api/map/live` — generates `frontend/map_live.html`

---

## 🚨 Feature 2: Alert System

Three notification channels, all with cooldown protection (15 min between repeat alerts):

### Email (SMTP / Gmail)
Set these environment variables:
```env
ALERT_EMAIL_TO=caregiver@example.com
ALERT_EMAIL_FROM=noreply@yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your_app_password
```

### SMS (Twilio)
```bash
pip install twilio
```
```env
TWILIO_SID=ACxxxxxxxxxxxxxxxxxx
TWILIO_TOKEN=your_auth_token
TWILIO_FROM=+1XXXXXXXXXX
TWILIO_TO=+91XXXXXXXXXX
```

### In-App
Alerts are always logged to `data/alerts.json` and served via `GET /api/alerts`.

**Example alert:**
```
⚠️ ALERT – HIGH RISK
Person: P002
Distance from home: 1.82 km
Location: 17.43571, 78.37022
Maps: https://maps.google.com/?q=17.43571,78.37022
```

---

## 📊 Feature 3: Movement History

`GET /api/history/{person_id}?hours=24` returns:
- Full GPS path for the last N hours
- Movement statistics (total distance, avg speed)
- Top 5 frequent locations (K-Means clustering)
- Time in safe zone percentage

Heatmap data: `GET /api/heatmap-data/{person_id}`

---

## 🧮 Feature 4: Enhanced Risk Scoring

```
Risk Score = 0.40 × distance_score
           + 0.25 × speed_anomaly_score
           + 0.20 × pattern_deviation_score
           + 0.15 × time_of_day_score
```

| Sub-score | Description |
|---|---|
| **distance_score** | 0 inside safe zone → 1 at 1.5km+ from home |
| **speed_anomaly_score** | 0 at walking speed → 1 at running/vehicle speed |
| **pattern_deviation_score** | 0 at usual location for this hour → 1 at novel location |
| **time_of_day_score** | 1.0 between 10 PM – 6 AM, 0.4 at twilight, 0 daytime |

**Risk levels:**
- `LOW` — score < 0.35
- `MEDIUM` — score 0.35 – 0.65
- `HIGH` — score > 0.65

---

## 🤖 Feature 5: Synthetic GPS Dataset

Since real GPS data of vulnerable individuals is **private and protected**, this project uses a **synthetic GPS simulator** designed to mimic real-world behavior:

**What it simulates:**
- Realistic daily routines: `home → park → home → market → home`
- GPS sensor noise (±15m Gaussian noise, realistic for consumer devices)
- **Wandering/drift events** (injected at configurable rate, default 20%)
- Multiple persons with independent movement patterns
- Realistic walking speeds (2–5 km/h)

**Research basis:** The simulation is inspired by published research on GPS wandering patterns in dementia patients (Algase et al., 2004) and uses movement statistics from real-world studies.

**Dataset fields:**
```
person_id, timestamp, latitude, longitude, activity,
is_anomaly, dist_from_home_km, in_safe_zone, hour, day_of_week, speed_kmh
```

Generate the dataset:
```bash
python src/data_generator.py
# Creates: data/gps_dataset.csv (30 days × 3 persons ≈ 15,000 records)
```

---

## 📈 Feature 6: Model Evaluation

```
GET /api/evaluate
```

Returns:
```json
{
  "precision": 0.847,
  "recall":    0.823,
  "accuracy":  0.891,
  "f1_score":  0.835,
  "confusion_matrix": { "tp": 412, "fp": 74, "fn": 88, "tn": 1896 }
}
```

**Metrics explained:**
- **Precision** = of all HIGH/MEDIUM alerts, what % were actual anomalies?
- **Recall** = of all true anomalies, what % did the system catch?
- **F1** = harmonic mean — balances precision and recall

---

## ⭐ Bonus Feature: Routine Learning

The system automatically learns each person's normal daily routine:
```
GET /api/routine/P001
```
```json
{
  "07:00": { "usual_location": [17.42013, 78.34987], "observations": 28 },
  "10:00": { "usual_location": [17.41802, 78.34793], "observations": 25 },
  ...
}
```
When a person is in an unusual location for their time of day, the `pattern_deviation_score` increases proportionally.

---

## 🚀 Getting Started

```bash
# 1. Clone and install
git clone https://github.com/vasanth-chinnam/ai-missing-person-drift-detection
cd ai-missing-person-drift-detection
pip install -r requirements.txt

# 2. Generate synthetic dataset
python src/data_generator.py

# 3. Configure alerts (optional)
cp .env.example .env
# Edit .env with your SMTP / Twilio credentials

# 4. Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Open the dashboard
open http://localhost:8000
```

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/gps` | Ingest a live GPS reading |
| GET | `/api/dashboard` | All persons: risk status |
| GET | `/api/history/{id}` | Movement history |
| GET | `/api/alerts` | Recent alerts |
| GET | `/api/map/{type}` | Generate map (live/heatmap/history) |
| GET | `/api/evaluate` | Model evaluation metrics |
| GET | `/api/routine/{id}` | Learned daily routine |
| GET | `/api/heatmap-data/{id}` | Heatmap data points |

---

## 🏗️ System Design

```
GPS Device / Simulator
        │
        ▼
  POST /api/gps
        │
   ┌────┴────────────────┐
   │   Risk Scorer       │  ← distance + speed + pattern + time
   └────┬────────────────┘
        │
   ┌────┴────────────────┐
   │   Alert System      │  ← Email / SMS / In-app
   └────┬────────────────┘
        │
   ┌────┴────────────────┐
   │   Map Visualizer    │  ← Folium HTML maps
   └─────────────────────┘
        │
   Dashboard (Leaflet.js)
```
