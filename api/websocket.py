from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.runtime import get_runtime_manager
from app.realtime import (
    get_connection_registry,
    get_snapshot_sequence_tracker,
    get_subscription_manager,
    get_websocket_manager,
)

from runtime.realtime_snapshot import (
    build_reconnect_snapshot,
)
from runtime.websocket_subscriber import (
    create_websocket_subscriber,
)

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    Phase 3B

    Responsibilities:
    - Validate runtime session existence.
    - Accept websocket transport through WebSocketManager.
    - Register a WebSocketSubscriber for realtime fanout.
    - Cleanly unregister and disconnect on teardown.

    Does not:
    - Dispatch events directly.
    - Own subscription fanout.
    - Access RuntimeSession internals.
    - Access GPSPipeline internals.
    """

    runtime_manager = get_runtime_manager()

    if not runtime_manager.session_exists(session_id):
        await websocket.close(code=4404)
        return

    websocket_manager = get_websocket_manager()
    subscription_manager = get_subscription_manager()

    connection_id = await websocket_manager.connect(
        websocket
    )
    state = runtime_manager.get_session_state(
        session_id
    )

    sequence = (
        get_snapshot_sequence_tracker()
        .next_sequence(session_id)
    )

    snapshot = build_reconnect_snapshot(
        state,
        sequence=sequence,
    )

    await websocket_manager.send(
        connection_id,
        snapshot.model_dump(mode="json"),
    )
    subscriber = create_websocket_subscriber(
        session_id=session_id,
        connection_id=connection_id,
        websocket_manager=websocket_manager,
    )

    subscription_id = subscription_manager.register(
        subscriber,
        session_id=session_id,
    )

    try:
        while True:
            await websocket.receive_text()
            get_connection_registry().mark_alive(
            connection_id
        )
        

    except WebSocketDisconnect:
        pass

    finally:
        subscription_manager.unregister(
            subscription_id
        )

        await websocket_manager.disconnect(
            connection_id
        )