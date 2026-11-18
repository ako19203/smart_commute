from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional

from runtime.models import GPSUpdate, SessionState
from runtime.event_bus import EventBus
from runtime.gps_pipeline import GPSPipeline


class RuntimeSession:
    """
    Represents a single active realtime commute runtime session.

    Responsibilities:
    - Own authoritative SessionState
    - Coordinate GPS processing
    - Maintain runtime lifecycle state
    - Delegate realtime evaluation to GPSPipeline
    - Serve as the live orchestration unit for a commute
    """

    def __init__(
        self,
        session_id: str,
        state: SessionState,
        gps_pipeline: GPSPipeline,
        event_bus: EventBus,
        user_id: Optional[str] = None,
    ) -> None:

        self.session_id = session_id
        self.user_id = user_id

        self.state = state

        self.gps_pipeline = gps_pipeline
        self.event_bus = event_bus

        self.created_at = datetime.now(UTC)
        self.last_update_at: Optional[datetime] = None

        self.is_active = True

    def process_gps_update(
        self,
        gps_update: GPSUpdate,
    ) -> SessionState:
        """
        Main runtime execution entrypoint.

        Flow:
        GPS Update
            ↓
        GPSPipeline
            ↓
        SessionState Evolution
        """

        if not self.is_active:
            raise RuntimeError(
                f"Runtime session '{self.session_id}' is inactive."
            )

        self.last_update_at = datetime.now(UTC)

        updated_state = self.gps_pipeline.process(
            self.state,
            gps_update,
        )

        self.state = updated_state

        return self.state

    def get_state(self) -> SessionState:
        """
        Returns the current authoritative runtime state.
        """

        return self.state

    def terminate(self) -> None:
        """
        Terminates the runtime session.
        """

        self.is_active = False

    def touch(self) -> None:
        """
        Updates runtime heartbeat timestamp.
        Useful later for:
        - stale session cleanup
        - runtime health monitoring
        - distributed coordination
        """

        self.last_update_at = datetime.now(UTC)

    @property
    def uptime_seconds(self) -> float:
        """
        Returns runtime session uptime in seconds.
        """

        return (
            datetime.now(UTC) - self.created_at
        ).total_seconds()

    def __repr__(self) -> str:
        return (
            f"RuntimeSession("
            f"session_id={self.session_id}, "
            f"is_active={self.is_active})"
        )