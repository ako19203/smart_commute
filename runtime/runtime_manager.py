from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional

from runtime.models import GPSUpdate, SessionState
from runtime.gps_pipeline import GPSPipeline
from runtime.event_bus import EventBus
from runtime.runtime_session import RuntimeSession
from runtime.session_manager import SessionManager
from runtime.runtime_queue import QueuedGPSUpdate, RuntimeQueue
from runtime.runtime_worker import RuntimeWorker

if TYPE_CHECKING:
    from runtime.realtime_dispatcher import RealtimeDispatcher


class RuntimeManager:
    """
    Central orchestration layer for realtime runtime infrastructure.

    Responsibilities:
    - Own all active runtime sessions
    - Coordinate runtime lifecycle
    - Allocate RuntimeSession instances
    - Manage runtime-level infrastructure references

    This becomes the authoritative runtime orchestrator.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        event_bus: EventBus,
        gps_pipeline: Optional[GPSPipeline] = None,
        runtime_queue: Optional[RuntimeQueue] = None,
        dispatcher: Optional[RealtimeDispatcher] = None,
    ) -> None:
        self.session_manager = session_manager
        self.event_bus = event_bus
        self.gps_pipeline = gps_pipeline or GPSPipeline(
            event_bus=event_bus
        )
        self.runtime_queue = runtime_queue or RuntimeQueue()
        self.dispatcher = dispatcher
        self.runtime_worker: Optional[RuntimeWorker] = None

        # Single authoritative source for active runtime sessions.
        self.active_sessions: Dict[str, RuntimeSession] = {}

    def start_session(
        self,
        session_id: str,
        origin_coordinates: tuple,
        destination_name: str,
        destination_coordinates: tuple,
        user_id: Optional[str] = None,
    ) -> SessionState:
        """
        Creates and registers a new active runtime session.
        """

        if session_id in self.active_sessions:
            raise ValueError(
                f"Runtime session '{session_id}' already exists."
            )

        state = self.session_manager.create_session(
            session_id=session_id,
            origin_coordinates=origin_coordinates,
            destination_name=destination_name,
            destination_coordinates=destination_coordinates,
        )

        runtime_session = RuntimeSession(
            session_id=session_id,
            user_id=user_id,
            state=state,
            gps_pipeline=self.gps_pipeline,
            event_bus=self.event_bus,
        )

        self.active_sessions[session_id] = runtime_session

        self.event_bus.emit(
            "SESSION_STARTED",
            {
                "session_id": session_id,
                "destination_name": destination_name,
                "user_id": user_id,
            }
        )

        return runtime_session.get_state()

    def process_gps_update(
        self,
        session_id: str,
        latitude: float,
        longitude: float,
        speed_mps: float = 0.0,
    ) -> SessionState:
        """
        Processes GPS update for an active runtime session.
        """
        session = self.active_sessions.get(session_id)

        if session is None:
            raise ValueError(
                f"Runtime session '{session_id}' does not exist."
            )

        if not session.is_active:
            raise RuntimeError(
                f"Runtime session '{session_id}' is inactive."
            )

        gps_update = GPSUpdate(
            session_id=session_id,
            latitude=latitude,
            longitude=longitude,
            speed_mps=speed_mps,
        )
        updated_state = session.process_gps_update(gps_update)
        self.session_manager.state_store.update_session(
            updated_state
        )

        return updated_state

    async def enqueue_gps_update(
        self,
        session_id: str,
        latitude: float,
        longitude: float,
        speed_mps: float = 0.0,
        await_result: bool = False,
    ) -> Optional[SessionState]:
        """
        Async runtime ingress API that decouples ingestion
        from processing by pushing updates to RuntimeQueue.
        """
        session = self.active_sessions.get(session_id)
        if session is None:
            raise ValueError(
                f"Runtime session '{session_id}' does not exist."
            )
        if not session.is_active:
            raise RuntimeError(
                f"Runtime session '{session_id}' is inactive."
            )

        result_future: Optional[
            asyncio.Future[SessionState]
        ] = None
        if await_result:
            loop = asyncio.get_running_loop()
            result_future = loop.create_future()

        queued_update = QueuedGPSUpdate(
            session_id=session_id,
            latitude=latitude,
            longitude=longitude,
            speed_mps=speed_mps,
            result_future=result_future,
        )
        await self.runtime_queue.put(queued_update)
        self.event_bus.emit(
            "GPS_UPDATE_ENQUEUED",
            {
                "session_id": session_id,
                "queue_size": self.runtime_queue.qsize(),
            },
        )

        if not result_future:
            return None
        return await result_future

    def end_session(
        self,
        session_id: str,
    ) -> None:
        """
        Terminates and removes a runtime session.
        """

        session = self.active_sessions.get(session_id)

        if session is None:
            raise ValueError(
                f"Runtime session '{session_id}' does not exist."
            )

        session.terminate()
        self.session_manager.terminate_session(session_id)

        del self.active_sessions[session_id]
        self.event_bus.emit(
            "SESSION_ENDED",
            {
                "session_id": session_id,
            }
        )

    def get_session_state(
        self,
        session_id: str,
    ) -> SessionState:
        """
        Returns current state for an active runtime session.
        """
        session = self.active_sessions.get(session_id)

        if session is None:
            raise ValueError(
                f"Runtime session '{session_id}' does not exist."
            )

        return session.get_state()

    def session_exists(
        self,
        session_id: str,
    ) -> bool:
        """
        Returns whether a runtime session exists.
        """

        return session_id in self.active_sessions

    def list_active_sessions(self) -> List[str]:
        """
        Returns all active runtime session IDs.
        """

        return list(self.active_sessions.keys())

    def active_session_count(self) -> int:
        """
        Returns number of active runtime sessions.
        """

        return len(self.active_sessions)

    def terminate_all_sessions(self) -> None:
        """
        Gracefully terminates all active runtime sessions.
        """
        for session_id in list(self.active_sessions.keys()):
            self.end_session(session_id)

    async def start_runtime_worker(self) -> None:
        """
        Starts async runtime worker for queued GPS ingestion.
        """
        if self.runtime_worker and self.runtime_worker.is_running:
            return

        self.runtime_worker = RuntimeWorker(
            manager=self,
            runtime_queue=self.runtime_queue,
            dispatcher=self.dispatcher,
        )
        await self.runtime_worker.start()
        self.event_bus.emit(
            "RUNTIME_WORKER_STARTED",
            {"queue_size": self.runtime_queue.qsize()},
        )

    async def stop_runtime_worker(self) -> None:
        """
        Stops async runtime worker.
        """
        if not self.runtime_worker:
            return

        await self.runtime_worker.stop()
        self.event_bus.emit("RUNTIME_WORKER_STOPPED", {})

    def __repr__(self) -> str:
        return (
            f"RuntimeManager("
            f"active_sessions={len(self.active_sessions)})"
        )