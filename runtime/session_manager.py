from typing import Optional

from runtime.models import SessionState
from runtime.state_store import StateStore

from engine.routing import (
    get_osrm_route,
    get_distance_matrix,
    route_distance_km,
)
class SessionManager:
    """
    Handles lifecycle management for active commute sessions.

    Responsible for:
    - creating sessions
    - retrieving sessions
    - terminating sessions
    - validating active sessions
    """

    def __init__(self, state_store: StateStore):
        self.state_store = state_store

    # =====================================================
    # Session Creation
    # =====================================================

    def create_session(
    self,
    session_id: str,
    origin_coordinates: tuple,
    destination_name: str,
    destination_coordinates: tuple,
    ) -> SessionState:
        """
        Create and register a new commute session.
        """

        # -------------------------------------------------
        # Build Initial Route
        # -------------------------------------------------

        route_points = [
            origin_coordinates,
            destination_coordinates,
        ]

        route_geometry = get_osrm_route(route_points)

        distance_matrix = get_distance_matrix(route_points)

        route_distance = route_distance_km(distance_matrix)

        # -------------------------------------------------
        # Create Session
        # -------------------------------------------------

        session = SessionState(
            session_id=session_id,

            destination_name=destination_name,

            destination_coordinates=destination_coordinates,

            current_location=origin_coordinates,

            route_geometry=route_geometry,

            route_distance_meters=route_distance * 1000,
        )

        self.state_store.add_session(session)

        return session

    # =====================================================
    # Session Retrieval
    # =====================================================

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieve active session by ID.
        """

        return self.state_store.get_session(session_id)

    # =====================================================
    # Session Termination
    # =====================================================

    def terminate_session(self, session_id: str) -> bool:
        """
        Terminate active commute session.
        """

        session = self.state_store.get_session(session_id)

        if not session:
            return False

        session.active = False

        self.state_store.remove_session(session_id)

        return True

    # =====================================================
    # Session Validation
    # =====================================================

    def session_exists(self, session_id: str) -> bool:
        """
        Check whether session exists.
        """

        return self.state_store.session_exists(session_id)

    # =====================================================
    # Utilities
    # =====================================================

    def total_active_sessions(self) -> int:
        """
        Return total active commute sessions.
        """

        return self.state_store.total_active_sessions()