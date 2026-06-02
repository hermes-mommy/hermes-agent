"""Guinevere memory domain models — 47 tables across 12 schemas (P3-002)."""
import uuid
from datetime import date, datetime
from typing import Optional, TypeAlias

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Computed,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    BigInteger,
    LargeBinary,
    TIMESTAMP,
    MetaData,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

JsonObject: TypeAlias = dict[str, object]
EPISODES_SEARCH_VECTOR_EXPRESSION = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(summary, '')), 'B') || "
    "setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')"
)

# ---------------------------------------------------------------------------
# Naming convention & Base
# ---------------------------------------------------------------------------
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata_obj = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    metadata = metadata_obj


# ---------------------------------------------------------------------------
# Mixin — classification / governance metadata columns
# ---------------------------------------------------------------------------
class ClassificationMetaMixin:
    """Reusable metadata columns required on all classified tables (ERD section 6.3)."""
    classification: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'Restricted'")
    )
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retention_class: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'Long-Term Curated'")
    )
    retention_until: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    access_policy: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'guinevere-core'")
    )
    encryption_profile: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'envelope-AES-256-GCM'")
    )
    deletion_state: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'active'")
    )
    key_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


# ===================================================================
# Schema: memory  (8 tables)
# ===================================================================


class Episodes(Base, ClassificationMetaMixin):
    __tablename__ = "episodes"
    __table_args__ = (
        Index("episodes_started_at_idx", text("started_at DESC")),
        Index(
            "ix_episodes_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 128},
        ),
        Index(
            "ix_episodes_search_vector_gin",
            "search_vector",
            postgresql_using="gin",
        ),
        {"schema": "memory"},
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), primary_key=True, nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    episode_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_insights: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
    mood_at_start: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mood_at_end: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotional_tone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    faiz_behavior: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536), nullable=True
    )
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        Computed(EPISODES_SEARCH_VECTOR_EXPRESSION),
        nullable=True,
    )
    do_not_recall: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    importance: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("5")
    )
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    related_ids: Mapped[Optional[list[uuid.UUID]]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    version: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("1")
    )


class SemanticFacts(Base, ClassificationMetaMixin):
    __tablename__ = "semantic_facts"
    __table_args__ = (
        Index("ix_semantic_facts_source_episode", "source_episode"),
        Index(
            "ix_semantic_facts_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 128},
        ),
        {"schema": "memory"},
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    object_val: Mapped[str] = mapped_column(Text, nullable=False)
    fact_type: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(
        Float, server_default=text("0.5")
    )
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_episode: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    last_verified: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    verified_count: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("1")
    )
    contradicts_ids: Mapped[Optional[list[uuid.UUID]]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    is_conflict: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )
    conflict_resolved: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )
    guinevere_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536), nullable=True
    )
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    version: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("1")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )


class FaizProfile(Base, ClassificationMetaMixin):
    __tablename__ = "faiz_profile"
    __table_args__ = {"schema": "memory"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    value_type: Mapped[str] = mapped_column(Text, nullable=False)
    sensitivity: Mapped[Optional[str]] = mapped_column(
        Text, server_default=text("'normal'")
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float, server_default=text("0.8")
    )
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    guinevere_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reveal_status: Mapped[Optional[str]] = mapped_column(
        Text, server_default=text("'never'")
    )
    access_count: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("0")
    )
    last_accessed: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class EmotionalEvents(Base, ClassificationMetaMixin):
    __tablename__ = "emotional_events"
    __table_args__ = (
        Index("ix_emotional_events_episode_id", "episode_id"),
        {"schema": "memory"},
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    episode_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    intensity: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("5")
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subjective_experience: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class InnerJournal(Base, ClassificationMetaMixin):
    __tablename__ = "inner_journal"
    __table_args__ = {"schema": "memory"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mood_self_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revealed_to_faiz: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )
    revealed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class FaizPredictions(Base, ClassificationMetaMixin):
    __tablename__ = "faiz_predictions"
    __table_args__ = {"schema": "memory"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    prediction_type: Mapped[str] = mapped_column(Text, nullable=False)
    prediction: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(
        Float, server_default=text("0.5")
    )
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    validated: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )


class ProceduralSkills(Base, ClassificationMetaMixin):
    __tablename__ = "procedural_skills"
    __table_args__ = {"schema": "memory"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    skill_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    skill_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
    evolved_from: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memory.procedural_skills.id", ondelete="SET NULL"),
        nullable=True,
    )
    success_count: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("0")
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class KnowledgeGraph(Base, ClassificationMetaMixin):
    __tablename__ = "knowledge_graph"
    __table_args__ = {"schema": "memory"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    from_entity: Mapped[str] = mapped_column(Text, nullable=False)
    relationship: Mapped[str] = mapped_column(Text, nullable=False)
    to_entity: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(
        Float, server_default=text("1.0")
    )
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ===================================================================
# Schema: persona  (5 tables)
# ===================================================================


class PersonaState(Base, ClassificationMetaMixin):
    __tablename__ = "persona_state"
    __table_args__ = {"schema": "persona"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    state_key: Mapped[str] = mapped_column(Text, nullable=False)
    state_value: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )
    updated_by: Mapped[str] = mapped_column(Text, nullable=False)


class DriftLog(Base, ClassificationMetaMixin):
    __tablename__ = "drift_log"
    __table_args__ = {"schema": "persona"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    drift_type: Mapped[str] = mapped_column(Text, nullable=False)
    before_state: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    after_state: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    delta: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    trigger_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    safety_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rollback_available: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("true")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class MoodHistory(Base, ClassificationMetaMixin):
    __tablename__ = "mood_history"
    __table_args__ = {"schema": "persona"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    mood: Mapped[str] = mapped_column(Text, nullable=False)
    intensity: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("5")
    )
    trigger: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class PunishmentLog(Base, ClassificationMetaMixin):
    __tablename__ = "punishment_log"
    __table_args__ = {"schema": "persona"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    violation_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    safe_word_triggered: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )
    safe_word_bypassed: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )
    applied_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class RewardLog(Base, ClassificationMetaMixin):
    __tablename__ = "reward_log"
    __table_args__ = {"schema": "persona"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    reward_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    streak_count: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("0")
    )
    awarded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


# ===================================================================
# Schema: surveillance  (4 tables)
# ===================================================================


class DeviceRegistry(Base):
    __tablename__ = "device_registry"
    __table_args__ = {"schema": "surveillance"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    device_name: Mapped[str] = mapped_column(Text, nullable=False)
    device_type: Mapped[str] = mapped_column(Text, nullable=False)
    tailscale_ip: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("true")
    )


class SurveillanceEvents(Base, ClassificationMetaMixin):
    __tablename__ = "events"
    __table_args__ = (
        Index("events_occurred_at_idx", text("occurred_at DESC")),
        {"schema": "surveillance"},
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("surveillance.device_registry.id"),
        nullable=False,
    )
    raw_payload: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True
    )
    extracted_facts: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), primary_key=True, nullable=False
    )
    ingested_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class IngestionLog(Base, ClassificationMetaMixin):
    __tablename__ = "ingestion_log"
    __table_args__ = {"schema": "surveillance"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("surveillance.device_registry.id"),
        nullable=False,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    events_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class ConfrontationBlockLog(Base, ClassificationMetaMixin):
    __tablename__ = "confrontation_block_log"
    __table_args__ = {"schema": "surveillance"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    target: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    blocked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


# ===================================================================
# Schema: financial  (4 tables)
# ===================================================================


class Transactions(Base, ClassificationMetaMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("transactions_occurred_at_idx", text("occurred_at DESC")),
        {"schema": "financial"},
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    transaction_type: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(
        Text, server_default=text("'IDR'")
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), primary_key=True, nullable=False
    )
    api_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class ProjectCosts(Base, ClassificationMetaMixin):
    __tablename__ = "project_costs"
    __table_args__ = {"schema": "financial"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    cost_category: Mapped[str] = mapped_column(Text, nullable=False)
    total_cost: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    billing_period: Mapped[str] = mapped_column(Text, nullable=False)


class MonthlyReports(Base, ClassificationMetaMixin):
    __tablename__ = "monthly_reports"
    __table_args__ = {"schema": "financial"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    report_month: Mapped[str] = mapped_column(Text, nullable=False)
    total_income: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 2), server_default=text("0")
    )
    total_expense: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    api_cost_breakdown: Mapped[Optional[JsonObject]] = mapped_column(
        JSONB, nullable=True
    )
    budget_remaining: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)


class OptimizationLog(Base):
    __tablename__ = "optimization_log"
    __table_args__ = {"schema": "financial"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    optimization_type: Mapped[str] = mapped_column(Text, nullable=False)
    savings_estimate: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


# ===================================================================
# Schema: projects  (4 tables)
# ===================================================================


class Tasks(Base, ClassificationMetaMixin):
    __tablename__ = "tasks"
    __table_args__ = {"schema": "projects"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    task_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class LoopInstances(Base, ClassificationMetaMixin):
    __tablename__ = "loop_instances"
    __table_args__ = (
        Index("ix_loop_instances_status", "status"),
        Index("ix_loop_instances_task_id", "task_id"),
        Index("ix_loop_instances_started_at", text("started_at DESC")),
        {"schema": "projects"},
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    loop_phase: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.tasks.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    result_summary: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    guardian_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    lqs_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_count: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("0")
    )
    retry_count: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("0")
    )


class AgentTasks(Base, ClassificationMetaMixin):
    __tablename__ = "agent_tasks"
    __table_args__ = {"schema": "projects"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    loop_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.loop_instances.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class EvidenceArtifacts(Base):
    __tablename__ = "evidence_artifacts"
    __table_args__ = {"schema": "projects"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.tasks.id"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


# ===================================================================
# Schema: social  (3 tables)
# ===================================================================


class SocialMap(Base, ClassificationMetaMixin):
    __tablename__ = "social_map"
    __table_args__ = {"schema": "social"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    contact_name: Mapped[str] = mapped_column(Text, nullable=False)
    relationship_type: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("5")
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_contact_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class ClientContacts(Base, ClassificationMetaMixin):
    __tablename__ = "client_contacts"
    __table_args__ = {"schema": "social"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    client_name: Mapped[str] = mapped_column(Text, nullable=False)
    project_association: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    contact_info: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    negotiation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CommunicationLog(Base, ClassificationMetaMixin):
    __tablename__ = "communication_log"
    __table_args__ = {"schema": "social"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social.social_map.id", ondelete="SET NULL"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


# ===================================================================
# Schema: agents  (3 tables)
# ===================================================================


class SubagentRegistry(Base):
    __tablename__ = "subagent_registry"
    __table_args__ = {"schema": "agents"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    agent_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    agent_type: Mapped[str] = mapped_column(Text, nullable=False)
    capabilities: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )
    max_concurrency: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("1")
    )
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("true")
    )
    registered_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class TaskQueue(Base, ClassificationMetaMixin):
    __tablename__ = "task_queue"
    __table_args__ = {"schema": "agents"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.subagent_registry.id"),
        nullable=False,
    )
    task_payload: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    priority: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("5")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    queued_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class ExecutionLog(Base, ClassificationMetaMixin):
    __tablename__ = "execution_log"
    __table_args__ = {"schema": "agents"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.task_queue.id"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.subagent_registry.id"),
        nullable=False,
    )
    execution_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_estimate: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


# ===================================================================
# Schema: consent  (3 tables)
# ===================================================================


class ConsentLedger(Base, ClassificationMetaMixin):
    __tablename__ = "consent_ledger"
    __table_args__ = {"schema": "consent"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    consent_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    granted_by: Mapped[str] = mapped_column(Text, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    revocation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_hash: Mapped[str] = mapped_column(Text, nullable=False)


class RevocationLog(Base, ClassificationMetaMixin):
    __tablename__ = "revocation_log"
    __table_args__ = {"schema": "consent"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    consent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consent.consent_ledger.id"),
        nullable=False,
    )
    revocation_type: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_scope: Mapped[str] = mapped_column(Text, nullable=False)
    cascade_effects: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
    revoked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class ScopeRegistry(Base, ClassificationMetaMixin):
    __tablename__ = "scope_registry"
    __table_args__ = {"schema": "consent"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    scope_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    scope_description: Mapped[str] = mapped_column(Text, nullable=False)
    default_status: Mapped[str] = mapped_column(Text, nullable=False)
    data_domains_affected: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )


# ===================================================================
# Schema: security  (3 tables)
# ===================================================================


class AccessLog(Base, ClassificationMetaMixin):
    __tablename__ = "access_log"
    __table_args__ = {"schema": "security"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    principal: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_table: Mapped[str] = mapped_column(Text, nullable=False)
    classification_bypassed: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    source_ip: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class BreakGlassLog(Base, ClassificationMetaMixin):
    __tablename__ = "break_glass_log"
    __table_args__ = {"schema": "security"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    principal: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    data_accessed: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class SecretRotationLog(Base, ClassificationMetaMixin):
    __tablename__ = "secret_rotation_log"
    __table_args__ = {"schema": "security"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    secret_name: Mapped[str] = mapped_column(Text, nullable=False)
    rotation_type: Mapped[str] = mapped_column(Text, nullable=False)
    old_key_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_key_id: Mapped[str] = mapped_column(Text, nullable=False)
    rotated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


# ===================================================================
# Schema: audit  (3 tables)
# ===================================================================


class AuditTrail(Base, ClassificationMetaMixin):
    __tablename__ = "audit_trail"
    __table_args__ = (
        Index("audit_trail_occurred_at_idx", text("occurred_at DESC")),
        {"schema": "audit"},
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_payload: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    principal: Mapped[str] = mapped_column(Text, nullable=False)
    event_hash: Mapped[str] = mapped_column(Text, nullable=False)
    previous_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), primary_key=True, nullable=False
    )


class EvidenceRegister(Base):
    __tablename__ = "evidence_register"
    __table_args__ = (
        Index("ix_evidence_register_audit_event_id", "audit_event_id"),
        {"schema": "audit"},
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    audit_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class ComplianceCheck(Base, ClassificationMetaMixin):
    __tablename__ = "compliance_check"
    __table_args__ = {"schema": "audit"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    check_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    findings: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


# ===================================================================
# Schema: ops  (4 tables)
# ===================================================================


class MigrationLog(Base, ClassificationMetaMixin):
    __tablename__ = "migration_log"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    migration_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    executed_by: Mapped[str] = mapped_column(Text, nullable=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    rollback_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    evidence_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checksum: Mapped[str] = mapped_column(Text, nullable=False)


class BackupLog(Base, ClassificationMetaMixin):
    __tablename__ = "backup_log"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    backup_type: Mapped[str] = mapped_column(Text, nullable=False)
    backup_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)


class HealthCheck(Base, ClassificationMetaMixin):
    __tablename__ = "health_check"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    check_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    alert_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )
    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


# ===================================================================
# Schema: extensions  (3 tables)
# ===================================================================


class PgvectorConfig(Base):
    __tablename__ = "pgvector_config"
    __table_args__ = {"schema": "extensions"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    extension_version: Mapped[str] = mapped_column(Text, nullable=False)
    default_index_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'hnsw'")
    )
    hnsw_m: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("16")
    )
    hnsw_ef_construction: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("128")
    )
    hnsw_ef_search: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("64")
    )


class TimescaledbConfig(Base):
    __tablename__ = "timescaledb_config"
    __table_args__ = {"schema": "extensions"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    extension_version: Mapped[str] = mapped_column(Text, nullable=False)
    default_chunk_interval: Mapped[Optional[str]] = mapped_column(
        Text, server_default=text("'7 days'")
    )
    compression_enabled: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("true")
    )
    retention_default_days: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("365")
    )


class PgcryptoConfig(Base):
    __tablename__ = "pgcrypto_config"
    __table_args__ = {"schema": "extensions"}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    extension_version: Mapped[str] = mapped_column(Text, nullable=False)
    default_algorithm: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'aes-256-gcm'")
    )
    key_derivation_function: Mapped[Optional[str]] = mapped_column(
        Text, server_default=text("'pbkdf2'")
    )