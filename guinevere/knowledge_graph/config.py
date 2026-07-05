"""Knowledge Graph module configuration via Pydantic ``BaseSettings``.

All values are loaded from environment variables with the ``GUINEVERE_KG_``
prefix.  Sensible defaults align with the PRD v2.2 P16 spec; override via
SOPS-decrypted env at runtime.  This module is intentionally free of any
DB / LLM client imports so it can be imported during config validation
without triggering heavy side effects.

Pattern matches ``guinevere.gmail.config`` and ``guinevere.x_poster.config``.

Env-var name mapping
--------------------
Pydantic-settings v2 has a documented behaviour where, when ``alias`` is
set on a field, the env-var name becomes the alias verbatim — the
``env_prefix`` is **not** prepended.  To produce operator-friendly env
var names (``GUINEVERE_KG_RRF_WEIGHT``) while keeping the public Python
field names prefixed with ``kg_`` (``kg_rrf_weight``), we set
``env_prefix=""`` and pass the full env-var name via ``validation_alias``
on every field.  ``populate_by_name=True`` keeps the ``kg_*`` field
names usable for programmatic access and direct construction
(``KGConfig(kg_rrf_weight=0.42)``).

Mapping::

    KGConfig field   env var
    ---------------  --------------------------
    kg_enabled       GUINEVERE_KG_ENABLED
    kg_rrf_weight    GUINEVERE_KG_RRF_WEIGHT
    kg_token_budget  GUINEVERE_KG_TOKEN_BUDGET
    kg_max_hops      GUINEVERE_KG_MAX_HOPS
    kg_batch_size    GUINEVERE_KG_BATCH_SIZE
    kg_cron_hour     GUINEVERE_KG_CRON_HOUR
    kg_cron_minute   GUINEVERE_KG_CRON_MINUTE
    kg_dedup_threshold  GUINEVERE_KG_DEDUP_THRESHOLD
    kg_entity_types  GUINEVERE_KG_ENTITY_TYPES  (list[str], JSON or CSV)
    kg_relation_types GUINEVERE_KG_RELATION_TYPES  (list[str], JSON or CSV)
"""
from __future__ import annotations

import json
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from guinevere.knowledge_graph.constants import (
    DEFAULT_ENTITY_TYPES,
    DEFAULT_RELATION_TYPES,
    KG_RRF_WEIGHT,
    KG_TOKEN_BUDGET_MAX,
    MAX_TRAVERSAL_HOPS,
)


# ---------------------------------------------------------------------------
# List parser (env vars → list[str])
# ---------------------------------------------------------------------------


def _parse_list_field(v: str | list[str]) -> list[str]:
    """Parse a ``list[str]`` env var that may be JSON, comma-separated, or empty.

    Handles:
    - ``["a", "b"]`` (JSON array)
    - ``"a,b,c"`` (comma-separated)
    - ``""`` (empty → ``[]``)
    - ``["scope"]`` (JSON single-element)

    Mirrors ``guinevere.gmail.config._parse_list_field`` to keep env-loading
    behaviour consistent across Guinevere modules.
    """
    if isinstance(v, list):
        return v
    if not isinstance(v, str):
        return []
    stripped = v.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
    return [s.strip() for s in stripped.split(",") if s.strip()]


ListOfStrings = Annotated[list[str], NoDecode, BeforeValidator(_parse_list_field)]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


# Env-var name constants.  Centralised so the prefix can be changed in
# one place and so static analysers can detect typos in alias strings.
ENV_ENABLED = "GUINEVERE_KG_ENABLED"
ENV_RRF_WEIGHT = "GUINEVERE_KG_RRF_WEIGHT"
ENV_TOKEN_BUDGET = "GUINEVERE_KG_TOKEN_BUDGET"
ENV_MAX_HOPS = "GUINEVERE_KG_MAX_HOPS"
ENV_BATCH_SIZE = "GUINEVERE_KG_BATCH_SIZE"
ENV_CRON_HOUR = "GUINEVERE_KG_CRON_HOUR"
ENV_CRON_MINUTE = "GUINEVERE_KG_CRON_MINUTE"
ENV_DEDUP_THRESHOLD = "GUINEVERE_KG_DEDUP_THRESHOLD"
ENV_ENTITY_TYPES = "GUINEVERE_KG_ENTITY_TYPES"
ENV_RELATION_TYPES = "GUINEVERE_KG_RELATION_TYPES"


class KGConfig(BaseSettings):
    """Knowledge Graph runtime configuration.

    Loaded from env vars with the ``GUINEVERE_KG_`` prefix.  All fields
    have production-safe defaults.  Validate explicitly with
    :meth:`KGConfig.model_validate` when loading from non-env sources
    (e.g. SOPS-decrypted JSON).
    """

    model_config = SettingsConfigDict(
        # env_prefix is empty because each field sets its full env var
        # name via ``validation_alias``.  See module docstring for the
        # rationale (pydantic-settings v2 alias semantics).
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # -- feature flag ------------------------------------------------------

    kg_enabled: bool = Field(
        default=True,
        validation_alias=ENV_ENABLED,
        description="Master switch for the KG module.  When false, the "
        "memory read pipeline falls back to vector+FTS only.",
    )

    # -- RRF + budgets -----------------------------------------------------

    kg_rrf_weight: float = Field(
        default=KG_RRF_WEIGHT,
        validation_alias=ENV_RRF_WEIGHT,
        ge=0.0,
        le=1.0,
        description="Weight applied to the KG channel during RRF fusion with "
        "the memory read pipeline (vector + FTS + recency).",
    )

    kg_token_budget: int = Field(
        default=KG_TOKEN_BUDGET_MAX,
        validation_alias=ENV_TOKEN_BUDGET,
        ge=1,
        description="Maximum tokens a single KG RecallContext may contribute.",
    )

    kg_max_hops: int = Field(
        default=MAX_TRAVERSAL_HOPS,
        validation_alias=ENV_MAX_HOPS,
        ge=1,
        le=10,
        description="Maximum BFS/DFS hop depth during subgraph retrieval.",
    )

    kg_batch_size: int = Field(
        default=100,
        validation_alias=ENV_BATCH_SIZE,
        ge=1,
        le=10_000,
        description="Number of episodes processed per ingestion batch.",
    )

    # -- cron (daily KG refresh) ------------------------------------------

    kg_cron_hour: int = Field(
        default=3,
        validation_alias=ENV_CRON_HOUR,
        ge=0,
        le=23,
        description="Scheduled hour (0-23) for the daily KG refresh job. "
        "Timezone is Asia/Bangkok (ICT, no DST) — see consolidation.py.",
    )

    kg_cron_minute: int = Field(
        default=30,
        validation_alias=ENV_CRON_MINUTE,
        ge=0,
        le=59,
        description="Scheduled minute (0-59) for the daily KG refresh job.",
    )

    # -- resolution thresholds --------------------------------------------

    kg_dedup_threshold: float = Field(
        default=0.85,
        validation_alias=ENV_DEDUP_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity for entity deduplication. "
        "Below this, a mention creates a new canonical entity instead of "
        "collapsing into an existing one.",
    )

    # -- taxonomy ----------------------------------------------------------

    kg_entity_types: ListOfStrings = Field(
        default_factory=lambda: list(DEFAULT_ENTITY_TYPES),
        validation_alias=ENV_ENTITY_TYPES,
        description="Allowed entity categories.  Override to narrow the "
        "closed taxonomy enforced by the extraction stage.",
    )

    kg_relation_types: ListOfStrings = Field(
        default_factory=lambda: list(DEFAULT_RELATION_TYPES),
        validation_alias=ENV_RELATION_TYPES,
        description="Allowed relation types.  Override to narrow the closed "
        "taxonomy enforced by the extraction stage.",
    )


__all__ = [
    "KGConfig",
    "ListOfStrings",
    # Env-var name constants (for documentation / tests)
    "ENV_ENABLED",
    "ENV_RRF_WEIGHT",
    "ENV_TOKEN_BUDGET",
    "ENV_MAX_HOPS",
    "ENV_BATCH_SIZE",
    "ENV_CRON_HOUR",
    "ENV_CRON_MINUTE",
    "ENV_DEDUP_THRESHOLD",
    "ENV_ENTITY_TYPES",
    "ENV_RELATION_TYPES",
]
