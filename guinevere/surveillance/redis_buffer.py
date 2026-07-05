"""Async Redis buffer for surveillance events (DB2, TTL 300s).

Provides a protocol-based interface for buffering surveillance events in Redis
DB2 with automatic TTL expiry. Events are serialized to JSON and pushed to a
Redis list. The buffer supports FIFO pop via RPUSH/LRANGE+LTRIM pipeline.

Design decisions:
- ``redis.asyncio`` (NOT synchronous Redis) for non-blocking I/O.
- DB2 is the dedicated surveillance namespace (cost tracking uses DB5).
- TTL of 300 seconds ensures stale events are auto-purged.
- Protocol-based design enables dependency injection and testing.
- Redis errors are caught and logged — the caller (endpoint) decides whether
  to return 202 or 5xx; the buffer itself never raises on push failures.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SurveillanceBuffer(Protocol):
    """Protocol for surveillance event buffering."""

    async def push_event(self, event_data: dict[str, Any]) -> bool:
        """Push an event to the buffer. Returns True on success."""
        ...

    async def pop_events(self, count: int = 10) -> list[dict[str, Any]]:
        """Pop up to ``count`` events from the buffer (FIFO order)."""
        ...

    async def buffer_size(self) -> int:
        """Return current number of events in the buffer."""
        ...

    async def close(self) -> None:
        """Close the Redis connection."""
        ...


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------


@dataclass
class RedisSurveillanceBuffer:
    """Redis DB2-backed surveillance event buffer.

    Events are JSON-serialized and stored as a Redis list. A TTL of 300
    seconds ensures the buffer key is auto-deleted if no new events arrive
    within the window.

    Attributes:
        _redis: An ``redis.asyncio.Redis`` client connected to DB2.
        _buffer_key: Redis key for the event list (default ``surveillance:buffer``).
        _ttl_seconds: Key TTL in seconds (default 300).
    """

    _redis: Any  # ``redis.asyncio.Redis`` — typed as Any to avoid import cost
    _buffer_key: str = "surveillance:buffer"
    _ttl_seconds: int = 300

    # ------------------------------------------------------------------
    # push_event
    # ------------------------------------------------------------------

    async def push_event(self, event_data: dict[str, Any]) -> bool:
        """Serialize and push an event to the buffer.

        Args:
            event_data: The surveillance event dict to buffer.

        Returns:
            ``True`` if the event was successfully pushed; ``False`` on any
            Redis error (connection, timeout, auth, etc.).
        """
        try:
            serialized = json.dumps(event_data, default=str)
            await self._redis.rpush(self._buffer_key, serialized)
            await self._redis.expire(self._buffer_key, self._ttl_seconds)

            size = await self._redis.llen(self._buffer_key)
            event_type = event_data.get("event_type", "unknown")
            device_id = event_data.get("device_id", "unknown")

            logger.info(
                "surveillance_buffer_push",
                event_type=event_type,
                device_id=device_id,
                buffer_size=size,
            )
            return True
        except Exception:
            logger.exception(
                "surveillance_buffer_push_failed",
                event_type=event_data.get("event_type", "unknown"),
                device_id=event_data.get("device_id", "unknown"),
            )
            return False

    # ------------------------------------------------------------------
    # pop_events
    # ------------------------------------------------------------------

    async def pop_events(self, count: int = 10) -> list[dict[str, Any]]:
        """Pop up to ``count`` events from the buffer in FIFO order.

        Uses a Redis pipeline to atomically read and trim the list.

        Args:
            count: Maximum number of events to pop (default 10).

        Returns:
            A list of deserialized event dicts. Events that fail JSON
            decoding are silently skipped and logged.
        """
        try:
            pipe = self._redis.pipeline()
            pipe.lrange(self._buffer_key, 0, count - 1)
            pipe.ltrim(self._buffer_key, count, -1)
            results = await pipe.execute()

            raw_items = results[0] if results else []
            events: list[dict[str, Any]] = []

            for item in raw_items:
                try:
                    events.append(json.loads(item))
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.warning(
                        "surveillance_buffer_bad_json",
                        error=str(exc),
                    )

            return events
        except Exception:
            logger.exception("surveillance_buffer_pop_failed")
            return []

    # ------------------------------------------------------------------
    # buffer_size
    # ------------------------------------------------------------------

    async def buffer_size(self) -> int:
        """Return the current number of events in the buffer."""
        try:
            return await self._redis.llen(self._buffer_key)
        except Exception:
            logger.exception("surveillance_buffer_size_failed")
            return 0

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the Redis connection gracefully."""
        try:
            await self._redis.aclose()
        except Exception:
            logger.exception("surveillance_buffer_close_failed")


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_buffer(
    host: str = "localhost",
    port: int = 6380,
    password: str | None = None,
) -> RedisSurveillanceBuffer:
    """Create a Redis surveillance buffer connected to DB2.

    Args:
        host: Redis server hostname (default ``localhost``).
        port: Redis server port (default ``6380``).
        password: Redis password. Falls back to ``REDIS_PASSWORD`` env var.

    Returns:
        A configured ``RedisSurveillanceBuffer`` instance.
    """
    redis_client = aioredis.Redis(
        host=host,
        port=port,
        db=2,
        password=password or os.environ.get("REDIS_PASSWORD", ""),
        decode_responses=True,
    )
    return RedisSurveillanceBuffer(_redis=redis_client)