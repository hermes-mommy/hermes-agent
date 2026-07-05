"""Knowledge Graph exception hierarchy.

All KG-originated failures derive from :class:`KGError`.  Every exception
carries a human-readable ``message`` and an optional structured ``context``
dict for audit logging.  Stringification includes the class name so logs
and Sentry breadcrumbs identify the failing subsystem at a glance.

Safety boundary: :class:`KGConsentError` is reserved for consent / safe-word
violations.  Callers must NOT swallow it — it must propagate up to the
persona safety gate.
"""
from __future__ import annotations

from typing import TypeAlias

# ---------------------------------------------------------------------------
# Type alias for context payloads
# ---------------------------------------------------------------------------

KGErrorContext: TypeAlias = dict[str, object]
"""Structured diagnostic context for KG errors.

Restricted to ``object`` values (not ``Any``) so callers cannot smuggle
unserializable objects into audit logs.  Common keys:

- ``entity_id`` / ``edge_id`` — UUID of the affected KG node
- ``episode_id`` — source episode in ``memory.episodes``
- ``principal_id`` — actor who triggered the operation
- ``hop_count`` — graph traversal depth when the error occurred
"""


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class KGError(Exception):
    """Base class for all Knowledge Graph module errors.

    All downstream P16 modules must catch this base (never bare
    :class:`Exception`) when handling KG-originated failures.  Subclasses
    narrow the error category for observability and policy routing.
    """

    def __init__(self, message: str, context: KGErrorContext | None = None) -> None:
        super().__init__(message)
        self.message: str = message
        self.context: KGErrorContext = dict(context) if context else {}

    def __str__(self) -> str:
        if not self.context:
            return f"{type(self).__name__}: {self.message}"
        # Compact context summary — never log raw user data here.
        keys = ", ".join(sorted(self.context.keys()))
        return f"{type(self).__name__}: {self.message} (context=[{keys}])"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(message={self.message!r}, context={self.context!r})"


# ---------------------------------------------------------------------------
# Configuration & schema
# ---------------------------------------------------------------------------


class KGConfigError(KGError):
    """Invalid or missing KG configuration (e.g. Pydantic validation failure)."""


class KGSchemaError(KGError):
    """Database schema mismatch (missing table, wrong column type, etc.)."""


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


class KGExtractionError(KGError):
    """Entity / relation extraction failure (NER, RE, LLM extraction)."""


class KGResolutionError(KGError):
    """Entity resolution / deduplication failure (exact, fuzzy, or LLM match)."""


class KGQueryError(KGError):
    """Subgraph query / traversal failure (BFS, pattern match, Cypher-like)."""


class KGIngestionError(KGError):
    """Pipeline-level ingestion failure (batch write, validation, transaction)."""


# ---------------------------------------------------------------------------
# Safety / consent / resource
# ---------------------------------------------------------------------------


class KGConsentError(KGError):
    """Consent / safe-word boundary violation.  MUST propagate to safety gate.

    Raised when an operation would surface safe-word-flagged content
    (see :data:`SAFE_WORD_INDICATORS`), bypass a consent token check, or
    traverse an edge whose ``consent_token`` does not authorize the
    requesting principal.  Treat as an unrecoverable safety failure.
    """


class KGBudgetExceededError(KGError):
    """Token / hop / batch budget exceeded during a KG operation."""


__all__ = [
    "KGErrorContext",
    "KGError",
    "KGConfigError",
    "KGSchemaError",
    "KGExtractionError",
    "KGResolutionError",
    "KGQueryError",
    "KGConsentError",
    "KGIngestionError",
    "KGBudgetExceededError",
]
