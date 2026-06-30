"""Voyager-pattern skill library for Guinevere autonomous loops.

Provides CRUD operations and hybrid semantic/keyword search over the
``memory.procedural_skills`` table. Embeddings are generated through the
existing ``EmbeddingService`` (P3-005) and stored as 1536-dimensional
pgvector vectors. Hybrid ranking uses reciprocal rank fusion (RRF, k=60)
to combine vector cosine similarity and ILIKE keyword search.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Literal, cast

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from guinvere.memory.embeddings import EmbeddingService
from guinvere.memory.models import ProceduralSkills

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

MAX_STEPS_PER_SKILL: int = 50
"""Maximum number of discrete steps a single skill may contain."""

MAX_DESCRIPTION_LENGTH: int = 500
"""Maximum character length for a skill description."""

SKILL_TYPES: set[str] = {"draft", "validated", "permanent", "deprecated"}
"""Allowed skill lifecycle states."""

_RRF_K: int = 60
"""Reciprocal rank fusion constant (mirrors ``guinvere.memory.read_pipeline.RRF_K``)."""

_EXPANDED_LIMIT_MULTIPLIER: int = 3
"""Expand per-signal queries so RRF has candidates to fuse."""

ALLOWED_UPDATE_FIELDS: set[str] = {"skill_type", "description", "evolved_from"}
"""Columns allowed to be updated through ``_update_single_field``."""


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillEntry:
    """Immutable representation of a stored procedural skill."""

    skill_id: int | None
    skill_name: str
    skill_type: str
    description: str
    steps: list[str]
    success_count: int
    last_used_at: datetime | None
    embedding: list[float] | None
    evolved_from: int | None


@dataclass(frozen=True)
class SkillSearchResult:
    """One ranked result from a hybrid skill search."""

    skill: SkillEntry
    score: float
    match_type: Literal["semantic", "keyword", "hybrid"]


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SkillLibraryError(Exception):
    """Raised when a skill-library operation cannot complete."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_value(row: object, key: str, default: object = None) -> object:
    """Retrieve *key* from a row-like object (mapping or attribute object)."""
    if isinstance(row, Mapping):
        return row.get(key, default)
    try:
        return getattr(row, key)
    except AttributeError:
        return default


def _row_to_entry(row: object) -> SkillEntry:
    """Convert a DB row or ORM object to a ``SkillEntry``."""
    raw_steps = _get_value(row, "steps") or []
    if isinstance(raw_steps, str):
        raw_steps = json.loads(raw_steps)
    if not isinstance(raw_steps, (list, tuple)):
        raw_steps = []
    steps: list[str] = [str(step) for step in raw_steps]

    raw_embedding = _get_value(row, "embedding")
    embedding: list[float] | None = None
    if isinstance(raw_embedding, (list, tuple)):
        embedding = [float(value) for value in raw_embedding]

    success_value = cast(int | None, _get_value(row, "success_count", 0))
    success_count = int(success_value) if success_value is not None else 0

    return SkillEntry(
        skill_id=cast(int | None, _get_value(row, "id")),
        skill_name=str(_get_value(row, "skill_name", "")),
        skill_type=str(_get_value(row, "skill_type", "")),
        description=str(_get_value(row, "description", "")),
        steps=steps,
        success_count=success_count,
        last_used_at=cast(datetime | None, _get_value(row, "last_used_at")),
        embedding=embedding,
        evolved_from=cast(int | None, _get_value(row, "evolved_from")),
    )


def _prepare_embedding_text(description: str, steps: list[str]) -> str:
    """Build the text payload used for skill embedding generation."""
    parts = [description.strip()]
    for step in steps:
        parts.append(step.strip())
    return "\n".join(parts)


def _vector_literal(vector: list[float]) -> str:
    """Return a pgvector literal string for a 1536-dimension vector."""
    return "[" + ",".join(str(value) for value in vector) + "]"


def _validate_skill_type(skill_type: str) -> None:
    """Ensure *skill_type* is a known lifecycle state."""
    if skill_type not in SKILL_TYPES:
        raise SkillLibraryError(
            f"Invalid skill_type '{skill_type}'. Allowed: {sorted(SKILL_TYPES)}"
        )


def _validate_description(description: str) -> None:
    """Ensure *description* length is within bounds."""
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise SkillLibraryError(
            f"description exceeds {MAX_DESCRIPTION_LENGTH} characters"
        )


def _validate_steps(steps: list[str] | list[object]) -> list[str]:
    """Ensure *steps* list size and content are valid.

    Returns a typed ``list[str]``.
    """
    if len(steps) > MAX_STEPS_PER_SKILL:
        raise SkillLibraryError(
            f"steps exceed {MAX_STEPS_PER_SKILL} items"
        )
    typed_steps: list[str] = []
    for step in steps:
        if not isinstance(step, str):
            raise SkillLibraryError("each step must be a string")
        typed_steps.append(step)
    return typed_steps


# ---------------------------------------------------------------------------
# Public skill library
# ---------------------------------------------------------------------------


class SkillLibrary:
    """CRUD + hybrid semantic/keyword search for procedural skills.

    Parameters
    ----------
    session_factory:
        Callable returning an async context manager that yields a
        SQLAlchemy ``AsyncSession``.
    embedding_service:
        Instance of ``EmbeddingService`` used to generate 1536-dimensional
        embeddings for skills and queries.
    """

    def __init__(
        self,
        session_factory: Callable[[], "AbstractAsyncContextManager[AsyncSession]"],
        embedding_service: EmbeddingService,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_service = embedding_service

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_inputs(
        skill_name: str,
        skill_type: str,
        description: str,
        steps: list[str] | list[object],
    ) -> None:
        """Validate common skill fields before persistence."""
        if not skill_name or not isinstance(skill_name, str):
            raise SkillLibraryError("skill_name must be a non-empty string")
        _validate_skill_type(skill_type)
        if not isinstance(description, str):
            raise SkillLibraryError("description must be a string")
        _validate_description(description)
        if not isinstance(steps, list):
            raise SkillLibraryError("steps must be a list of strings")
        _validate_steps(steps)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(
        self,
        name: str,
        skill_type: str,
        description: str,
        steps: list[str],
        *,
        evolved_from: int | None = None,
    ) -> SkillEntry:
        """Insert a new skill and generate its embedding.

        Parameters
        ----------
        name:
            Unique skill name.
        skill_type:
            One of ``draft``, ``validated``, ``permanent``, ``deprecated``.
        description:
            Human-readable skill description.
        steps:
            Ordered list of procedural steps.
        evolved_from:
            Optional parent skill identifier.

        Returns
        -------
        The persisted ``SkillEntry``.
        """
        self._validate_inputs(name, skill_type, description, steps)
        embedding = await self._embedding_service.aembed(
            _prepare_embedding_text(description, steps)
        )

        insert_sql = text(
            """
            INSERT INTO memory.procedural_skills
                (skill_name, skill_type, description, steps, evolved_from,
                 success_count, embedding)
            VALUES
                (:skill_name, :skill_type, :description, :steps, :evolved_from,
                 0, :embedding::vector)
            RETURNING id, skill_name, skill_type, description, steps,
                      evolved_from, success_count, last_used_at
            """
        )
        params = {
            "skill_name": name,
            "skill_type": skill_type,
            "description": description,
            "steps": steps,
            "evolved_from": evolved_from,
            "embedding": _vector_literal(embedding),
        }

        async with self._session_factory() as session:
            result = await session.execute(insert_sql, params)
            await session.commit()
            row = result.one()
        return _row_to_entry(row)

    async def get(self, skill_id: int) -> SkillEntry | None:
        """Return the skill with the given identifier, or ``None``.

        Parameters
        ----------
        skill_id:
            Primary key of the skill to retrieve.

        Returns
        -------
        ``SkillEntry`` if found, otherwise ``None``.
        """
        async with self._session_factory() as session:
            row = await session.get(ProceduralSkills, skill_id)
            if row is None:
                return None
        return _row_to_entry(row)

    async def update(self, skill_id: int, **fields: object) -> SkillEntry:
        """Update a skill and regenerate its embedding when text changes.

        Allowed fields: ``name``, ``skill_type``, ``description``, ``steps``,
        ``evolved_from``.

        Parameters
        ----------
        skill_id:
            Primary key of the skill to update.
        **fields:
            Fields to update.

        Returns
        -------
        The updated ``SkillEntry``.

        Raises
        ------
        SkillLibraryError
            If the skill does not exist or an field is invalid.
        """
        allowed = {"name", "skill_type", "description", "steps", "evolved_from"}
        for key in fields:
            if key not in allowed:
                raise SkillLibraryError(f"Cannot update field '{key}'")

        select_sql = text(
            """
            SELECT id, skill_name, skill_type, description, steps, evolved_from,
                   success_count, last_used_at
            FROM memory.procedural_skills
            WHERE id = :skill_id
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(select_sql, {"skill_id": skill_id})
            current = result.one_or_none()
            if current is None:
                raise SkillLibraryError(f"Skill {skill_id} not found")

            name = cast(str, fields.get("name", current.skill_name))
            skill_type = cast(str, fields.get("skill_type", current.skill_type))
            description = cast(str, fields.get("description", current.description))
            steps = cast(list[object], fields.get("steps", current.steps))
            evolved_from = cast(
                int | None, fields.get("evolved_from", current.evolved_from)
            )

            if not isinstance(name, str):
                raise SkillLibraryError("name must be a string")
            if not isinstance(description, str):
                raise SkillLibraryError("description must be a string")
            if not isinstance(steps, list):
                raise SkillLibraryError("steps must be a list of strings")
            self._validate_inputs(name, skill_type, description, steps)
            typed_steps = _validate_steps(steps)

            embedding_changed = "description" in fields or "steps" in fields
            if embedding_changed:
                embedding = await self._embedding_service.aembed(
                    _prepare_embedding_text(description, typed_steps)
                )
                embedding_literal = _vector_literal(embedding)
                update_sql = text(
                    """
                    UPDATE memory.procedural_skills
                    SET skill_name = :skill_name,
                        skill_type = :skill_type,
                        description = :description,
                        steps = :steps,
                        evolved_from = :evolved_from,
                        embedding = :embedding::vector
                    WHERE id = :skill_id
                    """
                )
                update_params: dict[str, object] = {
                    "skill_name": name,
                    "skill_type": skill_type,
                    "description": description,
                    "steps": typed_steps,
                    "evolved_from": evolved_from,
                    "embedding": embedding_literal,
                    "skill_id": skill_id,
                }
            else:
                update_sql = text(
                    """
                    UPDATE memory.procedural_skills
                    SET skill_name = :skill_name,
                        skill_type = :skill_type,
                        description = :description,
                        steps = :steps,
                        evolved_from = :evolved_from
                    WHERE id = :skill_id
                    """
                )
                update_params = {
                    "skill_name": name,
                    "skill_type": skill_type,
                    "description": description,
                    "steps": typed_steps,
                    "evolved_from": evolved_from,
                    "skill_id": skill_id,
                }

            await session.execute(update_sql, update_params)
            await session.commit()

            refreshed = await session.execute(select_sql, {"skill_id": skill_id})
            updated_row = refreshed.one()
        return _row_to_entry(updated_row)

    async def delete(self, skill_id: int) -> bool:
        """Delete the skill with the given identifier.

        Parameters
        ----------
        skill_id:
            Primary key of the skill to delete.

        Returns
        -------
        ``True`` if a row was removed, ``False`` otherwise.
        """
        async with self._session_factory() as session:
            row = await session.get(ProceduralSkills, skill_id)
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
        return True

    # ------------------------------------------------------------------
    # Search & relevance
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        limit: int = 10,
        skill_type: str | None = None,
    ) -> list[SkillSearchResult]:
        """Hybrid semantic + keyword search over skills.

        Vector and keyword results are fused with reciprocal rank fusion
        (RRF, k=60). The final list is sorted by combined score descending.

        Parameters
        ----------
        query:
            Natural-language query.
        limit:
            Maximum number of results to return.
        skill_type:
            Optional filter for skill lifecycle state.

        Returns
        -------
        List of ranked skill results.
        """
        if not query or not query.strip():
            return []

        if skill_type is not None and skill_type not in SKILL_TYPES:
            raise SkillLibraryError(
                f"Invalid skill_type filter '{skill_type}'"
            )

        query_vector = await self._embedding_service.aembed(query.strip())
        expanded_limit = limit * _EXPANDED_LIMIT_MULTIPLIER
        type_filter = "AND skill_type = :skill_type" if skill_type else ""

        semantic_sql = text(
            f"""
            SELECT id, skill_name, skill_type, description, steps, evolved_from,
                   success_count, last_used_at,
                   embedding <=> :query_vector::vector AS distance
            FROM memory.procedural_skills
            WHERE embedding IS NOT NULL {type_filter}
            ORDER BY embedding <=> :query_vector::vector
            LIMIT :limit
            """
        )
        keyword_sql = text(
            f"""
            SELECT id, skill_name, skill_type, description, steps, evolved_from,
                   success_count, last_used_at
            FROM memory.procedural_skills
            WHERE (skill_name ILIKE :pattern OR description ILIKE :pattern)
                  {type_filter}
            LIMIT :limit
            """
        )

        async with self._session_factory() as session:
            sem_result = await session.execute(
                semantic_sql,
                {
                    "query_vector": _vector_literal(query_vector),
                    "limit": expanded_limit,
                    "skill_type": skill_type,
                },
            )
            sem_rows = list(sem_result.mappings().all())

            pattern = f"%{query.strip()}%"
            kw_result = await session.execute(
                keyword_sql,
                {
                    "pattern": pattern,
                    "limit": expanded_limit,
                    "skill_type": skill_type,
                },
            )
            kw_rows = list(kw_result.mappings().all())

        merged: dict[object, dict[str, object]] = {}
        for rank, row in enumerate(sem_rows, start=1):
            merged[row["id"]] = {"row": row, "sem_rank": rank}
        for rank, row in enumerate(kw_rows, start=1):
            entry = merged.setdefault(row["id"], {"row": row})
            entry["kw_rank"] = rank

        results: list[SkillSearchResult] = []
        for item in merged.values():
            sem_rank = item.get("sem_rank")
            kw_rank = item.get("kw_rank")
            score = 0.0
            if sem_rank is not None:
                sem_rank_int: int = cast(int, sem_rank)
                score += 1.0 / (_RRF_K + sem_rank_int)
            if kw_rank is not None:
                kw_rank_int: int = cast(int, kw_rank)
                score += 1.0 / (_RRF_K + kw_rank_int)

            if sem_rank is not None and kw_rank is not None:
                match_type: Literal["semantic", "keyword", "hybrid"] = "hybrid"
            elif sem_rank is not None:
                match_type = "semantic"
            else:
                match_type = "keyword"

            results.append(
                SkillSearchResult(
                    skill=_row_to_entry(item["row"]),
                    score=score,
                    match_type=match_type,
                )
            )

        results.sort(key=lambda result: result.score, reverse=True)
        return results[:limit]

    async def get_relevant_skills(
        self,
        task_description: str,
        limit: int = 5,
    ) -> list[SkillSearchResult]:
        """Search for skills relevant to *task_description*.

        Parameters
        ----------
        task_description:
            Natural-language task description.
        limit:
            Maximum number of results to return.

        Returns
        -------
        List of ranked skill results.
        """
        return await self.search(task_description, limit=limit)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def record_success(self, skill_id: int) -> None:
        """Increment *success_count* and update *last_used_at* for a skill."""
        async with self._session_factory() as session:
            row = await session.get(ProceduralSkills, skill_id)
            if row is None:
                raise SkillLibraryError(f"Skill {skill_id} not found")
            row.success_count = (row.success_count or 0) + 1
            row.last_used_at = datetime.now(timezone.utc)
            await session.commit()

    async def promote_skill(self, skill_id: int, new_type: str) -> SkillEntry:
        """Change a skill's lifecycle state (e.g. ``draft`` -> ``validated``)."""
        _validate_skill_type(new_type)
        return await self._update_single_field(skill_id, "skill_type", new_type)

    async def demote_skill(self, skill_id: int) -> SkillEntry:
        """Mark a skill as deprecated."""
        return await self._update_single_field(
            skill_id, "skill_type", "deprecated"
        )

    async def _update_single_field(
        self, skill_id: int, field: str, value: object
    ) -> SkillEntry:
        """Update a single field on the skill row and return the new entry."""
        if field not in ALLOWED_UPDATE_FIELDS:
            raise ValueError(
                f"Invalid field '{field}'. Allowed: {sorted(ALLOWED_UPDATE_FIELDS)}"
            )
        update_sql = text(
            f"""
            UPDATE memory.procedural_skills
            SET {field} = :value
            WHERE id = :skill_id
            """
        )
        select_sql = text(
            """
            SELECT id, skill_name, skill_type, description, steps, evolved_from,
                   success_count, last_used_at
            FROM memory.procedural_skills
            WHERE id = :skill_id
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(
                update_sql, {"value": value, "skill_id": skill_id}
            )
            await session.commit()
            if getattr(result, "rowcount", 0) == 0:
                raise SkillLibraryError(f"Skill {skill_id} not found")
            refreshed = await session.execute(select_sql, {"skill_id": skill_id})
            row = refreshed.one()
        return _row_to_entry(row)

    async def list_skills(
        self,
        skill_type: str | None = None,
        limit: int = 100,
    ) -> list[SkillEntry]:
        """Return a list of skills, optionally filtered by lifecycle state."""
        if skill_type is not None and skill_type not in SKILL_TYPES:
            raise SkillLibraryError(
                f"Invalid skill_type filter '{skill_type}'"
            )

        stmt = select(ProceduralSkills).order_by(
            ProceduralSkills.created_at.desc()
        )
        if skill_type is not None:
            stmt = stmt.where(ProceduralSkills.skill_type == skill_type)
        stmt = stmt.limit(limit)

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            rows = list(result.scalars().all())
        return [_row_to_entry(row) for row in rows]


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "SkillEntry",
    "SkillLibrary",
    "SkillSearchResult",
    "SkillLibraryError",
    "MAX_STEPS_PER_SKILL",
    "MAX_DESCRIPTION_LENGTH",
    "SKILL_TYPES",
]
