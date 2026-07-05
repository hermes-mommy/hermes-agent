"""TimescaleDB storage + 3-tier retention for surveillance events.

Ports: guinevere/surveillance/retention.py, timescale.py.

Provides retention policy constants (7d/90d/365d), TimescaleDB batch/single
ingestion with IngestionLog audit entries, and uuid5 device resolution.

Fail-soft: if PG is unavailable, ingestion logs warnings and returns
failure results without crashing.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Callable, Final

import structlog

try:
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:  # pragma: no cover
    SQLAlchemyError = Exception

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Retention constants (from retention.py)
# ---------------------------------------------------------------------------

RETENTION_RAW_DAYS: Final[int] = 7
RETENTION_AGGREGATED_DAYS: Final[int] = 90
RETENTION_SUMMARY_DAYS: Final[int] = 365

COMPRESSION_AFTER_DAYS: Final[int] = 7
CHUNK_INTERVAL_DAYS: Final[int] = 1


class RetentionTier(StrEnum):
    """TimescaleDB retention tiers (raw, aggregated, summary)."""

    RAW = "raw"
    AGGREGATED = "aggregated"
    SUMMARY = "summary"


_TIER_DAYS: Final[dict[RetentionTier, int]] = {
    RetentionTier.RAW: RETENTION_RAW_DAYS,
    RetentionTier.AGGREGATED: RETENTION_AGGREGATED_DAYS,
    RetentionTier.SUMMARY: RETENTION_SUMMARY_DAYS,
}


def get_retention_days(tier: RetentionTier) -> int:
    """Return the retention period in days for a given tier.

    Unknown/empty tier defaults to RETENTION_RAW_DAYS (fail-safe).
    """
    return _TIER_DAYS.get(tier, RETENTION_RAW_DAYS)


def calculate_retention_until(
    tier: RetentionTier,
    occurred_at: datetime,
) -> datetime:
    """Calculate the expiry datetime for an event given its retention tier."""
    days = get_retention_days(tier)
    return occurred_at + timedelta(days=days)


def get_retention_policy_summary() -> dict[str, Any]:
    """Return a human-readable summary of all retention policies."""
    logger.info("retention_policy_summary_requested")
    return {
        "raw": {
            "tier": RetentionTier.RAW.value,
            "retention_days": RETENTION_RAW_DAYS,
            "description": "Raw events in surveillance.events hypertable",
            "compression_after_days": COMPRESSION_AFTER_DAYS,
            "chunk_interval_days": CHUNK_INTERVAL_DAYS,
        },
        "aggregated": {
            "tier": RetentionTier.AGGREGATED.value,
            "retention_days": RETENTION_AGGREGATED_DAYS,
            "description": "Continuous aggregates and materialized views",
            "compression_after_days": COMPRESSION_AFTER_DAYS,
            "chunk_interval_days": CHUNK_INTERVAL_DAYS,
        },
        "summary": {
            "tier": RetentionTier.SUMMARY.value,
            "retention_days": RETENTION_SUMMARY_DAYS,
            "description": "Curated long-term summaries",
        },
    }


# ---------------------------------------------------------------------------
# TimescaleDB ingestion (from timescale.py)
# ---------------------------------------------------------------------------

_DEVICE_NAMESPACE: uuid.UUID = uuid.NAMESPACE_DNS


@dataclass(frozen=True)
class IngestionResult:
    """Immutable result of a batch ingestion operation."""

    ingested_count: int
    failed_count: int
    batch_id: str
    errors: list[str]


class TimescaleIngester:
    """Async writer for surveillance.events (TimescaleDB hypertable).

    Fail-soft: if session_factory fails or PG is unavailable, operations
    log warnings and return failure results without crashing.

    Args:
        session_factory: Callable that returns an async SQLAlchemy session.
    """

    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._session_factory = session_factory

    async def ingest_batch(
        self,
        events: list[dict[str, Any]],
        device_id: str,
    ) -> IngestionResult:
        """Ingest a batch of surveillance events into surveillance.events.

        Each event dict is converted to a column dict for INSERT. On partial
        failure the successful rows are still committed; failed rows are
        recorded in IngestionResult.errors.
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
                errors.append(f"event[{idx}]: conversion failed -- {exc}")
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
                # Use raw SQL INSERT to avoid ORM dependency at import time
                from sqlalchemy import text as sql_text

                insert_stmt = sql_text("""
                    INSERT INTO surveillance.events (
                        id, event_type, device_id, occurred_at, raw_payload,
                        summary, extracted_facts, ingested_at
                    ) VALUES (
                        gen_random_uuid(), :event_type, :device_id,
                        :occurred_at, :raw_payload, :summary,
                        :extracted_facts, NOW()
                    )
                """)

                for row in row_dicts:
                    await session.execute(insert_stmt, {
                        "event_type": row["event_type"],
                        "device_id": str(row["device_id"]),
                        "occurred_at": row["occurred_at"],
                        "raw_payload": row["raw_payload"],
                        "summary": row.get("summary"),
                        "extracted_facts": json.dumps(row.get("extracted_facts")) if row.get("extracted_facts") else None,
                    })
                    ingested_count += 1

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
                failed_count += len(row_dicts)
                ingested_count = 0
                errors.append(f"batch insert failed -- {exc}")
                logger.exception(
                    "timescale_batch_insert_failed",
                    batch_id=batch_id,
                    device_id=device_id,
                )
            finally:
                await session.close()

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
        """Ingest a single surveillance event."""
        result = await self.ingest_batch([event], device_id)
        return result.ingested_count == 1

    async def get_event_count(
        self,
        since: datetime | None = None,
    ) -> int:
        """Count events in surveillance.events, optionally since a cutoff."""
        session = self._session_factory()
        try:
            from sqlalchemy import func, select, text as sql_text

            stmt = select(func.count()).select_from(
                sql_text("surveillance.events")
            )
            if since is not None:
                stmt = stmt.where(
                    sql_text("occurred_at >= :since")
                )
            result = await session.execute(
                stmt, {"since": since} if since else None
            )
            count = result.scalar_one()
            await session.commit()
            return int(count)
        except SQLAlchemyError as e:
            await session.rollback()
            logger.exception(
                "timescale_event_count_failed",
                since=str(since) if since else None,
                error=str(e),
            )
            return 0
        finally:
            await session.close()

    async def get_last_event(
        self,
        event_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve the most recent event, optionally filtered by type."""
        session = self._session_factory()
        try:
            from sqlalchemy import text as sql_text

            where_clause = ""
            params: dict[str, Any] = {}
            if event_type is not None:
                where_clause = "WHERE event_type = :event_type"
                params["event_type"] = event_type

            stmt = sql_text(f"""
                SELECT id, event_type, device_id, summary,
                       occurred_at, ingested_at, extracted_facts
                FROM surveillance.events
                {where_clause}
                ORDER BY occurred_at DESC
                LIMIT 1
            """)

            result = await session.execute(stmt, params)
            row = result.mappings().first()
            await session.commit()

            if row is None:
                return None

            return {
                "id": str(row["id"]),
                "event_type": row["event_type"],
                "device_id": str(row["device_id"]),
                "summary": row["summary"],
                "occurred_at": row["occurred_at"].isoformat() if row["occurred_at"] else None,
                "ingested_at": row["ingested_at"].isoformat() if row["ingested_at"] else None,
                "extracted_facts": row["extracted_facts"],
            }
        except SQLAlchemyError as e:
            await session.rollback()
            logger.exception(
                "timescale_last_event_failed",
                event_type=event_type,
                error=str(e),
            )
            return None
        finally:
            await session.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_device_uuid(device_id: str) -> uuid.UUID:
        """Convert a string device identifier to a deterministic UUID via uuid5."""
        return uuid.uuid5(_DEVICE_NAMESPACE, device_id)

    @staticmethod
    def _event_to_row(
        event: dict[str, Any],
        device_uuid: uuid.UUID,
    ) -> dict[str, Any]:
        """Convert a raw event dict into a column dict for INSERT.

        Raises:
            ValueError: If event_type or occurred_at is missing.
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

        payload = event.get("payload", {})
        if isinstance(payload, bytes):
            raw_payload = payload
        elif isinstance(payload, str):
            raw_payload = payload.encode("utf-8")
        else:
            raw_payload = json.dumps(payload, default=str).encode("utf-8")

        return {
            "event_type": event_type,
            "device_id": device_uuid,
            "occurred_at": occurred_at,
            "raw_payload": raw_payload,
            "summary": event.get("summary"),
            "extracted_facts": event.get("extracted_facts"),
        }

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
        """Write an IngestionLog row for the batch."""
        status = (
            "success" if failed_count == 0
            else "partial" if ingested_count > 0
            else "failed"
        )
        error_message = "; ".join(errors) if errors else None

        session = self._session_factory()
        try:
            from sqlalchemy import text as sql_text

            stmt = sql_text("""
                INSERT INTO surveillance.ingestion_log (
                    id, device_id, batch_id, events_count, status,
                    error_message, received_at
                ) VALUES (
                    gen_random_uuid(), :device_id, :batch_id, :events_count,
                    :status, :error_message, :received_at
                )
            """)
            await session.execute(stmt, {
                "device_id": str(device_uuid),
                "batch_id": batch_id,
                "events_count": total_events,
                "status": status,
                "error_message": error_message,
                "received_at": datetime.now(timezone.utc),
            })
            await session.commit()

            logger.debug(
                "timescale_ingestion_log_written",
                batch_id=batch_id,
                status=status,
                total_events=total_events,
                ingested_count=ingested_count,
            )
        except SQLAlchemyError as e:
            await session.rollback()
            logger.exception(
                "timescale_ingestion_log_failed",
                batch_id=batch_id,
                error=str(e),
            )
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "RETENTION_RAW_DAYS",
    "RETENTION_AGGREGATED_DAYS",
    "RETENTION_SUMMARY_DAYS",
    "COMPRESSION_AFTER_DAYS",
    "CHUNK_INTERVAL_DAYS",
    "RetentionTier",
    "get_retention_days",
    "calculate_retention_until",
    "get_retention_policy_summary",
    "IngestionResult",
    "TimescaleIngester",
]
