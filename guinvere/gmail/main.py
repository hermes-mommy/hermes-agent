from __future__ import annotations

"""Gmail service entry point — asyncio run for systemd ExecStart.

Usage:
    python -m src.gmail.main
    python src/gmail/main.py

Lifecycle:
    1. Load settings (GmailSettings via pydantic-settings)
    2. Configure structlog logging
    3. Start Prometheus metrics HTTP endpoint
    4. Create async Redis connection
    5. Initialise Hermes runtime (optional, graceful fallback)
    6. Create APScheduler
    7. Build and start GmailService
    8. Register SIGINT/SIGTERM handlers for graceful shutdown
    9. Block on shutdown event
    10. Reverse-order graceful shutdown
"""

import asyncio
import os
import signal
import sys
from typing import Any

import structlog

logger = structlog.get_logger("gmail.main")


def _try_configure_logging() -> None:
    """Configure structlog for the Gmail service.

    Attempts to use ``configure_gmail_logging`` from
    ``src.gmail.structured_logging``.  Falls back to a basic
    JSON‐rendering setup when the module is not yet available.
    """
    try:
        from guinvere.gmail.structured_logging import configure_gmail_logging

        configure_gmail_logging(
            log_level=os.environ.get("GMAIL_LOG_LEVEL", "INFO"),
            log_format=os.environ.get("GMAIL_LOG_FORMAT", "json"),
            log_output_path=os.environ.get("GMAIL_LOG_OUTPUT_PATH"),
            service_name="gmail",
        )
        logger.info("gmail.logging_configured", source="structured_logging")
    except (ImportError, AttributeError) as exc:
        # Fallback: basic structlog config when module not ready
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        logger.info(
            "gmail.logging_fallback",
            reason=str(exc),
        )


def _try_start_metrics_server(port: int) -> None:
    """Start the Prometheus metrics HTTP server on *port*.

    Delegates to ``start_metrics_server`` in ``src.gmail.metrics``
    when available; otherwise logs a warning and continues.
    """
    try:
        from guinvere.gmail.metrics import start_metrics_server

        start_metrics_server(port=port)
        logger.info("gmail.metrics_server_started", port=port)
    except (ImportError, AttributeError) as exc:
        logger.warning(
            "gmail.metrics_server_skipped",
            reason=str(exc),
            port=port,
        )


def _build_redis_client() -> Any:
    """Build an async Redis client from ``REDIS_URL`` env or default."""
    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    client = aioredis.from_url(redis_url, decode_responses=False)
    logger.info("gmail.redis_connected", url=redis_url.partition("@")[2] or "localhost")
    return client


def _register_signal_handlers(stop_event: asyncio.Event, loop: Any) -> None:
    """Register *stop_event* setters for SIGINT and SIGTERM.

    Silently ignores ``NotImplementedError`` on platforms (Windows)
    that do not support ``loop.add_signal_handler``.
    """

    def _handle_signal() -> None:
        logger.info("gmail.shutdown_signal_received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            logger.debug(
                "gmail.signal_handler_not_supported",
                signal=sig.name,
            )


async def main() -> None:
    """Initialise all components and run the Gmail service.

    Designed as a single coroutine so that ``asyncio.run()``
    manages the event loop lifecycle.

    Raises
    ------
    SystemExit
        On fatal initialisation failures (settings, token).
    """
    # ── 1. Load settings ────────────────────────────────────────────────
    try:
        from guinvere.gmail.config import get_gmail_settings

        settings = get_gmail_settings()
        logger.info("gmail.settings_loaded")
    except Exception as exc:
        logger.exception("gmail.settings_failed", error=str(exc))
        sys.exit(1)

    # ── 2. Configure logging ────────────────────────────────────────────
    _try_configure_logging()

    # ── 3. Start Prometheus metrics server ──────────────────────────────
    # NOTE: service.py also starts metrics on same port — leave it to
    # service.py for lifecycle management.
    # _try_start_metrics_server(port=settings.metrics_port)

    # ── 4. Create async Redis connection ─────────────────────────────────
    redis_client = _build_redis_client()

    # ── 5. Create APScheduler ────────────────────────────────────────────
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler()

    # ── 7. Build GmailService ────────────────────────────────────────────
    from guinvere.gmail.service import GmailService

    service = GmailService(
        redis_client=redis_client,
        scheduler=scheduler,
        metrics_port=settings.metrics_port,
        health_port=settings.health_port,
    )

    # ── 8. Signal handling ───────────────────────────────────────────────
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    _register_signal_handlers(stop_event, loop)

    # ── 9. Start the service ─────────────────────────────────────────────
    try:
        await service.start()
        logger.info(
            "gmail.service_started",
            health_port=settings.health_port,
            metrics_port=settings.metrics_port,
        )

        # ── 10. Wait until shutdown signal ───────────────────────────────
        await stop_event.wait()
    except Exception as exc:
        logger.exception("gmail.service_fatal_error", error=str(exc))
        raise
    finally:
        # ── 11. Graceful shutdown ────────────────────────────────────────
        logger.info("gmail.shutting_down")
        try:
            await service.stop()
        except Exception as exc:
            logger.exception("gmail.service_stop_error", error=str(exc))

        try:
            await redis_client.aclose()
        except Exception as exc:
            logger.warning("gmail.redis_close_error", error=str(exc))

        logger.info("gmail.shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
