"""TimescaleDB ingestion module — async write operations for surveillance events.

P7-007: Provides ``TimescaleIngester`` for batch and single-event ingestion into
the ``surveillance.events`` TimescaleDB hypertable, with per-batch
``IngestionLog`` audit entries.

Design decisions:
- **Session factory injection**: ``session_factory`` is passed at init so
  tests can supply mocks without touching real PostgreSQL.
- **uuid5 device resolution**: string device_ids are mapped to deterministic
  UUIDs via ``uuid.uuid5(NAMESPACE_DNS, ...)``, matching the FK column type.
- **Batch insert via SQLAlchemy Core**: uses ``insert(SurveillanceEvents)``
  with a list of dicts for efficient bulk writes.
- **Frozen dataclass**: ``IngestionResult`` is immutable after construction.
- **Metadata-only logging**: never logs raw surveillance payload content.
- **Structured error handling**: try/except with structlog; always returns
  an ``IngestionResult`` with error list on failure.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import structlog
from sqlalchemy import func, insert, select, text

from guinvere.memory.models import IngestionLog, SurveillanceEvents

_DEVICE_NAMESPACE: uuid.UUID = uuid.NAMESPACE_DNS

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# IngestionResult — frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngestionResult:
    """Immutable result of a batch ingestion operation.

    Attributes:
        ingested_count: Number of events successfully written.
        failed_count: Number of events that failed to write.
        batch_id: UUID string identifying this batch.
        errors: List of error messages (one per failed event).
    """

    ingested_count: int
    failed_count: int
    batch_id: str
    errors: list[str]


# ---------------------------------------------------------------------------
# TimescaleIngester
# ---------------------------------------------------------------------------


class TimescaleIngester:
    """Async writer for ``surveillance.events`` (TimescaleDB hypertable).

    Injects a session factory callable so tests can supply mocks. Each batch
    ingestion also writes an ``IngestionLog`` row for auditability.

    Args:
        session_factory: Callable that returns an async SQLAlchemy session.
    """

    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ingest_batch(
        self,
        events: list[dict[str, Any]],
        device_id: str,
    ) -> IngestionResult:
        """Ingest a batch of surveillance events into ``surveillance.events``.

        Each event dict is converted to a column dict for
        ``insert(SurveillanceEvents)``. On partial failure the successful
        rows are still committed; failed rows are recorded in
        ``IngestionResult.errors``.

        Args:
            events: List of event dicts with at least ``event_type`` and
                ``occurred_at`` fields.
            device_id: String device identifier (resolved to UUID via uuid5).

        Returns:
            ``IngestionResult`` with ingested/failed counts and error details.
        """
        batch_id = str(uuid.uuid4())
        device_uuid = self._resolve_device_uuid(device_id)

        ingested_count = 0
        failed_count = 0
        errors: list[str] = []

        row_dicts: list[dict[str, Any]] = []
        for idx, event in enumerate(events):
            try:
                row_dicts.append(self._event_to_row(event, device_uuid))
            except Exception as exc:
                failed_count += 1
                errors.append(f"event[{idx}]: conversion failed — {exc}")
                logger.warning(
                    "timescale_event_conversion_failed",
                    batch_id=batch_id,
                    device_id=device_id,
                    event_index=idx,
                    error=str(exc),
                )

        if row_dicts:
            session = self._session_factory()
            try:
                stmt = insert(SurveillanceEvents)
                result = await session.execute(stmt, row_dicts)
                ingested_count = result.rowcount  # type: ignore[union-attr]
                await session.commit()

                logger.info(
                    "timescale_batch_inserted",
                    batch_id=batch_id,
                    device_id=device_id,
                    ingested_count=ingested_count,
                    attempt_count=len(row_dicts),
                )
            except Exception as exc:
                await session.rollback()
                # Mark all attempted rows as failed
                failed_count += len(row_dicts)
                errors.append(f"batch insert failed — {exc}")
                logger.exception(
                    "timescale_batch_insert_failed",
                    batch_id=batch_id,
                    device_id=device_id,
                    error=str(exc),
                )
            finally:
                await session.close()

        # Always write an IngestionLog entry for the batch
        await self._write_ingestion_log(
            batch_id=batch_id,
            device_uuid=device_uuid,
            total_events=len(events),
            ingested_count=ingested_count,
            failed_count=failed_count,
            errors=errors,
        )

        return IngestionResult(
            ingested_count=ingested_count,
            failed_count=failed_count,
            batch_id=batch_id,
            errors=errors,
        )

    async def ingest_single(
        self,
        event: dict[str, Any],
        device_id: str,
    ) -> bool:
        """Ingest a single surveillance event.

        Wraps ``ingest_batch`` with a list of one event.

        Args:
            event: Event dict with at least ``event_type`` and ``occurred_at``.
            device_id: String device identifier.

        Returns:
            ``True`` if the event was ingested; ``False`` otherwise.
        """
        result = await self.ingest_batch([event], device_id)
        return result.ingested_count == 1

    async def get_event_count(
        self,
        since: datetime | None = None,
    ) -> int:
        """Count events in ``surveillance.events``, optionally since a cutoff.

        Args:
            since: Optional datetime; if provided, only events with
                ``occurred_at >= since`` are counted.

        Returns:
            Total number of matching events.
        """
        session = self._session_factory()
        try:
            stmt = select(func.count()).select_from(SurveillanceEvents)
            if since is not None:
                stmt = stmt.where(SurveillanceEvents.occurred_at >= since)
            result = await session.execute(stmt)
            count = result.scalar_one()
            await session.commit()
            return int(count)
        except Exception:
            await session.rollback()
            logger.exception("timescale_event_count_failed", since=str(since) if since else None)
            return 0
        finally:
            await session.close()

    async def get_last_event(
        self,
        event_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve the most recent event, optionally filtered by type.

        Args:
            event_type: Optional event type filter.

        Returns:
            Dict of column name → value for the most recent event, or
            ``None`` if no events exist.
        """
        session = self._session_factory()
        try:
            stmt = (
                select(SurveillanceEvents)
                .order_by(SurveillanceEvents.occurred_at.desc())
                .limit(1)
            )
            if event_type is not None:
                stmt = stmt.where(SurveillanceEvents.event_type == event_type)

            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            await session.commit()

            if row is None:
                return None

            return {
                "id": str(row.id),
                "event_type": row.event_type,
                "device_id": str(row.device_id),
                "summary": row.summary,
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                "ingested_at": row.ingested_at.isoformat() if row.ingested_at else None,
                "extracted_facts": row.extracted_facts,
            }
        except Exception:
            await session.rollback()
            logger.exception(
                "timescale_last_event_failed",
                event_type=event_type,
            )
            return None
        finally:
            await session.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_device_uuid(device_id: str) -> uuid.UUID:
        """Convert a string device identifier to a deterministic UUID.

        Uses uuid5 with the DNS namespace so the same ``device_id`` string
        always produces the same UUID.
        """
        return uuid.uuid5(_DEVICE_NAMESPACE, device_id)

    @staticmethod
    def _event_to_row(
        event: dict[str, Any],
        device_uuid: uuid.UUID,
    ) -> dict[str, Any]:
        """Convert a raw event dict into a column dict for INSERT.

        Extracts ``event_type``, ``occurred_at``, ``summary``, ``raw_payload``,
        and ``extracted_facts`` from the event.  Classification columns
        (``classification``, ``purpose``, ``retention_class``, etc.) are left
        to SQL server defaults unless explicitly provided in the event.

        Raises:
            ValueError: If ``event_type`` or ``occurred_at`` is missing.
        """
        event_type: str | None = event.get("event_type")
        if not event_type:
            raise ValueError("event_type is required")

        occurred_at_raw = event.get("occurred_at", event.get("timestamp"))
        if occurred_at_raw is None:
            raise ValueError("occurred_at (or timestamp) is required")

        occurred_at: datetime
        if isinstance(occurred_at_raw, datetime):
            occurred_at = occurred_at_raw
        else:
            try:
                occurred_at = datetime.fromisoformat(
                    str(occurred_at_raw).replace("Z", "+00:00")
                )
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"invalid occurred_at value: {occurred_at_raw!r}"
                ) from exc

        # Serialise payload as bytes
        payload = event.get("payload", {})
        if isinstance(payload, bytes):
            raw_payload = payload
        elif isinstance(payload, str):
            raw_payload = payload.encode("utf-8")
        else:
            import json
            raw_payload = json.dumps(payload, default=str).encode("utf-8")

        row: dict[str, Any] = {
            "event_type": event_type,
            "device_id": device_uuid,
            "occurred_at": occurred_at,
            "raw_payload": raw_payload,
            "summary": event.get("summary"),
            "extracted_facts": event.get("extracted_facts"),
        }

        return row

    async def _write_ingestion_log(
        self,
        *,
        batch_id: str,
        device_uuid: uuid.UUID,
        total_events: int,
        ingested_count: int,
        failed_count: int,
        errors: list[str],
    ) -> None:
        """Write an ``IngestionLog`` row for the batch.

        Logs to ``surveillance.ingestion_log`` with batch-level metadata.
        Errors are captured as a semicolon-separated string in
        ``error_message``.
        """
        status = "success" if failed_count == 0 else "partial" if ingested_count > 0 else "failed"
        error_message = "; ".join(errors) if errors else None

        session = self._session_factory()
        try:
            stmt = insert(IngestionLog).values(
                device_id=device_uuid,
                batch_id=uuid.UUID(batch_id),
                events_count=total_events,
                status=status,
                error_message=error_message,
                received_at=datetime.now(timezone.utc),
            )
            await session.execute(stmt)
            await session.commit()

            logger.debug(
                "timescale_ingestion_log_written",
                batch_id=batch_id,
                status=status,
                total_events=total_events,
                ingested_count=ingested_count,
            )
        except Exception:
            await session.rollback()
            logger.exception(
                "timescale_ingestion_log_failed",
                batch_id=batch_id,
            )
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "IngestionResult",
    "TimescaleIngester",
]