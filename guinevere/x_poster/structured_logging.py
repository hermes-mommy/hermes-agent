from __future__ import annotations

"""P13 X Poster — Structured logging configuration."""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def configure_xposter_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_output_path: str = "",
    service_name: str = "x_poster",
) -> None:
    """Configure structlog for the X Poster service.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format — ``"json"`` or ``"console"``.
        log_output_path: File path for log output. Empty means stdout.
        service_name: Service name injected into every log event.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.EventRenamer("msg"),
    ]

    if log_format == "console":
        renderer: Any = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    processors = shared_processors + [renderer]

    sink: Any = sys.stdout
    if log_output_path:
        try:
            path = Path(log_output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            sink = path.open("a", encoding="utf-8")
        except OSError:
            sink = sys.stdout

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sink),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", level=level, stream=sink)
    logger.info(
        "x_poster.logging_configured",
        level=log_level,
        format=log_format,
        output=log_output_path or "stdout",
        service=service_name,
    )


__all__ = ["configure_xposter_logging"]
