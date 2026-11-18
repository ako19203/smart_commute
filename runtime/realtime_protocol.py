from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, ClassVar, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# Protocol Versioning
# =========================================================

RUNTIME_PROTOCOL_VERSION = "1.0.0"
"""
Wire protocol version for realtime runtime streaming.

Increment when envelope or payload contracts change incompatibly.
"""


# =========================================================
# Canonical Runtime Websocket Event Types
# =========================================================


class RuntimeEventType(StrEnum):
    """
    Canonical event types for realtime runtime websocket streaming.

    These identifiers define the transport contract between runtime
    infrastructure and external realtime consumers. Internal runtime
    orchestration may emit additional in-process events; only types
    listed here (or mapped through translation) cross the wire.
    """

    # Session lifecycle
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_ENDED = "SESSION_ENDED"
    SESSION_EVOLUTION = "SESSION_EVOLUTION"

    # GPS telemetry and ingestion
    GPS_TELEMETRY = "GPS_TELEMETRY"
    GPS_INGESTION_QUEUED = "GPS_INGESTION_QUEUED"
    GPS_INGESTION_FAILED = "GPS_INGESTION_FAILED"

    # Route intelligence
    ROUTE_PROGRESS = "ROUTE_PROGRESS"
    DEVIATION_EVALUATED = "DEVIATION_EVALUATED"
    OFF_ROUTE = "OFF_ROUTE"
    ROUTE_REROUTED = "ROUTE_REROUTED"

    # Trigger intelligence
    TRIGGER_EVALUATED = "TRIGGER_EVALUATED"
    COMMUTE_ALERT = "COMMUTE_ALERT"

    # Runtime infrastructure (ops / future distributed coordination)
    RUNTIME_WORKER_STARTED = "RUNTIME_WORKER_STARTED"
    RUNTIME_WORKER_STOPPED = "RUNTIME_WORKER_STOPPED"


class StreamVisibility(StrEnum):
    """
    Classifies which events are intended for external streaming.
    """

    CLIENT = "client"
    OPERATIONS = "operations"
    INTERNAL = "internal"


# Maps internal event-bus identifiers to canonical websocket types.
_INTERNAL_TO_CANONICAL: dict[str, RuntimeEventType] = {
    "SESSION_STARTED": RuntimeEventType.SESSION_STARTED,
    "SESSION_ENDED": RuntimeEventType.SESSION_ENDED,
    "SESSION_STATE_UPDATED": RuntimeEventType.SESSION_EVOLUTION,
    "GPS_UPDATE_RECEIVED": RuntimeEventType.GPS_TELEMETRY,
    "GPS_UPDATE_ENQUEUED": RuntimeEventType.GPS_INGESTION_QUEUED,
    "GPS_UPDATE_PROCESSING_FAILED": RuntimeEventType.GPS_INGESTION_FAILED,
    "ROUTE_PROGRESS_UPDATED": RuntimeEventType.ROUTE_PROGRESS,
    "DEVIATION_CHECK_COMPLETED": RuntimeEventType.DEVIATION_EVALUATED,
    "OFF_ROUTE_DETECTED": RuntimeEventType.OFF_ROUTE,
    "ROUTE_REROUTED": RuntimeEventType.ROUTE_REROUTED,
    "TRIGGER_EVALUATED": RuntimeEventType.TRIGGER_EVALUATED,
    "COMMUTE_ALERT_TRIGGERED": RuntimeEventType.COMMUTE_ALERT,
    "RUNTIME_WORKER_STARTED": RuntimeEventType.RUNTIME_WORKER_STARTED,
    "RUNTIME_WORKER_STOPPED": RuntimeEventType.RUNTIME_WORKER_STOPPED,
}

_STREAM_VISIBILITY: dict[RuntimeEventType, StreamVisibility] = {
    RuntimeEventType.SESSION_STARTED: StreamVisibility.CLIENT,
    RuntimeEventType.SESSION_ENDED: StreamVisibility.CLIENT,
    RuntimeEventType.SESSION_EVOLUTION: StreamVisibility.CLIENT,
    RuntimeEventType.GPS_TELEMETRY: StreamVisibility.CLIENT,
    RuntimeEventType.ROUTE_PROGRESS: StreamVisibility.CLIENT,
    RuntimeEventType.DEVIATION_EVALUATED: StreamVisibility.CLIENT,
    RuntimeEventType.OFF_ROUTE: StreamVisibility.CLIENT,
    RuntimeEventType.ROUTE_REROUTED: StreamVisibility.CLIENT,
    RuntimeEventType.TRIGGER_EVALUATED: StreamVisibility.CLIENT,
    RuntimeEventType.COMMUTE_ALERT: StreamVisibility.CLIENT,
    RuntimeEventType.GPS_INGESTION_QUEUED: StreamVisibility.OPERATIONS,
    RuntimeEventType.GPS_INGESTION_FAILED: StreamVisibility.OPERATIONS,
    RuntimeEventType.RUNTIME_WORKER_STARTED: StreamVisibility.OPERATIONS,
    RuntimeEventType.RUNTIME_WORKER_STOPPED: StreamVisibility.OPERATIONS,
}


# =========================================================
# Transport-Safe Value Objects
# =========================================================


class GeoCoordinate(BaseModel):
    """
    Latitude/longitude pair safe for websocket transport.
    """

    model_config = ConfigDict(frozen=True)

    latitude: float
    longitude: float

    @classmethod
    def from_pair(
        cls,
        pair: Optional[tuple[float, float]],
    ) -> Optional["GeoCoordinate"]:
        if pair is None:
            return None
        return cls(latitude=pair[0], longitude=pair[1])


# =========================================================
# Transport-Safe Event Payloads
# =========================================================


class SessionStartedPayload(BaseModel):
    destination_name: Optional[str] = None
    user_id: Optional[str] = None


class SessionEndedPayload(BaseModel):
    reason: Optional[str] = None


class SessionEvolutionPayload(BaseModel):
    """
    Curated session evolution snapshot for realtime clients.

    Exposes only fields required for commute synchronization.
    Does not expose internal SessionState or route geometry.
    """

    current_location: Optional[GeoCoordinate] = None
    speed_mps: Optional[float] = None
    eta_minutes: Optional[float] = None
    progress_percent: Optional[float] = None
    deviated: Optional[bool] = None
    rerouting: Optional[bool] = None
    should_alert: Optional[bool] = None
    last_updated: Optional[datetime] = None


class GpsTelemetryPayload(BaseModel):
    location: GeoCoordinate
    speed_mps: float = 0.0


class GpsIngestionQueuedPayload(BaseModel):
    queue_size: int = 0


class GpsIngestionFailedPayload(BaseModel):
    error: str


class RouteProgressPayload(BaseModel):
    progress_percent: float


class DeviationEvaluatedPayload(BaseModel):
    has_deviated: bool
    distance_to_route_meters: float


class OffRoutePayload(BaseModel):
    distance_to_route_meters: float


class RouteReroutedPayload(BaseModel):
    new_route_points: int = 0
    message: str = ""


class TriggerEvaluatedPayload(BaseModel):
    eta_minutes: float
    trigger_confidence: float
    should_alert: bool


class CommuteAlertPayload(BaseModel):
    eta_minutes: float
    trigger_confidence: float


class RuntimeWorkerPayload(BaseModel):
    queue_size: Optional[int] = None


RuntimeEventPayload = Union[
    SessionStartedPayload,
    SessionEndedPayload,
    SessionEvolutionPayload,
    GpsTelemetryPayload,
    GpsIngestionQueuedPayload,
    GpsIngestionFailedPayload,
    RouteProgressPayload,
    DeviationEvaluatedPayload,
    OffRoutePayload,
    RouteReroutedPayload,
    TriggerEvaluatedPayload,
    CommuteAlertPayload,
    RuntimeWorkerPayload,
]


# =========================================================
# Transport Envelope
# =========================================================


class RuntimeEventMessage(BaseModel):
    """
    Transport-safe envelope for realtime runtime websocket streaming.

    This type is the only structure that should cross process or network
    boundaries. Internal SessionState objects must never be serialized
    directly into websocket frames.
    """

    model_config = ConfigDict(
        frozen=True,
        json_encoders={
            datetime: lambda value: value.astimezone(
                timezone.utc
            ).isoformat(),
        },
    )

    protocol_version: str = Field(
        default=RUNTIME_PROTOCOL_VERSION,
        description="Realtime protocol contract version.",
    )
    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message identifier for distributed tracing.",
    )
    event_type: RuntimeEventType
    session_id: str = Field(min_length=1)
    emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    payload: RuntimeEventPayload

    # Reserved for future multi-runtime coordination.
    source_runtime_id: Optional[str] = Field(
        default=None,
        description=(
            "Originating runtime instance identifier for distributed "
            "websocket fanout."
        ),
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Optional correlation identifier for ingress tracing.",
    )

    VISIBILITY: ClassVar[dict[RuntimeEventType, StreamVisibility]] = (
        _STREAM_VISIBILITY
    )

    def is_client_streamable(self) -> bool:
        visibility = self.VISIBILITY.get(self.event_type)
        return visibility == StreamVisibility.CLIENT

    def to_wire_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_wire_json(cls, raw: str) -> "RuntimeEventMessage":
        return cls.model_validate_json(raw)


# =========================================================
# Internal Event Translation
# =========================================================


def canonical_event_type(
    internal_event_type: str,
) -> Optional[RuntimeEventType]:
    return _INTERNAL_TO_CANONICAL.get(internal_event_type)


def translate_internal_event(
    internal_event_type: str,
    payload: dict[str, Any],
    *,
    source_runtime_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    include_operations_events: bool = False,
) -> Optional[RuntimeEventMessage]:
    """
    Translate in-process runtime event-bus emissions into transport-safe
    websocket messages.

    Returns None when the internal event is unknown or filtered by
    stream visibility policy.
    """
    event_type = canonical_event_type(internal_event_type)
    if event_type is None:
        return None

    visibility = _STREAM_VISIBILITY.get(event_type)
    if visibility == StreamVisibility.INTERNAL:
        return None
    if (
        visibility == StreamVisibility.OPERATIONS
        and not include_operations_events
    ):
        return None

    session_id = str(payload.get("session_id", ""))
    if not session_id:
        return None

    typed_payload = _build_payload(event_type, payload)
    if typed_payload is None:
        return None

    return RuntimeEventMessage(
        event_type=event_type,
        session_id=session_id,
        payload=typed_payload,
        source_runtime_id=source_runtime_id,
        correlation_id=correlation_id,
    )


def _build_payload(
    event_type: RuntimeEventType,
    payload: dict[str, Any],
) -> Optional[RuntimeEventPayload]:
    if event_type == RuntimeEventType.SESSION_STARTED:
        return SessionStartedPayload(
            destination_name=payload.get("destination_name"),
            user_id=payload.get("user_id"),
        )

    if event_type == RuntimeEventType.SESSION_ENDED:
        return SessionEndedPayload(
            reason=payload.get("reason"),
        )

    if event_type == RuntimeEventType.SESSION_EVOLUTION:
        location = GeoCoordinate.from_pair(payload.get("current_location"))
        last_updated = payload.get("last_updated")
        parsed_updated: Optional[datetime] = None
        if isinstance(last_updated, datetime):
            parsed_updated = last_updated
        elif isinstance(last_updated, str):
            parsed_updated = datetime.fromisoformat(last_updated)

        return SessionEvolutionPayload(
            current_location=location,
            speed_mps=payload.get("speed_mps"),
            eta_minutes=payload.get("eta_minutes"),
            progress_percent=payload.get("progress_percent"),
            deviated=payload.get("deviated"),
            rerouting=payload.get("rerouting"),
            should_alert=payload.get("should_alert"),
            last_updated=parsed_updated,
        )

    if event_type == RuntimeEventType.GPS_TELEMETRY:
        location = GeoCoordinate.from_pair(payload.get("location"))
        if location is None:
            return None
        return GpsTelemetryPayload(
            location=location,
            speed_mps=float(payload.get("speed_mps", 0.0)),
        )

    if event_type == RuntimeEventType.GPS_INGESTION_QUEUED:
        return GpsIngestionQueuedPayload(
            queue_size=int(payload.get("queue_size", 0)),
        )

    if event_type == RuntimeEventType.GPS_INGESTION_FAILED:
        return GpsIngestionFailedPayload(
            error=str(payload.get("error", "unknown_error")),
        )

    if event_type == RuntimeEventType.ROUTE_PROGRESS:
        return RouteProgressPayload(
            progress_percent=float(payload.get("progress_percent", 0.0)),
        )

    if event_type == RuntimeEventType.DEVIATION_EVALUATED:
        return DeviationEvaluatedPayload(
            has_deviated=bool(payload.get("has_deviated", False)),
            distance_to_route_meters=float(
                payload.get("distance_to_route_meters", 0.0)
            ),
        )

    if event_type == RuntimeEventType.OFF_ROUTE:
        return OffRoutePayload(
            distance_to_route_meters=float(
                payload.get("distance_to_route_meters", 0.0)
            ),
        )

    if event_type == RuntimeEventType.ROUTE_REROUTED:
        return RouteReroutedPayload(
            new_route_points=int(payload.get("new_route_points", 0)),
            message=str(payload.get("message", "")),
        )

    if event_type == RuntimeEventType.TRIGGER_EVALUATED:
        return TriggerEvaluatedPayload(
            eta_minutes=float(payload.get("eta_minutes", 0.0)),
            trigger_confidence=float(payload.get("trigger_confidence", 0.0)),
            should_alert=bool(payload.get("should_alert", False)),
        )

    if event_type == RuntimeEventType.COMMUTE_ALERT:
        return CommuteAlertPayload(
            eta_minutes=float(payload.get("eta_minutes", 0.0)),
            trigger_confidence=float(payload.get("trigger_confidence", 0.0)),
        )

    if event_type in {
        RuntimeEventType.RUNTIME_WORKER_STARTED,
        RuntimeEventType.RUNTIME_WORKER_STOPPED,
    }:
        return RuntimeWorkerPayload(
            queue_size=payload.get("queue_size"),
        )

    return None


def session_evolution_from_processing(
    *,
    session_id: str,
    current_location: Optional[tuple[float, float]],
    speed_mps: float,
    eta_minutes: float,
    progress_percent: float,
    deviated: bool,
    rerouting: bool,
    should_alert: bool,
    last_updated: Optional[datetime] = None,
) -> RuntimeEventMessage:
    """
    Build a curated session evolution message without exposing SessionState.
    """
    return RuntimeEventMessage(
        event_type=RuntimeEventType.SESSION_EVOLUTION,
        session_id=session_id,
        payload=SessionEvolutionPayload(
            current_location=GeoCoordinate.from_pair(current_location),
            speed_mps=speed_mps,
            eta_minutes=eta_minutes,
            progress_percent=progress_percent,
            deviated=deviated,
            rerouting=rerouting,
            should_alert=should_alert,
            last_updated=last_updated or datetime.now(timezone.utc),
        ),
    )
