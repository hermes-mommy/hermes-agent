"""FastAPI application factory with lifespan-managed TaskGroup.

Ported from ``guinevere/core/main.py`` L239-847 (lifespan) and L847-1052 (app).

Design (per r11):
  - M15's lifespan OWNS the TaskGroup.
  - M3 consciousness loop (W6) and M16 surveillance consumer (W5) run
    INSIDE the lifespan's TaskGroup — not competing.
  - Two-phase shutdown: ``asyncio.Event`` signal + 30s graceful drain,
    then cancel.
  - HTTP-triggered agent interactions gated by ``asyncio.Semaphore``.
  - D2: fail-soft — PG/Redis may be absent without crashing.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog.logging  # side-effect: registers stdlib log handler

from fastapi import FastAPI

from guinevere.http.middleware import PrometheusMiddleware
from guinevere.http.rate_limit import RateLimitMiddleware
from guinevere.http.routes import router

logger = logging.getLogger("guinevere.http")

# Singleton — ``create_app`` returns the same object after first call.
_app: FastAPI | None = None

# Maximum concurrent HTTP-triggered agent interactions (r11 S4).
_MAX_CONCURRENT_AGENTS: int = 5


async def _noop_placeholder() -> None:
    """Placeholder task — replaced by M3 consciousness substrates (W6).

    This coroutine simply blocks until cancelled, acting as a stand-in
    inside the TaskGroup so the lifespan structure is complete before
    M3 and M5 wire their real tasks.
    """
    try:
        await asyncio.Event().wait()  # block forever (until cancelled)
    except asyncio.CancelledError:
        pass




@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager — starts background TaskGroup, yields, shuts down.

    Lifecycle:
      1. Load config (fail-soft: settings=None is acceptable).
      2. Start ``asyncio.TaskGroup`` with placeholder tasks for M3/M16.
      3. ``yield`` — FastAPI serves requests.
      4. Two-phase shutdown: set ``_shutdown_event``, wait 30s, then cancel.
    """
    # ── Phase 0: load config (fail-soft) ──────────────────────────────
    settings = None
    try:
        from guinevere.config import load_settings

        settings = load_settings()
        app.state.settings = settings
        logger.info("config_loaded")
    except Exception as e:
        logger.warning("config_load_failed: %s", e, exc_info=True)
        app.state.settings = None

    # ── Phase 1: concurrency gate ─────────────────────────────────────
    app.state.agent_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_AGENTS)
    logger.info("agent_semaphore_created", max_concurrent=_MAX_CONCURRENT_AGENTS)

    # ── Phase 1b: runtime log level ────────────────────────────────────
    # Suppress DEBUG-level structlog noise (consciousness thought stream
    # generates ~30 log lines/sec at DEBUG, filling syslog in hours).
    # structlog's default processor chain routes through stdlib logging,
    # so setting the stdlib level is sufficient.
    for _ns in ("consciousness", "discord", "life_kernel", "channels", "x_poster"):
        logging.getLogger(f"guinevere.{_ns}").setLevel(logging.INFO)
    logging.getLogger("guinevere").setLevel(logging.INFO)

    # ── Phase 2: optional PG pool (fail-soft) ─────────────────────────
    pg_pool: Any = None
    if settings is not None:
        pg_dsn: str = settings.database.pg_dsn
        if pg_dsn:
            try:
                import asyncpg

                pg_pool = await asyncpg.create_pool(pg_dsn, min_size=1, max_size=5)
                app.state.pg_pool = pg_pool
                logger.info("pg_pool_created")
            except Exception as e:
                logger.warning("pg_pool_creation_failed: %s", e, exc_info=True)
                app.state.pg_pool = None

    # ── Phase 3: optional Redis client (fail-soft) ────────────────────
    redis_client: Any = None
    if settings is not None:
        redis_url: str = settings.redis.url
        if redis_url:
            try:
                import redis.asyncio as aioredis

                redis_client = aioredis.from_url(redis_url)
                app.state.redis_client = redis_client
                logger.info("redis_client_created")
            except Exception as e:
                logger.warning("redis_client_creation_failed: %s", e, exc_info=True)
                app.state.redis_client = None

    # ── Phase 4: start TaskGroup with real M3 + placeholder M16 ──────
    _shutdown_event = asyncio.Event()
    app.state.shutdown_event = _shutdown_event

    async with asyncio.TaskGroup() as tg:
        app.state.task_group = tg

        # M3 consciousness loop (P5 — delegates to Hermes AIAgent single brain).
        # The consciousness loop does NOT call the LLM itself; it delegates to
        # a Hermes AIAgent routed through 9router (provider=custom, model=
        # guinevere, localhost:20128). Built with no _guinevere_settings so
        # Group G consciousness-wire in agent_init no-ops (breaks the circular:
        # the brain must not build its own consciousness loop). Fail-soft.
        _consciousness_enabled = True
        if settings is not None:
            _cc = getattr(settings, "consciousness", None)
            if _cc is not None and not getattr(_cc, "enabled", True):
                _consciousness_enabled = False
                logger.info("m3_consciousness_disabled_by_config")

        if not _consciousness_enabled:
            consciousness_task = tg.create_task(
                _noop_placeholder(),
                name="m3-consciousness-disabled",
            )
            app.state.consciousness_loop = None
        else:
            try:
                from guinevere.consciousness import THOUGHT_TYPE_NAMES, ConsciousnessLoop
                from run_agent import AIAgent

                _consciousness_brain = AIAgent(
                    base_url="http://localhost:20128/v1",
                    api_key="sk-noauth",
                    provider="custom",
                    model="guinevere",
                    enabled_toolsets=[],
                )
                _redis = getattr(app.state, "redis_client", None)
                _consciousness_loop = ConsciousnessLoop(
                    llm_router=_consciousness_brain,
                    settings=settings,
                    redis_client=_redis,
                )
                _consciousness_loop.on_session_start()

                consciousness_task = tg.create_task(
                    _consciousness_loop.run(),
                    name="m3-consciousness",
                )
                app.state.consciousness_loop = _consciousness_loop
                logger.info("m3_consciousness_wired", thought_types=len(THOUGHT_TYPE_NAMES))
            except Exception as e:
                logger.warning("m3_consciousness_wire_failed: %s", e, exc_info=True)
                consciousness_task = tg.create_task(
                    _noop_placeholder(),
                    name="m3-consciousness-fallback",
                )
                app.state.consciousness_loop = None

        app.state.consciousness_task = consciousness_task

        # M16 surveillance consumer wires here (W5)
        surveillance_task = tg.create_task(
            _noop_placeholder(),
            name="m16-surveillance-placeholder",
        )
        app.state.surveillance_task = surveillance_task

        logger.info("task_group_started", tasks=["m3-consciousness", "m16-placeholder"])

        yield  # ── FastAPI serves requests here ──

        # ── Phase 5: two-phase shutdown ───────────────────────────────
        # Signal background tasks to drain gracefully via the shutdown event,
        # then cancel. NOTE (W4 audit F01): the 30s bounded drain window is
        # deferred until W6 — current placeholder tasks block on their own
        # asyncio.Event forever, so awaiting them would always hit the 30s
        # timeout (hanging test teardown). Once W6 wires real drainable M3
        # substrates, add `await asyncio.wait_for(gather(...), timeout=30)`
        # before the cancel. Instant-cancel is correct for placeholders.
        logger.info("shutdown_signaled")
        _shutdown_event.set()

        # Gracefully stop the consciousness loop (signals substrates).
        _cl = getattr(app.state, "consciousness_loop", None)
        if _cl is not None:
            _cl.on_session_end()

        # Cancel all tasks in the group; the TaskGroup will wait for
        # them to finish (CancelledError) before exiting.
        consciousness_task.cancel()
        surveillance_task.cancel()

        # TaskGroup exit waits for cancelled tasks to complete.

    # ── Phase 6: cleanup shared resources ─────────────────────────────
    app.state.task_group = None
    app.state.agent_semaphore = None

    if pg_pool is not None:
        with contextlib.suppress(Exception):
            await pg_pool.close()
        logger.info("pg_pool_closed")

    if redis_client is not None:
        with contextlib.suppress(Exception):
            await redis_client.aclose()
        logger.info("redis_client_closed")

    app.state.pg_pool = None
    app.state.redis_client = None
    app.state.settings = None
    logger.info("guinevere_http_shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure the Guinevere FastAPI application.

    Returns a singleton — subsequent calls return the same instance.
    """
    global _app
    if _app is not None:
        return _app

    new_app = FastAPI(
        title="Guinevere Core",
        version="0.2.0",
        lifespan=_lifespan,
    )

    # Middleware (order matters: outermost first)
    new_app.add_middleware(PrometheusMiddleware)
    new_app.add_middleware(RateLimitMiddleware)

    # Routes
    new_app.include_router(router)

    _app = new_app
    return _app


# Module-level ``app`` for ``uvicorn guinevere.http.server:app``.
app = create_app()
