def calculate_risk(speed, heart_rate, outside_geofence):

    risk = 0

    if speed > 6:
        risk += 30

    if heart_rate > 100:
        risk += 30

    if outside_geofence:
        risk += 40

    return risk