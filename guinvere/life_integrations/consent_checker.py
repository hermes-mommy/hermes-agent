"""P22-local consent checker — queries consent.consent_ledger directly.

The surveillance consent_gate whitelists only 8 scopes (none P22), so
P22 cannot delegate consent checks to it. Instead, P22ConsentChecker
queries the consent.consent_ledger table directly via raw SQL.

Fail-closed: on any exception (DB down, unexpected status, no row),
the checker returns False, which blocks the L2+ action.
Only status == 'ACTIVE' (exact uppercase, matching the canonical
ConsentStatus StrEnum) returns True.

Non-ACTIVE statuses (WITHDRAWN, PAUSED, revoked, granted, anything)
are treated as BLOCK.

Returns bool directly for ConsentGateShim's bool branch.
No Redis cache — every check hits DB; acceptable for low-frequency
P22 actions; revocation is visible immediately.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import text

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# SQL — single query, bound params, project_id conditional via OR/NULL
# ---------------------------------------------------------------------------

_CONSENT_SQL = text(
    "SELECT status FROM consent.consent_ledger "
    "WHERE scope = :scope "
    "AND (project_id = :pid OR project_id IS NULL) "
    "ORDER BY granted_at DESC LIMIT 1"
)


class P22ConsentChecker:
    """P22 consent checker — queries consent.consent_ledger directly.

    Attributes:
        _session_factory: An ``async_sessionmaker`` producing async sessions
            bound to the Guinevere database (or a dedicated P22 engine).
    """

    def __init__(self, session_factory: object) -> None:
        """Store the session factory.

        Args:
            session_factory: SQLAlchemy ``async_sessionmaker`` instance.
        """
        self._session_factory = session_factory

    async def check_consent(
        self,
        scope: str,
        project_id: uuid.UUID | None = None,
    ) -> bool:
        """Check whether consent is ACTIVE for *scope*.

        Queries ``consent.consent_ledger`` for the most recent row matching
        the scope. When ``project_id`` is set, project-scoped rows take
        precedence (ORDER BY granted_at DESC returns the newest matching row;
        a project-scoped row with a newer ``granted_at`` wins over an older
        global row).

        Decision: ``True`` only if the latest matching row's ``status``
        is exactly ``'ACTIVE'``.  ``False`` on:
        - No matching row (never consented).
        - Status is not ``'ACTIVE'`` (WITHDRAWN, PAUSED, revoked, etc.).
        - Any exception (DB down) — logged, returns ``False`` (fail-closed).

        Args:
            scope: Consent scope string (e.g.
                ``"consent.filesystem.write"``).
            project_id: Optional project UUID for scoping.  ``None`` means
                global-only check (matches rows where ``project_id IS NULL``).

        Returns:
            ``True`` if consent is granted and ACTIVE, ``False`` otherwise.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    _CONSENT_SQL,
                    {
                        "scope": scope,
                        "pid": str(project_id) if project_id else None,
                    },
                )
                row = result.fetchone()
                if row is None:
                    logger.info(
                        "p22.consent_check_no_row",
                        scope=scope,
                        project_id=str(project_id) if project_id else None,
                    )
                    return False
                status = row[0]
                if status == "ACTIVE":
                    return True
                logger.info(
                    "p22.consent_check_not_active",
                    scope=scope,
                    status=status,
                    project_id=str(project_id) if project_id else None,
                )
                return False
        except Exception as exc:
            logger.warning(
                "p22.consent_check_failed_fail_closed",
                scope=scope,
                project_id=str(project_id) if project_id else None,
                error=str(exc),
            )
            return False
