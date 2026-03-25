from geopy.distance import geodesic

# Safe location (user's actual house)
HOME_LOCATION = (17.3972319, 78.6100460)


def calculate_risk(prediction, outside, route_deviation):
    """
    Original risk calculation (used by the old Flask API).
    Kept for backward compatibility with app/api.py.
    """
    risk = 0

    if prediction == -1:
        risk += 40

    if outside:
        risk += 40

    if route_deviation:
        risk += 20

    return risk


def calculate_distance_km(lat, lon, home=HOME_LOCATION):
    """
    Calculate the geodesic distance in km between
    a GPS point and the home/safe location.
    """
    current = (lat, lon)
    return geodesic(home, current).km


def calculate_risk_from_distance(lat, lon, home=HOME_LOCATION):
    """
    Real km-based risk scoring using geodesic distance.
    Used by the live GPS tracking API.

    Distance thresholds:
        < 100m  (0.1 km) → risk 10  (Safe zone)
        100–300m          → risk 30  (Slight drift)
        300–700m          → risk 60  (Suspicious)
        > 700m  (0.7 km) → risk 90  (Wandering / Critical)

    Returns:
        dict with risk_score, distance_km, risk_level, distance_label
    """
    distance_km = calculate_distance_km(lat, lon, home)

    if distance_km < 0.1:
        risk = 10
        level = "safe"
        label = "Safe zone"
    elif distance_km < 0.3:
        risk = 30
        level = "warning"
        label = "Slight drift"
    elif distance_km < 0.7:
        risk = 60
        level = "high"
        label = "Suspicious movement"
    else:
        risk = 90
        level = "critical"
        label = "Wandering detected"

    return {
        "risk_score": risk,
        "distance_km": round(distance_km, 4),
        "risk_level": level,
        "distance_label": label,
    }