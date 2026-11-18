from engine.deviation import (
    detect_route_deviation
)
from engine.rerouting import (
    reroute_if_needed
)
from datetime import datetime
from engine.trigger import (
    calculate_remaining_distance_km,
    calculate_eta_minutes,
    get_trigger_threshold,
    evaluate_trigger_decision,
)

from engine.provider import OSRMProvider
from runtime.models import GPSUpdate, SessionState
from runtime.event_bus import EventBus
from engine.progress import (
    calculate_route_progress_percent
)

class GPSPipeline:
    """
    Central realtime orchestration pipeline.

    Responsible for:
    - processing live GPS updates
    - updating session state
    - coordinating engine modules
    - emitting runtime events
    """

    def __init__(
        self,
        event_bus: EventBus,
    ):
        self.event_bus = event_bus

    # =====================================================
    # Main Pipeline Entry
    # =====================================================

    def process(
        self,
        session_state: SessionState,
        gps_update: GPSUpdate
    ) -> SessionState:
        """
        Process incoming GPS update through runtime pipeline.
        """
        session = session_state

        # -------------------------------------------------
        # Update Live State
        # -------------------------------------------------

        session.current_location = gps_update.coordinates

        session.current_speed_mps = gps_update.speed_mps

        session.last_updated = datetime.utcnow()

        # -------------------------------------------------
        # Emit GPS Update Event
        # -------------------------------------------------

        self.event_bus.emit(
            "GPS_UPDATE_RECEIVED",
            {
                "session_id": session.session_id,
                "location": session.current_location,
                "speed_mps": session.current_speed_mps,
            }
        )

        # -------------------------------------------------
        # Route Progress Evaluation
        # -------------------------------------------------

        if session.route_geometry:

            progress_percent = (
                calculate_route_progress_percent(
                    route_geometry=session.route_geometry,
                    current_location=session.current_location,
                )
            )

            session.progress_percent = progress_percent

            # ---------------------------------------------
            # Emit Progress Event
            # ---------------------------------------------

            self.event_bus.emit(
                "ROUTE_PROGRESS_UPDATED",
                {
                    "session_id": session.session_id,
                    "progress_percent": progress_percent,
                }
            )

        # -------------------------------------------------
        # Deviation Detection
        # -------------------------------------------------

        deviation_result = detect_route_deviation(
            route_geometry=session.route_geometry,
            current_location=session.current_location,
        )

        session.deviated = (
            deviation_result["has_deviated"]
        )

        session.deviation_distance_meters = (
            deviation_result["distance_to_route_km"]
            * 1000
        )

        # -------------------------------------------------
        # Emit Deviation Event
        # -------------------------------------------------

        self.event_bus.emit(
            "DEVIATION_CHECK_COMPLETED",
            {
                "session_id": session.session_id,

                "has_deviated": (
                    session.deviated
                ),

                "distance_to_route_meters": (
                    session.deviation_distance_meters
                ),
            }
        )

        # -------------------------------------------------
        # Emit Off-Route Event
        # -------------------------------------------------

        if session.deviated:

            self.event_bus.emit(
                "OFF_ROUTE_DETECTED",
                {
                    "session_id": session.session_id,

                    "distance_to_route_meters": (
                        session.deviation_distance_meters
                    ),
                }
            )

        # -------------------------------------------------
        # Conditional Rerouting
        # -------------------------------------------------

        reroute_result = reroute_if_needed(
            current_location=session.current_location,

            destination=session.destination_coordinates,

            route_geometry=session.route_geometry,
        )

        session.rerouting = (
            reroute_result["rerouted"]
        )

        # -------------------------------------------------
        # Apply New Route If Needed
        # -------------------------------------------------

        if reroute_result["rerouted"]:

            session.route_geometry = (
                reroute_result["route_geometry"]
            )

            # ---------------------------------------------
            # Emit Reroute Event
            # ---------------------------------------------

            self.event_bus.emit(
                "ROUTE_REROUTED",
                {
                    "session_id": session.session_id,

                    "new_route_points": (
                        reroute_result.get(
                            "new_route_points",
                            0
                        )
                    ),

                    "message": (
                        reroute_result["message"]
                    ),
                }
            )

        # -------------------------------------------------
        # Trigger Evaluation
        # -------------------------------------------------

        provider = OSRMProvider()

        current_speed_kmh = (
            session.current_speed_mps * 3.6
        )

        remaining_distance_km = (
            calculate_remaining_distance_km(
                provider=provider,

                current_location=(
                    session.current_location
                ),

                destination=(
                    session.destination_coordinates
                ),
            )
        )

        eta_minutes = calculate_eta_minutes(
            distance_km=remaining_distance_km,

            speed_kmh=current_speed_kmh,
        )

        trigger_threshold_minutes = (
            get_trigger_threshold("car")
        )

        trigger_result = (
            evaluate_trigger_decision(
                eta_minutes=eta_minutes,

                trigger_threshold_minutes=(
                    trigger_threshold_minutes
                ),

                route_progress_percent=(
                    session.progress_percent
                ),

                has_deviated=(
                    session.deviated
                ),

                current_speed_kmh=(
                    current_speed_kmh
                ),
            )
        )

        session.eta_minutes = round(
            eta_minutes,
            2
        )

        session.trigger_confidence = (
            trigger_result[
                "trigger_confidence_score"
            ]
        )

        session.should_alert = (
            trigger_result[
                "should_trigger_alarm"
            ]
        )

        # -------------------------------------------------
        # Emit Trigger Evaluation Event
        # -------------------------------------------------

        self.event_bus.emit(
            "TRIGGER_EVALUATED",
            {
                "session_id": session.session_id,

                "eta_minutes": (
                    session.eta_minutes
                ),

                "trigger_confidence": (
                    session.trigger_confidence
                ),

                "should_alert": (
                    session.should_alert
                ),
            }
        )

        # -------------------------------------------------
        # Emit Alert Event
        # -------------------------------------------------

        if session.should_alert:

            self.event_bus.emit(
                "COMMUTE_ALERT_TRIGGERED",
                {
                    "session_id": session.session_id,

                    "eta_minutes": (
                        session.eta_minutes
                    ),

                    "trigger_confidence": (
                        session.trigger_confidence
                    ),
                }
            )

        # -------------------------------------------------
        # Emit State Updated Event
        # -------------------------------------------------

        self.event_bus.emit(
            "SESSION_STATE_UPDATED",
            {
                "session_id": session.session_id,
                "current_location": session.current_location,
                "last_updated": str(session.last_updated),
            }
        )

        return session