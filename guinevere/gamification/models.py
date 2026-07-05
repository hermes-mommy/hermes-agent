"""SQLAlchemy models for the gamification schema.

Tables:
    - gamification.level_thresholds  — seeded reference table (100 * level^2)
    - gamification.skill_xp          — per-skill XP and level tracking
    - gamification.agent_xp          — overall agent XP (singleton row)
    - gamification.xp_events         — append-only audit log of XP changes
    - gamification.level_ups         — log of level-up events
    - gamification.xp_multipliers    — configurable XP bonus multipliers
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Float,
    Index,
    Integer,
    Numeric,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from guinevere.memory.models import Base


# ============================================================
# Schema: gamification (6 tables)
# ============================================================


class LevelThreshold(Base):
    """Reference table mapping levels to cumulative XP requirements.

    Seeded with formula: xp_required = 100 * level²
    Read-only in practice; used for display and validation.
    """

    __tablename__ = "level_thresholds"
    __table_args__ = (
        {"schema": "gamification"},
    )

    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    xp_required: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class SkillXP(Base):
    """Per-skill XP tracking with automatic level calculation.

    Each unique skill_name has one row. The current_level column is
    maintained by a database trigger that fires on total_xp updates.
    """

    __tablename__ = "skill_xp"
    __table_args__ = (
        Index("ix_skill_xp_category", "category"),
        Index("ix_skill_xp_level", text("current_level DESC")),
        {"schema": "gamification"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    skill_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_xp_event: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class AgentXP(Base):
    """Overall agent XP tracking (singleton pattern).

    Only one row should exist. Enforced by a partial unique index.
    The current_level column is maintained by a database trigger.
    """

    __tablename__ = "agent_xp"
    __table_args__ = (
        Index("ix_agent_xp_singleton", text("(true)"), unique=True),
        {"schema": "gamification"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    total_xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lifetime_actions: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_xp_event: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class XPEvent(Base):
    """Append-only audit log of all XP changes.

    Records every XP gain (or loss) with source attribution and
    optional metadata for debugging and analytics.
    """

    __tablename__ = "xp_events"
    __table_args__ = (
        Index("ix_xp_events_skill", "skill_name", text("awarded_at DESC")),
        Index("ix_xp_events_time", text("awarded_at DESC")),
        {"schema": "gamification"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    skill_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    xp_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    awarded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class LevelUp(Base):
    """Log of level-up events for both skills and the agent.

    skill_name is NULL for agent-level-up events.
    """

    __tablename__ = "level_ups"
    __table_args__ = (
        Index("ix_level_ups_skill", "skill_name", text("achieved_at DESC")),
        {"schema": "gamification"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    skill_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    old_level: Mapped[int] = mapped_column(Integer, nullable=False)
    new_level: Mapped[int] = mapped_column(Integer, nullable=False)
    total_xp_at: Mapped[int] = mapped_column(Integer, nullable=False)
    achieved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class XPMultiplier(Base):
    """Configurable XP multipliers for bonus XP events.

    Examples: streak_bonus (1.50x), first_time_skill (2.00x), etc.
    Multipliers can be temporary (expires_at) or permanent.
    """

    __tablename__ = "xp_multipliers"
    __table_args__ = (
        UniqueConstraint("multiplier_name", name="uq_xp_multipliers_multiplier_name"),
        {"schema": "gamification"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    multiplier_name: Mapped[str] = mapped_column(Text, nullable=False)
    multiplier: Mapped[float] = mapped_column(
        Numeric(4, 2), nullable=False, server_default=text("1.00")
    )
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
