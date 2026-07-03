"""SQLAlchemy models for the Memory backend (P24 Task 3).

Provides Memory, MemoryType, and MemoryCollection models used by the
memory tool backend for 18 PostgreSQL + pgvector actions.

Embeddings are stored as JSON arrays (``embedding_json``) for cross-database
compatibility.  The backend computes cosine similarity in Python when pgvector
operators are unavailable (e.g. in-memory SQLite tests).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Declarative base shared across all memory domain models."""
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MemoryType(str, Enum):
    """Classification types for memory entries.

    Mirrors the cognitive science taxonomy used by the episodic/semantic
    memory subsystem.
    """

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    EMOTIONAL = "emotional"
    RELATIONSHIP = "relationship"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Memory(Base):
    """A single memory record with optional vector embedding.

    Embeddings are stored as JSON arrays of floats.  On PostgreSQL the
    backend can use pgvector cosine-distance operators; on SQLite the
    backend falls back to pure-Python cosine similarity.
    """

    __tablename__ = "memories"
    __table_args__ = (
        Index("ix_memories_memory_type", "memory_type"),
        Index("ix_memories_collection", "collection"),
        Index("ix_memories_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MemoryType.EPISODIC.value,
    )
    embedding_json: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
        comment="Vector embedding stored as JSON array of floats",
    )
    metadata_json: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    collection: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Named collection/group this memory belongs to",
    )
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    importance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    do_not_recall: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # -- serialisation --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict representation."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "embedding": self.embedding_json,
            "metadata": self.metadata_json or {},
            "collection": self.collection,
            "source": self.source,
            "importance": self.importance,
            "do_not_recall": self.do_not_recall,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MemoryCollection(Base):
    """A named collection (group) of memories.

    Collections let callers organise memories into logical sets
    (e.g. "project-alpha", "personal", "research-notes").
    """

    __tablename__ = "memory_collections"
    __table_args__ = (
        Index("ix_memory_collections_name", "name", unique=True),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


__all__ = [
    "Base",
    "Memory",
    "MemoryCollection",
    "MemoryType",
]
