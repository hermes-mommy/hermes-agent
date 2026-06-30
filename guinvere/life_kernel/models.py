"""Living Autonomy Kernel world model persistence models (LK-003)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import Boolean, Float, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from guinvere.memory.models import Base

logger = __import__("structlog").get_logger(__name__)


class LifeMindStateModel(Base):
    """Global life mind state: phase, observations, goals, commitments, concerns."""

    __tablename__ = "life_mind_state"
    __table_args__ = {"schema": "life_kernel"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    observations: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'")
    )
    goals: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'")
    )
    commitments: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'")
    )
    concerns: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'")
    )
    decision_context: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        default=lambda: datetime.now(tz=timezone.utc),
        nullable=False,
    )


class HeartbeatRecord(Base):
    """Heartbeat/interval records with latency tracking."""

    __tablename__ = "heartbeat_record"
    __table_args__ = (
        sa.CheckConstraint(
            "heartbeat_type IN ('1s', '10s', '30s', '60s', '5m', '1h')",
            name="heartbeat_type_check",
        ),
        {"schema": "life_kernel"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    heartbeat_type: Mapped[str] = mapped_column(String(16), nullable=False)
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        default=lambda: datetime.now(tz=timezone.utc),
        nullable=False,
    )


class DomainMindState(Base):
    """Domain-specific mind state (engineering, comms, finance, health, VPS, learning, self-improvement)."""

    __tablename__ = "domain_mind_state"
    __table_args__ = (
        {"schema": "life_kernel"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    domain: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    state_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    last_run: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    run_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    error_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )