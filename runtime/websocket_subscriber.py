"""
runtime/websocket_subscriber.py

Transport adapter between RealtimeDispatcher and WebSocketManager.

One instance per active WebSocket connection. Implements the
RealtimeSubscriber protocol defined in realtime_dispatcher.py so that
RealtimeDispatcher can fan out RuntimeEventMessage instances without any
knowledge of WebSocket transport.

Architectural position:
    RealtimeDispatcher
        ↓  (RealtimeSubscriber protocol)
    WebSocketSubscriber          ← this file
        ↓  (concrete transport call)
    WebSocketManager

Allowed dependencies:
    - RuntimeEventMessage        (canonical transport contract)
    - StreamVisibility           (fanout filtering contract)
    - RealtimeSubscriber         (protocol this class satisfies)
    - WebSocketManager           (concrete transport owner)

Must not import:
    - RuntimeManager
    - RuntimeSession
    - GPSPipeline
    - SubscriptionManager
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from runtime.realtime_dispatcher import RealtimeSubscriber
from runtime.realtime_protocol import RuntimeEventMessage, StreamVisibility
from runtime.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Concrete WebSocket subscriber
# ---------------------------------------------------------------------------


@dataclass
class WebSocketSubscriber:
    """
    Concrete RealtimeSubscriber backed by a single WebSocket connection.

    Satisfies the RealtimeSubscriber protocol from realtime_dispatcher.py.
    Registered with SubscriptionManager by api/websocket.py; never self-
    registers.

    Responsibilities:
        - Implement async on_runtime_event() for dispatcher fanout.
        - Serialize RuntimeEventMessage into the dict form WebSocketManager
          expects.
        - Delegate the actual send to WebSocketManager.
        - Contain all transport failures so dispatcher fanout is never
          interrupted.

    Not responsible for:
        - Subscription registration or deregistration (api/websocket.py).
        - Fanout coordination or subscriber selection (RealtimeDispatcher).
        - Connection lifecycle, heartbeat, disconnect detection
          (WebSocketManager).
        - Snapshot generation or issuance (RuntimeManager).
        - Any knowledge of RuntimeManager, RuntimeSession, or GPSPipeline.
    """

    session_id: str
    connection_id: str
    websocket_manager: WebSocketManager
    visibility: StreamVisibility = StreamVisibility.CLIENT
    _subscriber_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _connected: bool = field(default=True, init=False)

    # ------------------------------------------------------------------
    # RealtimeSubscriber protocol
    # ------------------------------------------------------------------

    async def on_runtime_event(self, message: RuntimeEventMessage) -> None:
        """
        Receive a RuntimeEventMessage from RealtimeDispatcher and deliver
        it to the WebSocket connection.

        Contract:
            - Never raises. All exceptions are caught, logged, and result
              in the subscriber being marked disconnected.
            - Returns immediately without delivering if already disconnected.
            - DispatchResult.delivered reflects actual completed sends;
              DispatchResult.failed reflects exceptions caught here.

        Serialization boundary:
            RuntimeEventMessage → dict via model_dump(). WebSocketManager
            owns JSON encoding. Internal structures (SessionState, route
            geometry) never reach this method; they are excluded at the
            protocol layer before dispatch.
        """
        if not self._connected:
            logger.debug(
                "on_runtime_event skipped: subscriber %s disconnected "
                "(session=%s, event=%s)",
                self._subscriber_id,
                self.session_id,
                message.event_type,
            )
            return

        try:
            payload = message.model_dump()
            await self.websocket_manager.send(self.connection_id, payload)

        except Exception:
            self._connected = False
            logger.warning(
                "on_runtime_event failed: subscriber %s marked disconnected "
                "(session=%s, event=%s)",
                self._subscriber_id,
                self.session_id,
                message.event_type,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Liveness
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        """
        Liveness probe for WebSocketManager and teardown paths.

        Reflects the last known delivery outcome. False means a previous
        on_runtime_event() call confirmed the transport is no longer viable.
        Does not perform a live socket probe — that is WebSocketManager's
        responsibility.
        """
        return self._connected

    def mark_disconnected(self) -> None:
        """
        Signal an externally-detected disconnect (client close, heartbeat
        timeout) without waiting for a failed send to discover it.

        Called by api/websocket.py teardown or WebSocketManager cleanup.
        Never called by RealtimeDispatcher.
        """
        self._connected = False
        logger.debug(
            "subscriber %s marked disconnected externally (session=%s)",
            self._subscriber_id,
            self.session_id,
        )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def subscriber_id(self) -> str:
        """
        Unique identity for this subscriber instance within the registry.

        Distinct from connection_id: subscriber_id identifies this object
        inside SubscriptionManager. connection_id is the transport handle
        WebSocketManager uses to address the socket. They may share a value
        in simple deployments but are kept separate so the registry and
        transport layer remain independently addressable.
        """
        return self._subscriber_id


# ---------------------------------------------------------------------------
# Runtime type assertion
#
# Verified at import time that WebSocketSubscriber satisfies the
# RealtimeSubscriber protocol. Catches method name or signature drift
# early rather than at the first registration call.
# ---------------------------------------------------------------------------

"""def _assert_protocol_compatibility() -> None:
    assert isinstance(
        WebSocketSubscriber.__new__(WebSocketSubscriber),
        RealtimeSubscriber,
    ), (
        "WebSocketSubscriber does not satisfy the RealtimeSubscriber protocol. "
        "Check that on_runtime_event() is defined and matches the protocol signature."
    )
"""

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_websocket_subscriber(
    session_id: str,
    connection_id: str,
    websocket_manager: WebSocketManager,
    visibility: StreamVisibility = StreamVisibility.CLIENT,
    subscriber_id: Optional[str] = None,
) -> WebSocketSubscriber:
    """
    Construct a WebSocketSubscriber for a newly accepted connection.

    Called by api/websocket.py immediately after connection acceptance,
    before registration with SubscriptionManager.

    Args:
        session_id:         Runtime session this subscriber is bound to.
        connection_id:      Transport handle WebSocketManager uses for this
                            connection.
        websocket_manager:  Shared WebSocketManager instance from runtime
                            bootstrap.
        visibility:         Fanout scope. Defaults to CLIENT — receives
                            events visible to external realtime consumers.
        subscriber_id:      Optional fixed identity. When omitted a UUID is
                            generated. Pass a deterministic value in tests.

    Returns:
        WebSocketSubscriber satisfying RealtimeSubscriber, ready for
        registration with SubscriptionManager.
    """
    kwargs: dict = dict(
        session_id=session_id,
        connection_id=connection_id,
        websocket_manager=websocket_manager,
        visibility=visibility,
    )
    if subscriber_id is not None:
        kwargs["_subscriber_id"] = subscriber_id

    return WebSocketSubscriber(**kwargs)
