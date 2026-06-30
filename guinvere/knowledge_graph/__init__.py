"""Guinevere Knowledge Graph (KG) module — P16.

Foundational package for the Knowledge Graph subsystem.  This ``__init__``
re-exports the lightweight surface (config, types, errors, constants)
eagerly and defers heavier modules (currently ``repository``, which
imports SQLAlchemy) to PEP 562 lazy attribute access.

Usage::

    from guinvere.knowledge_graph import (
        KGConfig,
        KGEntity,
        KGEdge,
        KGError,
        EntityCategory,
        RelationType,
        SAFE_WORD_INDICATORS,
    )

    # Repository is loaded on first attribute access:
    from guinvere.knowledge_graph import KGRepository  # noqa: E402

Submodule layout (each has its own ``__init__``):

- :mod:`guinvere.knowledge_graph.extraction`  — NER / RE pipeline
- :mod:`guinvere.knowledge_graph.resolution`  — entity resolution / dedup
- :mod:`guinvere.knowledge_graph.query`       — subgraph traversal
- :mod:`guinvere.knowledge_graph.ingestion`   — batch write pipeline
- :mod:`guinvere.knowledge_graph.consent`     — consent token + safe-word gates
- :mod:`guinvere.knowledge_graph.eval`        — evaluation harness
- :mod:`guinvere.knowledge_graph.observability` — metrics, tracing
- :mod:`guinvere.knowledge_graph.tests`       — internal test utilities
"""
from __future__ import annotations

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Eager re-exports (lightweight, no I/O, no DB driver import)
# ---------------------------------------------------------------------------

# Config
from guinvere.knowledge_graph.config import KGConfig

# Errors
from guinvere.knowledge_graph.errors import (
    KGBudgetExceededError,
    KGConfigError,
    KGConsentError,
    KGError,
    KGExtractionError,
    KGIngestionError,
    KGQueryError,
    KGResolutionError,
    KGSchemaError,
)

# Types
from guinvere.knowledge_graph.types import (
    EdgeStatus,
    EntityCategory,
    EntityResolutionResult,
    EntityType,
    ExtractedEntity,
    ExtractedRelation,
    KGEdge,
    KGEntity,
    KGTriple,
    RecallContext,
    RelationType,
    SemanticFact,
)

# Constants
from guinvere.knowledge_graph.constants import (
    CONSENT_TOKEN_PREFIX,
    DEFAULT_ENTITY_TYPES,
    DEFAULT_RELATION_TYPES,
    KG_RRF_WEIGHT,
    KG_TOKEN_BUDGET_MAX,
    MAX_TRAVERSAL_HOPS,
    RRF_K,
    SAFE_WORD_INDICATORS,
)


# ---------------------------------------------------------------------------
# Lazy re-exports (heavy modules — touched only on first attribute access)
# ---------------------------------------------------------------------------

# Maps the public name to the fully-qualified module that owns it.  Adding
# a new heavy submodule?  Drop it here and to ``__all__``; callers will
# get it transparently on first access.
_LAZY_EXPORTS: dict[str, str] = {
    "KGRepository": "guinvere.knowledge_graph.repository",
    "KGHealthStatus": "guinvere.knowledge_graph.repository",
    "AsyncSessionProtocol": "guinvere.knowledge_graph.repository",
    "SessionFactory": "guinvere.knowledge_graph.repository",
    # Wave 2 (P16-007) extraction layer — extractors are pulled in lazily
    # so this module's eager import cost stays flat.  Callers that hit
    # the extraction API will trigger the import on first access.
    "EntityExtractor": "guinvere.knowledge_graph.extraction",
    "RelationExtractor": "guinvere.knowledge_graph.extraction",
    "ENTITY_PATTERNS": "guinvere.knowledge_graph.extraction",
    "PREDICATE_MAP": "guinvere.knowledge_graph.extraction",
}


def __getattr__(name: str) -> object:
    """PEP 562 lazy attribute loader for heavy submodules.

    Only names registered in :data:`_LAZY_EXPORTS` are imported on
    demand.  Anything else raises ``AttributeError`` so accidental typos
    surface immediately instead of being silently masked.
    """
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )
    import importlib
    module = importlib.import_module(target)
    value = getattr(module, name)
    # Cache on the module so subsequent lookups are O(1).
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return all public names — including lazy ones — for ``dir()`` /
    IDE autocomplete support."""
    return sorted(set(__all__) | set(_LAZY_EXPORTS.keys()))


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    # Meta
    "__version__",
    # Key exports
    "KGConfig",
    "KGEntity",
    "KGEdge",
    "KGError",
    # Errors
    "KGConfigError",
    "KGSchemaError",
    "KGExtractionError",
    "KGResolutionError",
    "KGQueryError",
    "KGConsentError",
    "KGIngestionError",
    "KGBudgetExceededError",
    # Types
    "EntityCategory",
    "EntityType",
    "RelationType",
    "EdgeStatus",
    "KGTriple",
    "RecallContext",
    "EntityResolutionResult",
    # Extraction layer (P16-007)
    "ExtractedEntity",
    "ExtractedRelation",
    "SemanticFact",
    # Constants
    "RRF_K",
    "KG_RRF_WEIGHT",
    "KG_TOKEN_BUDGET_MAX",
    "MAX_TRAVERSAL_HOPS",
    "CONSENT_TOKEN_PREFIX",
    "DEFAULT_ENTITY_TYPES",
    "DEFAULT_RELATION_TYPES",
    "SAFE_WORD_INDICATORS",
    # Lazy (re-exported via __getattr__)
    "KGRepository",
    "KGHealthStatus",
    "AsyncSessionProtocol",
    "SessionFactory",
    "EntityExtractor",
    "RelationExtractor",
    "ENTITY_PATTERNS",
    "PREDICATE_MAP",
]
