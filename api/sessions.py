from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.runtime import get_runtime_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    origin_coordinates: tuple[float, float]
    destination_name: str = Field(min_length=1)
    destination_coordinates: tuple[float, float]
    user_id: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
def start_session(payload: StartSessionRequest) -> dict:
    runtime_manager = get_runtime_manager()
    try:
        state = runtime_manager.start_session(
            session_id=payload.session_id,
            origin_coordinates=payload.origin_coordinates,
            destination_name=payload.destination_name,
            destination_coordinates=payload.destination_coordinates,
            user_id=payload.user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return {"status": "started", "state": state.__dict__}


@router.get("/{session_id}", status_code=status.HTTP_200_OK)
def get_session_state(session_id: str) -> dict:
    runtime_manager = get_runtime_manager()
    try:
        state = runtime_manager.get_session_state(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return {"session_id": session_id, "state": state.__dict__}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def end_session(session_id: str) -> None:
    runtime_manager = get_runtime_manager()
    try:
        runtime_manager.end_session(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
