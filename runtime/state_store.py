from typing import Dict, Optional

from runtime.models import SessionState


class StateStore:
    """
    Centralized in-memory runtime state storage.

    Responsible ONLY for storing and retrieving
    active commute session states.
    """

    def __init__(self):
        self.active_sessions: Dict[str, SessionState] = {}

    # =====================================================
    # Session CRUD
    # =====================================================

    def add_session(self, session: SessionState) -> None:
        """
        Store a new active session.
        """
        self.active_sessions[session.session_id] = session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieve active session by ID.
        """
        return self.active_sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """
        Remove session from active storage.
        """
        self.active_sessions.pop(session_id, None)

    def update_session(self, session: SessionState) -> None:
        """
        Replace/update existing session state.
        """
        self.active_sessions[session.session_id] = session

    # =====================================================
    # Utilities
    # =====================================================

    def session_exists(self, session_id: str) -> bool:
        """
        Check whether session exists.
        """
        return session_id in self.active_sessions

    def total_active_sessions(self) -> int:
        """
        Return count of active sessions.
        """
        return len(self.active_sessions)

    def get_all_sessions(self) -> Dict[str, SessionState]:
        """
        Return all active sessions.
        """
        return self.active_sessions