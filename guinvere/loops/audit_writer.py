"""Hash-chained audit trail writer for loop actions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select

logger = structlog.get_logger()


@dataclass(frozen=True)
class AuditEvent:
    """Audit event with hash chain.

    Each event includes SHA-256 hash of previous event,
    creating tamper-evident log.
    """

    event_type: str  # "loop.start", "phase.complete", "tool.call", "reflection.extracted"
    loop_id: str
    timestamp: datetime
    data: dict[str, Any]
    event_hash: str  # SHA-256 of event
    previous_hash: str  # SHA-256 of previous event (or "genesis")


class AuditWriter:
    """Hash-chained audit trail writer for loop actions.

    Writes events to audit.audit_trail table with SHA-256 hash chain.
    Each event includes hash of previous event, creating tamper-evident log.

    Constructor injection:
    - session_factory: SQLAlchemy async session factory
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def write_event(
        self,
        event_type: str,
        loop_id: str,
        data: dict[str, Any],
    ) -> AuditEvent:
        """Write hash-chained audit event.

        Queries previous event for loop_id, computes new hash, inserts row.
        """
        from guinvere.memory.models import AuditTrail  # Lazy import to avoid circular

        timestamp = datetime.now(timezone.utc)

        async with self._session_factory() as session:
            # Get previous event for this loop
            # Use event_payload to store loop_id and other context
            prev_query = select(AuditTrail).where(
                AuditTrail.event_payload["loop_id"].astext == loop_id
            ).order_by(AuditTrail.occurred_at.desc()).limit(1)
            prev_result = await session.execute(prev_query)
            prev_row = prev_result.scalar_one_or_none()

            previous_hash = prev_row.event_hash if prev_row else "genesis"

            # Compute hash
            event_hash = compute_hash(event_type, loop_id, timestamp, data, previous_hash)

            # Create audit event
            audit_event = AuditEvent(
                event_type=event_type,
                loop_id=loop_id,
                timestamp=timestamp,
                data=data,
                event_hash=event_hash,
                previous_hash=previous_hash,
            )

            # Insert to DB
            # Store loop_id inside event_payload (JSONB)
            db_row = AuditTrail(
                event_type=event_type,
                event_payload={
                    "loop_id": loop_id,
                    **data,
                },
                principal="guinevere-core",
                event_hash=event_hash,
                previous_hash=previous_hash,
                occurred_at=timestamp,
            )
            session.add(db_row)
            await session.commit()

            logger.info(
                "audit.event_written",
                event_type=event_type,
                loop_id=loop_id,
                hash=event_hash[:12],
            )

            return audit_event

    async def verify_chain(self, loop_id: str) -> bool:
        """Verify hash chain integrity for a loop.

        Replays all events for loop_id, recomputes hashes, compares to stored.
        Returns True if chain intact, False if tampered.
        """
        from guinvere.memory.models import AuditTrail

        async with self._session_factory() as session:
            # Query events ordered by occurred_at
            query = select(AuditTrail).where(
                AuditTrail.event_payload["loop_id"].astext == loop_id
            ).order_by(AuditTrail.occurred_at.asc())
            result = await session.execute(query)
            rows = result.scalars().all()

            if not rows:
                return True  # Empty chain is valid

            previous_hash = "genesis"
            for row in rows:
                expected_hash = compute_hash(
                    row.event_type,
                    row.event_payload["loop_id"],
                    row.occurred_at,
                    row.event_payload,
                    previous_hash,
                )
                if expected_hash != row.event_hash:
                    logger.error(
                        "audit.chain_broken",
                        loop_id=loop_id,
                        event_id=row.id,
                        expected=expected_hash[:12],
                        actual=row.event_hash[:12],
                    )
                    return False
                previous_hash = row.event_hash

            return True


def compute_hash(
    event_type: str,
    loop_id: str,
    timestamp: datetime,
    data: dict[str, Any],
    previous_hash: str,
) -> str:
    """Compute SHA-256 hash for audit event.

    Args:
        event_type: Type of audit event
        loop_id: Loop identifier
        timestamp: Event timestamp
        data: Event data dictionary
        previous_hash: Hash of previous event

    Returns:
        SHA-256 hex digest
    """
    import hashlib

    # Deterministic serialization
    data_str = json.dumps(data, sort_keys=True, default=str)
    timestamp_str = timestamp.isoformat()

    hash_input = f"{event_type}:{loop_id}:{timestamp_str}:{data_str}:{previous_hash}"
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()