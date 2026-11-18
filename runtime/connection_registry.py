from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Optional


class ConnectionState(StrEnum):
    """
    Lifecycle state for a tracked realtime connection.

    Metadata only — transport and fanout layers interpret these states;
    this registry does not own sockets or event delivery.
    """

    CONNECTED = "connected"
    SUBSCRIBED = "subscribed"
    STALE = "stale"
    DISCONNECTED = "disconnected"


@dataclass
class ConnectionRecord:
    """
    Connection lifecycle metadata snapshot.

    ``subscriptions`` tracks session identifiers for lifecycle purposes only.
    Session-aware fanout is owned by SubscriptionManager elsewhere.
    """

    connection_id: str
    state: ConnectionState
    connected_at: datetime
    last_seen: datetime
    subscriptions: set[str] = field(default_factory=set)


class ConnectionRegistryError(Exception):
    """Base error for connection registry operations."""


class ConnectionNotFoundError(ConnectionRegistryError):
    """Raised when a connection identifier is not registered or active."""


class ConnectionAlreadyRegisteredError(ConnectionRegistryError):
    """Raised when registering a duplicate connection identifier."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot(record: ConnectionRecord) -> ConnectionRecord:
    return ConnectionRecord(
        connection_id=record.connection_id,
        state=record.state,
        connected_at=record.connected_at,
        last_seen=record.last_seen,
        subscriptions=set(record.subscriptions),
    )


def _active_state_for(record: ConnectionRecord) -> ConnectionState:
    if record.subscriptions:
        return ConnectionState.SUBSCRIBED
    return ConnectionState.CONNECTED


class ConnectionRegistry:
    """
    Authoritative in-memory registry for realtime connection lifecycle metadata.

    Owns:
    - connection registration and disconnect
    - last-seen liveness tracking
    - stale connection identification
    - subscribed session id tracking (metadata only)

    Does not own:
    - websocket transport
    - subscription fanout or event delivery
    - runtime orchestration (RuntimeManager, RuntimeSession, etc.)
    - framework bindings (FastAPI, ASGI)
    """

    def __init__(self, *, stale_threshold: timedelta) -> None:
        if stale_threshold <= timedelta(0):
            raise ValueError("stale_threshold must be positive")
        self._stale_threshold = stale_threshold
        self._connections: dict[str, ConnectionRecord] = {}

    @property
    def stale_threshold(self) -> timedelta:
        return self._stale_threshold

    def register_connection(
        self,
        connection_id: str,
        *,
        connected_at: Optional[datetime] = None,
    ) -> ConnectionRecord:
        """Register a new connection in CONNECTED state."""
        if connection_id in self._connections:
            raise ConnectionAlreadyRegisteredError(connection_id)

        now = connected_at or _utc_now()
        if now.tzinfo is None:
            raise ValueError("connected_at must be timezone-aware")

        record = ConnectionRecord(
            connection_id=connection_id,
            state=ConnectionState.CONNECTED,
            connected_at=now,
            last_seen=now,
        )
        self._connections[connection_id] = record
        return _snapshot(record)

    def mark_alive(
        self,
        connection_id: str,
        *,
        seen_at: Optional[datetime] = None,
    ) -> ConnectionRecord:
        """Refresh last-seen and recover from STALE when applicable."""
        record = self._require_active(connection_id)

        now = seen_at or _utc_now()
        if now.tzinfo is None:
            raise ValueError("seen_at must be timezone-aware")

        record.last_seen = now
        if record.state is ConnectionState.STALE:
            record.state = _active_state_for(record)

        return _snapshot(record)

    def add_subscription(
        self,
        connection_id: str,
        session_id: str,
    ) -> ConnectionRecord:
        """Track a subscribed session id for this connection."""
        record = self._require_active(connection_id)
        record.subscriptions.add(session_id)
        record.state = ConnectionState.SUBSCRIBED
        return _snapshot(record)

    def remove_subscription(
        self,
        connection_id: str,
        session_id: str,
    ) -> ConnectionRecord:
        """Remove a tracked session id from this connection."""
        record = self._require_active(connection_id)
        record.subscriptions.discard(session_id)
        if record.state is not ConnectionState.STALE:
            record.state = _active_state_for(record)
        return _snapshot(record)

    def disconnect(self, connection_id: str) -> bool:
        """
        Disconnect a connection and remove it from active tracking.

        Returns False when the connection id is unknown.
        """
        record = self._connections.get(connection_id)
        if record is None:
            return False

        record.state = ConnectionState.DISCONNECTED
        record.subscriptions.clear()
        del self._connections[connection_id]
        return True

    def get_connection(
        self,
        connection_id: str,
    ) -> Optional[ConnectionRecord]:
        """Return a metadata snapshot for an active connection, if present."""
        record = self._connections.get(connection_id)
        if record is None:
            return None
        return _snapshot(record)

    def get_stale_connections(
        self,
        *,
        as_of: Optional[datetime] = None,
    ) -> list[ConnectionRecord]:
        """
        Find connections past the stale threshold and mark them STALE.

        Returns snapshots of connections whose last_seen is older than
        ``stale_threshold`` relative to ``as_of`` (default: now).
        """
        now = as_of or _utc_now()
        if now.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        stale: list[ConnectionRecord] = []
        cutoff = now - self._stale_threshold

        for record in self._connections.values():
            if record.state is ConnectionState.DISCONNECTED:
                continue
            if record.last_seen > cutoff:
                continue

            record.state = ConnectionState.STALE
            stale.append(_snapshot(record))

        return stale

    def active_connection_count(self) -> int:
        """Count connections in CONNECTED or SUBSCRIBED state."""
        return sum(
            1
            for record in self._connections.values()
            if record.state
            in (ConnectionState.CONNECTED, ConnectionState.SUBSCRIBED)
        )

    def _require_active(self, connection_id: str) -> ConnectionRecord:
        record = self._connections.get(connection_id)
        if record is None or record.state is ConnectionState.DISCONNECTED:
            raise ConnectionNotFoundError(connection_id)
        return record
