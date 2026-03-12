def calculate_risk(prediction, outside, route_deviation):

    risk = 0

    if prediction == -1:
        risk += 40

    if outside:
        risk += 40

    if route_deviation:
        risk += 20

    return risk