from engine.provider import OSRMProvider

from engine.deviation import (
    detect_route_deviation
)


# =========================================================
# REROUTING ENGINE
# =========================================================

def recalculate_route(
    current_location,
    destination,
    provider=None,
):
    """
    Generate a new route geometry
    from current location to destination.
    """

    if provider is None:
        provider = OSRMProvider()

    new_route_geometry = provider.get_route([
        current_location,
        destination
    ])

    return {

        "route_geometry": (
            new_route_geometry
        ),

        "route_point_count": (
            len(new_route_geometry)
        ),

        "rerouting_successful": (
            len(new_route_geometry) > 1
        ),
    }


# =========================================================
# CONDITIONAL REROUTING
# =========================================================

def reroute_if_needed(
    current_location,
    destination,
    route_geometry,
    provider=None,
):
    """
    Detect route deviation and
    reroute if necessary.
    """

    if provider is None:
        provider = OSRMProvider()

    # -----------------------------------------------------
    # CHECK DEVIATION
    # -----------------------------------------------------

    deviation_result = (
        detect_route_deviation(
            route_geometry,
            current_location
        )
    )

    has_deviated = (
        deviation_result[
            "has_deviated"
        ]
    )

    # -----------------------------------------------------
    # NO REROUTE NEEDED
    # -----------------------------------------------------

    if not has_deviated:

        return {

            "rerouted": False,

            "route_geometry": (
                route_geometry
            ),

            "distance_to_route_km": (
                deviation_result[
                    "distance_to_route_km"
                ]
            ),

            "message": (
                "User still on expected route."
            ),
        }

    # -----------------------------------------------------
    # REROUTE
    # -----------------------------------------------------

    reroute_result = (
        recalculate_route(
            current_location=current_location,
            destination=destination,
            provider=provider,
        )
    )

    return {

        "rerouted": True,

        "route_geometry": (
            reroute_result[
                "route_geometry"
            ]
        ),

        "distance_to_route_km": (
            deviation_result[
                "distance_to_route_km"
            ]
        ),

        "new_route_points": (
            reroute_result[
                "route_point_count"
            ]
        ),

        "rerouting_successful": (
            reroute_result[
                "rerouting_successful"
            ]
        ),

        "message": (
            "Route deviation detected. "
            "Generated new route."
        ),
    }