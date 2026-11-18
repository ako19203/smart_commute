from __future__ import annotations

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from runtime.realtime_protocol import session_evolution_from_processing
from runtime.runtime_queue import QueuedGPSUpdate, RuntimeQueue

if TYPE_CHECKING:
    from runtime.realtime_dispatcher import RealtimeDispatcher
    from runtime.runtime_manager import RuntimeManager

logger = logging.getLogger(__name__)


class RuntimeWorker:
    """
    Background worker that drains RuntimeQueue and delegates
    processing through RuntimeManager.
    """

    def __init__(
        self,
        manager: "RuntimeManager",
        runtime_queue: RuntimeQueue,
        dispatcher: Optional["RealtimeDispatcher"] = None,
    ) -> None:
        self.manager = manager
        self.runtime_queue = runtime_queue
        self.dispatcher = dispatcher
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None

    async def start(self) -> None:
        if self.is_running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if not self._task:
            return

        await self.runtime_queue.put_stop_signal()
        await self._task
        self._task = None
        self._running = False

    async def _run_loop(self) -> None:
        while True:
            queue_item = await self.runtime_queue.get()
            try:
                if queue_item == RuntimeQueue.STOP:
                    break

                if not isinstance(queue_item, QueuedGPSUpdate):
                    continue

                update = queue_item
                try:
                    # process_gps_update performs blocking IO through
                    # routing/provider calls. Move work off event loop.
                    updated_state = await asyncio.to_thread(
                        self.manager.process_gps_update,
                        update.session_id,
                        update.latitude,
                        update.longitude,
                        update.speed_mps,
                    )
                except Exception as exc:
                    if (
                        update.result_future
                        and not update.result_future.done()
                    ):
                        update.result_future.set_exception(exc)
                    self.manager.event_bus.emit(
                        "GPS_UPDATE_PROCESSING_FAILED",
                        {
                            "session_id": update.session_id,
                            "error": str(exc),
                        },
                    )
                    continue

                if (
                    update.result_future
                    and not update.result_future.done()
                ):
                    update.result_future.set_result(updated_state)

                if self.dispatcher is not None:
                    try:
                        message = session_evolution_from_processing(
                            session_id=updated_state.session_id,
                            current_location=updated_state.current_location,
                            speed_mps=updated_state.current_speed_mps,
                            eta_minutes=updated_state.eta_minutes,
                            progress_percent=updated_state.progress_percent,
                            deviated=updated_state.deviated,
                            rerouting=updated_state.rerouting,
                            should_alert=updated_state.should_alert,
                            last_updated=updated_state.last_updated,
                        )
                        await self.dispatcher.dispatch(message)
                    except Exception:
                        logger.exception(
                            "Realtime dispatch failed after GPS processing "
                            "(session_id=%s)",
                            updated_state.session_id,
                        )
            finally:
                self.runtime_queue.task_done()
