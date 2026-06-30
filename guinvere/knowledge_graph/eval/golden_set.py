"""Golden test set for KG recall evaluation (P16-005).

Defines the manually-curated benchmark used to measure recall quality
with and without the Knowledge Graph integration.

Structure
---------

* :class:`GoldenCase` — one labelled query with expected entity, edge,
  and recall IDs plus difficulty and category tags.
* :class:`GoldenTestSet` — collection of cases with load/validate/
  filter helpers.
* :func:`create_sample_golden_set` — deterministic 10-case fixture for
  smoke-testing the harness.

The golden set is intentionally **not** the recall source itself — it
is the ground-truth labels (oracle).  The harness calls
:func:`src.memory.read_pipeline.recall_memories` twice (once with
``kg_enabled=False`` and once with ``kg_enabled=True``), computes the
metric deltas, and writes a comparison report.

File format
-----------

JSON object with the following shape::

    {
      "version": "1.0",
      "description": "Free-form description of the set",
      "cases": [
        {
          "id": "case-001",
          "query": "What is Guinevere?",
          "expected_entity_ids": ["..."],
          "expected_edge_ids": ["..."],
          "expected_recall_ids": ["..."],
          "difficulty": "easy",
          "category": "project_meta"
        }
      ]
    """

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Schema version emitted by :func:`create_sample_golden_set` and
#: expected by :meth:`GoldenTestSet.load`.  Bump on incompatible
#: changes to the JSON shape.
GOLDEN_SET_SCHEMA_VERSION: Final[str] = "1.0"

#: Valid difficulty buckets.  Anything else triggers
#: :class:`GoldenSetValidationError`.
VALID_DIFFICULTIES: Final[tuple[str, ...]] = ("easy", "medium", "hard")

#: Maximum allowed length of a single ``query`` string.  Beyond this
#: we reject the case to keep the benchmark queries realistic.
MAX_QUERY_LENGTH: Final[int] = 1024

#: Maximum allowed expected-ID list size.  Curated sets should stay
#: small enough to review manually — 200 IDs per case is a generous
#: ceiling.
MAX_EXPECTED_IDS_PER_CASE: Final[int] = 200


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class GoldenSetValidationError(ValueError):
    """Raised when a golden set file fails validation.

    The message includes the offending field and (when available) the
    case index so the operator can locate the problem quickly.
    """


# ---------------------------------------------------------------------------
# GoldenCase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoldenCase:
    """One labelled query for the KG recall benchmark.

    Attributes:
        id: Stable identifier for the case (e.g. ``"case-001"``).
            Used in reports and audit logs.
        query: Natural-language query string.  Must be non-empty and
            at most :data:`MAX_QUERY_LENGTH` characters.
        expected_entity_ids: Entity UUIDs that **should** appear in
            KG-driven recall results.  Used to score the
            ``with-KG`` run only — the baseline run ignores this list.
        expected_edge_ids: Edge UUIDs that should be discovered via
            graph traversal.  Used to validate the KG signal path.
        expected_recall_ids: Memory (episode) UUIDs that **any**
            recall (with or without KG) should surface.  These are
            the canonical relevance labels.
        difficulty: One of ``"easy"``, ``"medium"``, ``"hard"``.
            Drives the per-difficulty breakdown in the report.
        category: Free-form bucket (``"project_meta"``,
            ``"person_entity"``, ``"temporal"``, ...).  Drives the
            per-category breakdown.
        notes: Optional human-readable annotation.  Never used by
            the evaluator; surfaced only in the report.
    """

    id: str
    query: str
    expected_entity_ids: list[str] = field(default_factory=list)
    expected_edge_ids: list[str] = field(default_factory=list)
    expected_recall_ids: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    category: str = "general"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise GoldenSetValidationError("case.id must be non-empty")
        if not self.query or not self.query.strip():
            raise GoldenSetValidationError(
                f"case.query must be non-empty (case_id={self.id})",
            )
        if len(self.query) > MAX_QUERY_LENGTH:
            raise GoldenSetValidationError(
                f"case.query exceeds {MAX_QUERY_LENGTH} chars "
                f"(case_id={self.id})",
            )
        if self.difficulty not in VALID_DIFFICULTIES:
            raise GoldenSetValidationError(
                f"case.difficulty must be one of {VALID_DIFFICULTIES}; "
                f"got {self.difficulty!r} (case_id={self.id})",
            )
        for label, ids in (
            ("expected_entity_ids", self.expected_entity_ids),
            ("expected_edge_ids", self.expected_edge_ids),
            ("expected_recall_ids", self.expected_recall_ids),
        ):
            if len(ids) > MAX_EXPECTED_IDS_PER_CASE:
                raise GoldenSetValidationError(
                    f"case.{label} has {len(ids)} entries; ceiling is "
                    f"{MAX_EXPECTED_IDS_PER_CASE} (case_id={self.id})",
                )
            for raw in ids:
                try:
                    uuid.UUID(str(raw))
                except (ValueError, AttributeError, TypeError) as exc:
                    raise GoldenSetValidationError(
                        f"case.{label} contains invalid UUID "
                        f"{raw!r} (case_id={self.id})",
                    ) from exc


# ---------------------------------------------------------------------------
# GoldenTestSet
# ---------------------------------------------------------------------------


@dataclass
class GoldenTestSet:
    """Collection of :class:`GoldenCase` entries with filter helpers.

    Construct one of three ways:

    1. Load from a JSON file via :meth:`load`.
    2. Build programmatically by appending :class:`GoldenCase` to
       :attr:`cases`.
    3. Use :func:`create_sample_golden_set` for a 10-case fixture.

    Iteration yields the cases in insertion order so reports are
    deterministic.
    """

    version: str = GOLDEN_SET_SCHEMA_VERSION
    description: str = ""
    cases: list[GoldenCase] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Re-validate unique case IDs — the dataclass-level check on
        # GoldenCase does not catch cross-case duplicates.
        seen: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                raise GoldenSetValidationError(
                    f"duplicate case.id {case.id!r} in golden set",
                )
            seen.add(case.id)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> GoldenTestSet:
        """Load and validate a golden set from a JSON file.

        Args:
            path: Filesystem path to the JSON file.

        Returns:
            A populated :class:`GoldenTestSet`.

        Raises:
            FileNotFoundError: The file does not exist.
            GoldenSetValidationError: The file is malformed, the
                schema version is unsupported, or any case fails
                validation.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"golden set file not found: {file_path}")
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GoldenSetValidationError(
                f"golden set file is not valid JSON: {file_path} ({exc})",
            ) from exc

        if not isinstance(raw, dict):
            raise GoldenSetValidationError(
                "golden set root must be a JSON object",
            )

        version = str(raw.get("version", GOLDEN_SET_SCHEMA_VERSION))
        if version != GOLDEN_SET_SCHEMA_VERSION:
            raise GoldenSetValidationError(
                f"unsupported golden set version {version!r}; "
                f"this evaluator expects {GOLDEN_SET_SCHEMA_VERSION!r}",
            )

        description = str(raw.get("description", ""))
        cases_raw = raw.get("cases", [])
        if not isinstance(cases_raw, list):
            raise GoldenSetValidationError(
                "'cases' must be a JSON array",
            )

        cases: list[GoldenCase] = []
        for index, entry in enumerate(cases_raw):
            cases.append(cls._parse_case(entry, index))

        return cls(version=version, description=description, cases=cases)

    @classmethod
    def from_cases(
        cls,
        cases: list[GoldenCase],
        *,
        description: str = "",
    ) -> GoldenTestSet:
        """Build a test set directly from a list of :class:`GoldenCase`.

        Args:
            cases: Pre-built cases (already validated by their own
                ``__post_init__``).
            description: Optional human-readable description.

        Returns:
            A :class:`GoldenTestSet` with duplicate IDs rejected.
        """
        return cls(
            version=GOLDEN_SET_SCHEMA_VERSION,
            description=description,
            cases=list(cases),
        )

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[GoldenCase]:
        return iter(self.cases)

    def __len__(self) -> int:
        return len(self.cases)

    def __getitem__(self, key: str | int) -> GoldenCase:
        """Look up a case by string ID or by integer index.

        Args:
            key: Either a :class:`GoldenCase.id` (string) or a
                positional index into :attr:`cases`.

        Returns:
            The matching :class:`GoldenCase`.

        Raises:
            KeyError: No case matches ``key``.
            IndexError: ``key`` is a negative or out-of-range int.
            TypeError: ``key`` is neither ``str`` nor ``int``.
        """
        if isinstance(key, str):
            for case in self.cases:
                if case.id == key:
                    return case
            raise KeyError(f"no golden case with id {key!r}")
        if isinstance(key, int):
            return self.cases[key]
        raise TypeError(
            f"GoldenTestSet indices must be str or int, "
            f"not {type(key).__name__}",
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_by_category(self, category: str) -> GoldenTestSet:
        """Return a new set containing only cases with ``category``.

        Args:
            category: Exact category string to match (case-sensitive).

        Returns:
            A new :class:`GoldenTestSet` with the matching subset.
        """
        matched = [c for c in self.cases if c.category == category]
        return GoldenTestSet(
            version=self.version,
            description=(
                f"{self.description} [category={category}]"
                if self.description else f"filtered by category={category}"
            ),
            cases=matched,
        )

    def filter_by_difficulty(self, difficulty: str) -> GoldenTestSet:
        """Return a new set containing only cases with ``difficulty``.

        Args:
            difficulty: One of ``"easy"``, ``"medium"``, ``"hard"``.

        Returns:
            A new :class:`GoldenTestSet` with the matching subset.

        Raises:
            GoldenSetValidationError: ``difficulty`` is not one of
                the allowed values.
        """
        if difficulty not in VALID_DIFFICULTIES:
            raise GoldenSetValidationError(
                f"invalid difficulty {difficulty!r}; "
                f"expected one of {VALID_DIFFICULTIES}",
            )
        matched = [c for c in self.cases if c.difficulty == difficulty]
        return GoldenTestSet(
            version=self.version,
            description=(
                f"{self.description} [difficulty={difficulty}]"
                if self.description else f"filtered by difficulty={difficulty}"
            ),
            cases=matched,
        )

    def categories(self) -> list[str]:
        """Return the distinct categories present in the set."""
        return sorted({c.category for c in self.cases})

    def difficulties(self) -> list[str]:
        """Return the distinct difficulty buckets present in the set."""
        return sorted({c.difficulty for c in self.cases})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_case(entry: object, index: int) -> GoldenCase:
        """Validate and coerce one JSON entry into a :class:`GoldenCase`."""
        if not isinstance(entry, dict):
            raise GoldenSetValidationError(
                f"case entry #{index} must be a JSON object, got "
                f"{type(entry).__name__}",
            )

        try:
            case_id = str(entry["id"])
        except KeyError as exc:
            raise GoldenSetValidationError(
                f"case entry #{index} missing required field 'id'",
            ) from exc

        try:
            query = str(entry["query"])
        except KeyError as exc:
            raise GoldenSetValidationError(
                f"case {case_id!r} missing required field 'query'",
            ) from exc

        try:
            return GoldenCase(
                id=case_id,
                query=query,
                expected_entity_ids=_coerce_uuid_list(
                    entry.get("expected_entity_ids", []), "expected_entity_ids", case_id,
                ),
                expected_edge_ids=_coerce_uuid_list(
                    entry.get("expected_edge_ids", []), "expected_edge_ids", case_id,
                ),
                expected_recall_ids=_coerce_uuid_list(
                    entry.get("expected_recall_ids", []), "expected_recall_ids", case_id,
                ),
                difficulty=str(entry.get("difficulty", "medium")),
                category=str(entry.get("category", "general")),
                notes=str(entry.get("notes", "")),
            )
        except GoldenSetValidationError:
            raise
        except Exception as exc:  # noqa: BLE001 — narrowed to value errors
            raise GoldenSetValidationError(
                f"case {case_id!r} could not be parsed: {exc}",
            ) from exc


def _coerce_uuid_list(
    raw: object,
    field_name: str,
    case_id: str,
) -> list[str]:
    """Validate that ``raw`` is a list of UUID strings.

    Args:
        raw: Value pulled from JSON (expected to be a list of strings).
        field_name: Name of the field (for error messages).
        case_id: ID of the enclosing case (for error messages).

    Returns:
        The list coerced to ``list[str]``.

    Raises:
        GoldenSetValidationError: ``raw`` is not a list, or any
            element is not a valid UUID string.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise GoldenSetValidationError(
            f"case {case_id!r}: {field_name} must be a list",
        )
    out: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            raise GoldenSetValidationError(
                f"case {case_id!r}: {field_name} entry {entry!r} "
                f"is not a string",
            )
        try:
            uuid.UUID(entry)
        except ValueError as exc:
            raise GoldenSetValidationError(
                f"case {case_id!r}: {field_name} entry {entry!r} "
                f"is not a valid UUID",
            ) from exc
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Sample fixture
# ---------------------------------------------------------------------------


def create_sample_golden_set() -> GoldenTestSet:
    """Return a deterministic 10-case fixture for smoke testing.

    The IDs are deterministic UUIDv5 strings so the fixture is
    reproducible across runs.  They do **not** point at real
    episodes — they exist solely to exercise the metric, A/B, and
    report machinery end-to-end.

    Categories covered:

    * ``project_meta`` — easy
    * ``person_entity`` — easy / medium
    * ``temporal`` — medium
    * ``factual_recall`` — easy / medium / hard
    * ``cross_hop`` — hard
    * ``noisy`` — hard

    Returns:
        A :class:`GoldenTestSet` ready for the harness.
    """
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000001")
    cases: list[GoldenCase] = [
        GoldenCase(
            id="case-001",
            query="What is Guinevere?",
            expected_entity_ids=[str(uuid.uuid5(namespace, "guinevere-project"))],
            expected_edge_ids=[],
            expected_recall_ids=[str(uuid.uuid5(namespace, "guinevere-recall-1"))],
            difficulty="easy",
            category="project_meta",
            notes="Trivial project self-description",
        ),
        GoldenCase(
            id="case-002",
            query="Who is Faiz?",
            expected_entity_ids=[
                str(uuid.uuid5(namespace, "faiz-person")),
                str(uuid.uuid5(namespace, "guinevere-operator")),
            ],
            expected_edge_ids=[str(uuid.uuid5(namespace, "faiz-owns-guinevere"))],
            expected_recall_ids=[str(uuid.uuid5(namespace, "faiz-recall-1"))],
            difficulty="easy",
            category="person_entity",
            notes="Single-entity lookup, KG should add nothing",
        ),
        GoldenCase(
            id="case-003",
            query="What PostgreSQL schema does Guinevere use for memory?",
            expected_entity_ids=[
                str(uuid.uuid5(namespace, "postgresql-db")),
                str(uuid.uuid5(namespace, "memory-schema")),
            ],
            expected_edge_ids=[str(uuid.uuid5(namespace, "memory-uses-postgres"))],
            expected_recall_ids=[
                str(uuid.uuid5(namespace, "schema-recall-1")),
                str(uuid.uuid5(namespace, "schema-recall-2")),
            ],
            difficulty="medium",
            category="factual_recall",
            notes="Two-entity query, KG can boost ranking",
        ),
        GoldenCase(
            id="case-004",
            query="When was the safety policy last updated?",
            expected_entity_ids=[str(uuid.uuid5(namespace, "persona-safety-policy"))],
            expected_edge_ids=[str(uuid.uuid5(namespace, "policy-edited-at"))],
            expected_recall_ids=[str(uuid.uuid5(namespace, "policy-recall-1"))],
            difficulty="medium",
            category="temporal",
            notes="Date-style query, recency dominates",
        ),
        GoldenCase(
            id="case-005",
            query="Which ADRs govern the consent framework?",
            expected_entity_ids=[
                str(uuid.uuid5(namespace, "adr-001")),
                str(uuid.uuid5(namespace, "adr-002")),
                str(uuid.uuid5(namespace, "consent-policy")),
            ],
            expected_edge_ids=[
                str(uuid.uuid5(namespace, "adr-001-cites-consent")),
                str(uuid.uuid5(namespace, "adr-002-cites-consent")),
            ],
            expected_recall_ids=[
                str(uuid.uuid5(namespace, "adr-recall-1")),
                str(uuid.uuid5(namespace, "adr-recall-2")),
            ],
            difficulty="medium",
            category="cross_hop",
            notes="Multi-hop: ADR -> policy",
        ),
        GoldenCase(
            id="case-006",
            query="What is the disaster recovery RTO for PostgreSQL?",
            expected_entity_ids=[
                str(uuid.uuid5(namespace, "dr-plan")),
                str(uuid.uuid5(namespace, "postgresql-db")),
            ],
            expected_edge_ids=[str(uuid.uuid5(namespace, "dr-rto-postgres"))],
            expected_recall_ids=[str(uuid.uuid5(namespace, "dr-recall-1"))],
            difficulty="medium",
            category="factual_recall",
            notes="Specific numeric lookup",
        ),
        GoldenCase(
            id="case-007",
            query="How does the agent loop handle HARD STOP?",
            expected_entity_ids=[
                str(uuid.uuid5(namespace, "agent-loop")),
                str(uuid.uuid5(namespace, "persona-safety-policy")),
                str(uuid.uuid5(namespace, "hard-stop-token")),
            ],
            expected_edge_ids=[
                str(uuid.uuid5(namespace, "agent-loop-uses-hard-stop")),
            ],
            expected_recall_ids=[
                str(uuid.uuid5(namespace, "hard-stop-recall-1")),
                str(uuid.uuid5(namespace, "hard-stop-recall-2")),
            ],
            difficulty="hard",
            category="cross_hop",
            notes="Cross-domain: agent loop + safety policy",
        ),
        GoldenCase(
            id="case-008",
            query="Explain the RRF fusion weights used by recall",
            expected_entity_ids=[
                str(uuid.uuid5(namespace, "read-pipeline")),
                str(uuid.uuid5(namespace, "kg-rrf-fusion")),
            ],
            expected_edge_ids=[str(uuid.uuid5(namespace, "pipeline-uses-rrf"))],
            expected_recall_ids=[
                str(uuid.uuid5(namespace, "rrf-recall-1")),
                str(uuid.uuid5(namespace, "rrf-recall-2")),
                str(uuid.uuid5(namespace, "rrf-recall-3")),
            ],
            difficulty="hard",
            category="factual_recall",
            notes="Technical recall mechanics, KG should rank higher",
        ),
        GoldenCase(
            id="case-009",
            query="Asdfgh random gibberish nonsense",
            expected_entity_ids=[],
            expected_edge_ids=[],
            expected_recall_ids=[],
            difficulty="hard",
            category="noisy",
            notes="Negative case: no recall expected",
        ),
        GoldenCase(
            id="case-010",
            query="What projects does Faiz oversee besides Guinevere?",
            expected_entity_ids=[
                str(uuid.uuid5(namespace, "faiz-person")),
                str(uuid.uuid5(namespace, "guinevere-project")),
            ],
            expected_edge_ids=[str(uuid.uuid5(namespace, "faiz-owns-guinevere"))],
            expected_recall_ids=[str(uuid.uuid5(namespace, "projects-recall-1"))],
            difficulty="hard",
            category="cross_hop",
            notes="Multi-hop fan-out: person -> owned projects",
        ),
    ]
    return GoldenTestSet.from_cases(
        cases,
        description="P16-005 sample fixture (10 cases, deterministic UUIDv5)",
    )


# ---------------------------------------------------------------------------
# JSON schema (informational, for documentation consumers)
# ---------------------------------------------------------------------------

GOLDEN_SET_JSON_SCHEMA: Final[dict[str, object]] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Guinevere Golden Test Set",
    "type": "object",
    "required": ["version", "cases"],
    "additionalProperties": False,
    "properties": {
        "version": {
            "type": "string",
            "const": GOLDEN_SET_SCHEMA_VERSION,
            "description": "Schema version. Must match evaluator build.",
        },
        "description": {
            "type": "string",
            "description": "Free-form human description of the set.",
        },
        "cases": {
            "type": "array",
            "minItems": 1,
            "maxItems": 1000,
            "items": {
                "type": "object",
                "required": ["id", "query"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "query": {"type": "string", "minLength": 1, "maxLength": MAX_QUERY_LENGTH},
                    "expected_entity_ids": {
                        "type": "array",
                        "items": {"type": "string", "format": "uuid"},
                        "maxItems": MAX_EXPECTED_IDS_PER_CASE,
                    },
                    "expected_edge_ids": {
                        "type": "array",
                        "items": {"type": "string", "format": "uuid"},
                        "maxItems": MAX_EXPECTED_IDS_PER_CASE,
                    },
                    "expected_recall_ids": {
                        "type": "array",
                        "items": {"type": "string", "format": "uuid"},
                        "maxItems": MAX_EXPECTED_IDS_PER_CASE,
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": list(VALID_DIFFICULTIES),
                    },
                    "category": {"type": "string", "minLength": 1},
                    "notes": {"type": "string"},
                },
            },
        },
    },
}


__all__ = [
    "GoldenCase",
    "GoldenTestSet",
    "GoldenSetValidationError",
    "GOLDEN_SET_SCHEMA_VERSION",
    "GOLDEN_SET_JSON_SCHEMA",
    "VALID_DIFFICULTIES",
    "create_sample_golden_set",
]