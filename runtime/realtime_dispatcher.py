from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Protocol, runtime_checkable
from uuid import uuid4

from runtime.realtime_protocol import (
    RuntimeEventMessage,
    RuntimeEventType,
    StreamVisibility,
)

logger = logging.getLogger(__name__)


def event_stream_visibility(
    event_type: RuntimeEventType,
) -> Optional[StreamVisibility]:
    """
    Resolve stream visibility for a canonical runtime event type.
    """
    return RuntimeEventMessage.VISIBILITY.get(event_type)


# =========================================================
# Subscriber Abstraction
# =========================================================


@runtime_checkable
class RealtimeSubscriber(Protocol):
    """
    Transport-agnostic consumer of canonical runtime event messages.

    Implementations may wrap websocket writers, logging sinks, or
    distributed fanout bridges without owning transport infrastructure.
    """

    async def on_runtime_event(self, message: RuntimeEventMessage) -> None:
        """
        Receive a transport-safe runtime event message.

        Implementations must:
        - be awaitable
        - isolate all internal failures
        - never raise into the dispatcher fanout loop
        """


class RealtimeSubscriberBase(ABC):
    """
    Optional ABC for explicit subscriber implementations.
    """

    @abstractmethod
    async def on_runtime_event(self, message: RuntimeEventMessage) -> None:
        pass


# =========================================================
# Subscription Registry
# =========================================================


@dataclass(frozen=True)
class RealtimeSubscription:
    """
    Session-aware subscription binding for realtime fanout.
    """

    subscription_id: str
    subscriber: RealtimeSubscriber
    session_id: Optional[str] = None
    visibilities: FrozenSet[StreamVisibility] = field(
        default_factory=lambda: frozenset({StreamVisibility.CLIENT})
    )

    def accepts_session(self, session_id: str) -> bool:
        return self.session_id is None or self.session_id == session_id

    def accepts_visibility(self, visibility: StreamVisibility) -> bool:
        return visibility in self.visibilities


class SubscriptionManager:
    """
    In-memory subscription registry for session-aware realtime fanout.

    This abstraction is intentionally simple and replaceable for future
    distributed runtime coordination (e.g. Redis-backed registries).
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, RealtimeSubscription] = {}

    def register(
        self,
        subscriber: RealtimeSubscriber,
        *,
        session_id: Optional[str] = None,
        visibilities: Optional[FrozenSet[StreamVisibility]] = None,
        subscription_id: Optional[str] = None,
    ) -> str:
        """
        Register a subscriber for realtime runtime fanout.

        When session_id is None, the subscription receives events for all
        sessions (intended for operations or infrastructure observers).
        """
        sub_id = subscription_id or str(uuid4())
        if sub_id in self._subscriptions:
            raise ValueError(
                f"Subscription '{sub_id}' already exists."
            )

        visibility_set = visibilities or frozenset(
            {StreamVisibility.CLIENT}
        )
        self._subscriptions[sub_id] = RealtimeSubscription(
            subscription_id=sub_id,
            subscriber=subscriber,
            session_id=session_id,
            visibilities=visibility_set,
        )
        return sub_id

    def unregister(self, subscription_id: str) -> bool:
        return self._subscriptions.pop(subscription_id, None) is not None

    def unregister_session(self, session_id: str) -> int:
        """
        Remove all subscriptions bound to a specific session.
        """
        to_remove = [
            sub_id
            for sub_id, sub in self._subscriptions.items()
            if sub.session_id == session_id
        ]
        for sub_id in to_remove:
            del self._subscriptions[sub_id]
        return len(to_remove)

    def match(
        self,
        session_id: str,
        visibility: StreamVisibility,
    ) -> list[RealtimeSubscriber]:
        """
        Return subscribers eligible for a session and visibility pair.
        """
        return [
            sub.subscriber
            for sub in self._subscriptions.values()
            if sub.accepts_session(session_id)
            and sub.accepts_visibility(visibility)
        ]

    def subscription_count(self) -> int:
        return len(self._subscriptions)

    def session_subscription_count(self, session_id: str) -> int:
        return sum(
            1
            for sub in self._subscriptions.values()
            if sub.session_id == session_id
        )


# =========================================================
# Realtime Dispatcher
# =========================================================


@dataclass(frozen=True)
class DispatchResult:
    """
    Summary of a fanout dispatch operation.
    """

    targeted: int
    delivered: int
    failed: int
    skipped_visibility: bool = False


class RealtimeDispatcher:
    """
    Coordinates session-aware fanout of canonical runtime event messages.

    Responsibilities:
    - accept only RuntimeEventMessage instances
    - filter by StreamVisibility through subscription bindings
    - delegate delivery to RealtimeSubscriber implementations
    - isolate subscriber failures during fanout

    This component does not own websockets, FastAPI, or orchestration.
    RuntimeManager remains the authoritative runtime ingress layer.
    """

    def __init__(
        self,
        subscription_manager: SubscriptionManager,
    ) -> None:
        self.subscription_manager = subscription_manager

    async def dispatch(self, message: RuntimeEventMessage) -> DispatchResult:
        """
        Fan out a canonical runtime event message to matching subscribers.

        Each subscriber is awaited individually. A subscriber failure is
        caught, logged, and counted without interrupting fanout to remaining
        subscribers. DispatchResult reflects actual delivery outcomes, not
        scheduled ones.
        """
        if not isinstance(message, RuntimeEventMessage):
            raise TypeError(
                "RealtimeDispatcher accepts only RuntimeEventMessage "
                f"instances, got {type(message)!r}."
            )

        visibility = event_stream_visibility(message.event_type)
        if visibility is None:
            return DispatchResult(
                targeted=0,
                delivered=0,
                failed=0,
                skipped_visibility=True,
            )

        subscribers = self.subscription_manager.match(
            session_id=message.session_id,
            visibility=visibility,
        )

        delivered = 0
        failed = 0

        for subscriber in subscribers:
            try:
                await subscriber.on_runtime_event(message)
                delivered += 1
            except Exception:
                failed += 1
                logger.exception(
                    "Realtime subscriber delivery failed "
                    "(session_id=%s, event_type=%s, message_id=%s)",
                    message.session_id,
                    message.event_type,
                    message.message_id,
                )

        return DispatchResult(
            targeted=len(subscribers),
            delivered=delivered,
            failed=failed,
        )
