"""FastAPI routes for Guinevere internal API — loop management."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Any, Optional

from src.core.api.auth import get_api_key

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1")


class LoopRequest(BaseModel):
    """Request body for creating a new loop."""

    task: str = Field(..., description="Human-readable task description")
    priority: str = Field(default="normal", description="Loop priority level")
    max_phases: int = Field(default=7, description="Maximum SDLC phases")
    goal: Optional[str] = Field(default=None, description="Optional loop goal")


class LoopResponse(BaseModel):
    """Response shape for loop endpoints."""

    loop_id: str
    status: str
    current_phase: int
    task: str
    goal: Optional[str] = None


def _get_loop_manager(request: Request):
    """Extract LoopManager from app state."""
    manager = getattr(request.app.state, "loop_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Loop manager not initialized",
        )
    return manager


@router.get("/loops")
async def list_loops(request: Request) -> dict[str, Any]:
    """List all loops with summary counts."""
    manager = _get_loop_manager(request)
    try:
        loops = await manager.list_loops()
    except Exception:
        logger.exception("routes.list_loops_failed")
        raise HTTPException(status_code=500, detail="Failed to list loops")
    active = sum(1 for l in loops if l.get("status") == "running")
    completed = sum(1 for l in loops if l.get("status") == "complete")
    logger.info("list_loops_requested", count=len(loops))
    return {"loops": loops, "active": active, "completed": completed}


@router.post("/loops", response_model=LoopResponse, status_code=201)
async def create_loop(
    request: LoopRequest,
    req: Request,
    _api_key: str = Depends(get_api_key),
) -> LoopResponse:
    """Create a new loop instance."""
    manager = _get_loop_manager(req)
    try:
        loop_id = await manager.start_loop(
            task=request.task,
            goal=request.goal or request.task,
            priority=request.priority,
        )
    except Exception:
        logger.exception("routes.create_loop_failed")
        raise HTTPException(status_code=500, detail="Failed to create loop")
    logger.info("loop_created", loop_id=loop_id, task=request.task)
    return LoopResponse(
        loop_id=loop_id,
        status="running",
        current_phase=1,
        task=request.task,
        goal=request.goal,
    )


@router.get("/loops/{loop_id}")
async def get_loop(loop_id: str, request: Request) -> dict[str, Any]:
    """Get details of a specific loop."""
    manager = _get_loop_manager(request)
    try:
        status = await manager.get_loop_status(loop_id)
    except Exception:
        logger.exception("routes.get_loop_failed", loop_id=loop_id)
        raise HTTPException(status_code=500, detail="Failed to get loop status")
    if status is None:
        raise HTTPException(status_code=404, detail=f"Loop {loop_id} not found")
    logger.info("get_loop_requested", loop_id=loop_id)
    return status


@router.post("/loops/{loop_id}/cancel")
async def cancel_loop(
    loop_id: str,
    request: Request,
    _api_key: str = Depends(get_api_key),
) -> dict[str, Any]:
    """Cancel a running loop."""
    manager = _get_loop_manager(request)
    try:
        result = await manager.stop_loop(loop_id)
    except Exception:
        logger.exception("routes.cancel_loop_failed", loop_id=loop_id)
        raise HTTPException(status_code=500, detail="Failed to cancel loop")
    logger.info("cancel_loop_requested", loop_id=loop_id)
    return result