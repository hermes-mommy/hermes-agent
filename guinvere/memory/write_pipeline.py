"""Guinevere memory write pipeline — P3-009.

Stores episodic memories into ``memory.episodes`` using SQLAlchemy
AsyncSession/ORM and the existing P3-005 ``EmbeddingService``.

Privacy guards:
- Default classification is ``Restricted`` (not ``Internal``).
- ``Critical`` classification fails closed unless a sanitized ``summary`` is
  provided (which is used for embedding instead of raw content).
- ``Restricted`` / ``Confidential`` classification auto-redacts sensitive
  patterns via ``EmbeddingService.aembed()``.
- Never logs raw content, vector values, secrets, or decrypted values.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Protocol, TypeAlias, cast

from guinvere.memory.embeddings import (
    CONFIDENTIAL,
    CRITICAL,
    INTERNAL,
    PUBLIC,
    RESTRICTED,
    CriticalEmbeddingError,
)
from guinvere.memory.models import Episodes


class EpisodeRow(Protocol):
    """Fields read back from an Episodes ORM instance after flush."""

    id: object

# ---------------------------------------------------------------------------
# Re-export classification constants so callers of write_pipeline can
# reference them without importing from embeddings directly.
# ---------------------------------------------------------------------------

__all__ = [
    "PUBLIC",
    "INTERNAL",
    "RESTRICTED",
    "CONFIDENTIAL",
    "CRITICAL",
    "CriticalEmbeddingError",
    "WritePipelineError",
    "WritePipelineCriticalError",
    "store_episode",
    "store_episode_batch",
]

# ---------------------------------------------------------------------------
# Logger — stdlib, not structlog, to keep diagnostics clean without
# requiring structlog to be installed in all environments.
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

JsonObject: TypeAlias = dict[str, object]


class EpisodeSession(Protocol):
    """Minimal async session protocol required by the write pipeline."""

    def add(self, obj: object) -> None:
        """Add an ORM object to the session."""

    async def flush(self) -> None:
        """Flush pending ORM changes."""


class EmbeddingClient(Protocol):
    """Minimal embedding client protocol required by the write pipeline."""

    async def aembed(
        self,
        text: str,
        classification: str = RESTRICTED,
        *,
        sanitized_summary: str | None = None,
    ) -> list[float]:
        """Return one embedding vector."""
        raise NotImplementedError

# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------


class WritePipelineError(Exception):
    """Base error for the memory write pipeline."""


class WritePipelineCriticalError(WritePipelineError):
    """Raised when Critical memory cannot be written safely."""


# ---------------------------------------------------------------------------
# store_episode — single episode write
# ---------------------------------------------------------------------------


async def store_episode(
    session: EpisodeSession,
    content: str,
    *,
    source: str,
    classification: str = RESTRICTED,
    importance: int = 5,
    title: str | None = None,
    summary: str | None = None,
    episode_type: str = "conversation",
    tags: list[str] | None = None,
    metadata: JsonObject | None = None,
    embedding_service: EmbeddingClient | None = None,
    started_at: datetime | None = None,
    project_id: uuid.UUID | None = None,
    project_scope: str = "project",
) -> uuid.UUID:
    """Store an episodic memory in ``memory.episodes``.

    Parameters
    ----------
    session:
        SQLAlchemy ``AsyncSession`` bound to the Guinevere database.
    content:
        Raw memory content to store and (optionally) embed.
    source:
        Origin label for the memory (e.g. ``"discord"``, ``"surveillance"``,
        ``"agent-loop"``).
    classification:
        Data classification level.  Default ``Restricted``.
    importance:
        Importance score (1-10).  Default ``5``.
    title:
        Optional human-readable title.
    summary:
        Optional short summary.  **Required** when classification is
        ``Critical``; used as the embedding source in that case.
    episode_type:
        Type label.  Default ``"conversation"``.
    tags:
        Optional list of string tags.
    metadata:
        Optional metadata dict stored as JSONB in ``key_insights``.
    embedding_service:
        If provided, a 1536-dimensional embedding is computed via
        ``embedding_service.aembed()`` and stored in the ``embedding`` column.
    started_at:
        Explicit start timestamp.  Defaults to UTC now.

    Returns
    -------
    ``uuid.UUID`` of the newly created episode row.

    Raises
    ------
    WritePipelineCriticalError
        If classification is ``Critical`` and no non-empty ``summary`` is
        provided (fail-closed).
    WritePipelineError
        On other pipeline errors.
    CriticalEmbeddingError
        Propagated from ``EmbeddingService`` if Critical data is sent without
        a sanitized summary path.
    DimensionMismatchError
        Propagated from ``EmbeddingService`` if the API returns a vector with
        unexpected dimension.
    """
    # ---- fail-closed: Critical requires a sanitized summary -----------------
    _guard_critical(classification, summary)

    # ---- optional embedding -------------------------------------------------
    embedding: list[float] | None = None
    if embedding_service is not None:
        embedding = await _compute_embedding(
            service=embedding_service,
            content=content,
            classification=classification,
            summary=summary,
        )

    # ---- build and persist ORM instance -------------------------------------
    episode_start = started_at if started_at is not None else datetime.now(timezone.utc)

    episode = Episodes(
        raw_content=content,
        embedding=embedding,
        do_not_recall=False,
        classification=classification,
        source=source,
        importance=importance,
        title=title,
        summary=summary,
        episode_type=episode_type,
        tags=tags if tags else None,
        key_insights=metadata,
        started_at=episode_start,
        project_id=project_id,
        project_scope=project_scope,
    )

    session.add(episode)
    await session.flush()

    # After flush the server-default UUID is populated by SQLAlchemy's
    # autobegin / refresh-on-flush mechanics.
    episode_row = cast(EpisodeRow, episode)
    episode_id = uuid.UUID(str(episode_row.id))

    _logger.info(
        "episode_stored",
        extra={
            "episode_id": str(episode_id),
            "classification": classification,
            "source": source,
            "episode_type": episode_type,
            "has_embedding": embedding is not None,
            "char_count": len(content),
        },
    )

    return episode_id


# ---------------------------------------------------------------------------
# store_episode_batch — batch write helper
# ---------------------------------------------------------------------------


async def store_episode_batch(
    session: EpisodeSession,
    episodes: list[JsonObject],
    *,
    embedding_service: EmbeddingClient | None = None,
    project_id: uuid.UUID | None = None,
    project_scope: str = "project",
) -> list[uuid.UUID]:
    """Store multiple episodes in a batch.

    Each dict must contain at least ``"content"`` and ``"source"`` keys.
    Optional keys match :func:`store_episode` parameters.

    If ``embedding_service`` is provided, episodes are embedded individually
    (future optimisation: a single batch API call can be added when the
    embedding service supports mixing classifications).

    P19: ``project_id`` and ``project_scope`` are forwarded to each
    ``store_episode`` call. Per-episode overrides from ``ep_data`` take
    precedence over the batch-level defaults.
    """
    ids: list[uuid.UUID] = []
    for ep_data in episodes:
        ep_project_id = _opt_uuid_field(ep_data, "project_id", project_id)
        ep_project_scope = _opt_str_field(ep_data, "project_scope", project_scope)
        ep_id = await store_episode(
            session,
            content=_str_field(ep_data, "content"),
            source=_str_field(ep_data, "source"),
            classification=_str_field(ep_data, "classification", RESTRICTED),
            importance=_int_field(ep_data, "importance", 5),
            title=_opt_str_field(ep_data, "title"),
            summary=_opt_str_field(ep_data, "summary"),
            episode_type=_str_field(ep_data, "episode_type", "conversation"),
            tags=_opt_list_field(ep_data, "tags"),
            metadata=_opt_dict_field(ep_data, "metadata"),
            embedding_service=embedding_service,
            started_at=_opt_dt_field(ep_data, "started_at"),
            project_id=ep_project_id,
            project_scope=ep_project_scope,
        )
        ids.append(ep_id)
    return ids


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _guard_critical(classification: str, summary: str | None) -> None:
    """Fail closed if ``Critical`` classification lacks a sanitized summary.

    The ``EmbeddingService`` independently enforces this as well, but we
    fail fast here before even constructing the ORM object.
    """
    if classification == CRITICAL and (not summary or not summary.strip()):
        raise WritePipelineCriticalError(
            "Cannot store Critical memory without a sanitized summary. "
            + "Provide a non-empty 'summary' parameter."
        )


async def _compute_embedding(
    service: EmbeddingClient,
    content: str,
    classification: str,
    summary: str | None,
) -> list[float]:
    """Compute a 1536-dim embedding via the EmbeddingService.

    For ``Critical`` classification the ``summary`` (which must be non-empty
    per ``_guard_critical``) is passed as ``sanitized_summary`` so that the
    embedding is derived from the sanitised summary, not the raw content.
    """
    sanitized_summary: str | None = summary if classification == CRITICAL else None
    vector = await service.aembed(
        content,
        classification=classification,
        sanitized_summary=sanitized_summary,
    )
    return vector


# ---------------------------------------------------------------------------
# Field coercers for batch API
# ---------------------------------------------------------------------------


def _str_field(d: JsonObject, key: str, default: str = "") -> str:
    val: object = d.get(key, default)
    return str(val) if val is not None else default


def _int_field(d: JsonObject, key: str, default: int = 0) -> int:
    val: object = d.get(key, default)
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default
    return default


def _opt_str_field(d: JsonObject, key: str, default: str | None = None) -> str | None:
    val: object = d.get(key)
    if val is None:
        return default
    s = str(val)
    return s if s else default


def _opt_uuid_field(d: JsonObject, key: str, default: uuid.UUID | None = None) -> uuid.UUID | None:
    val: object = d.get(key)
    if val is None:
        return default
    if isinstance(val, uuid.UUID):
        return val
    if isinstance(val, str):
        try:
            return uuid.UUID(val)
        except ValueError:
            return default
    return default


def _opt_list_field(d: JsonObject, key: str) -> list[str] | None:
    val: object = d.get(key)
    if isinstance(val, list):
        raw = cast(list[object], val)
        return [str(item) for item in raw] if raw else None
    return None


def _opt_dict_field(d: JsonObject, key: str) -> JsonObject | None:
    val: object = d.get(key)
    if isinstance(val, dict):
        raw = cast(dict[str, object], val)
        return {k: v for k, v in raw.items()}
    return None


def _opt_dt_field(d: JsonObject, key: str) -> datetime | None:
    val: object = d.get(key)
    if isinstance(val, datetime):
        return val
    return None