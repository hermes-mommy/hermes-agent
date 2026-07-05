"""Tool backend Memory models — separate from P24 domain models.

This module provides the Memory/MemoryType/MemoryCollection classes
used by the M8 tool backend (guinevere.tools.backends.memory).
Kept separate from models.py to avoid merging conflicts with the
47-table P24 domain schema.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Index, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from guinevere.memory.models import Base


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    EMOTIONAL = "emotional"
    RELATIONSHIP = "relationship"


class Memory(Base):
    __tablename__ = "tool_memories"
    __table_args__ = (Index("ix_tool_memories_type", "memory_type"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, default=MemoryType.EPISODIC.value)
    metadata_json: Mapped[Optional[dict]] = mapped_column(String, nullable=True)
    collection: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    importance: Mapped[float] = mapped_column(default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "content": self.content, "memory_type": self.memory_type, "metadata": self.metadata_json or {}, "collection": self.collection, "importance": self.importance, "created_at": self.created_at.isoformat() if self.created_at else None, "updated_at": self.updated_at.isoformat() if self.updated_at else None}


class MemoryCollection(Base):
    __tablename__ = "tool_memory_collections"
    __table_args__ = (Index("ix_tool_memory_collections_name", "name", unique=True),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "description": self.description, "created_at": self.created_at.isoformat() if self.created_at else None}

__all__ = ["Memory", "MemoryCollection", "MemoryType"]
