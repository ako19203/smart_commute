from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.maintenance import (
    get_stale_connection_worker,
)
from api.gps import router as gps_router
from api.sessions import router as sessions_router
from api.websocket import router as websocket_router
from app.runtime import get_runtime_manager
from api.runtime import (
    router as runtime_router,
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    runtime_manager = get_runtime_manager()
    stale_worker = get_stale_connection_worker()
    await runtime_manager.start_runtime_worker()
    await stale_worker.start()
    try:
        yield
    finally:
        await stale_worker.stop()
        await runtime_manager.stop_runtime_worker()


app = FastAPI(
    title="Smart Commute Runtime API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(sessions_router)
app.include_router(gps_router)
app.include_router(websocket_router)
app.include_router(runtime_router)