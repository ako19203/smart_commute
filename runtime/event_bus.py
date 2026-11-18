from collections import defaultdict
from typing import Callable, Dict, List, Any


class EventBus:
    """
    Simple in-memory event bus.

    Allows runtime systems to:
    - emit events
    - subscribe to events
    - decouple runtime components
    """

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)

    # =====================================================
    # Subscribe
    # =====================================================

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Register callback for event type.
        """

        self.subscribers[event_type].append(callback)

    # =====================================================
    # Emit
    # =====================================================

    def emit(self, event_type: str, payload: Any) -> None:
        """
        Emit event to all subscribers.
        """

        callbacks = self.subscribers.get(event_type, [])

        for callback in callbacks:
            callback(payload)

    # =====================================================
    # Utilities
    # =====================================================

    def total_subscribers(self, event_type: str) -> int:
        """
        Return subscriber count for event type.
        """

        return len(self.subscribers.get(event_type, []))