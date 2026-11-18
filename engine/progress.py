from math import radians, sin, cos, sqrt, atan2


# =========================================================
# HAVERSINE DISTANCE
# =========================================================

def haversine_distance_km(
    point_a,
    point_b
):
    """
    Compute great-circle distance between
    two coordinates using Haversine formula.
    """

    lat1, lon1 = point_a
    lat2, lon2 = point_b

    earth_radius_km = 6371.0

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return earth_radius_km * c


# =========================================================
# CLOSEST ROUTE POINT
# =========================================================

def find_closest_route_index(
    route_geometry,
    current_location
):
    """
    Find closest route point index
    to current user location.
    """

    closest_index = 0

    closest_distance = float("inf")

    for idx, route_point in enumerate(route_geometry):

        distance = haversine_distance_km(
            current_location,
            route_point
        )

        if distance < closest_distance:

            closest_distance = distance

            closest_index = idx

    return closest_index


# =========================================================
# ROUTE PROGRESS
# =========================================================

def calculate_route_progress_percent(
    route_geometry,
    current_location
):
    """
    Calculate approximate percentage
    of route completed.
    """

    if not route_geometry:
        return 0.0

    closest_index = find_closest_route_index(
        route_geometry,
        current_location
    )

    total_points = len(route_geometry)

    if total_points <= 1:
        return 100.0

    progress = (
        closest_index
        / (total_points - 1)
    ) * 100

    return round(progress, 2)


# =========================================================
# ROUTE REMAINING POINTS
# =========================================================

def get_remaining_route_geometry(
    route_geometry,
    current_location
):
    """
    Return remaining portion
    of route after current position.
    """

    closest_index = find_closest_route_index(
        route_geometry,
        current_location
    )

    return route_geometry[closest_index:]