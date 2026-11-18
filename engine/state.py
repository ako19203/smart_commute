from dataclasses import dataclass, field
from typing import Optional, Tuple, List


# =========================================================
# TYPE ALIASES
# =========================================================

Coordinate = Tuple[float, float]


# =========================================================
# COMMUTE STATE
# =========================================================

@dataclass
class CommuteState:
    """
    Centralized mobility state object.

    This becomes the single source of truth
    for the commute engine.
    """

    # -----------------------------------------------------
    # LOCATION STATE
    # -----------------------------------------------------

    current_location: Optional[Coordinate] = None

    destination: Optional[Coordinate] = None

    route_geometry: List[Coordinate] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # MOVEMENT STATE
    # -----------------------------------------------------

    current_speed_kmh: float = 0.0

    travel_mode: str = "bus"

    # -----------------------------------------------------
    # ROUTE STATE
    # -----------------------------------------------------

    remaining_distance_km: float = 0.0

    eta_minutes: float = 0.0

    route_progress_percent: float = 0.0

    # -----------------------------------------------------
    # DEVIATION STATE
    # -----------------------------------------------------

    distance_to_route_km: float = 0.0

    has_deviated: bool = False

    # -----------------------------------------------------
    # TRIGGER STATE
    # -----------------------------------------------------

    trigger_threshold_minutes: float = 0.0

    trigger_confidence_score: float = 0.0

    should_trigger_alarm: bool = False

    # -----------------------------------------------------
    # SYSTEM STATE
    # -----------------------------------------------------

    rerouting_active: bool = False

    simulation_step: int = 0

    # -----------------------------------------------------
    # UPDATE METHODS
    # -----------------------------------------------------

    def update_location(
        self,
        current_location: Coordinate
    ):
        """
        Update user location.
        """

        self.current_location = (
            current_location
        )

    def update_speed(
        self,
        speed_kmh: float
    ):
        """
        Update current travel speed.
        """

        self.current_speed_kmh = (
            speed_kmh
        )

    def update_route_geometry(
        self,
        route_geometry: List[Coordinate]
    ):
        """
        Update active route geometry.
        """

        self.route_geometry = (
            route_geometry
        )

    def increment_step(self):
        """
        Increment simulation step.
        """

        self.simulation_step += 1

    # -----------------------------------------------------
    # BULK STATE UPDATE
    # -----------------------------------------------------

    def apply_trigger_result(
        self,
        trigger_result: dict
    ):
        """
        Apply trigger engine output
        to centralized state.
        """

        self.remaining_distance_km = (
            trigger_result[
                "remaining_distance_km"
            ]
        )

        self.eta_minutes = (
            trigger_result[
                "eta_minutes"
            ]
        )

        self.route_progress_percent = (
            trigger_result[
                "route_progress_percent"
            ]
        )

        self.distance_to_route_km = (
            trigger_result[
                "distance_to_route_km"
            ]
        )

        self.has_deviated = (
            trigger_result[
                "has_deviated"
            ]
        )

        self.trigger_threshold_minutes = (
            trigger_result[
                "trigger_threshold_minutes"
            ]
        )

        self.trigger_confidence_score = (
            trigger_result[
                "trigger_confidence_score"
            ]
        )

        self.should_trigger_alarm = (
            trigger_result[
                "should_trigger_alarm"
            ]
        )

    # -----------------------------------------------------
    # STATE SNAPSHOT
    # -----------------------------------------------------

    def to_dict(self):
        """
        Export state as dictionary.
        Useful for:
        - APIs
        - logging
        - Flutter integration
        - debugging
        """

        return {

            "current_location": (
                self.current_location
            ),

            "destination": (
                self.destination
            ),

            "current_speed_kmh": (
                self.current_speed_kmh
            ),

            "travel_mode": (
                self.travel_mode
            ),

            "remaining_distance_km": (
                self.remaining_distance_km
            ),

            "eta_minutes": (
                self.eta_minutes
            ),

            "route_progress_percent": (
                self.route_progress_percent
            ),

            "distance_to_route_km": (
                self.distance_to_route_km
            ),

            "has_deviated": (
                self.has_deviated
            ),

            "trigger_threshold_minutes": (
                self.trigger_threshold_minutes
            ),

            "trigger_confidence_score": (
                self.trigger_confidence_score
            ),

            "should_trigger_alarm": (
                self.should_trigger_alarm
            ),

            "rerouting_active": (
                self.rerouting_active
            ),

            "simulation_step": (
                self.simulation_step
            ),
        }