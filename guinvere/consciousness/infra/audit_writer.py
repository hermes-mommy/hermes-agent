"""Hash-chained audit trail writer for loop actions.

Ported from ``guinvere/loops/audit_writer.py`` — API preserved for M10 (W14).
The lazy import of ``guinvere.memory.models.AuditTrail`` is kept so the DB
schema reference resolves at write-time (not import-time).
"""

from __future__ import annotations

import json
import uuid
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
    project_id: uuid.UUID | None = None  # P19-010: project namespace
    chain_version: int = 2  # P19-010: 1=legacy (pre-P19), 2=P19+ (project_id in payload)


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
        project_id: uuid.UUID | None = None,
    ) -> AuditEvent:
        """Write hash-chained audit event.

        Queries previous event for loop_id, computes new hash, inserts row.

        Args:
            event_type: Type of audit event.
            loop_id: Loop identifier.
            data: Event data dictionary.
            project_id: P19-010 project namespace UUID. ``None`` = legacy/global.
        """
        from guinvere.memory.models import AuditTrail  # Lazy import to avoid circular

        timestamp = datetime.now(timezone.utc)

        async with self._session_factory() as session:
            # Get previous event for this loop
            prev_query = select(AuditTrail).where(
                AuditTrail.event_payload["loop_id"].astext == loop_id
            ).order_by(AuditTrail.occurred_at.desc()).limit(1)
            prev_result = await session.execute(prev_query)
            prev_row = prev_result.scalar_one_or_none()

            previous_hash = prev_row.event_hash if prev_row else "genesis"

            # Build payload — project_id stored inside JSONB for scoping
            payload: dict[str, Any] = {
                "loop_id": loop_id,
                **data,
            }
            if project_id is not None:
                payload["project_id"] = str(project_id)

            # Compute hash
            event_hash = compute_hash(event_type, loop_id, timestamp, payload, previous_hash)

            # Create audit event
            audit_event = AuditEvent(
                event_type=event_type,
                loop_id=loop_id,
                timestamp=timestamp,
                data=payload,
                event_hash=event_hash,
                previous_hash=previous_hash,
                project_id=project_id,
                chain_version=2,  # P19-010: all new events are v2
            )

            # Insert to DB
            db_row = AuditTrail(
                event_type=event_type,
                event_payload=payload,
                principal="guinevere-core",
                event_hash=event_hash,
                previous_hash=previous_hash,
                occurred_at=timestamp,
                chain_version=2,  # P19-010: all new events are v2
            )
            session.add(db_row)
            await session.commit()

            logger.info(
                "audit.event_written",
                event_type=event_type,
                loop_id=loop_id,
                project_id=str(project_id) if project_id else "global",
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
            query = select(AuditTrail).where(
                AuditTrail.event_payload["loop_id"].astext == loop_id
            ).order_by(AuditTrail.occurred_at.asc())
            result = await session.execute(query)
            rows = result.scalars().all()

            if not rows:
                return True  # Empty chain is valid

            previous_hash = "genesis"
            for row in rows:
                cv = getattr(row, "chain_version", 1)
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
                        chain_version=cv,
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
