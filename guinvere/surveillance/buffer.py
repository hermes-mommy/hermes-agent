"""Async Redis buffer + background consumer for surveillance events.

Ports: guinvere/surveillance/redis_buffer.py, consumer.py.

The buffer provides RPUSH/LRANGE+LTRIM on Redis DB2 with 300s TTL.
The consumer drains the buffer and processes events through a pipeline:
classify -> secret-scan -> store.

Operator approval step REMOVED per ADR-062: Hermes owns all surveillance decisions.
No approval checks or status fields in the pipeline.

Fail-soft: if Redis is unavailable, buffering is skipped with a warning;
the receiver can still accept events without buffering them.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, runtime_checkable

import structlog

logger = structlog.get_logger(__name__)

# Redis raises its own exception hierarchy (redis.exceptions.RedisError) which
# is NOT a subclass of builtins ConnectionError/OSError. Catch it explicitly so
# redis connection failures are handled as fail-soft, not raised to callers.
# When the redis package is absent, fall back to a sentinel that matches
# nothing (the import-guarded code paths never raise redis errors then).
try:
    from redis.exceptions import RedisError as _RedisError
except ImportError:  # pragma: no cover - redis optional

    class _RedisError(Exception):
        """Sentinel: redis absent, so no redis error can ever be raised."""


# ---------------------------------------------------------------------------
# Buffer protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SurveillanceBuffer(Protocol):
    """Protocol for surveillance event buffering."""

    async def push_event(self, event_data: dict[str, Any]) -> bool:
        """Push an event to the buffer. Returns True on success."""
        ...

    async def pop_events(self, count: int = 10) -> list[dict[str, Any]]:
        """Pop up to count events from the buffer (FIFO order)."""
        ...

    async def buffer_size(self) -> int:
        """Return current number of events in the buffer."""
        ...

    async def close(self) -> None:
        """Close the Redis connection."""
        ...


# ---------------------------------------------------------------------------
# Null buffer — used when Redis is unavailable (fail-soft)
# ---------------------------------------------------------------------------


@dataclass
class NullBuffer:
    """No-op buffer that discards events and logs warnings.

    Used when Redis is unavailable so the system degrades gracefully
    rather than crashing.
    """

    async def push_event(self, event_data: dict[str, Any]) -> bool:
        logger.warning(
            "buffer_unavailable_push_skipped",
            event_type=event_data.get("event_type", "unknown"),
            device_id=event_data.get("device_id", "unknown"),
        )
        return False

    async def pop_events(self, count: int = 10) -> list[dict[str, Any]]:
        return []

    async def buffer_size(self) -> int:
        return 0

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Redis-backed buffer
# ---------------------------------------------------------------------------


@dataclass
class RedisSurveillanceBuffer:
    """Redis DB2-backed surveillance event buffer.

    Events are JSON-serialized and stored as a Redis list with TTL of 300s.
    """

    _redis: Any
    _buffer_key: str = "surveillance:buffer"
    _ttl_seconds: int = 300

    async def push_event(self, event_data: dict[str, Any]) -> bool:
        """Serialize and push an event to the buffer."""
        try:
            serialized = json.dumps(event_data, default=str)
            await self._redis.rpush(self._buffer_key, serialized)
            await self._redis.expire(self._buffer_key, self._ttl_seconds)

            size = await self._redis.llen(self._buffer_key)
            logger.info(
                "surveillance_buffer_push",
                event_type=event_data.get("event_type", "unknown"),
                device_id=event_data.get("device_id", "unknown"),
                buffer_size=size,
            )
            return True
        except (ConnectionError, TimeoutError, OSError, ValueError, TypeError, _RedisError) as e:
            logger.exception(
                "surveillance_buffer_push_failed",
                event_type=event_data.get("event_type", "unknown"),
                device_id=event_data.get("device_id", "unknown"),
                error=str(e),
            )
            return False

    async def pop_events(self, count: int = 10) -> list[dict[str, Any]]:
        """Pop up to count events from the buffer in FIFO order."""
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
        except (ConnectionError, TimeoutError, OSError, _RedisError) as e:
            logger.exception("surveillance_buffer_pop_failed", error=str(e))
            return []

    async def buffer_size(self) -> int:
        """Return the current number of events in the buffer."""
        try:
            return await self._redis.llen(self._buffer_key)
        except (ConnectionError, TimeoutError, OSError, _RedisError) as e:
            logger.exception("surveillance_buffer_size_failed", error=str(e))
            return 0

    async def close(self) -> None:
        """Close the Redis connection gracefully."""
        try:
            await self._redis.aclose()
        except (ConnectionError, TimeoutError, OSError, _RedisError) as e:
            logger.exception("surveillance_buffer_close_failed", error=str(e))


def create_buffer(
    host: str = "localhost",
    port: int = 6380,
    password: str | None = None,
) -> RedisSurveillanceBuffer | NullBuffer:
    """Create a surveillance buffer. Returns NullBuffer if Redis is unavailable.

    Args:
        host: Redis server hostname.
        port: Redis server port.
        password: Redis password. Falls back to REDIS_PASSWORD env var.
    """
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.Redis(
            host=host,
            port=port,
            db=2,
            password=password or os.environ.get("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        return RedisSurveillanceBuffer(_redis=redis_client)
    except (ImportError, ConnectionError, TimeoutError, OSError, _RedisError) as e:
        logger.warning("buffer_redis_unavailable_using_null_buffer", error=str(e))
        return NullBuffer()


# ---------------------------------------------------------------------------
# Consumer — background drain pipeline (per ADR-062, Hermes owns decisions)
# ---------------------------------------------------------------------------


@runtime_checkable
class _AsyncDBSession(Protocol):
    """Minimal protocol for an async SQLAlchemy session."""

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> Any: ...

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def close(self) -> None: ...


class SurveillanceConsumer:
    """Async worker that drains the Redis surveillance buffer and processes events.

    Pipeline per event (per ADR-062, Hermes owns all decisions):
    1. Classify event data
    2. Scan clipboard text for secrets + redact
    3. Store to database with retry (max 3 attempts)

    Args:
        buffer: A SurveillanceBuffer implementation (injected).
        db_session_factory: Callable that returns an async DB session.
        poll_interval: Seconds to sleep between poll cycles.
        batch_size: Maximum events to pop per cycle.
    """

    def __init__(
        self,
        buffer: SurveillanceBuffer,
        db_session_factory: Callable[[], _AsyncDBSession],
        poll_interval: float = 5.0,
        batch_size: int = 10,
    ) -> None:
        self._buffer = buffer
        self._db_session_factory = db_session_factory
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._running = False

    async def run(self) -> None:
        """Start the main consumer loop."""
        self._running = True
        logger.info(
            "consumer_started",
            poll_interval=self._poll_interval,
            batch_size=self._batch_size,
        )

        while self._running:
            try:
                await self._drain_and_process()
            except Exception as e:
                logger.exception("consumer_cycle_failed", error=str(e))
            await asyncio.sleep(self._poll_interval)

        await self._buffer.close()
        logger.info("consumer_stopped")

    async def stop(self) -> None:
        """Signal the consumer to shut down gracefully."""
        logger.info("consumer_stop_requested")
        self._running = False

    async def process_event(self, event: dict[str, Any]) -> bool:
        """Process a single event through the pipeline.

        Pipeline (per ADR-062, Hermes owns all decisions):
        1. Classify event data
        2. Scan clipboard text for secrets + redact
        3. Store to database with retry
        """
        # Lazy import to avoid circular dependency at module level
        from guinevere.surveillance.receiver import classify_event, scan_text

        event_type: str = event.get("event_type", "unknown")
        device_id: str = event.get("device_id", "unknown")

        # Step 1: classify
        classification = classify_event(event_type)

        # Step 2: secret scan (clipboard events only)
        scan_result = None
        if event_type == "clipboard":
            payload = event.get("payload", {})
            if isinstance(payload, dict) and "text" in payload:
                text_to_scan = str(payload["text"])
                scan_result = scan_text(text_to_scan)
                if scan_result.has_secrets:
                    event_copy = dict(event)
                    payload_copy = dict(payload)
                    payload_copy["text"] = scan_result.redacted_text
                    event_copy["payload"] = payload_copy
                    event = event_copy

        # Step 3: store with retry
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await self._store_event(
                    event=event,
                    classification=classification,
                    scan_result=scan_result,
                )
                logger.debug(
                    "consumer_event_stored",
                    event_type=event_type,
                    device_id=device_id,
                    classification=classification.classification.value,
                )
                return True
            except (ConnectionError, TimeoutError, OSError, ValueError, KeyError, TypeError, AttributeError) as e:
                logger.exception(
                    "consumer_store_failed",
                    event_type=event_type,
                    device_id=device_id,
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(e),
                )
                if attempt < max_retries:
                    backoff = 0.5 * attempt
                    await asyncio.sleep(backoff)
                else:
                    return False

        return False  # unreachable but satisfies type checker

    async def _drain_and_process(self) -> None:
        """Pop a batch from the buffer and process each event."""
        try:
            events = await self._buffer.pop_events(self._batch_size)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.exception("consumer_buffer_pop_failed", error=str(e))
            return

        if not events:
            return

        batch_id = str(uuid.uuid4())
        processed = 0
        dropped = 0

        for event in events:
            success = await self.process_event(event)
            if success:
                processed += 1
            else:
                dropped += 1

        logger.info(
            "consumer_batch_complete",
            batch_id=batch_id,
            batch_size=len(events),
            processed=processed,
            dropped=dropped,
        )

    async def _store_event(
        self,
        *,
        event: dict[str, Any],
        classification: Any,
        scan_result: Any,
    ) -> None:
        """Persist a processed event to surveillance.events.

        Approval-gating fields omitted per ADR-062 (Hermes owns decisions).
        """
        event_type: str = event.get("event_type", "unknown")
        device_id: str = event.get("device_id", "unknown")
        occurred_at_str: str = event.get("occurred_at", event.get("timestamp", ""))

        occurred_at: datetime | None = None
        if occurred_at_str:
            try:
                occurred_at = datetime.fromisoformat(
                    occurred_at_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                occurred_at = datetime.now(timezone.utc)

        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)

        payload_bytes = json.dumps(event.get("payload", {}), default=str).encode("utf-8")

        extracted_facts: dict[str, Any] = {
            "secrets_detected": scan_result.has_secrets if scan_result else False,
        }
        if scan_result and scan_result.has_secrets:
            extracted_facts["secret_types"] = scan_result.secret_types
            extracted_facts["secrets_found"] = scan_result.secrets_found

        from sqlalchemy import text as sql_text

        insert_stmt = sql_text("""
            INSERT INTO surveillance.events (
                id, event_type, device_id, raw_payload, extracted_facts, summary,
                classification, purpose, retention_class, access_policy,
                encryption_profile, occurred_at, ingested_at
            ) VALUES (
                gen_random_uuid(),
                :event_type,
                :device_id,
                :raw_payload,
                :extracted_facts,
                :summary,
                :classification,
                :purpose,
                :retention_class,
                :access_policy,
                :encryption_profile,
                :occurred_at,
                NOW()
            )
        """)

        device_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, device_id))

        session = self._db_session_factory()
        try:
            await session.execute(
                insert_stmt,
                {
                    "event_type": event_type,
                    "device_id": device_uuid,
                    "raw_payload": payload_bytes,
                    "extracted_facts": json.dumps(extracted_facts),
                    "summary": event.get("summary", ""),
                    "classification": classification.classification.value,
                    "purpose": classification.purpose,
                    "retention_class": classification.retention_class,
                    "access_policy": classification.access_policy,
                    "encryption_profile": classification.encryption_profile,
                    "occurred_at": occurred_at,
                },
            )
            await session.commit()
        except Exception as e:
            logger.exception("surveillance_store_event_failed", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "SurveillanceBuffer",
    "NullBuffer",
    "RedisSurveillanceBuffer",
    "create_buffer",
    "SurveillanceConsumer",
]
