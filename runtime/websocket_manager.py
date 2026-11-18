from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Optional, Sequence
from uuid import uuid4

from fastapi import WebSocket

from runtime.connection_registry import (
    ConnectionAlreadyRegisteredError,
    ConnectionRegistry,
)

logger = logging.getLogger(__name__)

JSONMessage = Mapping[str, Any]


class WebSocketManagerError(Exception):
    """Base error for websocket transport operations."""


class WebSocketConnectionNotFoundError(WebSocketManagerError):
    """Raised when a connection id has no active websocket transport."""


class WebSocketSendError(WebSocketManagerError):
    """Raised when sending on a websocket transport fails."""


class SendManyResult:
    """
    Outcome summary for a multi-connection JSON send.
    """

    __slots__ = ("sent", "not_found", "failed")

    def __init__(
        self,
        *,
        sent: tuple[str, ...] = (),
        not_found: tuple[str, ...] = (),
        failed: tuple[str, ...] = (),
    ) -> None:
        self.sent = sent
        self.not_found = not_found
        self.failed = failed

    @property
    def delivered_count(self) -> int:
        return len(self.sent)


class WebSocketManager:
    """
    Transport-only websocket connection manager.

    Owns:
    - websocket accept/close operations
    - connection_id → WebSocket mapping
    - JSON frame delivery to one or many connections

    Integrates with:
    - ConnectionRegistry for connection lifecycle metadata

    Does not own:
    - subscriptions or SubscriptionManager
    - event fanout or RealtimeDispatcher
    - runtime orchestration (RuntimeManager, RuntimeSession)
    - FastAPI route/endpoint wiring
    - heartbeat or reconnect business logic
    """

    def __init__(self, connection_registry: ConnectionRegistry) -> None:
        self._registry = connection_registry
        self._websockets: dict[str, WebSocket] = {}

    async def connect(
        self,
        websocket: WebSocket,
        *,
        connection_id: Optional[str] = None,
    ) -> str:
        """
        Accept a websocket and register it under a connection id.

        Returns the assigned connection id.
        """
        assigned_id = connection_id or str(uuid4())

        await websocket.accept()

        try:
            self._registry.register_connection(assigned_id)
        except ConnectionAlreadyRegisteredError:
            await self._close_websocket(websocket)
            raise

        self._websockets[assigned_id] = websocket
        return assigned_id

    async def disconnect(self, connection_id: str) -> bool:
        """
        Close websocket transport and remove lifecycle metadata.
        """
        websocket = self._websockets.pop(connection_id, None)
        registry_removed = self._registry.disconnect(connection_id)

        if websocket is not None:
            await self._close_websocket(websocket)

        return websocket is not None or registry_removed

    async def send(
        self,
        connection_id: str,
        message: JSONMessage,
    ) -> None:
        """
        Send a JSON-serializable message to a single connection.
        """
        websocket = self._require_websocket(connection_id)
        payload = _encode_json(message)

        try:
            await websocket.send_text(payload)
        except Exception as exc:
            raise WebSocketSendError(connection_id) from exc

    async def send_many(
        self,
        connection_ids: Sequence[str],
        message: JSONMessage,
    ) -> SendManyResult:
        """
        Send the same JSON message to multiple connections.

        Missing connections are reported in ``not_found``; transport failures
        in ``failed``. Successful deliveries are listed in ``sent``.
        """
        payload = _encode_json(message)
        sent: list[str] = []
        not_found: list[str] = []
        failed: list[str] = []

        for connection_id in connection_ids:
            websocket = self._websockets.get(connection_id)
            if websocket is None:
                not_found.append(connection_id)
                continue

            try:
                await websocket.send_text(payload)
            except Exception:
                logger.exception(
                    "Websocket send failed (connection_id=%s)",
                    connection_id,
                )
                failed.append(connection_id)
                continue

            sent.append(connection_id)

        return SendManyResult(
            sent=tuple(sent),
            not_found=tuple(not_found),
            failed=tuple(failed),
        )

    def has_connection(self, connection_id: str) -> bool:
        """Return whether an active websocket exists for the connection id."""
        return connection_id in self._websockets

    def connection_count(self) -> int:
        """Return the number of active websocket transports."""
        return len(self._websockets)

    def connection_ids(self) -> frozenset[str]:
        """Return all active transport connection ids."""
        return frozenset(self._websockets)

    def get_websocket(
        self,
        connection_id: str,
    ) -> Optional[WebSocket]:
        """Return the websocket instance for a connection id, if connected."""
        return self._websockets.get(connection_id)

    def _require_websocket(self, connection_id: str) -> WebSocket:
        websocket = self._websockets.get(connection_id)
        if websocket is None:
            raise WebSocketConnectionNotFoundError(connection_id)
        return websocket

    async def _close_websocket(self, websocket: WebSocket) -> None:
        try:
            await websocket.close()
        except Exception:
            logger.debug("Websocket close failed", exc_info=True)


def _encode_json(message: JSONMessage) -> str:
    return json.dumps(message, separators=(",", ":"), default=str)
