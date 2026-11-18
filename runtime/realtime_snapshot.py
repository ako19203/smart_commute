from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from runtime.models import SessionState
from runtime.realtime_protocol import GeoCoordinate


# =========================================================
# Snapshot Protocol Versioning
# =========================================================

SNAPSHOT_PROTOCOL_VERSION = "1.0.0"
"""
Reconnect snapshot contract version.

Increment when SessionStateProjection fields change incompatibly.
"""


# =========================================================
# Client-Safe Session Projection
# =========================================================


class SessionStateProjection(BaseModel):
    """
    Transport-agnostic, client-safe view of an active commute session.

    This type is the only session shape that should be exposed across
    realtime interfaces during reconnect synchronization. Internal
    SessionState structures must be projected through runtime boundaries
    controlled by RuntimeManager orchestration.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1)
    active: bool = True

    destination_name: Optional[str] = None
    destination: Optional[GeoCoordinate] = None

    current_location: Optional[GeoCoordinate] = None
    current_speed_mps: float = 0.0

    route_distance_meters: float = 0.0
    eta_minutes: float = 0.0
    progress_percent: float = 0.0
    distance_remaining_meters: float = 0.0

    deviated: bool = False
    deviation_distance_meters: float = 0.0
    rerouting: bool = False

    trigger_confidence: float = 0.0
    should_alert: bool = False
    last_trigger_reason: Optional[str] = None

    created_at: datetime
    last_updated: datetime


# =========================================================
# Reconnect Snapshot Envelope
# =========================================================


class ReconnectSnapshot(BaseModel):
    """
    Authoritative reconnect snapshot for session resynchronization.

    Used when clients reconnect to realtime interfaces and require a
    consistent point-in-time view without receiving internal runtime
    state structures.
    """

    model_config = ConfigDict(frozen=True)

    protocol_version: str = Field(default=SNAPSHOT_PROTOCOL_VERSION)
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    state: SessionStateProjection

    # Reserved for future distributed runtime coordination.
    source_runtime_id: Optional[str] = None

    def to_wire_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_wire_json(cls, raw: str) -> "ReconnectSnapshot":
        return cls.model_validate_json(raw)


# =========================================================
# Projection Boundary
# =========================================================


def project_session_state(state: SessionState) -> SessionStateProjection:
    """
    Project authoritative runtime SessionState into a client-safe shape.

    This function is the explicit runtime boundary for session exposure.
    Callers outside runtime orchestration should receive only
    SessionStateProjection or ReconnectSnapshot instances.

    Intentionally excluded from projection:
    - route_geometry
    - any other internal routing structures
    """
    return SessionStateProjection(
        session_id=state.session_id,
        active=state.active,
        destination_name=state.destination_name,
        destination=GeoCoordinate.from_pair(
            state.destination_coordinates
        ),
        current_location=GeoCoordinate.from_pair(
            state.current_location
        ),
        current_speed_mps=state.current_speed_mps,
        route_distance_meters=state.route_distance_meters,
        eta_minutes=state.eta_minutes,
        progress_percent=state.progress_percent,
        distance_remaining_meters=state.distance_remaining_meters,
        deviated=state.deviated,
        deviation_distance_meters=state.deviation_distance_meters,
        rerouting=state.rerouting,
        trigger_confidence=state.trigger_confidence,
        should_alert=state.should_alert,
        last_trigger_reason=state.last_trigger_reason,
        created_at=_ensure_utc(state.created_at),
        last_updated=_ensure_utc(state.last_updated),
    )


def build_reconnect_snapshot(
    state: SessionState,
    *,
    sequence: int,
    source_runtime_id: Optional[str] = None,
) -> ReconnectSnapshot:
    """
    Build a reconnect snapshot from authoritative runtime session state.

    RuntimeManager remains responsible for deciding when snapshots are
    issued; this helper only shapes transport-safe reconnect payloads.
    """
    projection = project_session_state(state)
    return ReconnectSnapshot(
        session_id=state.session_id,
        sequence=sequence,
        state=projection,
        source_runtime_id=source_runtime_id,
    )


# =========================================================
# Reconnect Sequence Tracking
# =========================================================


class SnapshotSequenceTracker:
    """
    Monotonic per-session sequence generator for reconnect snapshots.

    Supports deterministic client ordering during reconnect
    synchronization and future distributed runtime evolution.
    """

    def __init__(self) -> None:
        self._sequences: dict[str, int] = {}

    def next_sequence(self, session_id: str) -> int:
        current = self._sequences.get(session_id, 0)
        current += 1
        self._sequences[session_id] = current
        return current

    def current_sequence(self, session_id: str) -> int:
        return self._sequences.get(session_id, 0)

    def reset_session(self, session_id: str) -> None:
        self._sequences.pop(session_id, None)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
