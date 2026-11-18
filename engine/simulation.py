import time

from provider import OSRMProvider

from trigger import (
    evaluate_alarm_trigger
)

from rerouting import (
    reroute_if_needed
)

from state import (
    CommuteState
)


# =========================================================
# PROVIDER
# =========================================================

provider = OSRMProvider()


# =========================================================
# TRIP CONFIGURATION
# =========================================================

ORIGIN = (12.9710, 77.5940)

DESTINATION = (12.9500, 77.6200)

TRAVEL_MODE = "bus"

SIMULATION_DELAY_SECONDS = 0.3


# =========================================================
# DYNAMIC SPEED SIMULATION
# =========================================================

SIMULATED_SPEEDS = [
    35,
    34,
    32,
    30,
    28,
    24,
    18,
    12,
    8,
    15,
    22,
    30,
    35,
]


# =========================================================
# GENERATE INITIAL ROUTE
# =========================================================

print("\nFetching OSRM route geometry...\n")

full_route_geometry = provider.get_route([
    ORIGIN,
    DESTINATION
])

print(
    f"Full Route Geometry Points: "
    f"{len(full_route_geometry)}"
)


# =========================================================
# SAFE ROUTE SAMPLING
# =========================================================

if len(full_route_geometry) > 50:

    SIMULATED_ROUTE = (
        full_route_geometry[::5]
    )

else:

    SIMULATED_ROUTE = (
        full_route_geometry
    )


# =========================================================
# CENTRALIZED COMMUTE STATE
# =========================================================

commute_state = CommuteState(
    current_location=ORIGIN,
    destination=DESTINATION,
    route_geometry=SIMULATED_ROUTE,
    travel_mode=TRAVEL_MODE,
)


# =========================================================
# OPTIONAL DEVIATION INJECTION
# =========================================================

ENABLE_FAKE_DEVIATION = True

FAKE_DEVIATION_STEP = 18


# =========================================================
# SIMULATION LOOP
# =========================================================

def simulate_trip():
    """
    Simulate movement along actual road geometry
    using centralized commute state.
    """

    global SIMULATED_ROUTE

    print(
        f"Loaded {len(SIMULATED_ROUTE)} "
        f"simulation points.\n"
    )

    print("Starting commute simulation...\n")

    for step, current_location in enumerate(
        SIMULATED_ROUTE,
        start=1
    ):

        # -------------------------------------------------
        # OPTIONAL FAKE DEVIATION
        # -------------------------------------------------

        if (
            ENABLE_FAKE_DEVIATION
            and step == FAKE_DEVIATION_STEP
        ):

            print("\nFAKE DEVIATION INJECTED\n")

            current_location = (
                current_location[0] + 0.01,
                current_location[1] + 0.01,
            )

        # -------------------------------------------------
        # DYNAMIC SPEED
        # -------------------------------------------------

        current_speed_kmh = (
            SIMULATED_SPEEDS[
                step % len(SIMULATED_SPEEDS)
            ]
        )

        # -------------------------------------------------
        # UPDATE COMMUTE STATE
        # -------------------------------------------------

        commute_state.update_location(
            current_location
        )

        commute_state.update_speed(
            current_speed_kmh
        )

        commute_state.increment_step()

        # -------------------------------------------------
        # TRIGGER ENGINE
        # -------------------------------------------------

        result = evaluate_alarm_trigger(
            current_location=(
                commute_state.current_location
            ),

            destination=(
                commute_state.destination
            ),

            current_speed_kmh=(
                commute_state.current_speed_kmh
            ),

            travel_mode=(
                commute_state.travel_mode
            ),

            route_geometry=(
                commute_state.route_geometry
            ),
        )

        # -------------------------------------------------
        # APPLY RESULT TO STATE
        # -------------------------------------------------

        commute_state.apply_trigger_result(
            result
        )

        # -------------------------------------------------
        # OUTPUT
        # -------------------------------------------------

        print("=" * 60)

        print(
            f"STEP: "
            f"{commute_state.simulation_step}"
        )

        print(
            f"Current Location: "
            f"{commute_state.current_location}"
        )

        print(
            f"Current Speed: "
            f"{commute_state.current_speed_kmh} km/h"
        )

        print(
            f"Remaining Distance: "
            f"{commute_state.remaining_distance_km} km"
        )

        print(
            f"ETA: "
            f"{commute_state.eta_minutes} mins"
        )

        print(
            f"Route Progress: "
            f"{commute_state.route_progress_percent}%"
        )

        print(
            f"Distance To Route: "
            f"{commute_state.distance_to_route_km} km"
        )

        print(
            f"Has Deviated: "
            f"{commute_state.has_deviated}"
        )

        print(
            f"Trigger Confidence: "
            f"{commute_state.trigger_confidence_score}%"
        )

        print(
            f"Trigger Threshold: "
            f"{commute_state.trigger_threshold_minutes} mins"
        )

        print(
            f"ALARM STATUS: "
            f"{commute_state.should_trigger_alarm}"
        )

        # -------------------------------------------------
        # REROUTING ENGINE
        # -------------------------------------------------

        reroute_result = reroute_if_needed(
            current_location=(
                commute_state.current_location
            ),

            destination=(
                commute_state.destination
            ),

            route_geometry=(
                commute_state.route_geometry
            ),

            provider=provider,
        )

        if reroute_result["rerouted"]:

            print("\nREROUTING TRIGGERED")

            print(
                f"New Route Points: "
                f"{reroute_result['new_route_points']}"
            )

            print(
                reroute_result["message"]
            )

            new_route = (
                reroute_result[
                    "route_geometry"
                ]
            )

            # ---------------------------------------------
            # SAFE SAMPLING
            # ---------------------------------------------

            if len(new_route) > 50:

                SIMULATED_ROUTE = (
                    new_route[::5]
                )

            else:

                SIMULATED_ROUTE = (
                    new_route
                )

            # ---------------------------------------------
            # UPDATE CENTRAL STATE
            # ---------------------------------------------

            commute_state.update_route_geometry(
                SIMULATED_ROUTE
            )

            commute_state.rerouting_active = True

            print(
                f"Updated Simulation Route Points: "
                f"{len(SIMULATED_ROUTE)}"
            )

        else:

            commute_state.rerouting_active = False

        # -------------------------------------------------
        # STOP SIMULATION IF ALARM TRIGGERS
        # -------------------------------------------------

        if commute_state.should_trigger_alarm:

            print("\nALARM TRIGGERED")

            print(
                "Prepare to get down soon."
            )

            break

        time.sleep(SIMULATION_DELAY_SECONDS)

    print("\nSimulation complete.")


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    simulate_trip()