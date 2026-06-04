"""Guinevere Core - Main FastAPI Application."""
import os
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from src.observability import init_sentry

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

    # P8-012: Initialize Sentry error tracking
    init_sentry(
        environment="production",
        release="0.1.0",
    )

    loop_manager = LoopManager()
    app.state.loop_manager = loop_manager

    guardian_task = asyncio.create_task(
        loop_manager.guardian.monitor(),
        name="guardian-monitor",
    )
    app.state.guardian_task = guardian_task

    # P8-019: Register monthly cost report scheduler
    from src.core.services.monthly_report import register_monthly_report_scheduler

    report_scheduler = register_monthly_report_scheduler()
    report_scheduler.start()
    app.state.report_scheduler = report_scheduler

    # RG-004: Start surveillance consumer background worker
    surveillance_task = None
    try:
        import redis.asyncio as aioredis_surv
        from sqlalchemy.ext.asyncio import (
            AsyncSession as _AsyncSession,
            async_sessionmaker as _async_sessionmaker,
            create_async_engine as _create_async_engine,
        )
        from src.surveillance.consumer import SurveillanceConsumer
        from src.surveillance.redis_buffer import RedisSurveillanceBuffer

        _redis_password = os.environ.get("REDIS_PASSWORD", "")
        _redis_client = aioredis_surv.Redis(
            host="localhost",
            port=6380,
            db=2,
            username="guinevere_core",
            password=_redis_password,
            decode_responses=True,
        )
        _buffer = RedisSurveillanceBuffer(_redis_client)

        _db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://guinevere_core@localhost:5433/guinevere_core",
        )
        _engine = _create_async_engine(_db_url, pool_size=2, pool_pre_ping=True)
        _session_factory = _async_sessionmaker(
            _engine, class_=_AsyncSession, expire_on_commit=False,
        )

        _consumer = SurveillanceConsumer(
            buffer=_buffer, db_session_factory=_session_factory,
        )
        surveillance_task = asyncio.create_task(
            _consumer.run(), name="surveillance-consumer",
        )
        app.state.surveillance_consumer = _consumer
        app.state.surveillance_task = surveillance_task
        app.state.surveillance_engine = _engine
        logger.info("surveillance_consumer_started")
    except Exception as surv_err:
        logger.warning("surveillance_consumer_start_failed", error=str(surv_err))

    logger.info("guinevere_starting", version="0.1.0")
    yield
    logger.info("guinevere_stopping")

    # Graceful shutdown
    report_scheduler.shutdown(wait=False)

    # RG-004: Graceful surveillance consumer shutdown
    surv_consumer = getattr(app.state, "surveillance_consumer", None)
    surv_task = getattr(app.state, "surveillance_task", None)
    surv_engine = getattr(app.state, "surveillance_engine", None)
    if surv_consumer is not None:
        surv_consumer.stop()
    if surv_task is not None:
        surv_task.cancel()
        try:
            await surv_task
        except asyncio.CancelledError:
            pass
    if surv_engine is not None:
        await surv_engine.dispose()
    logger.info("surveillance_consumer_stopped")

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

# ---------------------------------------------------------------------------
# RG-007: Prometheus metrics endpoint
# ---------------------------------------------------------------------------
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
import time

_REQUESTS_TOTAL = Counter(
    "guinevere_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
_REQUEST_DURATION = Histogram(
    "guinevere_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
_HEALTH_FAILURES = Counter(
    "guinevere_health_check_failures_total",
    "Health check component failures",
    ["component", "check"],
)


class _PrometheusMiddleware(BaseHTTPMiddleware):
    """Track request count and duration for Prometheus."""

    async def dispatch(self, request: StarletteRequest, call_next):  # type: ignore[override]
        method = request.method
        endpoint = request.url.path
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        _REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=str(response.status_code)).inc()
        _REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        return response


app.add_middleware(_PrometheusMiddleware)


@app.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


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

    # RG-009: PostgreSQL connectivity check
    try:
        import asyncpg

        _pg_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://guinevere_core@localhost:5433/guinevere_core",
        )
        # Convert asyncpg URL for sync check
        _pg_url_sync = _pg_url.replace("postgresql+asyncpg://", "postgresql://")
        _pg_conn = await asyncpg.connect(_pg_url_sync, timeout=2)
        await _pg_conn.fetchval("SELECT 1")
        await _pg_conn.close()
        components["postgresql"] = {"status": "ok"}
    except Exception:
        components["postgresql"] = {"status": "unavailable"}
        _HEALTH_FAILURES.labels(component="postgresql", check="connectivity").inc()

    # RG-009: 9Router availability check
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2.0) as _client:
            _resp = await _client.get("http://localhost:20128/v1/models")
            if _resp.status_code == 200:
                components["9router"] = {"status": "ok", "models": len(_resp.json().get("data", []))}
            else:
                components["9router"] = {"status": "degraded", "http_status": _resp.status_code}
                _HEALTH_FAILURES.labels(component="9router", check="models_endpoint").inc()
    except Exception:
        components["9router"] = {"status": "unavailable"}
        _HEALTH_FAILURES.labels(component="9router", check="connectivity").inc()

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