from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.runtime import get_runtime_manager

router = APIRouter(prefix="/gps", tags=["gps"])


class GPSIngestRequest(BaseModel):
    session_id: str = Field(min_length=1)
    latitude: float
    longitude: float
    speed_mps: float = 0.0
    await_result: bool = False


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_gps_update(payload: GPSIngestRequest) -> dict:
    runtime_manager = get_runtime_manager()
    try:
        result = await runtime_manager.enqueue_gps_update(
            session_id=payload.session_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed_mps=payload.speed_mps,
            await_result=payload.await_result,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if result is None:
        return {
            "status": "queued",
            "session_id": payload.session_id,
        }

    return {
        "status": "processed",
        "session_id": payload.session_id,
        "state": result.__dict__,
    }
