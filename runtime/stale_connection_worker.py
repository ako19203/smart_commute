from __future__ import annotations

import asyncio
import logging
from typing import Optional

from runtime.connection_registry import ConnectionRegistry

logger = logging.getLogger(__name__)


class StaleConnectionWorker:
    """
    Periodically scans ConnectionRegistry for stale connections
    and removes them from active tracking.
    """

    def __init__(
        self,
        connection_registry: ConnectionRegistry,
        interval_seconds: int = 60,
    ) -> None:
        self.connection_registry = connection_registry
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None

    async def start(self) -> None:
        if self.is_running:
            return

        self._running = True
        self._task = asyncio.create_task(
            self._run_loop()
        )

    async def stop(self) -> None:
        self._running = False

        if self._task:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

    async def _run_loop(self) -> None:
        while self._running:
            try:
                stale_connections = (
                    self.connection_registry
                    .get_stale_connections()
                )

                for record in stale_connections:
                    logger.warning(
                        "Disconnecting stale connection %s",
                        record.connection_id,
                    )
                    logger.warning(
                        "STALE CONNECTION FOUND: %s",
                        record.connection_id,
                    )
                    self.connection_registry.disconnect(
                        record.connection_id
                    )

            except Exception:
                logger.exception(
                    "Stale connection cleanup failed"
                )

            await asyncio.sleep(
                self.interval_seconds
            )