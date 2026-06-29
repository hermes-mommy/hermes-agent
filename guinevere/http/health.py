"""Health check logic for Guinevere HTTP endpoints.

Ported from ``src/core/main.py`` L916-1008 (/health, /health/detailed),
extended with readiness and agent-state probes.

Design decisions (per r11):
  - Liveness (``/health``) always returns 200 — process alive.
  - Readiness (``/health/ready``) is fail-soft (D2): PG/Redis missing
    reports ``degraded`` but does NOT force 503 unless config itself
    failed to load.
  - Agent state (``/health/agent``) is NEW per r11 — reports current
    turn, token usage, emotion.
"""

from __future__ import annotations

import asyncio
from typing import Any


async def check_postgres(pg_dsn: str) -> dict[str, Any]:
    """Ping PostgreSQL via asyncpg with a 2-second timeout.

    Returns ``{"status": "ok"}`` or ``{"status": "unavailable", ...}``.
    Never raises — fail-soft (D2).
    """
    try:
        import asyncpg  # noqa: F401

        dsn = pg_dsn.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=2.0)
        try:
            await conn.fetchval("SELECT 1")
        finally:
            await conn.close()
        return {"status": "ok"}
    except Exception:
        return {"status": "unavailable"}


async def check_redis(redis_url: str) -> dict[str, Any]:
    """Ping Redis with a 2-second timeout.

    Returns ``{"status": "ok"}`` or ``{"status": "unavailable", ...}``.
    Never raises — fail-soft (D2).
    """
    try:
        import redis.asyncio as aioredis  # noqa: F401

        client = aioredis.from_url(redis_url, socket_connect_timeout=2)
        try:
            await asyncio.wait_for(client.ping(), timeout=2.0)
        finally:
            await client.aclose()
        return {"status": "ok"}
    except Exception:
        return {"status": "unavailable"}


async def build_liveness() -> dict[str, Any]:
    """Liveness probe — always healthy if the process is running."""
    return {
        "status": "healthy",
        "service": "guinevere-core",
        "version": "0.2.0",
    }


async def build_readiness(app_state: Any) -> tuple[dict[str, Any], int]:
    """Readiness probe — config loaded, background tasks alive, infra fail-soft.

    Returns a tuple of (body_dict, status_code).
    """
    components: dict[str, dict[str, object]] = {}
    overall_status = "ready"

    # Config check (critical)
    settings = getattr(app_state, "settings", None)
    if settings is not None:
        components["config"] = {"status": "ok"}
    else:
        components["config"] = {"status": "degraded", "reason": "settings_not_loaded"}
        # Config absent but process alive — degraded, not hard-down.
        overall_status = "degraded"

    # Consciousness task check (W6 placeholder — always "placeholder" for now)
    tg = getattr(app_state, "task_group", None)
    if tg is not None:
        components["consciousness"] = {"status": "placeholder"}
    else:
        components["consciousness"] = {"status": "not_started"}

    # PG / Redis — fail-soft (D2): degrade, don't 503.
    pg_dsn = getattr(getattr(settings, "database", None), "pg_dsn", "") if settings else ""
    redis_url = getattr(getattr(settings, "redis", None), "url", "") if settings else ""

    if pg_dsn:
        components["postgresql"] = await check_postgres(pg_dsn)
        if components["postgresql"]["status"] != "ok":
            overall_status = "degraded"
    else:
        components["postgresql"] = {"status": "not_configured"}

    if redis_url:
        components["redis"] = await check_redis(redis_url)
        if components["redis"]["status"] != "ok":
            overall_status = "degraded"
    else:
        components["redis"] = {"status": "not_configured"}

    status_code = 200
    if overall_status == "not_ready":
        status_code = 503

    return {
        "status": overall_status,
        "service": "guinevere-core",
        "version": "0.2.0",
        "components": components,
    }, status_code


async def build_agent_state(app_state: Any) -> dict[str, Any]:
    """Agent state report — current turn, token usage, emotion.

    All fields are optional (absent until M3/M6 wire them).
    """
    state: dict[str, object] = {"service": "guinevere-core", "version": "0.2.0"}

    # M3 will populate app_state.consciousness with turn/token/emotion.
    consciousness = getattr(app_state, "consciousness", None)
    if consciousness is not None:
        state["turn"] = getattr(consciousness, "current_turn", None)
        state["tokens_used"] = getattr(consciousness, "tokens_used", None)
        state["emotion"] = getattr(consciousness, "emotion", None)
    else:
        state["turn"] = None
        state["tokens_used"] = None
        state["emotion"] = None

    return state
