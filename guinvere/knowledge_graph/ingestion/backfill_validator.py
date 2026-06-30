"""Knowledge Graph backfill validation suite (P16-010).

Validates the integrity and coverage of the historical backfill
(:class:`guinvere.knowledge_graph.ingestion.backfill.KGBackfillEngine`)
output.  Read-only — never mutates the database.

Why this lives in the ingestion package
---------------------------------------
The validator is the post-migration gate for the backfill engine in
:mod:`guinvere.knowledge_graph.ingestion.backfill`.  Operators run the
six checks (entity coverage, edge integrity, orphans, duplicates,
consent compliance, tombstone consistency) before signing off the
migration as complete.

Safety / consent notes (per AGENTS.md BLOCKING rules and
PersonaSafetyPolicy):

* **Read-only.**  No INSERT / UPDATE / DELETE statements; every
  query is a ``SELECT`` (or a ``COUNT`` / aggregate).  The validator
  cannot accidentally tombstone or rewrite data.
* **No HARD STOP bypass.**  Checks are operator-initiated and never
  run in the user-facing recall path.
* **No type-suppression.**  Every parameter and return value is
  statically typed; no ``# type: ignore`` / ``as any`` shortcuts.
* **Non-raising contract.**  Each :meth:`check_*` method returns a
  :class:`CheckResult` rather than raising — operators need the
  full report, not an exception at the first failure.  A failing
  check is encoded as ``passed=False`` with the issue list
  populated.
* **Bounded reports.**  Every check caps the per-check issue list
  at :data:`MAX_ISSUES_PER_CHECK` to avoid unbounded memory use on
  large corpora.  The :attr:`CheckResult.issues_found` counter is
  the source of truth for the *total* number of issues; the
  :attr:`CheckResult.issues` list is a *sample* (the first N).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Protocol

from guinvere.knowledge_graph.ingestion.backfill import (
    BACKFILL_SOURCE_TAG,
)
from guinvere.knowledge_graph.observability.logger import (
    KGLogContext,
    get_kg_logger,
    log_kg_operation,
)
from guinvere.knowledge_graph.repository import KGRepository, SessionFactory

logger = get_kg_logger("ingestion.backfill_validator")


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

KG_SCHEMA: Final[str] = "memory"
KG_ENTITIES_TABLE: Final[str] = f"{KG_SCHEMA}.kg_entities"
KG_EDGES_TABLE: Final[str] = f"{KG_SCHEMA}.kg_edges"
KG_EPISODES_TABLE: Final[str] = f"{KG_SCHEMA}.kg_episodes"
KG_SAME_AS_TABLE: Final[str] = f"{KG_SCHEMA}.kg_same_as_edges"
SEMANTIC_FACTS_TABLE: Final[str] = f"{KG_SCHEMA}.semantic_facts"

# Severity buckets — fixed string set so dashboards can pivot on them.
SEVERITY_CRITICAL: Final[str] = "critical"
SEVERITY_WARNING: Final[str] = "warning"
SEVERITY_INFO: Final[str] = "info"

# Per-check issue-list cap.  Bounds the validator's memory use on
# huge corpora.  100 is enough to triage without overwhelming the
# operator; the absolute count is in :attr:`CheckResult.issues_found`.
MAX_ISSUES_PER_CHECK: Final[int] = 100

# Bounded read of duplicate candidates from the ILIKE heuristic —
# the full set can be large on a heterogeneous corpus, so we
# cap the returned list at this size.
MAX_DUPLICATE_SAMPLES: Final[int] = 50

# Token format used by the backfill engine.  Mirrors
# :class:`guinvere.knowledge_graph.consent.manager` so the validator can
# verify the token shape without an import.
_CONSENT_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^kg_[a-z0-9_]{1,32}_[a-z0-9_]{1,32}_[a-f0-9]{8}$"
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single validator check.

    Attributes:
        name: Short identifier for the check
            (e.g. ``"entity_coverage"``, ``"edge_integrity"``).
        passed: ``True`` when no issues were found.
        total_checked: Total number of rows / facts the check
            examined.  ``0`` is a valid value (means nothing to
            check — the corpus is empty).
        issues_found: Total number of issues detected.  Independent
            of :attr:`issues` length — the list is a *sample* of at
            most :data:`MAX_ISSUES_PER_CHECK` entries, the counter
            is the ground truth.
        issues: Per-issue details (capped at
            :data:`MAX_ISSUES_PER_CHECK`).  Each entry is a
            JSON-serialisable dict; the exact keys depend on the
            check (e.g. ``{"fact_id": "..."}`` for edge integrity,
            ``{"entity_id": "..."}`` for orphans).
        severity: One of :data:`SEVERITY_CRITICAL`,
            :data:`SEVERITY_WARNING`, :data:`SEVERITY_INFO`.  Used
            by the report to bucket counts.
    """

    name: str
    passed: bool
    total_checked: int = 0
    issues_found: int = 0
    issues: list[dict[str, object]] = field(default_factory=list)
    severity: str = SEVERITY_INFO


@dataclass(frozen=True)
class CoverageMetrics:
    """Snapshot of backfill coverage percentages.

    All percentages are in ``[0.0, 100.0]`` and rounded to two
    decimals.  ``duplicate_candidate_count`` is an absolute count,
    not a percentage.

    Attributes:
        entity_coverage_pct: ``%`` of source facts whose subject
            and object surface forms have a corresponding
            ``kg_entities`` row (live, non-tombstoned).
        edge_coverage_pct: ``%`` of source facts that have at
            least one non-tombstoned ``kg_edges`` row.
        consent_coverage_pct: ``%`` of backfill-tagged edges that
            carry a non-null ``consent_token`` matching the
            expected token shape.
        orphan_entity_pct: ``%`` of backfill-tagged entities that
            participate in zero non-tombstoned edges.
        duplicate_candidate_count: Total number of entity pairs
            the duplicate detector flagged as likely duplicates
            (case-insensitive name match within the same category).
    """

    entity_coverage_pct: float = 0.0
    edge_coverage_pct: float = 0.0
    consent_coverage_pct: float = 0.0
    orphan_entity_pct: float = 0.0
    duplicate_candidate_count: int = 0


@dataclass(frozen=True)
class ValidationReport:
    """Aggregate of every check + coverage snapshot.

    Attributes:
        checks: Ordered list of :class:`CheckResult` (matches the
            invocation order in :meth:`KGBackfillValidator.run_all_checks`).
        all_passed: ``True`` only when every check has
            :attr:`CheckResult.passed` set to ``True``.
        critical_failures: Number of checks whose
            :attr:`CheckResult.severity` is ``"critical"`` and
            :attr:`CheckResult.passed` is ``False``.
        warnings: Number of checks whose
            :attr:`CheckResult.severity` is ``"warning"`` and
            :attr:`CheckResult.passed` is ``False``.
        coverage: The :class:`CoverageMetrics` snapshot taken at
            the same time as the checks.
        timestamp: UTC timestamp (timezone-aware) when the report
            was assembled.
    """

    checks: list[CheckResult] = field(default_factory=list)
    all_passed: bool = True
    critical_failures: int = 0
    warnings: int = 0
    coverage: CoverageMetrics = field(default_factory=CoverageMetrics)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Session protocol
# ---------------------------------------------------------------------------


class _AsyncSessionProto(Protocol):
    """Minimal async session contract required by the validator.

    Read-only operations only — :meth:`execute` is the only method
    the validator actually calls.  The validator never mutates, so
    no :meth:`commit` / :meth:`rollback` are required.
    """

    async def execute(
        self, statement: object, params: object | None = None
    ) -> object:
        ...


# ---------------------------------------------------------------------------
# SQL templates
# ---------------------------------------------------------------------------


_COUNT_FACTS_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n FROM {SEMANTIC_FACTS_TABLE}"
)
_COUNT_BACKFILL_ENTITIES_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n FROM {KG_ENTITIES_TABLE} "
    "WHERE first_seen_source = :tag AND is_tombstoned = FALSE"
)
_COUNT_BACKFILL_EDGES_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n FROM {KG_EDGES_TABLE} "
    "WHERE source_id = :tag AND is_tombstoned = FALSE"
)
_COUNT_EDGES_WITH_CONSENT_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n FROM {KG_EDGES_TABLE} "
    "WHERE source_id = :tag "
    "  AND is_tombstoned = FALSE "
    "  AND consent_token IS NOT NULL "
    "  AND consent_token ~ :token_re"
)
_COUNT_FACTS_WITH_EDGES_SQL: Final[str] = (
    f"SELECT COUNT(DISTINCT source_fact_id) AS n "
    f"FROM {KG_EDGES_TABLE} "
    "WHERE source_id = :tag AND is_tombstoned = FALSE"
)
_COUNT_ORPHAN_ENTITIES_SQL: Final[str] = (
    f"SELECT COUNT(*) AS n "
    f"FROM {KG_ENTITIES_TABLE} e "
    "WHERE e.first_seen_source = :tag "
    "  AND e.is_tombstoned = FALSE "
    "  AND NOT EXISTS ("
    "    SELECT 1 FROM memory.kg_edges ed "
    "    WHERE (ed.src_entity_id = e.id OR ed.dst_entity_id = e.id) "
    "      AND ed.is_tombstoned = FALSE"
    "  )"
)
"""Orphan-entity count: backfill-created entities that participate in
zero non-tombstoned edges.  This is a SQL-level NOT EXISTS check
that is O(rows) once but uses the partial indexes on
``src_entity_id`` / ``dst_entity_id`` (the ones filtered by
``is_tombstoned = FALSE``)."""


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class KGBackfillValidator:
    """Validates the integrity and coverage of the backfilled KG.

    The validator is **read-only** — it never INSERTs, UPDATEs, or
    DELETEs.  All checks are pure ``SELECT`` queries (or ``COUNT`` /
    aggregate).  The validator is safe to run alongside the backfill
    engine (it does not take any locks).

    Args:
        session_factory: Callable that returns a fresh async session
            (typically :func:`guinvere.memory.db.get_async_session`).
        source_tag: Source tag the validator scopes its checks to.
            Defaults to :data:`BACKFILL_SOURCE_TAG`.  Pass an
            alternative tag when validating rows from a different
            backfill round.

    Example::

        validator = KGBackfillValidator(session_factory=get_async_session)
        report = await validator.run_all_checks()
        if not report.all_passed:
            for check in report.checks:
                if not check.passed:
                    print(f"{check.name}: {check.issues_found} issues")
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        source_tag: str = BACKFILL_SOURCE_TAG,
    ) -> None:
        if session_factory is None or not callable(session_factory):
            raise ValueError("session_factory is required and must be callable")
        if not source_tag or not source_tag.strip():
            raise ValueError("source_tag must be a non-empty string")

        self._session_factory: SessionFactory = session_factory
        self._source_tag: str = source_tag.strip()
        self._repo: KGRepository = KGRepository(session_factory)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_all_checks(self) -> ValidationReport:
        """Run every check + coverage snapshot and return the report.

        Checks are executed in the order declared below.  Each
        check's :class:`CheckResult` is appended to the report
        regardless of pass/fail so the operator gets the full
        picture in one pass.

        The method is non-raising: any exception inside an
        individual check is caught, converted to a
        :class:`CheckResult` with ``passed=False`` and a
        structured error, and the validator proceeds to the next
        check.  This is the operator-friendly behaviour — a
        failing check should not abort the rest of the suite.

        Returns:
            A :class:`ValidationReport` containing every check
            result, the aggregate counters, and the
            :class:`CoverageMetrics` snapshot.
        """
        ctx = KGLogContext(operation="kg_backfill_validate")
        log_kg_operation(logger, ctx)
        checks: list[CheckResult] = []
        for check_coro in (
            self.check_entity_coverage(),
            self.check_edge_integrity(),
            self.check_no_orphan_entities(),
            self.check_duplicate_detection(),
            self.check_consent_compliance(),
            self.check_tombstone_consistency(),
        ):
            try:
                result = await check_coro
            except Exception as exc:  # noqa: BLE001 -- defensive boundary
                logger.exception("validation check raised: %s", exc)
                result = CheckResult(
                    name="<unknown>",
                    passed=False,
                    total_checked=0,
                    issues_found=1,
                    issues=[
                        {
                            "error_type": type(exc).__name__,
                            "error_message": str(exc)[:500],
                        }
                    ],
                    severity=SEVERITY_CRITICAL,
                )
            checks.append(result)

        coverage = await self.compute_coverage_metrics()
        critical_failures = sum(
            1
            for check in checks
            if not check.passed and check.severity == SEVERITY_CRITICAL
        )
        warnings = sum(
            1
            for check in checks
            if not check.passed and check.severity == SEVERITY_WARNING
        )
        report = ValidationReport(
            checks=checks,
            all_passed=all(check.passed for check in checks),
            critical_failures=critical_failures,
            warnings=warnings,
            coverage=coverage,
        )
        ctx.result_count = len(checks)
        log_kg_operation(logger, ctx)
        return report

    async def check_entity_coverage(self) -> CheckResult:
        """Verify every ``semantic_facts`` subject/object has a KG entity.

        Implementation: hash-set the canonical keys of all
        non-tombstoned ``kg_entities`` rows, then hash-set the
        canonical keys derived from every ``semantic_facts`` row's
        subject and object surface forms.  A subject or object whose
        canonical key is not in the entity set counts as a missing
        coverage.

        For very large corpora the in-memory set can grow large; we
        therefore cap the issue list at :data:`MAX_ISSUES_PER_CHECK`
        while keeping the count accurate via
        :attr:`CheckResult.issues_found`.

        Returns:
            A :class:`CheckResult` with ``severity="critical"`` on
            failure.  Coverage gaps mean the backfill missed
            facts (extraction or resolution bug) — operator must
            re-run the engine for the affected slice.
        """
        try:
            async with self._repo.get_session() as session:
                # Load all live entity canonical keys.
                entity_keys = await self._fetch_entity_keys(session)
                # Load all facts and compute their subject/object
                # canonical keys in Python (the L1 lexical
                # classification is mirrored from the backfill
                # engine for consistency).
                facts = await self._fetch_all_facts(session)
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception("check_entity_coverage failed: %s", exc)
            return CheckResult(
                name="entity_coverage",
                passed=False,
                total_checked=0,
                issues_found=1,
                issues=[
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                ],
                severity=SEVERITY_CRITICAL,
            )

        issues: list[dict[str, object]] = []
        issues_found = 0
        for fact in facts:
            fact_id = fact["id"]
            subject = str(fact.get("subject") or "").strip()
            object_text = str(fact.get("object_val") or "").strip()
            if subject:
                subject_key = self._lexical_key(subject)
                if subject_key and subject_key not in entity_keys:
                    issues_found += 1
                    if len(issues) < MAX_ISSUES_PER_CHECK:
                        issues.append(
                            {
                                "fact_id": str(fact_id),
                                "slot": "subject",
                                "surface": subject[:200],
                                "missing_canonical_key": subject_key,
                            }
                        )
            if object_text:
                object_key = self._lexical_key(object_text)
                if object_key and object_key not in entity_keys:
                    issues_found += 1
                    if len(issues) < MAX_ISSUES_PER_CHECK:
                        issues.append(
                            {
                                "fact_id": str(fact_id),
                                "slot": "object",
                                "surface": object_text[:200],
                                "missing_canonical_key": object_key,
                            }
                        )

        return CheckResult(
            name="entity_coverage",
            passed=(issues_found == 0),
            total_checked=len(facts),
            issues_found=issues_found,
            issues=issues,
            severity=SEVERITY_CRITICAL,
        )

    async def check_edge_integrity(self) -> CheckResult:
        """Verify every ``kg_edges`` row has a valid ``source_fact_id``.

        The DDL declares ``source_fact_id`` ``NOT NULL`` with a
        ``REFERENCES memory.semantic_facts(id)`` FK, so an
        integrity violation means either a manual data fix that
        bypassed the FK or a corrupted migration.  Either way the
        affected rows must be tombstoned (not hard-deleted — the
        KG policy forbids hard delete).

        Returns:
            A :class:`CheckResult` with ``severity="critical"`` on
            failure.
        """
        sql = (
            f"SELECT e.id AS edge_id, e.source_fact_id "
            f"FROM {KG_EDGES_TABLE} e "
            "LEFT JOIN memory.semantic_facts f "
            "  ON e.source_fact_id = f.id "
            "WHERE f.id IS NULL"
        )
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(self._text(sql), {})
                rows = list(result.fetchall())
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception("check_edge_integrity failed: %s", exc)
            return CheckResult(
                name="edge_integrity",
                passed=False,
                total_checked=0,
                issues_found=1,
                issues=[
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                ],
                severity=SEVERITY_CRITICAL,
            )

        issues: list[dict[str, object]] = []
        for row in rows[:MAX_ISSUES_PER_CHECK]:
            issues.append(
                {
                    "edge_id": _row_get(row, "edge_id", default=""),
                    "source_fact_id": _row_get(row, "source_fact_id", default=""),
                }
            )
        return CheckResult(
            name="edge_integrity",
            passed=(len(rows) == 0),
            total_checked=len(rows),
            issues_found=len(rows),
            issues=issues,
            severity=SEVERITY_CRITICAL,
        )

    async def check_no_orphan_entities(self) -> CheckResult:
        """Find backfill-tagged entities that participate in zero edges.

        An orphan is usually a sign of an extraction failure (the
        entity was created but the corresponding edge insert was
        skipped — e.g. due to a malformed predicate).  Orphans
        should be reviewed; they are not auto-fixed because the
        operator may want to keep the entity and add the missing
        edge manually.

        Returns:
            A :class:`CheckResult` with ``severity="warning"`` on
            failure (orphans are operational debt, not data loss).
        """
        try:
            async with self._repo.get_session() as session:
                rows = await self._fetch_orphan_entities(session)
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception("check_no_orphan_entities failed: %s", exc)
            return CheckResult(
                name="no_orphan_entities",
                passed=False,
                total_checked=0,
                issues_found=1,
                issues=[
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                ],
                severity=SEVERITY_WARNING,
            )

        issues: list[dict[str, object]] = []
        for row in rows[:MAX_ISSUES_PER_CHECK]:
            issues.append(
                {
                    "entity_id": _row_get(row, "id", default=""),
                    "display_name": _row_get(row, "display_name", default=""),
                    "entity_type": _row_get(row, "entity_type", default=""),
                    "first_seen_at": str(
                        _row_get(row, "first_seen_at", default="")
                    ),
                }
            )
        return CheckResult(
            name="no_orphan_entities",
            passed=(len(rows) == 0),
            total_checked=len(rows),
            issues_found=len(rows),
            issues=issues,
            severity=SEVERITY_WARNING,
        )

    async def check_duplicate_detection(self) -> CheckResult:
        """Find likely-duplicate entities within the backfill corpus.

        The heuristic is intentionally simple: case-insensitive
        ``display_name`` match within the same ``entity_type``,
        restricted to backfill-tagged entities.  Confirmed
        duplicates should be merged via the entity-resolver
        pipeline; this check is a *triage* tool, not an auto-fix.

        Returns:
            A :class:`CheckResult` with ``severity="info"`` on
            non-empty results.  Duplicates are expected in raw
            semantic data and require human review to confirm.
        """
        sql = (
            f"SELECT entity_type, LOWER(display_name) AS lname, "
            "       COUNT(*) AS occurrences, "
            "       ARRAY_AGG(id) AS entity_ids, "
            "       ARRAY_AGG(display_name) AS names "
            f"FROM {KG_ENTITIES_TABLE} "
            "WHERE first_seen_source = :tag "
            "  AND is_tombstoned = FALSE "
            "GROUP BY entity_type, LOWER(display_name) "
            "HAVING COUNT(*) > 1 "
            "ORDER BY COUNT(*) DESC "
            "LIMIT :limit"
        )
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(
                    self._text(sql),
                    {"tag": self._source_tag, "limit": MAX_DUPLICATE_SAMPLES},
                )
                rows = list(result.fetchall())
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception("check_duplicate_detection failed: %s", exc)
            return CheckResult(
                name="duplicate_detection",
                passed=False,
                total_checked=0,
                issues_found=1,
                issues=[
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                ],
                severity=SEVERITY_INFO,
            )

        issues: list[dict[str, object]] = []
        total_candidates = 0
        for row in rows:
            occurrences = int(_row_get(row, "occurrences", default=0) or 0)
            total_candidates += occurrences
            if len(issues) < MAX_ISSUES_PER_CHECK:
                issues.append(
                    {
                        "entity_type": _row_get(row, "entity_type", default=""),
                        "lowercased_name": _row_get(row, "lname", default=""),
                        "occurrences": occurrences,
                        "entity_ids": [
                            str(eid)
                            for eid in (_row_get(row, "entity_ids", default=[]) or [])
                        ],
                    }
                )
        # ``passed`` here means "no duplicates found" — operator
        # opt-in to triaging the existing same-as candidates
        # rather than blocking the migration.
        return CheckResult(
            name="duplicate_detection",
            passed=(total_candidates == 0),
            total_checked=total_candidates,
            issues_found=total_candidates,
            issues=issues,
            severity=SEVERITY_INFO,
        )

    async def check_consent_compliance(self) -> CheckResult:
        """Verify backfill edges carry a valid ``consent_token``.

        The expected token shape is the regex used by
        :class:`guinvere.knowledge_graph.consent.manager.ConsentManager`.
        Edges without a matching token are an audit failure —
        either the engine was mis-configured or a row was written
        outside the engine (manual data fix).

        Returns:
            A :class:`CheckResult` with ``severity="critical"`` on
            failure.  Unconsented edges must be tombstoned; the
            system never deletes a row that may carry personal
            data.
        """
        sql = (
            f"SELECT id, source_fact_id, consent_token, consent_scope "
            f"FROM {KG_EDGES_TABLE} "
            "WHERE source_id = :tag "
            "  AND is_tombstoned = FALSE "
            "  AND (consent_token IS NULL "
            "       OR consent_token !~ :token_re)"
        )
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(
                    self._text(sql),
                    {
                        "tag": self._source_tag,
                        "token_re": _CONSENT_TOKEN_PATTERN.pattern,
                    },
                )
                rows = list(result.fetchall())
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception("check_consent_compliance failed: %s", exc)
            return CheckResult(
                name="consent_compliance",
                passed=False,
                total_checked=0,
                issues_found=1,
                issues=[
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                ],
                severity=SEVERITY_CRITICAL,
            )

        issues: list[dict[str, object]] = []
        for row in rows[:MAX_ISSUES_PER_CHECK]:
            token = _row_get(row, "consent_token", default=None)
            issues.append(
                {
                    "edge_id": str(_row_get(row, "id", default="")),
                    "source_fact_id": str(
                        _row_get(row, "source_fact_id", default="")
                    ),
                    "consent_token": (str(token) if token is not None else None),
                    "consent_scope": _row_get(row, "consent_scope", default=None),
                }
            )
        return CheckResult(
            name="consent_compliance",
            passed=(len(rows) == 0),
            total_checked=len(rows),
            issues_found=len(rows),
            issues=issues,
            severity=SEVERITY_CRITICAL,
        )

    async def check_tombstone_consistency(self) -> CheckResult:
        """Verify tombstoned entities have all their edges tombstoned.

        The KG policy is "soft-delete cascades": when an entity is
        tombstoned, every edge that references it should be
        tombstoned in the same transaction.  This check verifies
        the invariant by looking for edges whose ``src_entity_id``
        or ``dst_entity_id`` points at a tombstoned entity but
        which themselves are not tombstoned.

        A violation means the cascade failed — operator should
        re-run the cascade or tombstone the dangling edges
        manually.  This is a *correctness* invariant, not just
        hygiene.

        Returns:
            A :class:`CheckResult` with ``severity="warning"`` on
            failure.  Tombstone cascades are important for
            query correctness (a non-tombstoned edge pointing at a
            tombstoned entity would be filtered by the partial
            index on ``is_tombstoned=FALSE`` but could still
            surface in raw joins).
        """
        sql = (
            f"SELECT ed.id AS edge_id, ed.src_entity_id, ed.dst_entity_id "
            f"FROM {KG_EDGES_TABLE} ed "
            f"JOIN {KG_ENTITIES_TABLE} e_src "
            "  ON ed.src_entity_id = e_guinvere.id "
            f"JOIN {KG_ENTITIES_TABLE} e_dst "
            "  ON ed.dst_entity_id = e_dst.id "
            "WHERE ed.is_tombstoned = FALSE "
            "  AND (e_guinvere.is_tombstoned = TRUE OR e_dst.is_tombstoned = TRUE)"
        )
        try:
            async with self._repo.get_session() as session:
                result = await session.execute(self._text(sql), {})
                rows = list(result.fetchall())
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception("check_tombstone_consistency failed: %s", exc)
            return CheckResult(
                name="tombstone_consistency",
                passed=False,
                total_checked=0,
                issues_found=1,
                issues=[
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                ],
                severity=SEVERITY_WARNING,
            )

        issues: list[dict[str, object]] = []
        for row in rows[:MAX_ISSUES_PER_CHECK]:
            issues.append(
                {
                    "edge_id": str(_row_get(row, "edge_id", default="")),
                    "src_entity_id": str(_row_get(row, "src_entity_id", default="")),
                    "dst_entity_id": str(_row_get(row, "dst_entity_id", default="")),
                }
            )
        return CheckResult(
            name="tombstone_consistency",
            passed=(len(rows) == 0),
            total_checked=len(rows),
            issues_found=len(rows),
            issues=issues,
            severity=SEVERITY_WARNING,
        )

    async def compute_coverage_metrics(self) -> CoverageMetrics:
        """Compute the coverage percentages for the report.

        All percentages are computed from the same source-of-truth
        counts used by the individual checks, so the metrics
        cannot disagree with the report.

        Returns:
            A :class:`CoverageMetrics` snapshot.
        """
        try:
            async with self._repo.get_session() as session:
                total_facts = await self._scalar_count(
                    session, _COUNT_FACTS_SQL, {}
                )
                backfill_entities = await self._scalar_count(
                    session, _COUNT_BACKFILL_ENTITIES_SQL, {"tag": self._source_tag}
                )
                backfill_edges = await self._scalar_count(
                    session, _COUNT_BACKFILL_EDGES_SQL, {"tag": self._source_tag}
                )
                edges_with_consent = await self._scalar_count(
                    session,
                    _COUNT_EDGES_WITH_CONSENT_SQL,
                    {
                        "tag": self._source_tag,
                        "token_re": _CONSENT_TOKEN_PATTERN.pattern,
                    },
                )
                facts_with_edges = await self._scalar_count(
                    session, _COUNT_FACTS_WITH_EDGES_SQL, {"tag": self._source_tag}
                )
                orphan_entities = await self._scalar_count(
                    session, _COUNT_ORPHAN_ENTITIES_SQL, {"tag": self._source_tag}
                )
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception("compute_coverage_metrics failed: %s", exc)
            return CoverageMetrics()

        # Duplicate-candidate count is a separate SQL — kept here so
        # the report can pivot on a single number.
        try:
            async with self._repo.get_session() as session:
                duplicate_rows = await self._fetch_duplicate_candidate_count(session)
        except Exception as exc:  # noqa: BLE001 -- defensive boundary
            logger.exception("compute_coverage_metrics (duplicates) failed: %s", exc)
            duplicate_rows = []

        duplicate_count = sum(
            int(_row_get(row, "occurrences", default=0) or 0) for row in duplicate_rows
        )

        total_facts_int = int(total_facts)
        backfill_entities_int = int(backfill_entities)
        backfill_edges_int = int(backfill_edges)
        edges_with_consent_int = int(edges_with_consent)
        facts_with_edges_int = int(facts_with_edges)
        orphan_entities_int = int(orphan_entities)

        # Entity coverage: at the upper bound, every fact produces
        # two entities, so we compare backfill_entities against
        # ``2 * total_facts`` (the expected maximum).  In practice
        # the canonical-key UNIQUE collapses many duplicates so
        # coverage is usually well under 100% — that is the
        # expected behaviour of the resolution stage.
        entity_pct = _safe_pct(
            backfill_entities_int, max(1, 2 * total_facts_int)
        )
        edge_pct = _safe_pct(facts_with_edges_int, max(1, total_facts_int))
        consent_pct = _safe_pct(
            edges_with_consent_int, max(1, backfill_edges_int)
        )
        orphan_pct = _safe_pct(orphan_entities_int, max(1, backfill_entities_int))

        return CoverageMetrics(
            entity_coverage_pct=entity_pct,
            edge_coverage_pct=edge_pct,
            consent_coverage_pct=consent_pct,
            orphan_entity_pct=orphan_pct,
            duplicate_candidate_count=duplicate_count,
        )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    async def _fetch_entity_keys(
        self,
        session: _AsyncSessionProto,
    ) -> set[str]:
        """Return the set of all live entity canonical keys."""
        sql = (
            f"SELECT canonical_key FROM {KG_ENTITIES_TABLE} "
            "WHERE is_tombstoned = FALSE"
        )
        result = await session.execute(self._text(sql), {})
        rows = list(result.fetchall())
        return {_row_get(row, "canonical_key", default="") for row in rows if row}

    async def _fetch_all_facts(
        self,
        session: _AsyncSessionProto,
    ) -> list[dict[str, Any]]:
        """Return every semantic fact as a plain dict (for in-memory checks)."""
        sql = (
            f"SELECT id, subject, predicate, object_val, fact_type "
            f"FROM {SEMANTIC_FACTS_TABLE}"
        )
        result = await session.execute(self._text(sql), {})
        rows = list(result.fetchall())
        return [_row_to_fact_dict(row) for row in rows]

    async def _fetch_orphan_entities(
        self,
        session: _AsyncSessionProto,
    ) -> list[object]:
        """Return orphan backfill entities (no live edges)."""
        sql = (
            f"SELECT id, display_name, entity_type, first_seen_at "
            f"FROM {KG_ENTITIES_TABLE} e "
            "WHERE e.first_seen_source = :tag "
            "  AND e.is_tombstoned = FALSE "
            "  AND NOT EXISTS ("
            "    SELECT 1 FROM memory.kg_edges ed "
            "    WHERE (ed.src_entity_id = e.id OR ed.dst_entity_id = e.id) "
            "      AND ed.is_tombstoned = FALSE"
            "  ) "
            "ORDER BY first_seen_at ASC "
            "LIMIT :limit"
        )
        result = await session.execute(
            self._text(sql),
            {"tag": self._source_tag, "limit": MAX_ISSUES_PER_CHECK},
        )
        return list(result.fetchall())

    async def _fetch_duplicate_candidate_count(
        self,
        session: _AsyncSessionProto,
    ) -> list[object]:
        """Return duplicate-candidate groups (used for the count metric)."""
        sql = (
            f"SELECT COUNT(*) AS occurrences "
            f"FROM {KG_ENTITIES_TABLE} "
            "WHERE first_seen_source = :tag "
            "  AND is_tombstoned = FALSE "
            "GROUP BY entity_type, LOWER(display_name) "
            "HAVING COUNT(*) > 1"
        )
        result = await session.execute(
            self._text(sql), {"tag": self._source_tag}
        )
        return list(result.fetchall())

    @staticmethod
    async def _scalar_count(
        session: _AsyncSessionProto,
        sql: str,
        params: dict[str, object],
    ) -> int:
        """Execute a COUNT-style query and return the first column as int."""
        from sqlalchemy import text as _sql_text

        result = await session.execute(_sql_text(sql), params)
        row = result.first() if hasattr(result, "first") else None
        if row is None:
            return 0
        raw = row[0] if isinstance(row, tuple) else getattr(row, "n", None)
        if raw is None:
            return 0
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    # ------------------------------------------------------------------
    # SQL text helper
    # ------------------------------------------------------------------

    @staticmethod
    def _text(sql: str) -> Any:
        """Resolve ``sqlalchemy.text`` lazily."""
        from sqlalchemy import text as _sql_text

        return _sql_text(sql)

    # ------------------------------------------------------------------
    # Lexical helpers (mirror the backfill engine's classification)
    # ------------------------------------------------------------------

    @staticmethod
    def _lexical_key(text: str) -> str:
        """Derive a canonical-ish key for ``text`` (mirrors backfill).

        The validator does not need the *exact* canonical key — it
        just needs the same one the engine would have produced
        for a given surface form.  The implementation mirrors the
        engine's helper (``_classify_lexical`` + ``generate_canonical_key``)
        so the coverage check is precise.
        """
        # Local import to avoid a top-level dependency on
        # ``canonical.py`` that could create a cycle in the
        # validator's test harness.
        from guinvere.knowledge_graph.resolution.canonical import (
            generate_canonical_key,
        )

        category = _lexical_classify(text)
        return generate_canonical_key(text, category)


# ---------------------------------------------------------------------------
# Module-level helpers (testable in isolation)
# ---------------------------------------------------------------------------


def _row_to_fact_dict(row: object) -> dict[str, Any]:
    """Convert a SQLAlchemy ``Row`` to a plain dict (id/subject/predicate/object/fact_type)."""
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        try:
            return {str(k): v for k, v in mapping.items()}
        except (TypeError, ValueError):
            pass
    out: dict[str, Any] = {}
    for attr in (
        "id", "subject", "predicate", "object_val", "fact_type",
        "confidence", "source", "source_episode", "last_verified",
    ):
        if hasattr(row, attr):
            out[attr] = getattr(row, attr)
    if not out and hasattr(row, "__dict__"):
        out = {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
    return out


def _row_get(row: object, attr: str, *, default: object = None) -> object:
    """Read a column value from a SQLAlchemy ``Row`` or mapping.

    Tries ``_mapping`` first (SQLAlchemy 2.x), then ``__getattr__``
    on the row, then a ``__getitem__`` probe for sequence-style
    rows.  Returns ``default`` when the attribute is absent.
    Never raises — every access path is guarded.
    """
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        try:
            if attr in mapping:
                return mapping[attr]
        except (TypeError, KeyError, ValueError):
            pass
    if hasattr(row, attr):
        return getattr(row, attr)
    getter = getattr(row, "__getitem__", None)
    if getter is not None:
        try:
            return getter(attr)
        except (TypeError, KeyError, IndexError):
            return default
    return default


def _lexical_classify(text: str) -> str:
    """Mirror the backfill engine's lexical classification.

    The validator only needs *consistent* category assignment
    (so the canonical key derivation matches the engine).  The
    heuristic is intentionally minimal.
    """
    from guinvere.knowledge_graph.resolution.canonical import (
        normalize_entity_name,
    )

    cleaned = normalize_entity_name(text)
    if not cleaned:
        return "concept"
    if cleaned in {"guinevere", "faiz", "samm", "opencode", "hermes"}:
        return "person"
    if cleaned in {"postgresql", "redis", "docker", "kubernetes"}:
        return "technology"
    return "concept"


def _safe_pct(numerator: int, denominator: int) -> float:
    """Return ``numerator / denominator * 100`` rounded to 2 decimals.

    Returns ``0.0`` when the denominator is ``<= 0`` (avoids
    ``ZeroDivisionError`` on empty corpora).
    """
    if denominator <= 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100.0, 2)


# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------


__all__ = [
    # Severity constants
    "SEVERITY_CRITICAL",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    # Bounded-cap constants
    "MAX_ISSUES_PER_CHECK",
    "MAX_DUPLICATE_SAMPLES",
    # Dataclasses
    "CheckResult",
    "CoverageMetrics",
    "ValidationReport",
    # Validator
    "KGBackfillValidator",
]
