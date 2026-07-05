from __future__ import annotations

"""P12-022 — Structured logging configuration for the Gmail service.

Configures structlog with JSON or console output, stdlib integration,
ISO 8601 timestamps, consistent field naming, and optional file rotation.
"""

import logging
import logging.handlers
import sys

import structlog
from structlog.types import EventDict, Processor


def _service_name_processor(service_name: str) -> Processor:
    """Return a processor that injects *service_name* into every event dict."""

    def processor(_logger: object, _method_name: str, event_dict: EventDict) -> EventDict:
        event_dict["service"] = service_name
        return event_dict

    return processor


def configure_gmail_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_output_path: str | None = None,
    service_name: str = "guinevere-gmail",
) -> None:
    """Configure structlog for the Gmail service.

    Sets up structlog with JSON or console output, stdlib integration,
    ISO 8601 timestamps, and optional file rotation logging.
    Safe to call multiple times (``structlog.configure_once``).

    Args:
        log_level: Logging level string (e.g. ``"INFO"``, ``"DEBUG"``).
        log_format: ``"json"`` for ``JSONRenderer``, ``"console"`` for
            ``ConsoleRenderer`` (dev-friendly, colourised).
        log_output_path: Optional file path for persistent log output
            (auto-rotated at 10 MB, up to 5 backups).
        service_name: Service identifier injected into every log event
            under the ``service`` key.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # ------------------------------------------------------------------
    # Standard-library root logger
    # ------------------------------------------------------------------
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear pre-existing handlers so we own the output pipeline.
    root_logger.handlers.clear()

    # ------------------------------------------------------------------
    # structlog processor chain
    # ------------------------------------------------------------------
    shared_processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
        _service_name_processor(service_name),
    ]

    # Final renderer — everything before it is shared between formats.
    if log_format == "console":
        renderer: Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    processors = shared_processors + [renderer]

    # ------------------------------------------------------------------
    # Standard-library handlers
    # ------------------------------------------------------------------
    # Console handler (stdout).  Structlog already renders the final line
    # so the stdlib formatter is a simple %(message)s passthrough.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    # Optional file handler with rotation (10 MB per file, 5 backups).
    if log_output_path:
        file_handler = logging.handlers.RotatingFileHandler(
            log_output_path,
            maxBytes=10_485_760,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(file_handler)

    # ------------------------------------------------------------------
    # structlog configuration (runs once regardless of call count)
    # ------------------------------------------------------------------
    structlog.configure_once(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
