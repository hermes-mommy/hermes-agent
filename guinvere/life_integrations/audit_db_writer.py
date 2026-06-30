"""P22 audit DB writer — persists AuditEvents to audit.integration_api_log.

Writes hash-chained integration audit events via SQLAlchemy async sessions.
Never raises to caller (audit must not block the action path).

Matches synthesis §2 schema:
- INSERT only (WORM enforced at DB level)
- project_scope = NULL
- chain_version = 2 (configurable via P22_AUDIT_CHAIN_VERSION env var)
- metadata via CAST(:metadata AS jsonb)  (NOT ::jsonb — P20 collision bug)

Also provides :class:`FileAuditWriter` — a JSON-lines file fallback used when
the database is unavailable. The file fallback MUST engage cleanly so the
core app cannot crash on startup when DATABASE_URL is unset.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import structlog
from prometheus_client import Counter
from sqlalchemy import text as sa_text

logger = structlog.get_logger(__name__)


# F21: counter for audit write failures. ``prometheus_client`` is already a
# transitive dep (used by 10+ modules in this repo — see src/core/main.py,
# src/gmail/metrics.py, etc.) so we use it directly. Counter labels carry
# enough context for dashboard drill-down without leaking the event payload.
_AUDIT_WRITE_FAILURES = Counter(
    "p22_audit_write_failures_total",
    "P22 audit DB write failures (audit must not block; this counter is the "
    "operator-visible signal that audit gap is growing).",
    ["integration_id", "error_type"],
)

# F29: chain_version is configurable via env var so future schema upgrades
# can be staged without redeploying a hardcoded literal. To upgrade:
# 1. Bump P22_AUDIT_CHAIN_VERSION to the new value.
# 2. Run a migration that updates audit.integration_api_log.chain_version
#    DEFAULT to match.
# 3. Update AuditLogger.verify_chain() with version-specific canonicalization.
# Defaults to 2 (current production chain version).
_CHAIN_VERSION = int(os.environ.get("P22_AUDIT_CHAIN_VERSION", "2"))


class IntegrationAuditWriter:
    """Persists audit events to audit.integration_api_log.

    Args:
        session_factory: SQLAlchemy async_sessionmaker (or callable returning
            an async context-manager session).
    """

    def __init__(self, session_factory: object) -> None:
        self._session_factory = session_factory

    async def seed_last_hash(self) -> str | None:
        """Return the event_hash of the most recent row.

        Returns:
            ``str`` containing the last event_hash, ``""`` for an empty/fresh
            chain (legitimate case — table unseeded), or ``None`` on DB error.

        Caller contract:
            Empty string (``""``) = fresh chain OK to start from genesis.
            ``None`` = DB unreachable / query failed. Caller MUST treat this as
            DEGRADED (do not silently start a fresh chain — that would
            tamper-evade the existing chain).
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    sa_text(
                        "SELECT event_hash FROM audit.integration_api_log "
                        "ORDER BY sequence DESC LIMIT 1"
                    )
                )
                row = result.first()
                if row and row[0]:
                    return str(row[0])
                # Empty result is legitimate (fresh chain) — return "".
                return ""
        except Exception as exc:
            # CRITICAL log: seeding failure is operator-visible. Distinct from
            # empty-result (which is fine) so operators can tell them apart.
            logger.critical(
                "p22.audit_seed_failed_critical",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            # Return None — NOT "" — to force caller into DEGRADED mode.
            # Returning "" here would silently start a fresh chain, breaking
            # tamper-evidence for any prior chain.
            return None

    async def write_event(self, event_dict: dict) -> None:
        """INSERT one audit event row.  Never raises to caller.

        Args:
            event_dict: dict produced by AuditEvent.to_dict().
        """
        # Coerce string fields to the native types asyncpg expects for the
        # typed DB columns (AuditEvent stores ISO-8601 strings + UUID strings;
        # asyncpg will not auto-coerce str -> TIMESTAMPTZ / UUID).
        project_id_raw = event_dict.get("project_id")
        project_id = uuid.UUID(project_id_raw) if project_id_raw else None

        occurred_at_raw = event_dict["occurred_at"]
        if isinstance(occurred_at_raw, str):
            occurred_at = datetime.fromisoformat(occurred_at_raw)
        else:
            occurred_at = occurred_at_raw

        event_id = uuid.UUID(event_dict["event_id"])
        correlation_id_raw = event_dict.get("correlation_id")
        correlation_id = (
            uuid.UUID(correlation_id_raw) if correlation_id_raw else None
        )

        metadata_json = json.dumps(event_dict["metadata"])

        try:
            async with self._session_factory() as session:
                await session.execute(
                    sa_text(
                        "INSERT INTO audit.integration_api_log ("
                        "    event_id, occurred_at, actor_type, actor_id,"
                        "    integration_id, provider, action, tier,"
                        "    project_id, project_scope, result, correlation_id,"
                        "    metadata, previous_hash, event_hash, chain_version"
                        ") VALUES ("
                        "    :event_id, :occurred_at, :actor_type, :actor_id,"
                        "    :integration_id, :provider, :action, :tier,"
                        "    :project_id, NULL, :result, :correlation_id,"
                        "    CAST(:metadata AS jsonb), :previous_hash, :event_hash, "
                        "    :chain_version"
                        ")"
                    ),
                    {
                        "event_id": event_id,
                        "occurred_at": occurred_at,
                        "actor_type": event_dict["actor_type"],
                        "actor_id": event_dict["actor_id"],
                        "integration_id": event_dict["integration_id"],
                        "provider": event_dict["provider"],
                        "action": event_dict["action"],
                        "tier": event_dict["tier"],
                        "project_id": project_id,
                        "result": event_dict["result"],
                        "correlation_id": correlation_id,
                        "metadata": metadata_json,
                        "previous_hash": event_dict["previous_hash"],
                        "event_hash": event_dict["event_hash"],
                        "chain_version": _CHAIN_VERSION,
                    },
                )
                await session.commit()
        except Exception as exc:
            # F21: keep non-blocking (audit must never raise into action path).
            # Emit ERROR log + prom counter so the failure is dashboard-visible.
            integration_id_label = event_dict.get("integration_id") or "unknown"
            _AUDIT_WRITE_FAILURES.labels(
                integration_id=integration_id_label,
                error_type=type(exc).__name__,
            ).inc()
            logger.error(
                "p22.audit_write_failed",
                event_id=event_dict.get("event_id", "<unknown>"),
                integration_id=integration_id_label,
                error=str(exc),
                error_type=type(exc).__name__,
            )


def get_audit_write_failure_count() -> int:
    """Health accessor: total P22 audit-write failures since process start.

    Returns:
        Sum across all (integration_id, error_type) label combinations of
        the prometheus counter. Useful for /healthz endpoints and dashboards
        when no prometheus collector is running in-process.

    Reading from ``prometheus_client.Counter`` requires going through the
    collector registry; we use the public ``_value.get()`` attribute which is
    stable across prometheus_client releases.
    """
    total = 0
    try:
        for metric in _AUDIT_WRITE_FAILURES.collect():
            for sample in metric.samples:
                total += int(sample.value)
    except Exception:
        logger.debug("audit_metrics_collect_failed", exc_info=True)
        # Never raise from health accessor.
        return total
    return total


# ---------------------------------------------------------------------------
# F05: JSON-lines file fallback for environments where DATABASE_URL is unset
# or unreachable. Honored contract is identical to IntegrationAuditWriter:
# non-blocking, never raises, append-only.
# ---------------------------------------------------------------------------


class FileAuditWriter:
    """Append-only JSON-lines audit writer used when DB is unavailable.

    Persists one ``event_dict`` per line to ``logs/audit-integration.log``
    (overridable via ``path`` ctor arg). Honors the same non-blocking
    contract as :class:`IntegrationAuditWriter`: file-write failures are
    logged at CRITICAL but NEVER raised — audit must not block the action
    path even if the filesystem is wedged.

    Args:
        path: Filesystem path to write JSON-lines to. The parent directory
            is created (if missing) at construction time.
    """

    def __init__(self, path: str = "logs/audit-integration.log") -> None:
        self._path = path
        try:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            # Cannot even create the dir — keep going so ctor never raises.
            # write_event will log the failure loudly.
            logger.error(
                "p22.audit_file_writer_dir_failed",
                path=self._path,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def write_event(self, event_dict: dict) -> None:
        """Append one event dict as a JSON line. Never raises to caller."""
        try:
            line = json.dumps(event_dict, sort_keys=True, default=str) + "\n"
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception as exc:
            # CRITICAL — file-write failure is extremely unlikely but loud.
            logger.critical(
                "p22.audit_file_write_failed",
                path=self._path,
                event_id=event_dict.get("event_id", "<unknown>"),
                error=str(exc),
                error_type=type(exc).__name__,
            )
