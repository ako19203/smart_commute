from __future__ import annotations
from app.realtime import get_realtime_dispatcher
from runtime.event_bus import EventBus
from runtime.runtime_manager import RuntimeManager
from runtime.session_manager import SessionManager
from runtime.state_store import StateStore

_runtime_manager: RuntimeManager | None = None


def get_runtime_manager() -> RuntimeManager:
    """
    Singleton runtime bootstrap used by API layers.
    """
    global _runtime_manager

    if _runtime_manager is None:
        state_store = StateStore()
        session_manager = SessionManager(state_store)
        event_bus = EventBus()
        _runtime_manager = RuntimeManager(
        session_manager=session_manager,
        event_bus=event_bus,
        dispatcher=get_realtime_dispatcher(),
        )

    return _runtime_manager
