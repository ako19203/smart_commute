from __future__ import annotations
from runtime.realtime_snapshot import SnapshotSequenceTracker
from datetime import timedelta

from runtime.connection_registry import ConnectionRegistry
from runtime.websocket_manager import WebSocketManager
from runtime.realtime_dispatcher import (
    RealtimeDispatcher,
    SubscriptionManager,
)
from runtime.realtime_snapshot import SnapshotSequenceTracker
_connection_registry: ConnectionRegistry | None = None
_websocket_manager: WebSocketManager | None = None
_subscription_manager: SubscriptionManager | None = None
_realtime_dispatcher: RealtimeDispatcher | None = None
_snapshot_sequence_tracker: SnapshotSequenceTracker | None = None


def get_connection_registry() -> ConnectionRegistry:
    global _connection_registry

    if _connection_registry is None:
        _connection_registry = ConnectionRegistry(
            stale_threshold=timedelta(minutes=2)
        )

    return _connection_registry


def get_websocket_manager() -> WebSocketManager:
    global _websocket_manager

    if _websocket_manager is None:
        _websocket_manager = WebSocketManager(
            get_connection_registry()
        )

    return _websocket_manager


def get_subscription_manager() -> SubscriptionManager:
    global _subscription_manager

    if _subscription_manager is None:
        _subscription_manager = SubscriptionManager()

    return _subscription_manager


def get_realtime_dispatcher() -> RealtimeDispatcher:
    global _realtime_dispatcher

    if _realtime_dispatcher is None:
        _realtime_dispatcher = RealtimeDispatcher(
            get_subscription_manager()
        )

    return _realtime_dispatcher

def get_snapshot_sequence_tracker() -> SnapshotSequenceTracker:
    global _snapshot_sequence_tracker

    if _snapshot_sequence_tracker is None:
        _snapshot_sequence_tracker = SnapshotSequenceTracker()

    return _snapshot_sequence_tracker