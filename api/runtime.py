from __future__ import annotations

from fastapi import APIRouter

from app.realtime import (
    get_connection_registry,
    get_subscription_manager,
    get_websocket_manager,
)
from app.runtime import get_runtime_manager

router = APIRouter(
    prefix="/runtime",
    tags=["runtime"],
)


@router.get("/stats")
def runtime_stats() -> dict:
    runtime_manager = get_runtime_manager()

    websocket_manager = get_websocket_manager()

    subscription_manager = get_subscription_manager()

    connection_registry = get_connection_registry()

    worker = runtime_manager.runtime_worker

    return {
        "runtime": {
            "worker_running": (
                worker.is_running
                if worker
                else False
            ),
            "queue_size": runtime_manager.runtime_queue.qsize(),
        },
        "sessions": {
            "active": runtime_manager.active_session_count(),
        },
        "connections": {
            "transport": websocket_manager.connection_count(),
            "registry": connection_registry.active_connection_count(),
        },
        "subscriptions": {
            "active": subscription_manager.subscription_count(),
        },
    }