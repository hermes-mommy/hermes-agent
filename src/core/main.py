"""Guinevere Core - Main FastAPI Application."""
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# P3-015 consolidation scheduler registration (optional — no DB by default)
# ---------------------------------------------------------------------------
# To activate the daily consolidation scheduler at runtime, inject an async
# SQLAlchemy session factory (async_sessionmaker) into the lifespan:
#
#   from apscheduler.schedulers.asyncio import AsyncIOScheduler
#   from src.memory.consolidation import register_consolidation_job
#
#   scheduler = AsyncIOScheduler()
#   await register_consolidation_job(scheduler, session_factory=AsyncSessionLocal)
#   scheduler.start()
#
# DO NOT start a live APScheduler without a valid async DB sessionmaker, as
# the consolidation job requires database access.  In tests, use the synthetic
# consolidation unit tests (tests/memory/test_consolidation.py) which do not
# require a running scheduler or real database.
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from src.loops.manager import LoopManager

    loop_manager = LoopManager()
    app.state.loop_manager = loop_manager

    guardian_task = asyncio.create_task(
        loop_manager.guardian.monitor(),
        name="guardian-monitor",
    )
    app.state.guardian_task = guardian_task

    logger.info("guinevere_starting", version="0.1.0")
    yield
    logger.info("guinevere_stopping")

    # Graceful shutdown
    await loop_manager.guardian.stop()
    guardian_task.cancel()
    try:
        await guardian_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Guinevere Core",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "guinevere-core", "version": "0.1.0"}


@app.get("/health/detailed")
async def health_detailed(request: Request):
    """Detailed health check with component status."""
    import asyncio
    import os

    components: dict[str, dict[str, object]] = {}
    status_code = 200

    # Loop Manager check
    loop_mgr = getattr(request.app.state, "loop_manager", None)
    if loop_mgr is not None:
        try:
            loops = await loop_mgr.list_loops()
            components["loop_manager"] = {
                "status": "ok",
                "active_loops": len(loops),
            }
        except Exception:
            components["loop_manager"] = {"status": "error"}
            status_code = 503
    else:
        components["loop_manager"] = {"status": "not_initialized"}
        status_code = 503

    # Guardian check
    guardian_task = getattr(request.app.state, "guardian_task", None)
    if guardian_task is not None and not guardian_task.done():
        components["guardian"] = {"status": "ok"}
    else:
        components["guardian"] = {"status": "not_running"}
        status_code = 503

    # Redis connectivity (optional — fail-soft, don't block health)
    try:
        import redis.asyncio as aioredis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
        r = aioredis.from_url(redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        components["redis"] = {"status": "ok"}
    except Exception:
        components["redis"] = {"status": "unavailable"}
        # Redis is non-critical for health — don't set 503

    return JSONResponse(
        status_code=status_code,
        content={
            "service": "guinevere-core",
            "version": "0.1.0",
            "components": components,
        },
    )


@app.get("/")
async def root():
    return {"message": "Guinevere de Baroque is online.", "status": "active"}


# ---------------------------------------------------------------------------
# P5-001: Internal API router — loop management
# ---------------------------------------------------------------------------
from src.core.api.routes import router

app.include_router(router)

# ---------------------------------------------------------------------------
# P7-001: Surveillance webhook receiver
# ---------------------------------------------------------------------------
from src.surveillance.router import surveillance_router

app.include_router(surveillance_router)