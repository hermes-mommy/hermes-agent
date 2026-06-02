"""Guinevere memory do-not-recall (DNR) hardening — P3-013.

Provides controlled mark/unmark/query APIs for ``memory.episodes.do_not_recall``
with authorization, audit, and pre-injection verification.

Safety rules:
- Only ``principal == "guinevere_core"`` may mark or unmark DNR.
- Unauthorized principals fail closed with ``DNRAuthorizationError``.
- Mutations emit metadata-only audit events via ``audit.audit_trail``.
- No raw memory content or raw reason string is ever logged or included
  in events. Reason is represented as a hash and length only.
- Query-level ``exclude_dnr=True`` defaults in ``read_pipeline`` are preserved.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select, update

from src.memory.models import AuditTrail, Episodes

# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "DNRAuthorizationError",
    "DNRStateError",
    "DNRViolationError",
    "mark_memory_dnr",
    "unmark_memory_dnr",
    "is_memory_dnr",
    "verify_recall_results_dnr_free",
    "MEMORY_DNR_MARKED",
    "DNR_REVOKED",
]

# ---------------------------------------------------------------------------
# Event type constants (encoded in audit_trail.event_type)
# ---------------------------------------------------------------------------

MEMORY_DNR_MARKED: str = "MEMORY_DNR_MARKED"
DNR_REVOKED: str = "DNR_REVOKED"

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------


class DNRAuthorizationError(Exception):
    """Raised when a non-authorized principal attempts a DNR mutation."""


class DNRStateError(Exception):
    """Raised when a DNR operation is invalid for the current state."""


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class DNRSession(Protocol):
    """Minimal async session protocol required by the DNR API."""

    async def execute(self, statement: object) -> _ExecuteResult:
        """Execute a SQLAlchemy statement and return a result."""
        raise NotImplementedError

    async def flush(self) -> None:
        """Flush pending ORM changes."""
        raise NotImplementedError

    def add(self, obj: object) -> None:
        """Add an ORM object to the session."""
        raise NotImplementedError


class _ExecuteResult(Protocol):
    """Protocol for SQLAlchemy execution results used by DNR helpers."""

    @property
    def rowcount(self) -> int:
        """Number of rows affected by the statement."""
        return 0

    def scalar_one_or_none(self) -> object | None:
        """Return the first scalar value or None."""
        return None


async def _execute_typed(session: DNRSession, statement: object) -> _ExecuteResult:
    """Execute a SQLAlchemy statement using the typed result protocol."""
    result: _ExecuteResult = await session.execute(statement)
    return result


# ---------------------------------------------------------------------------
# Authorization helper
# ---------------------------------------------------------------------------

_AUTHORIZED_PRINCIPALS: frozenset[str] = frozenset({"guinevere_core"})


def _check_authorized(principal: str) -> None:
    """Fail closed if principal is not authorized for DNR mutations."""
    if principal not in _AUTHORIZED_PRINCIPALS:
        sorted_auth = sorted(_AUTHORIZED_PRINCIPALS)
        msg = (
            f"Principal '{principal}' is not authorized for DNR mutations. "
            f"Authorized principals: {sorted_auth}"
        )
        raise DNRAuthorizationError(msg)


# ---------------------------------------------------------------------------
# Audit helper — metadata-only AuditTrail record
# ---------------------------------------------------------------------------


async def _emit_audit_event(
    session: DNRSession,
    *,
    event_type: str,
    principal: str,
    episode_id: uuid.UUID,
    reason_hash: str,
    reason_length: int,
    previous_hash: str | None = None,
) -> uuid.UUID:
    """Insert a metadata-only audit record and return its new ID.

    The event payload contains only metadata: episode_id (UUID), event,
    principal, reason_hash, reason_length, and timestamp. No raw content
    or raw reason string is stored.
    """
    now = datetime.now(timezone.utc)
    event_payload = {
        "episode_id": str(episode_id),
        "event": event_type,
        "principal": principal,
        "reason_hash": reason_hash,
        "reason_length": reason_length,
        "occurred_at": now.isoformat(),
    }
    payload_hash = hashlib.sha256(
        f"{event_type}:{episode_id}:{principal}:{now.isoformat()}".encode()
    ).hexdigest()[:32]

    audit_row = AuditTrail(
        event_type=event_type,
        event_payload=event_payload,
        principal=principal,
        event_hash=payload_hash,
        previous_hash=previous_hash,
        occurred_at=now,
    )
    session.add(audit_row)
    await session.flush()
    return audit_row.id


# ---------------------------------------------------------------------------
# mark_memory_dnr
# ---------------------------------------------------------------------------


async def mark_memory_dnr(
    session: DNRSession,
    memory_id: uuid.UUID,
    *,
    reason: str,
    principal: str = "guinevere_core",
) -> uuid.UUID:
    """Mark an episode as do-not-recall.

    Parameters
    ----------
    session:
        SQLAlchemy ``AsyncSession`` bound to the Guinevere database.
    memory_id:
        UUID of the episode to mark.
    reason:
        Human-readable reason for the DNR marking. Stored in audit event
        as a hash and length only; never logged as raw content.
    principal:
        Identity requesting the mutation. Default ``"guinevere_core"``.
        Must equal ``"guinevere_core"`` or ``DNRAuthorizationError`` is
        raised before any mutation occurs.

    Returns
    -------
    ``uuid.UUID``
        The ``memory_id`` that was marked (echoed for caller confirmation).

    Raises
    ------
    DNRAuthorizationError
        If ``principal`` is not ``"guinevere_core"``.
    DNRStateError
        If the episode is already marked ``do_not_recall=True``.
    """
    _check_authorized(principal)

    stmt = (
        update(Episodes)
        .where(Episodes.id == memory_id)
        .where(Episodes.do_not_recall.is_(False))
        .values(do_not_recall=True)
    )
    result = await _execute_typed(session, stmt)
    row_count = result.rowcount

    if row_count == 0:
        existing = await _execute_typed(
            session, select(Episodes.do_not_recall).where(Episodes.id == memory_id)
        )
        current = existing.scalar_one_or_none()
        if current is True:
            raise DNRStateError(
                f"Episode {memory_id} is already marked do-not-recall."
            )
        raise DNRStateError(
            f"Episode {memory_id} not found or could not be marked."
        )

    reason_hash = hashlib.sha256(reason.encode()).hexdigest()[:32]
    _ = await _emit_audit_event(
        session,
        event_type=MEMORY_DNR_MARKED,
        principal=principal,
        episode_id=memory_id,
        reason_hash=reason_hash,
        reason_length=len(reason),
    )

    _logger.info(
        "memory_dnr_marked",
        extra={
            "memory_id": str(memory_id),
            "principal": principal,
            "reason_hash": hashlib.sha256(reason.encode()).hexdigest()[:16],
        },
    )

    return memory_id


# ---------------------------------------------------------------------------
# unmark_memory_dnr
# ---------------------------------------------------------------------------


async def unmark_memory_dnr(
    session: DNRSession,
    memory_id: uuid.UUID,
    *,
    reason: str,
    principal: str = "guinevere_core",
) -> uuid.UUID:
    """Remove the do-not-recall mark from an episode.

    Parameters
    ----------
    session:
        SQLAlchemy ``AsyncSession`` bound to the Guinevere database.
    memory_id:
        UUID of the episode to unmark.
    reason:
        Human-readable reason for the reversal. Stored in audit event
        as a hash and length only; never logged as raw content.
    principal:
        Identity requesting the mutation. Default ``"guinevere_core"``.
        Must equal ``"guinevere_core"`` or ``DNRAuthorizationError`` is
        raised before any mutation occurs.

    Returns
    -------
    ``uuid.UUID``
        The ``memory_id`` that was unmarked.

    Raises
    ------
    DNRAuthorizationError
        If ``principal`` is not ``"guinevere_core"``.
    DNRStateError
        If the episode is not currently marked ``do_not_recall=True``.
    """
    _check_authorized(principal)

    stmt = (
        update(Episodes)
        .where(Episodes.id == memory_id)
        .where(Episodes.do_not_recall.is_(True))
        .values(do_not_recall=False)
    )
    result = await _execute_typed(session, stmt)
    row_count = result.rowcount

    if row_count == 0:
        existing = await _execute_typed(
            session, select(Episodes.do_not_recall).where(Episodes.id == memory_id)
        )
        current = existing.scalar_one_or_none()
        if current is False or current is None:
            msg = (
                f"Episode {memory_id} is not marked do-not-recall; "
                + "cannot unmark."
            )
            raise DNRStateError(msg)
        raise DNRStateError(
            f"Episode {memory_id} not found or could not be unmarked."
        )

    reason_hash = hashlib.sha256(reason.encode()).hexdigest()[:32]
    _ = await _emit_audit_event(
        session,
        event_type=DNR_REVOKED,
        principal=principal,
        episode_id=memory_id,
        reason_hash=reason_hash,
        reason_length=len(reason),
    )

    _logger.info(
        "memory_dnr_unmarked",
        extra={
            "memory_id": str(memory_id),
            "principal": principal,
            "reason_hash": hashlib.sha256(reason.encode()).hexdigest()[:16],
        },
    )

    return memory_id


# ---------------------------------------------------------------------------
# is_memory_dnr
# ---------------------------------------------------------------------------


async def is_memory_dnr(session: DNRSession, memory_id: uuid.UUID) -> bool:
    """Return whether the episode is currently marked do-not-recall.

    Parameters
    ----------
    session:
        SQLAlchemy ``AsyncSession``.
    memory_id:
        UUID of the episode to query.

    Returns
    -------
    ``bool``
        ``True`` if ``do_not_recall=True``, ``False`` otherwise.
        Returns ``False`` if the episode does not exist (fail-closed).
    """
    result = await _execute_typed(
        session, select(Episodes.do_not_recall).where(Episodes.id == memory_id)
    )
    value = result.scalar_one_or_none()
    return bool(value) if value is not None else False


# ---------------------------------------------------------------------------
# verify_recall_results_dnr_free
# ---------------------------------------------------------------------------


class DNRViolationError(Exception):
    """Raised when a DNR-tagged entry is detected in recall results."""


def verify_recall_results_dnr_free(
    results: list[dict[str, object]],
) -> None:
    """Fail-closed guard: verify no DNR entry is present in recall results.

    This function is intended to be called after recall and before prompt
    injection (post-recall / pre-injection gate).

    Parameters
    ----------
    results:
        List of recall result dicts as returned by ``recall_memories``.

    Raises
    ------
    DNRViolationError
        If any candidate has ``do_not_recall=True`` or if a DNR marker
        is otherwise detected in the result dict.
    """
    for idx, entry in enumerate(results):
        dnr_flag = entry.get("do_not_recall")
        if dnr_flag is True:
            msg = (
                "DNR violation detected at result index "
                + f"{idx}: episode {entry.get('id')} "
                + "has do_not_recall=True."
            )
            raise DNRViolationError(msg)
        if dnr_flag == "True" or dnr_flag == "true":
            msg = (
                "DNR violation (string flag) at result index "
                + f"{idx}: episode {entry.get('id')}."
            )
            raise DNRViolationError(msg)
