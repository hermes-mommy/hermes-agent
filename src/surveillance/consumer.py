"""Async surveillance event consumer — drains Redis DB2 buffer and processes events.

P7-006: Background worker that polls the Redis surveillance buffer, enforces
consent-gated ingestion, classifies events, scans for secrets, and stores
processed events to the database via an injected session factory.

Pipeline per event:
    1. Map event_type → consent scope
    2. Check consent (fail-closed: denied → dropped)
    3. Classify event data
    4. Scan clipboard text for secrets + redact
    5. Store to surveillance.events (with retry)

Design decisions:
- **Protocol injection**: buffer and session factory are passed at init so tests
  can supply mocks without touching real Redis or PostgreSQL.
- **Graceful shutdown**: SIGTERM/SIGINT set ``_running = False``; the current
  batch completes before the loop exits.
- **Retry with backoff**: DB write failures retry up to 3 times with
  exponential backoff (0.5s, 1.0s, 1.5s). Redis failures skip the batch.
- **Consent is fail-closed gate**: consent check failures (exception) result in
  the event being dropped — logged as metadata only.
- **Metadata-only logging**: never log raw surveillance payload content.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, runtime_checkable

import structlog

from src.surveillance.classification import classify_event
from src.surveillance.consent_gate import check_consent
from src.surveillance.redis_buffer import SurveillanceBuffer
from src.surveillance.secret_scanner import scan_text

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Event type → consent scope mapping
# ---------------------------------------------------------------------------

_EVENT_SCOPE_MAP: dict[str, str] = {
    "app_usage": "surveillance.app_usage",
    "location": "surveillance.location",
    "notification": "surveillance.notifications",
    "clipboard": "surveillance.clipboard",
}

_DEFAULT_SCOPE: str = "surveillance.app_usage"


def _map_event_to_scope(event_type: str) -> str:
    """Map an event type string to the corresponding consent scope.

    Unknown event types default to ``surveillance.app_usage``.
    """
    return _EVENT_SCOPE_MAP.get(event_type, _DEFAULT_SCOPE)


# ---------------------------------------------------------------------------
# DB session protocol — injectable for testing
# ---------------------------------------------------------------------------


@runtime_checkable
class _AsyncDBSession(Protocol):
    """Minimal protocol for an async SQLAlchemy session."""

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------


class SurveillanceConsumer:
    """Async worker that drains the Redis surveillance buffer and processes events.

    The consumer polls Redis DB2 at ``poll_interval`` seconds, pops up to
    ``batch_size`` events, and runs each through the consent → classify →
    scan → store pipeline.

    Attributes:
        _buffer: A ``SurveillanceBuffer`` implementation (injected).
        _db_session_factory: Callable that returns an async DB session.
        _poll_interval: Seconds to sleep between poll cycles.
        _batch_size: Maximum events to pop per cycle.
        _running: Internal flag for graceful shutdown.
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the main consumer loop.

        Polls the buffer, processes batches, and handles shutdown signals.
        Exits cleanly when ``stop()`` is called or SIGTERM/SIGINT is received.
        """
        self._running = True
        logger.info(
            "consumer_started",
            poll_interval=self._poll_interval,
            batch_size=self._batch_size,
        )

        while self._running:
            try:
                await self._drain_and_process()
            except Exception:
                logger.exception("consumer_cycle_failed")
            await asyncio.sleep(self._poll_interval)

        await self._buffer.close()
        logger.info("consumer_stopped")

    async def stop(self) -> None:
        """Signal the consumer to shut down gracefully.

        Sets ``_running = False``. The current batch will finish processing
        before the loop exits.
        """
        logger.info("consumer_stop_requested")
        self._running = False

    async def process_event(self, event: dict[str, Any]) -> bool:
        """Process a single surveillance event through the full pipeline.

        Pipeline steps:
            1. Map event_type to consent scope.
            2. Check consent (fail-closed: denied/error → dropped).
            3. Classify event data.
            4. Scan clipboard text for secrets + redact.
            5. Store to database with retry (max 3 attempts).

        Args:
            event: The raw event dict from the Redis buffer.

        Returns:
            ``True`` if the event was successfully processed and stored;
            ``False`` if it was dropped (consent denied, error, or retry
            exhaustion).
        """
        event_type: str = event.get("event_type", "unknown")
        device_id: str = event.get("device_id", "unknown")

        # Step 1: map to consent scope
        scope = _map_event_to_scope(event_type)

        # Step 2: consent gate (fail-closed)
        try:
            consent_result = await check_consent(scope)
        except Exception:
            logger.exception(
                "consumer_consent_check_failed",
                event_type=event_type,
                device_id=device_id,
                scope=scope,
            )
            return False

        if not consent_result.allowed:
            logger.info(
                "consumer_consent_denied_drop",
                event_type=event_type,
                device_id=device_id,
                scope=scope,
                reason=consent_result.reason,
            )
            return False

        # Step 3: classify
        classification = classify_event(event_type)

        # Step 4: secret scan (clipboard events only)
        scan_result = None
        if event_type == "clipboard":
            payload = event.get("payload", {})
            if isinstance(payload, dict) and "text" in payload:
                text_to_scan = str(payload["text"])
                scan_result = scan_text(text_to_scan)
                if scan_result.has_secrets:
                    # Deep-copy-safe: mutate a copy, not the original
                    event_copy = dict(event)
                    payload_copy = dict(payload)
                    payload_copy["text"] = scan_result.redacted_text
                    event_copy["payload"] = payload_copy
                    event = event_copy

        # Step 5: store with retry
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await self._store_event(
                    event=event,
                    classification=classification,
                    consent_status=consent_result.status.value if consent_result.status else "unknown",
                    scan_result=scan_result,
                )
                logger.debug(
                    "consumer_event_stored",
                    event_type=event_type,
                    device_id=device_id,
                    classification=classification.classification.value,
                )
                return True
            except Exception:
                logger.exception(
                    "consumer_store_failed",
                    event_type=event_type,
                    device_id=device_id,
                    attempt=attempt,
                    max_retries=max_retries,
                )
                if attempt < max_retries:
                    backoff = 0.5 * attempt
                    await asyncio.sleep(backoff)
                else:
                    return False

        return False  # unreachable but satisfies type checker

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _drain_and_process(self) -> None:
        """Pop a batch of events from the buffer and process each one.

        Redis errors are caught per-cycle — a failed pop skips the batch
        without crashing the loop.
        """
        try:
            events = await self._buffer.pop_events(self._batch_size)
        except Exception:
            logger.exception("consumer_buffer_pop_failed")
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
        consent_status: str,
        scan_result: Any,
    ) -> None:
        """Persist a processed event to ``surveillance.events``.

        Uses the injected session factory to obtain an async DB session.
        The session is closed in a ``finally`` block to prevent leaks.

        Raises:
            Exception: Any SQLAlchemy or connectivity error (handled by the
                retry loop in ``process_event``).
        """
        event_type: str = event.get("event_type", "unknown")
        device_id: str = event.get("device_id", "unknown")
        occurred_at_str: str = event.get("occurred_at", event.get("timestamp", ""))

        occurred_at: datetime | None = None
        if occurred_at_str:
            try:
                occurred_at = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                occurred_at = datetime.now(timezone.utc)

        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)

        # Serialise payload as JSON bytes for raw_payload column
        payload_bytes = json.dumps(event.get("payload", {}), default=str).encode("utf-8")

        # Build extracted_facts JSONB payload with governance metadata
        extracted_facts: dict[str, Any] = {
            "consent_status": consent_status,
            "secrets_detected": scan_result.has_secrets if scan_result else False,
        }
        if scan_result and scan_result.has_secrets:
            extracted_facts["secret_types"] = scan_result.secret_types
            extracted_facts["secrets_found"] = scan_result.secrets_found

        from sqlalchemy import text

        insert_stmt = text("""
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

        # Generate deterministic UUID from device_id string via UUID5
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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Module-level entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    """Entry point for ``python -m src.surveillance.consumer``.

    Creates a ``RedisSurveillanceBuffer`` and an async session factory,
    then runs the consumer with graceful shutdown on SIGTERM/SIGINT.
    """
    from src.surveillance.redis_buffer import RedisSurveillanceBuffer

    import redis.asyncio as aioredis

    # ---- Redis buffer (DB2) ----
    redis_client = aioredis.Redis(
        host="localhost",
        port=6380,
        db=2,
        password=os.environ.get("REDIS_PASSWORD", ""),
        decode_responses=True,
    )
    buffer = RedisSurveillanceBuffer(_redis=redis_client)

    # ---- DB session factory ----
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        db_password = os.environ.get("GUINEVERE_DB_PASSWORD", "")
        if not db_password:
            raise RuntimeError(
                "Neither DATABASE_URL nor GUINEVERE_DB_PASSWORD is set. "
                "The consumer requires a PostgreSQL connection to store events."
            )
        database_url = (
            f"postgresql+asyncpg://guinevere:{db_password}"
            f"@localhost:5433/guinevere"
        )

    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    _session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
    logger.info("consumer_db_session_factory_initialized")

    def db_session_factory() -> _AsyncDBSession:
        return _session_factory()

    consumer = SurveillanceConsumer(
        buffer=buffer,
        db_session_factory=db_session_factory,
    )

    # ---- Signal handlers for graceful shutdown ----
    loop = asyncio.get_running_loop()

    def _on_signal() -> None:
        logger.info("consumer_signal_received", signal="SIGTERM/SIGINT")
        asyncio.ensure_future(consumer.stop())

    if os.name != "nt":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _on_signal)
    else:
        logger.warning("consumer_signal_handler_not_supported", os_name=os.name)

    try:
        await consumer.run()
    finally:
        await engine.dispose()
        logger.info("consumer_db_engine_disposed")


if __name__ == "__main__":
    asyncio.run(main())


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "SurveillanceConsumer",
    "main",
    "_map_event_to_scope",
]