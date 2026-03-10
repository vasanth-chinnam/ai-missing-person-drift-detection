from geopy.distance import geodesic

# Safe location (example home location)
SAFE_LOCATION = (12.9716, 77.5946)

SAFE_RADIUS = 500  # meters


def check_geofence(latitude, longitude):

    current_location = (latitude, longitude)

    distance = geodesic(SAFE_LOCATION, current_location).meters

    if distance > SAFE_RADIUS:
        return True, distance
    else:
        return False, distance