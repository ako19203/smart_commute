from __future__ import annotations

from runtime.stale_connection_worker import (
    StaleConnectionWorker,
)

from app.realtime import (
    get_connection_registry,
)

_stale_connection_worker: (
    StaleConnectionWorker | None
) = None


def get_stale_connection_worker(
) -> StaleConnectionWorker:
    global _stale_connection_worker

    if _stale_connection_worker is None:
        _stale_connection_worker = (
            StaleConnectionWorker(
                get_connection_registry(),
                interval_seconds=15,
            )
        )

    return _stale_connection_worker