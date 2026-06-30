from __future__ import annotations

"""X Poster service entry point — asyncio run for systemd ExecStart.

Usage:
    python -m src.x_poster.main
    python src/x_poster/main.py

Lifecycle:
    1. Load settings (XPosterSettings via pydantic-settings)
    2. Configure structlog logging
    3. Create and start XPosterService
    4. Start health HTTP endpoint on 8097
    5. Register SIGINT/SIGTERM handlers for graceful shutdown
    6. Block on shutdown event
    7. Reverse-order graceful shutdown
"""

import asyncio
import signal

import structlog

from .config import get_xposter_settings
from .health import XPosterHealthEndpoint
from .service import XPosterService
from .structured_logging import configure_xposter_logging

logger = structlog.get_logger("x_poster.main")


async def _run() -> int:
    """Run the full X Poster service until shutdown signal."""
    settings = get_xposter_settings()

    configure_xposter_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_output_path=settings.log_output_path,
        service_name="x_poster",
    )

    service = XPosterService(settings=settings)
    health = XPosterHealthEndpoint(service_ref=service, port=settings.health_port)

    stop_event = asyncio.Event()

    def _request_shutdown() -> None:
        logger.info("x_poster.shutdown_requested")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            pass

    try:
        await service.start()
        await health.start()
        logger.info(
            "x_poster.main_started",
            health_port=settings.health_port,
            metrics_port=settings.metrics_port,
            media_root=settings.media_root,
            x_access_token=settings.x_access_token[:8] + "..." if settings.x_access_token else "not_set",
        )
        _ = await stop_event.wait()
        return 0
    except Exception as exc:
        logger.exception("x_poster.main_fatal", error=str(exc))
        return 1
    finally:
        try:
            await health.stop()
        except Exception as exc:
            logger.warning("x_poster.health_stop_failed", error=str(exc))
        try:
            await service.stop()
        except Exception as exc:
            logger.warning("x_poster.service_stop_failed", error=str(exc))


def main() -> None:
    """Synchronous process entry point."""
    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
