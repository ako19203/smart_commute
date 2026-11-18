from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from runtime.models import SessionState


@dataclass
class QueuedGPSUpdate:
    """
    Ingestion unit for async runtime processing.
    """

    session_id: str
    latitude: float
    longitude: float
    speed_mps: float = 0.0
    enqueued_at: datetime = field(default_factory=datetime.utcnow)
    result_future: Optional[asyncio.Future[SessionState]] = None


class RuntimeQueue:
    """
    Async queue used to decouple GPS ingestion from processing.
    """

    STOP = "__RUNTIME_QUEUE_STOP__"

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: asyncio.Queue[object] = asyncio.Queue(
            maxsize=maxsize
        )

    async def put(self, item: QueuedGPSUpdate) -> None:
        await self._queue.put(item)

    async def put_stop_signal(self) -> None:
        await self._queue.put(self.STOP)

    async def get(self) -> object:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    def qsize(self) -> int:
        return self._queue.qsize()
