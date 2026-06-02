"""Replay protection: timestamp window validation + atomic nonce dedup via Redis.

P7-003: Provides ``validate_timestamp`` (checks the ``X-Timestamp`` header is
within a 300-second window) and ``check_nonce`` (atomically stores the nonce
in Redis DB2 with ``SET NX EX`` to detect replays).

Design decisions:
- Timestamp check runs first (zero I/O, free) so expired requests are rejected
  before hitting Redis.
- Nonce is stored with ``SET key value NX EX 660`` — strictly atomic, never
  GET-then-SET.
- Nonce TTL is 660 seconds (>= 2× the 300-second timestamp window) so a nonce
  outlives the window it guards.
- Redis DB2 is the dedicated surveillance namespace (same as the event buffer).
- Redis connection failure causes the request to be rejected (fail-closed).
"""

from __future__ import annotations

import os
import time

import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIMESTAMP_WINDOW_SECONDS: int = 300
"""Maximum allowed clock skew in seconds (5 minutes)."""

NONCE_TTL_SECONDS: int = 660
"""Nonce TTL in seconds — must be >= 2× ``TIMESTAMP_WINDOW_SECONDS``."""

NONCE_KEY_PREFIX: str = "surveillance:nonce:"
"""Redis key prefix for namespace isolation."""

# ---------------------------------------------------------------------------
# Module-level Redis client (lazy singleton, overridable for tests)
# ---------------------------------------------------------------------------

_redis: aioredis.Redis | None = None
"""Module-level Redis client connected to DB2. Created lazily on first use."""


def _get_redis() -> aioredis.Redis:
    """Return the module-level Redis client, creating it if necessary."""
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host="localhost",
            port=6380,
            db=2,
            decode_responses=True,
            password=os.environ.get("REDIS_PASSWORD", ""),
        )
    return _redis


def _set_redis_for_testing(client: aioredis.Redis | None) -> None:
    """Replace the module-level Redis client (for test injection).

    Intended **only** for test isolation — production code should never
    need to call this.
    """
    global _redis
    _redis = client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def validate_timestamp(timestamp: str) -> None:
    """Raise ``HTTPException(401)`` if *timestamp* is outside the allowed window.

    Args:
        timestamp: Unix epoch seconds as a string (the ``X-Timestamp`` header value).

    Raises:
        HTTPException(401): The timestamp is missing, unparseable, or outside
            the ±300-second window.
    """
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        logger.warning("replay_timestamp_invalid_format", timestamp=timestamp)
        raise HTTPException(status_code=401, detail="Request expired")

    now = int(time.time())
    diff = abs(now - ts)

    if diff > TIMESTAMP_WINDOW_SECONDS:
        logger.warning(
            "replay_timestamp_expired",
            server_time=now,
            request_timestamp=ts,
            diff_seconds=diff,
            window_seconds=TIMESTAMP_WINDOW_SECONDS,
        )
        raise HTTPException(status_code=401, detail="Request expired")

    logger.debug("replay_timestamp_valid", timestamp=ts, server_time=now)


async def check_nonce(nonce: str) -> None:
    """Atomically store *nonce* in Redis and reject duplicates.

    Uses ``SET key value NX EX 660`` — the operation is atomic and will
    only succeed if the key does not already exist.

    Args:
        nonce: The ``X-Nonce`` header value.

    Raises:
        HTTPException(409): The nonce has already been seen (replay detected).
        HTTPException(503): Redis is unreachable (fail-closed).
    """
    redis_client = _get_redis()
    nonce_key = f"{NONCE_KEY_PREFIX}{nonce}"

    try:
        # SET NX EX — returns True if the key was set (first time),
        # None if the key already existed (duplicate).
        result = await redis_client.set(nonce_key, "1", nx=True, ex=NONCE_TTL_SECONDS)

        if result is None:
            logger.warning(
                "replay_nonce_duplicate",
                nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
            )
            raise HTTPException(status_code=409, detail="Replay detected")

        logger.debug(
            "replay_nonce_accepted",
            nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "replay_redis_error",
            nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
        )
        raise HTTPException(status_code=503, detail="Replay protection unavailable")


# ---------------------------------------------------------------------------
# Test helpers (exported for test isolation)
# ---------------------------------------------------------------------------

__all__ = [
    "TIMESTAMP_WINDOW_SECONDS",
    "NONCE_TTL_SECONDS",
    "NONCE_KEY_PREFIX",
    "validate_timestamp",
    "check_nonce",
    "_set_redis_for_testing",
]