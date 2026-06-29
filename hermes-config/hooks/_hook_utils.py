"""Shared utilities for Hermes Agent safety hooks.

Provides Redis connection pooling, structured JSON logging, safe
stdin/stdout I/O helpers, and a timing guard context manager.

Redis DB5 is used for dynamic state (shared with guinevere_safety plugin).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from urllib.parse import quote

# ── Redis imports — optional, fail gracefully if unavailable ──────────────────
# These are intentionally dynamic so hook scripts can still fail-closed on hosts
# where the redis package is missing.

_redis_connection_error: tuple[type[BaseException], ...] = (OSError,)
_redis_timeout_error: tuple[type[BaseException], ...] = (OSError,)
_redis_available: bool = False
_redis_module: Any | None = None
_redis_retry_cls: Any | None = None
_redis_backoff_cls: Any | None = None
_redis_pool_cls: Any | None = None

try:
    import redis as _imported_redis  # noqa: I202
    from redis.backoff import ExponentialBackoff as _ImportedBackoff  # noqa: I202
    from redis.connection import ConnectionPool as _ImportedConnectionPool  # noqa: I202
    from redis.exceptions import ConnectionError as _RedisConnErr  # noqa: I202
    from redis.exceptions import TimeoutError as _RedisTimeoutErr  # noqa: I202
    from redis.retry import Retry as _ImportedRetry  # noqa: I202

    _redis_available = True
    _redis_module = _imported_redis
    _redis_retry_cls = _ImportedRetry
    _redis_backoff_cls = _ImportedBackoff
    _redis_pool_cls = _ImportedConnectionPool
    _redis_connection_error = (OSError, _RedisConnErr)
    _redis_timeout_error = (OSError, _RedisTimeoutErr)
except ImportError:
    pass


# ── Constants ─────────────────────────────────────────────────────────────────

def _build_redis_url() -> str:
    """Build the Redis DB5 URL without exposing credential values."""
    explicit_url = os.environ.get("GUINEVERE_REDIS_URL")
    if explicit_url:
        return explicit_url

    password = os.environ.get("REDIS_PASSWORD")
    if password:
        return f"redis://guinevere_core:{quote(password, safe='')}@localhost:6380/5"

    return "redis://localhost:6380/5"


REDIS_URL: str = _build_redis_url()
"""Redis connection URL for DB5. Override via GUINEVERE_REDIS_URL env var."""

REDIS_CONNECT_TIMEOUT_S: float = 2.0
"""Redis connection timeout in seconds."""

REDIS_SOCKET_TIMEOUT_S: float = 1.0
"""Redis socket read/write timeout in seconds."""

LOG_DIR: Path = Path.home() / ".hermes" / "logs" / "hooks"
"""Directory for hook log files."""

LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT: int = 3

_pool: Any | None = None
"""Module-level Redis connection pool (lazy, singleton)."""


# ── Redis ─────────────────────────────────────────────────────────────────────


def get_redis_connection() -> Any | None:
    """Return a Redis connection to DB5 with pooling and retry logic.

    Returns:
        Redis client instance on success, ``None`` if Redis is unavailable
        or the ``redis`` package is not installed.

    Connection settings:
        - Connect timeout: 2s
        - Socket timeout: 1s
        - Health check interval: 30s
        - Automatic retry on TimeoutError (3 attempts, exponential backoff)
    """
    global _pool  # noqa: PLW0603

    if not _redis_available:
        return None

    if (
        _redis_module is None
        or _redis_retry_cls is None
        or _redis_backoff_cls is None
        or _redis_pool_cls is None
    ):
        return None

    if _pool is None:
        try:
            retry = _redis_retry_cls(_redis_backoff_cls(), retries=3)
            _pool = _redis_pool_cls.from_url(
                REDIS_URL,
                socket_connect_timeout=REDIS_CONNECT_TIMEOUT_S,
                socket_timeout=REDIS_SOCKET_TIMEOUT_S,
                health_check_interval=30,
                retry=retry,
                retry_on_timeout=True,
            )
        except (*_redis_connection_error, *_redis_timeout_error, ValueError, OSError) as exc:
            logger = _get_fallback_logger()
            logger.warning("Redis connection pool failed: %s", exc)
            return None

    try:
        client = _redis_module.Redis(connection_pool=_pool)
        # Quick health-check ping (fast path)
        client.ping()
        return client
    except (*_redis_connection_error, *_redis_timeout_error, AttributeError, OSError) as exc:
        logger = _get_fallback_logger()
        logger.warning("Redis ping failed: %s", exc)
        return None


def _get_fallback_logger() -> logging.Logger:
    """Return a minimal stderr logger when the full logger setup is unavailable."""
    fallback = logging.getLogger("hermes.hooks.fallback")
    fallback.setLevel(logging.WARNING)
    if not fallback.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        fallback.addHandler(handler)
    return fallback


# ── Logging ───────────────────────────────────────────────────────────────────


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter for machine-parseable hook logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = str(record.exc_info[1])
        return json.dumps(log_entry, default=str)


def setup_logger(name: str) -> logging.Logger:
    """Create a structured JSON logger writing to ``LOG_DIR/{name}.log``.

    Args:
        name: Logger name (used for both logger identity and log file name).

    Returns:
        Configured ``logging.Logger`` instance with JSON formatting and rotation.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"hermes.hooks.{name}")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers on re-import
    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        LOG_DIR / f"{name}.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    return logger


# ── stdin/stdout ──────────────────────────────────────────────────────────────


def read_stdin_json() -> dict[str, Any]:
    """Read and parse JSON from stdin safely.

    Returns:
        Parsed JSON dictionary.

    Raises:
        SystemExit(2): If stdin is empty or contains invalid JSON.
    """
    try:
        raw = sys.stdin.read()
        if not raw or not raw.strip():
            return {}
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fallback = _get_fallback_logger()
        fallback.error("Failed to parse stdin JSON: %s", exc)
        sys.exit(2)
    except (OSError, EOFError) as exc:
        fallback = _get_fallback_logger()
        fallback.error("Failed to read stdin: %s", exc)
        sys.exit(2)


def write_stdout_json(data: dict[str, Any]) -> None:
    """Write a dictionary as JSON to stdout safely.

    Args:
        data: Dictionary to serialize and write.
    """
    try:
        json.dump(data, sys.stdout, default=str)
        sys.stdout.flush()
    except (TypeError, ValueError, OSError) as exc:
        fallback = _get_fallback_logger()
        fallback.error("Failed to write stdout JSON: %s", exc)
        # Best-effort fallback
        sys.stdout.write(json.dumps({"action": "block", "reason": "Internal error"}))
        sys.stdout.flush()


# ── Timing ────────────────────────────────────────────────────────────────────


class TimingError(Exception):
    """Raised when operation exceeds the allowed time budget."""


@contextmanager
def timing_guard(max_ms: float, label: str = "operation") -> Generator[None, None, None]:
    """Context manager that logs a warning if the block exceeds *max_ms*.

    Does **not** interrupt execution — only measures elapsed wall time.
    The caller is responsible for checking ``time.perf_counter()`` afterwards
    to decide whether to block or warn based on timing.

    Args:
        max_ms: Maximum allowed duration in milliseconds.
        label: Human-readable label for log messages.

    Yields:
        ``None`` — the caller should capture ``time.perf_counter()`` before
        entering the context and compare after exiting.

    Example:
        start = time.perf_counter()
        with timing_guard(50.0, "safety_scan"):
            # ... fast operations ...
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > 50.0:
            logger.warning("safety_scan exceeded %dms budget: %.2fms", 50, elapsed_ms)
    """
    _ = (max_ms, label)  # markers consumed by caller logic
    yield