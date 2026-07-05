"""HTTP route definitions for Guinevere.

Ported from ``guinevere/core/main.py`` L910-1037 (/metrics, /health, /health/detailed,
/) and extended with /health/ready (readiness), /health/agent (agent state).

Design:
  - ``/`` — root welcome.
  - ``/health`` — liveness probe (always 200).
  - ``/health/ready`` — readiness probe (fail-soft PG/Redis, D2).
  - ``/health/agent`` — agent state (turn/token/emotion, NEW per r11).
  - ``/metrics`` — Prometheus exposition.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from guinevere.http.health import build_agent_state, build_liveness, build_readiness

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    """Root welcome endpoint."""
    return {"message": "Guinevere de Baroque is online.", "status": "active"}


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always 200 if the process is running."""
    return await build_liveness()


@router.get("/health/ready")
async def health_ready(request: Request) -> Response:
    """Readiness probe — config loaded, background tasks, infra fail-soft.

    PG/Redis being absent reports ``degraded`` (still 200) rather than 503,
    per Decision D2 (local-runtime-only).  Only returns 503 when the
    overall status is ``not_ready``.
    """
    app_state = request.app.state
    body, status_code = await build_readiness(app_state)

    return Response(
        content=json.dumps(body),
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/health/agent")
async def health_agent(request: Request) -> dict[str, object]:
    """Agent state — current turn, token usage, emotion.

    All fields are ``None`` until M3 consciousness loop is wired (W6).
    """
    app_state = request.app.state
    return await build_agent_state(app_state)


@router.get("/metrics")
async def metrics() -> PlainTextResponse:
    """Prometheus scrape endpoint."""
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
