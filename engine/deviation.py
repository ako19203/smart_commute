from engine.progress import (
    haversine_distance_km
)


# =========================================================
# CONFIG
# =========================================================

DEVIATION_THRESHOLD_KM = 0.3


# =========================================================
# DISTANCE TO ROUTE
# =========================================================

def calculate_distance_to_route(
    route_geometry,
    current_location
):
    """
    Calculate minimum distance between
    current location and expected route.
    """

    if not route_geometry:
        return float("inf")

    minimum_distance = float("inf")

    for route_point in route_geometry:

        distance = haversine_distance_km(
            current_location,
            route_point
        )

        if distance < minimum_distance:
            minimum_distance = distance

    return round(minimum_distance, 4)


# =========================================================
# DEVIATION DETECTION
# =========================================================

def detect_route_deviation(
    route_geometry,
    current_location,
    threshold_km=DEVIATION_THRESHOLD_KM
):
    """
    Detect whether user has deviated
    significantly from expected route.
    """

    distance_to_route = (
        calculate_distance_to_route(
            route_geometry,
            current_location
        )
    )

    has_deviated = (
        distance_to_route > threshold_km
    )

    return {

        "distance_to_route_km": (
            distance_to_route
        ),

        "deviation_threshold_km": (
            threshold_km
        ),

        "has_deviated": (
            has_deviated
        ),
    }