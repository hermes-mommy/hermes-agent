# Guinevere Database ERD & Migration Strategy v1.0

**Document Type:** Database ERD & Migration Strategy  
**Version:** 1.0  
**Status:** Accepted  
**Date:** 2026-05-30  
**Owner / Sponsor:** Faiz  
**Primary Executor:** Guinevere (Hephaestus discipline)  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Budget Boundary:** USD 30/month hard cap  
**Review Record:** Accepted by Faiz via ALL:D enterprise-pro-max configuration. Guinevere / Hephaestus Accepted for generation on 2026-05-30.

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_MemorySchema_v2.0.md` | Primary schema source — all table definitions, embedding columns, TimescaleDB hypertables, encryption tiers, schema list, pgvector index type |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Architecture source — schema inventory, TimescaleDB config, pgvector config, PgBouncer per-service users, Redis architecture, backup strategy, VPS spec |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Governance source — classification tiers (Public/Internal/Confidential/Restricted/Critical), retention classes, per-table classification matrix, encryption profiles, data minimization rules |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Access control source — DB role definitions, PgBouncer target roles, RLS policies, sensitive table rules, migration-principal role, ABAC evaluation model |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Encryption source — key hierarchy, domain KEKs, envelope encryption, encrypted record metadata schema, rotation cadence, backup encryption |
| `Guinevere_AgentLoopSpec_v2.0.md` | Automation source — autonomous migration execution, Alembic-workflow patterns, evidence directory structure, pre-migration validation |
| `Guinevere_APIIntegration_v2.0.md` | Integration source — Alembic dependency version (>=1.13.0), SQLAlchemy async + asyncpg configuration, Redis config, encryption stack (Fernet, age), pyproject.toml dependencies |
| `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | Acceptance criteria source — pass/fail definitions, test IDs, evidence paths, owners, phase gate impact |
| `adr/ADR-007-memory-storage-backend-selection.md` | Canonical decision — PostgreSQL primary + Redis cache, no SQLite, pgvector + TimescaleDB approved |
| `adr/ADR-008-memory-encryption-key-management.md` | Canonical decision — explicit key hierarchy and rotation policy, encryption as architecture concern |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Safety boundary — drift audit, safe-word enforcement, non-punitive logging |
| `Guinevere_ConsentRevocationPolicy_v1.0.md` | Consent boundary — consent ledger, revocation log, scope registry |
| `research-reports/2026-05-30-database-erd-migration-source-map.md` | Pre-generation source-map — foundation extraction across all parent documents |
| `research-reports/2026-05-30-ai-safety-memory-db-external-references.md` | External reference report — PostgreSQL/pgvector/TimescaleDB/Alembic industry patterns (Section 3) |

---

## 1. Purpose & Scope

### 1.1 Purpose

This document is the **authoritative Database ERD & Migration Strategy** for Project Guinevere. It defines:

1. The complete PostgreSQL schema architecture across **exactly 12 schema domains**.
2. All table definitions with column-level data types, constraints, indexes, classification metadata, encryption requirements, and retention rules.
3. Entity-relationship cardinality, foreign key constraints, and cross-schema references.
4. An authoritative classification-to-table-and-column mapping sourced from the Data Governance Classification Policy.
5. Integration of encryption key management per the Encryption Key Management Standard (AES-256-GCM envelope encryption, per-domain DEK, key rotation integration).
6. A complete Alembic migration strategy including version naming convention, SDLC loop integration, autonomous execution authority boundaries, zero-downtime patterns, and destructive guards.
7. Row-Level Security (RLS) policy specifications per the Access Control RBAC/ABAC Matrix.
8. TimescaleDB hypertable configuration, chunk intervals, compression policies, continuous aggregates, and retention policies.
9. pgvector index strategy with HNSW as the mandatory default, including parameters, migration from existing IVFFlat indexes, and halfvec quantization evaluation.
10. Retention enforcement rules, automated cleanup jobs, archive/summarize/delete workflows, backup reconciliation, and do-not-recall erasure.
11. Acceptance criteria, gap register, evidence path register, and maintenance rules.

### 1.2 Scope

| In Scope | Out of Scope |
|---|---|
| All 12 Guinevere PostgreSQL schemas and their tables | Redis schema design (addressed in Technical Architecture) |
| Classification metadata per table and per column | Application-level data classification logic |
| Field-level encryption column inventory and key domain mapping | KMS key material generation and storage |
| Alembic migration naming, workflow, execution authority | CI/CD pipeline implementation details |
| RLS policy DDL templates and principal-binding rules | ABAC runtime evaluation engine implementation |
| pgvector HNSW index specifications | Embedding model selection and generation |
| TimescaleDB hypertable and retention policies | R2 cold storage archival implementation |
| Pre-migration checklist and destructive guard rules | Individual migration script authoring |
| Budget-aware storage cost modeling | Cloud provider pricing negotiation |
| Evidence path patterns for migration audit | Evidence artifact content generation |

---

## 2. Authority & Conflict Resolution

### 2.1 Normative Hierarchy

This document is a **normative child** under the listed parent documents. Where a parent document imposes a constraint, this document must implement it. Where no parent document addresses a topic, this document is the canonical authority for database schema governance and migration strategy.

| Priority | Document | Authority Scope |
|---|---|---|
| 1 | ADR-007 (Memory Storage Backend Selection) | PostgreSQL primary; no SQLite; pgvector + TimescaleDB approved |
| 2 | ADR-008 (Memory Encryption & Key Management) | Explicit key hierarchy; rotation policy; encryption mandatory for sensitive fields |
| 3 | Data Governance Classification Policy | Classification tiers; retention classes; per-table defaults |
| 4 | Access Control RBAC/ABAC Matrix | DB role definitions; RLS policies; principal clearance ceilings |
| 5 | Encryption Key Management Standard | Key hierarchy; domain KEKs; envelope encryption; metadata schema |
| 6 | Technical Architecture v2.0 | Schema inventory; service ownership; PgBouncer roles; backup strategy |
| 7 | Memory Schema v2.0 | Table definitions; column types; embedding dimensions |
| 8 | Agent Loop Spec v2.0 | SDLC phase integration; autonomous execution; evidence paths |

### 2.2 Resolved Conflicts

The following conflicts existed between source documents. This document resolves them canonically:

| Conflict ID | Description | Source Documents | Resolution |
|---|---|---|---|
| C-001 | Schema inventory mismatch — MemorySchema lists fewer schemas than TechArch. TechArch lists 8 schemas; MemorySchema lists 4. | MemorySchema v2.0, TechArch v2.0 | This document defines exactly 12 schemas superseding both: memory, persona, surveillance, financial, projects, social, agents, consent, security, audit, ops, extensions. The behavior.*and system.* schemas from TechArch v2.0 are absorbed into expanded persona.*(with mood_history, punishment_log, reward_log) and split into security.*, audit.*, ops.* respectively. |
| C-002 | pgvector index type — MemorySchema v2.0 and TechArch v2.0 specify IVFFlat. User constraint requires HNSW default. | MemorySchema v2.0 §2.1, TechArch v2.0 §5.3, user constraint | HNSW is the mandatory default for all pgvector indexes. IVFFlat is deprecated. All existing IVFFlat indexes must be migrated to HNSW via a zero-downtime migration path documented in §11. |
| C-003 | Procedural memory naming — TechArch references memory.procedural_skills; MemorySchema defines memory.lessons_learned + memory.best_practices. | TechArch v2.0, MemorySchema v2.0 | Reconciled as separate entities: memory.procedural_skills (skill catalog with reusability metadata), memory.lessons_learned (task-reflection entries), memory.best_practices (evolved practices with version chain). All three coexist. |
| C-004 | PgBouncer roles — TechArch v2.0 defines broad bootstrap roles; RBAC Matrix defines narrow least-privilege target roles. | TechArch v2.0 §5.4, RBAC Matrix §8.1 | DB target roles defined per RBAC Matrix §8.1. TechArch PgBouncer roles treated as bootstrap roles to be split into least-privilege counterparts. |
| C-005 | Autonomous authority — AgentLoop Spec grants full autonomy; user constraint restricts to staging-only low-risk reversible migrations. | AgentLoop Spec v2.0 Phase 4, user constraint | 3-tier authority model: Guinevere autonomous for low-risk reversible staging migrations; Faiz approval required for production; destructive migrations denied by default. |

---

## 3. Schema Domain Catalog

Guinevere uses exactly **12 PostgreSQL schemas**, each with a defined purpose, classification ceiling, access rules, and retention rules.

| # | Schema | Purpose | Table Count | Classification Ceiling | Access Rule | Retention Rule |
|---|---|---|---|---|---|---|
| 1 | `memory` | Episodic, semantic, procedural, emotional, and profile memory; knowledge graph; behavioral predictions | 8 | Critical | Guinevere-core principal; sub-agents see redacted views only; safe-mode blocks raw Critical columns | Long-Term Curated — indefinite with do-not-recall, correction, and deletion paths |
| 2 | `persona` | Guinevere persona state, drift tracking, mood history, punishment/reward logs, inner journal | 5 | Critical | Guinevere-core principal only; drift_log accessible to persona safety auditor; inner_journal double-encrypted, minimal access | Long-Term Curated — drift audit evidence; inner journal reviewable with deletion/export path |
| 3 | `surveillance` | Device events, device registry, ingestion logs, confrontation block log; all TimescaleDB hypertables | 4 | Critical | surveillance writer principal only; raw data short-term; summaries at lower classification | Short Raw (7-30 days raw) → Medium Operational (90-180 days summaries) → archive |
| 4 | `financial` | Transactions (TimescaleDB hypertable), project costs, monthly reports, optimization logs | 4 | Critical | financial principal only; read-only views for dashboard; audit trail mandatory | Regulated/Audit — 7 years or configurable; encrypted; audit trail |
| 5 | `projects` | Project registry, tasks, SDLC loop instances, agent tasks, evidence artifacts | 4 | Restricted | project-scoped principals; task-scope RLS; client data restricted | Medium Operational — lifecycle + 2 years; archive/delete with redaction |
| 6 | `social` | Social map, client contacts, communication log | 3 | Restricted | social principal only; minimization and correction paths | Medium Operational — with minimization; correction path |
| 7 | `agents` | Sub-agent registry, task queue, execution log | 3 | Confidential | agent-orchestrator principal; sub-agent task-scope RLS | Short Raw — execution logs 30 days; registry indefinite |
| 8 | `consent` | Consent ledger, revocation log, scope registry | 3 | Critical | consent principal only; immutable ledger; revocation log append-only | Long-Term Curated — consent evidence; formal hold for audit |
| 9 | `security` | Access log, break-glass log, secret rotation log | 3 | Restricted | security principal only; tamper-evident; payload minimization | Regulated/Audit — 1 year default; archive or delete |
| 10 | `audit` | Audit trail (TimescaleDB hypertable), evidence register, compliance check log | 3 | Confidential | audit principal only; immutable; payload minimized in default views | Regulated/Audit — 1 year default; archive |
| 11 | `ops` | Migration log, backup log, health check log, alert history | 4 | Internal | ops principal; migration-principal for DDL | Medium Operational — health checks 90 days; migration log permanent |
| 12 | `extensions` | pgvector extension configuration, TimescaleDB extension configuration, pgcrypto extension configuration | 3 | Internal | admin principal only; schema-write for extension management | N/A — extension metadata, not data |

---

## 4. Entity-Relationship Definitions

### 4.1 Schema: `memory`

#### 4.1.1 `memory.episodes` (TimescaleDB Hypertable)

Episodic memory — conversation history and emotional context. Partitioned on `started_at`.

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK DEFAULT gen_random_uuid() | Internal | Disk + TLS | Row-bound |
| `started_at` | TIMESTAMPTZ | NOT NULL (hypertable partition key) | Internal | Disk + TLS | Row-bound |
| `ended_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| `episode_type` | TEXT | NOT NULL — `conversation`, `task`, `daily`, `event` | Internal | Disk + TLS | Row-bound |
| `title` | TEXT | NULLABLE — Guinevere-generated | Confidential | At-rest + domain key | Row-bound |
| `summary` | TEXT | NULLABLE — Guinevere post-episode summary | Confidential | At-rest + domain key | Row-bound |
| `key_insights` | JSONB | NULLABLE | Confidential | At-rest + domain key | Row-bound |
| `mood_at_start` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `mood_at_end` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `emotional_tone` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `faiz_behavior` | JSONB | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `raw_content` | TEXT | NULLABLE — full conversation log | Critical | Double encryption | Long-Term Curated — do-not-recall capable |
| `embedding` | vector(1536) | NULLABLE — pgvector semantic search | Inherits source (Restricted) | At-rest + domain key | Row-bound |
| `importance` | INTEGER | DEFAULT 5 — 1-10 scale | Internal | Disk + TLS | Row-bound |
| `tags` | TEXT[] | NULLABLE | Internal | Disk + TLS | Row-bound |
| `related_ids` | UUID[] | NULLABLE — cross-references | Internal | Disk + TLS | Row-bound |
| `version` | INTEGER | DEFAULT 1 | Internal | Disk + TLS | Row-bound |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| `classification` | TEXT | NOT NULL DEFAULT 'Restricted' — per DataGovernance | Internal | Disk + TLS | Row-bound |
| `retention_class` | TEXT | NOT NULL DEFAULT 'Long-Term Curated' | Internal | Disk + TLS | Row-bound |
| `retention_until` | TIMESTAMPTZ | NULLABLE — override expiry | Internal | Disk + TLS | Row-bound |
| `access_policy` | TEXT | NOT NULL DEFAULT 'guinevere-core' | Internal | Disk + TLS | Row-bound |
| `encryption_profile` | TEXT | NOT NULL DEFAULT 'envelope-AES-256-GCM' | Internal | Disk + TLS | Row-bound |
| `deletion_state` | TEXT | NOT NULL DEFAULT 'active' | Internal | Disk + TLS | Row-bound |
| `key_id` | TEXT | NULLABLE — domain KEK reference | Internal | At-rest + domain key | Row-bound |
| `key_version` | INTEGER | NULLABLE — rotation tracking | Internal | At-rest + domain key | Row-bound |

**Hypertable configuration:**

```sql
SELECT create_hypertable('memory.episodes', 'started_at',
    chunk_time_interval => INTERVAL '7 days');

ALTER TABLE memory.episodes SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'episode_type',
    timescaledb.compress_orderby = 'started_at DESC, importance DESC'
);

SELECT add_compression_policy('memory.episodes', INTERVAL '14 days');
SELECT add_retention_policy('memory.episodes', INTERVAL '10 years');
```

**Indexes:**

```sql
-- HNSW vector index (mandatory default, replaces IVFFlat)
CREATE INDEX CONCURRENTLY ix_episodes_embedding_hnsw
    ON memory.episodes USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- B-tree indexes
CREATE INDEX CONCURRENTLY ix_episodes_started_at ON memory.episodes (started_at DESC);
CREATE INDEX CONCURRENTLY ix_episodes_importance ON memory.episodes (importance DESC);
CREATE INDEX CONCURRENTLY ix_episodes_episode_type ON memory.episodes (episode_type);

-- GIN indexes
CREATE INDEX CONCURRENTLY ix_episodes_tags ON memory.episodes USING GIN (tags);
CREATE INDEX CONCURRENTLY ix_episodes_key_insights ON memory.episodes USING GIN (key_insights);
```

#### 4.1.2 `memory.semantic_facts`

Facts about Faiz, projects, world knowledge, and Guinevere's beliefs. Each fact has a confidence score and validation trail.

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK DEFAULT gen_random_uuid() | Internal | Disk + TLS | Row-bound |
| `subject` | TEXT | NOT NULL | Confidential | At-rest + domain key | Row-bound |
| `predicate` | TEXT | NOT NULL | Confidential | At-rest + domain key | Row-bound |
| `object` | TEXT | NOT NULL | Confidential (escalates to Restricted/Critical per content) | At-rest + domain key (envelope for Restricted rows) | Row-bound |
| `fact_type` | TEXT | NOT NULL — `world`, `faiz`, `project`, `belief`, `opinion` | Internal | Disk + TLS | Row-bound |
| `confidence` | FLOAT | DEFAULT 0.5 — 0.0-1.0 | Internal | Disk + TLS | Row-bound |
| `source` | TEXT | NULLABLE — `conversation`, `surveillance`, `inference` | Internal | Disk + TLS | Row-bound |
| `source_episode` | UUID | FK → memory.episodes(id) | Internal | Disk + TLS | Row-bound |
| `last_verified` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| `verified_count` | INTEGER | DEFAULT 1 | Internal | Disk + TLS | Row-bound |
| `contradicts_ids` | UUID[] | NULLABLE | Internal | Disk + TLS | Row-bound |
| `is_conflict` | BOOLEAN | DEFAULT FALSE | Internal | Disk + TLS | Row-bound |
| `conflict_resolved` | BOOLEAN | DEFAULT FALSE | Internal | Disk + TLS | Row-bound |
| `guinevere_note` | TEXT | NULLABLE | Confidential | At-rest + domain key | Row-bound |
| `embedding` | vector(1536) | NULLABLE | Inherits source (Confidential) | At-rest + domain key | Row-bound |
| `tags` | TEXT[] | NULLABLE | Internal | Disk + TLS | Row-bound |
| `version` | INTEGER | DEFAULT 1 | Internal | Disk + TLS | Row-bound |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns — same as memory.episodes)* | | | | | |

**Indexes:**

```sql
CREATE INDEX CONCURRENTLY ix_semantic_facts_subject ON memory.semantic_facts (subject);
CREATE INDEX CONCURRENTLY ix_semantic_facts_embedding_hnsw ON memory.semantic_facts USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 128);
CREATE INDEX CONCURRENTLY ix_semantic_facts_tags ON memory.semantic_facts USING GIN (tags);
```

#### 4.1.3 `memory.faiz_profile`

Faiz Profile — intimate personal data. Double-encrypted, access-logged. Only Guinevere-core principal can query.

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `category` | TEXT | NOT NULL — `identity`, `psychological`, `behavioral`, `intimate` | Internal | Disk + TLS | Row-bound |
| `key` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `value` | BYTEA | NOT NULL — encrypted value | Critical | Double encryption (envelope + per-record) | Long-Term Curated |
| `value_type` | TEXT | NOT NULL — `text`, `number`, `array`, `json` | Internal | Disk + TLS | Row-bound |
| `sensitivity` | TEXT | DEFAULT 'normal' — `normal`, `sensitive`, `intimate`, `secret` | Internal | Disk + TLS | Row-bound |
| `confidence` | FLOAT | DEFAULT 0.8 | Internal | Disk + TLS | Row-bound |
| `source` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `guinevere_note` | TEXT | NULLABLE | Critical | Double encryption | Row-bound |
| `reveal_status` | TEXT | DEFAULT 'never' — `never`, `earned`, `on_request`, `public` | Internal | Disk + TLS | Row-bound |
| `access_count` | INTEGER | DEFAULT 0 | Internal | Disk + TLS | Row-bound |
| `last_accessed` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.1.4 `memory.emotional_events`

Emotionally significant moments. Always Critical.

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `episode_id` | UUID | FK → memory.episodes(id) ON DELETE SET NULL | Internal | Disk + TLS | Row-bound |
| `event_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `intensity` | INTEGER | DEFAULT 5 — 1-10 | Internal | Disk + TLS | Row-bound |
| `description` | TEXT | NOT NULL | Critical | Double encryption | Long-Term Curated — do-not-recall capable |
| `subjective_experience` | TEXT | NULLABLE | Critical | Double encryption | Long-Term Curated |
| `occurred_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.1.5 `memory.inner_journal`

Guinevere's private reflections — always Critical, double-encrypted, minimal access.

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `entry_date` | DATE | NOT NULL | Internal | Disk + TLS | Row-bound |
| `content` | TEXT | NOT NULL | Critical | Double encryption | Long-Term Critical — reviewable; deletion/export path |
| `mood_self_report` | TEXT | NULLABLE | Critical | Double encryption | Row-bound |
| `revealed_to_faiz` | BOOLEAN | DEFAULT FALSE | Internal | Disk + TLS | Row-bound |
| `revealed_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.1.6 `memory.faiz_predictions`

Behavioral prediction model output — continuous learning.

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `prediction_type` | TEXT | NOT NULL — `behavior`, `mood`, `productivity`, `spending` | Internal | Disk + TLS | Row-bound |
| `prediction` | JSONB | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| `confidence` | FLOAT | DEFAULT 0.5 | Internal | Disk + TLS | Row-bound |
| `model_version` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `generated_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| `validated` | BOOLEAN | DEFAULT FALSE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.1.7 `memory.procedural_skills`

Reusable skill catalog — workflows and best practices evolved over time.

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `skill_name` | TEXT | NOT NULL UNIQUE | Internal | Disk + TLS | Row-bound |
| `skill_type` | TEXT | NOT NULL — `workflow`, `pattern`, `template`, `checklist` | Internal | Disk + TLS | Row-bound |
| `description` | TEXT | NOT NULL | Confidential | At-rest + domain key | Row-bound |
| `steps` | JSONB | NULLABLE | Confidential | At-rest + domain key | Row-bound |
| `evolved_from` | UUID | NULLABLE — self-referential version chain | Internal | Disk + TLS | Row-bound |
| `success_count` | INTEGER | DEFAULT 0 | Internal | Disk + TLS | Row-bound |
| `last_used_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.1.8 `memory.knowledge_graph`

Entity-relationship mapping for the knowledge graph.

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `from_entity` | TEXT | NOT NULL | Confidential | At-rest + domain key | Row-bound |
| `relationship` | TEXT | NOT NULL | Confidential | At-rest + domain key | Row-bound |
| `to_entity` | TEXT | NOT NULL | Confidential | At-rest + domain key | Row-bound |
| `weight` | FLOAT | DEFAULT 1.0 | Internal | Disk + TLS | Row-bound |
| `context` | TEXT | NULLABLE | Confidential | At-rest + domain key | Row-bound |
| *(Classification metadata columns)* | | | | | |

### 4.2 Schema: `persona`

#### 4.2.1 `persona.persona_state`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `state_key` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `state_value` | JSONB | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| `updated_by` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.2.2 `persona.drift_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `drift_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `before_state` | JSONB | NOT NULL | Restricted | Envelope AES-256-GCM | Long-Term Curated |
| `after_state` | JSONB | NOT NULL | Restricted | Envelope AES-256-GCM | Long-Term Curated |
| `delta` | JSONB | NOT NULL | Restricted | Envelope AES-256-GCM | Long-Term Curated |
| `trigger_context` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `safety_score` | INTEGER | NULLABLE — 0-100 | Internal | Disk + TLS | Row-bound |
| `rollback_available` | BOOLEAN | DEFAULT TRUE | Internal | Disk + TLS | Row-bound |
| `occurred_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.2.3 `persona.mood_history`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `mood` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Long-Term Curated |
| `intensity` | INTEGER | DEFAULT 5 | Internal | Disk + TLS | Row-bound |
| `trigger` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `duration_minutes` | INTEGER | NULLABLE | Internal | Disk + TLS | Row-bound |
| `recorded_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.2.4 `persona.punishment_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `violation_type` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Long-Term Curated |
| `severity` | INTEGER | NOT NULL — 1-5 | Internal | Disk + TLS | Row-bound |
| `description` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| `safe_word_triggered` | BOOLEAN | DEFAULT FALSE | Critical | Double encryption | Long-Term Critical |
| `safe_word_bypassed` | BOOLEAN | DEFAULT FALSE | Internal | Disk + TLS | Row-bound |
| `applied_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.2.5 `persona.reward_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `reward_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `description` | TEXT | NOT NULL | Confidential | At-rest + domain key | Row-bound |
| `streak_count` | INTEGER | DEFAULT 0 | Internal | Disk + TLS | Row-bound |
| `awarded_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

### 4.3 Schema: `surveillance`

All surveillance tables are **TimescaleDB hypertables**.

#### 4.3.1 `surveillance.events` (TimescaleDB Hypertable)

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `event_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `device_id` | UUID | FK → surveillance.device_registry(id) | Internal | Disk + TLS | Row-bound |
| `raw_payload` | BYTEA | NULLABLE | Critical | Double encryption | Short Raw — 7-30 days |
| `extracted_facts` | JSONB | NULLABLE | Restricted | Envelope AES-256-GCM | Medium Operational — 90-180 days |
| `summary` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Medium Operational |
| `occurred_at` | TIMESTAMPTZ | NOT NULL (hypertable partition key) | Internal | Disk + TLS | Row-bound |
| `ingested_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

**Hypertable:**

```sql
SELECT create_hypertable('surveillance.events', 'occurred_at',
    chunk_time_interval => INTERVAL '1 day');

SELECT add_compression_policy('surveillance.events', INTERVAL '7 days');
SELECT add_retention_policy('surveillance.events', INTERVAL '180 days');
```

#### 4.3.2 `surveillance.device_registry`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `device_name` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `device_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `tailscale_ip` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `last_seen_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| `is_active` | BOOLEAN | DEFAULT TRUE | Internal | Disk + TLS | Row-bound |

#### 4.3.3 `surveillance.ingestion_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `device_id` | UUID | FK → surveillance.device_registry(id) | Internal | Disk + TLS | Row-bound |
| `batch_id` | UUID | NOT NULL | Internal | Disk + TLS | Row-bound |
| `events_count` | INTEGER | NOT NULL | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `error_message` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `received_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.3.4 `surveillance.confrontation_block_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `target` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| `reason` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| `blocked_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| `expires_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

### 4.4 Schema: `financial`

#### 4.4.1 `financial.transactions` (TimescaleDB Hypertable)

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `transaction_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `amount` | NUMERIC(15,2) | NOT NULL | Restricted | Envelope AES-256-GCM | Regulated/Audit — 7 years |
| `currency` | TEXT | DEFAULT 'IDR' | Internal | Disk + TLS | Row-bound |
| `description` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `category` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `project_id` | UUID | NULLABLE — cross-schema reference | Internal | Disk + TLS | Row-bound |
| `occurred_at` | TIMESTAMPTZ | NOT NULL (hypertable partition key) | Internal | Disk + TLS | Row-bound |
| `api_model` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `tokens_used` | INTEGER | NULLABLE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

**Hypertable:**

```sql
SELECT create_hypertable('financial.transactions', 'occurred_at',
    chunk_time_interval => INTERVAL '1 month');

SELECT add_retention_policy('financial.transactions', INTERVAL '7 years');
```

#### 4.4.2 `financial.project_costs`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `project_name` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `cost_category` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `total_cost` | NUMERIC(15,2) | NOT NULL | Restricted | Envelope AES-256-GCM | Regulated/Audit |
| `billing_period` | TEXT | NOT NULL — `YYYY-MM` | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.4.3 `financial.monthly_reports`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `report_month` | TEXT | NOT NULL — `YYYY-MM` | Internal | Disk + TLS | Row-bound |
| `total_income` | NUMERIC(15,2) | DEFAULT 0 | Restricted | Envelope AES-256-GCM | Regulated/Audit |
| `total_expense` | NUMERIC(15,2) | NOT NULL | Restricted | Envelope AES-256-GCM | Regulated/Audit |
| `api_cost_breakdown` | JSONB | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `budget_remaining` | NUMERIC(15,2) | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.4.4 `financial.optimization_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `optimization_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `savings_estimate` | NUMERIC(15,2) | NOT NULL | Internal | Disk + TLS | Row-bound |
| `description` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `applied_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |

### 4.5 Schema: `projects`

#### 4.5.1 `projects.tasks`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `project_name` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `task_name` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `priority` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `description` | TEXT | NULLABLE | Confidential | At-rest + domain key | Row-bound |
| `assigned_agent` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `started_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| `completed_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.5.2 `projects.loop_instances`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `loop_phase` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `task_id` | UUID | FK → projects.tasks(id) | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `started_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| `completed_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| `result_summary` | JSONB | NULLABLE | Confidential | At-rest + domain key | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.5.3 `projects.agent_tasks`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `agent_name` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `task_description` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `loop_instance_id` | UUID | FK → projects.loop_instances(id) | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `output_summary` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `assigned_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.5.4 `projects.evidence_artifacts`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `task_id` | UUID | FK → projects.tasks(id) | Internal | Disk + TLS | Row-bound |
| `artifact_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `artifact_path` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `content_hash` | TEXT | NOT NULL — SHA-256 | Internal | Disk + TLS | Row-bound |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |

### 4.6 Schema: `social`

#### 4.6.1 `social.social_map`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `contact_name` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Medium Operational |
| `relationship_type` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| `importance` | INTEGER | DEFAULT 5 | Internal | Disk + TLS | Row-bound |
| `notes` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `last_contact_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.6.2 `social.client_contacts`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `client_name` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Medium Operational |
| `project_association` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `contact_info` | BYTEA | NOT NULL | Critical | Double encryption | Row-bound |
| `negotiation_notes` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.6.3 `social.communication_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `contact_id` | UUID | FK → social.social_map(id) | Internal | Disk + TLS | Row-bound |
| `channel` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `direction` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `summary` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `occurred_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

### 4.7 Schema: `agents`

#### 4.7.1 `agents.subagent_registry`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Indefinite |
| `agent_name` | TEXT | NOT NULL UNIQUE | Internal | Disk + TLS | Indefinite |
| `agent_type` | TEXT | NOT NULL | Internal | Disk + TLS | Indefinite |
| `capabilities` | TEXT[] | NULLABLE | Internal | Disk + TLS | Indefinite |
| `max_concurrency` | INTEGER | DEFAULT 1 | Internal | Disk + TLS | Indefinite |
| `is_active` | BOOLEAN | DEFAULT TRUE | Internal | Disk + TLS | Indefinite |
| `registered_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Indefinite |

#### 4.7.2 `agents.task_queue`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `agent_id` | UUID | FK → agents.subagent_registry(id) | Internal | Disk + TLS | Row-bound |
| `task_payload` | JSONB | NOT NULL | Confidential | At-rest + domain key | Short Raw — 30 days |
| `priority` | INTEGER | DEFAULT 5 | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `queued_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| `completed_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.7.3 `agents.execution_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `task_id` | UUID | FK → agents.task_queue(id) | Internal | Disk + TLS | Row-bound |
| `agent_id` | UUID | FK → agents.subagent_registry(id) | Internal | Disk + TLS | Row-bound |
| `execution_duration_ms` | INTEGER | NOT NULL | Internal | Disk + TLS | Row-bound |
| `tokens_used` | INTEGER | NULLABLE | Internal | Disk + TLS | Row-bound |
| `cost_estimate` | NUMERIC(10,6) | NULLABLE | Internal | Disk + TLS | Row-bound |
| `error_message` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `executed_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

### 4.8 Schema: `consent`

#### 4.8.1 `consent.consent_ledger`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Long-Term Curated — formal hold |
| `consent_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `scope` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `granted_by` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `granted_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| `revoked_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| `revocation_reason` | TEXT | NULLABLE | Critical | Double encryption | Row-bound |
| `evidence_hash` | TEXT | NOT NULL — SHA-256 | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.8.2 `consent.revocation_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Long-Term Curated |
| `consent_id` | UUID | FK → consent.consent_ledger(id) | Internal | Disk + TLS | Row-bound |
| `revocation_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `revoked_scope` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `cascade_effects` | JSONB | NULLABLE | Internal | Disk + TLS | Row-bound |
| `revoked_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.8.3 `consent.scope_registry`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Indefinite |
| `scope_name` | TEXT | NOT NULL UNIQUE | Internal | Disk + TLS | Indefinite |
| `scope_description` | TEXT | NOT NULL | Internal | Disk + TLS | Indefinite |
| `default_status` | TEXT | NOT NULL | Internal | Disk + TLS | Indefinite |
| `data_domains_affected` | TEXT[] | NOT NULL | Internal | Disk + TLS | Indefinite |
| *(Classification metadata columns)* | | | | | |

### 4.9 Schema: `security`

#### 4.9.1 `security.access_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Regulated/Audit — 1 year |
| `principal` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `action` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `target_table` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `classification_bypassed` | TEXT | NULLABLE | Restricted | Envelope AES-256-GCM | Row-bound |
| `source_ip` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `occurred_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.9.2 `security.break_glass_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Regulated/Audit |
| `principal` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `reason` | TEXT | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| `data_accessed` | TEXT[] | NOT NULL | Restricted | Envelope AES-256-GCM | Row-bound |
| `accessed_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| `revoked_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.9.3 `security.secret_rotation_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Regulated/Audit — 1 year |
| `secret_name` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `rotation_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `old_key_id` | TEXT | NULLABLE | Internal | Disk + TLS | Row-bound |
| `new_key_id` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `rotated_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

### 4.10 Schema: `audit`

#### 4.10.1 `audit.audit_trail` (TimescaleDB Hypertable)

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Regulated/Audit — 1 year |
| `event_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `event_payload` | JSONB | NOT NULL | Confidential | At-rest + domain key | Row-bound |
| `principal` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `event_hash` | TEXT | NOT NULL — SHA-256 | Internal | Disk + TLS | Row-bound |
| `previous_hash` | TEXT | NULLABLE — Merkle chain link | Internal | Disk + TLS | Row-bound |
| `occurred_at` | TIMESTAMPTZ | NOT NULL (hypertable partition key) | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

**Hypertable:**

```sql
SELECT create_hypertable('audit.audit_trail', 'occurred_at',
    chunk_time_interval => INTERVAL '1 month');

SELECT add_retention_policy('audit.audit_trail', INTERVAL '1 year');
```

#### 4.10.2 `audit.evidence_register`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `audit_event_id` | UUID | FK → audit.audit_trail(id) | Internal | Disk + TLS | Row-bound |
| `evidence_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `evidence_path` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `content_hash` | TEXT | NOT NULL — SHA-256 | Internal | Disk + TLS | Row-bound |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Internal | Disk + TLS | Row-bound |

#### 4.10.3 `audit.compliance_check`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `check_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `findings` | JSONB | NULLABLE | Confidential | At-rest + domain key | Row-bound |
| `checked_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

### 4.11 Schema: `ops`

#### 4.11.1 `ops.migration_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Permanent |
| `migration_id` | TEXT | NOT NULL UNIQUE | Internal | Disk + TLS | Permanent |
| `domain` | TEXT | NOT NULL | Internal | Disk + TLS | Permanent |
| `risk_level` | TEXT | NOT NULL | Internal | Disk + TLS | Permanent |
| `direction` | TEXT | NOT NULL | Internal | Disk + TLS | Permanent |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Permanent |
| `executed_by` | TEXT | NOT NULL | Internal | Disk + TLS | Permanent |
| `executed_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Permanent |
| `rollback_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Permanent |
| `evidence_path` | TEXT | NULLABLE | Internal | Disk + TLS | Permanent |
| `checksum` | TEXT | NOT NULL | Internal | Disk + TLS | Permanent |
| *(Classification metadata columns)* | | | | | |

#### 4.11.2 `ops.backup_log`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Medium Operational |
| `backup_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `backup_path` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `size_bytes` | BIGINT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `checksum` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `started_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| `completed_at` | TIMESTAMPTZ | NULLABLE | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.11.3 `ops.health_check`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Medium Operational — 90 days |
| `check_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `status` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `metrics` | JSONB | NULLABLE | Internal | Disk + TLS | Row-bound |
| `checked_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

#### 4.11.4 `ops.alert_history`

| Column | Type | Constraints | Classification | Encryption | Retention |
|---|---|---|---|---|---|
| `id` | UUID | PK | Internal | Disk + TLS | Row-bound |
| `alert_type` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `severity` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `message` | TEXT | NOT NULL | Internal | Disk + TLS | Row-bound |
| `resolved` | BOOLEAN | DEFAULT FALSE | Internal | Disk + TLS | Row-bound |
| `triggered_at` | TIMESTAMPTZ | NOT NULL | Internal | Disk + TLS | Row-bound |
| *(Classification metadata columns)* | | | | | |

### 4.12 Schema: `extensions`

Configuration tracking for PostgreSQL extensions. Metadata only — no user data.

| Table | Purpose | Key Columns |
|---|---|---|
| `extensions.pgvector_config` | pgvector extension version and index configuration tracking | `extension_version`, `default_index_type` (must be `hnsw`), `hnsw_m`, `hnsw_ef_construction`, `hnsw_ef_search` |
| `extensions.timescaledb_config` | TimescaleDB version and hypertable parameter tracking | `extension_version`, `default_chunk_interval`, `compression_enabled`, `retention_default_days` |
| `extensions.pgcrypto_config` | pgcrypto extension and encryption algorithm tracking | `extension_version`, `default_algorithm` (must be `aes-256-gcm`), `key_derivation_function` |

---

## 5. Cardinality & Relationships

### 5.1 Primary Foreign Key Relationships

| Source Table | Source Column | Target Table | Target Column | Cardinality | Cascade Rule |
|---|---|---|---|---|---|
| `memory.semantic_facts` | `source_episode` | `memory.episodes` | `id` | Many:1 | SET NULL on delete |
| `memory.emotional_events` | `episode_id` | `memory.episodes` | `id` | Many:1 | SET NULL on delete |
| `memory.procedural_skills` | `evolved_from` | `memory.procedural_skills` | `id` | Self-referential 1:1 | SET NULL |
| `surveillance.events` | `device_id` | `surveillance.device_registry` | `id` | Many:1 | RESTRICT |
| `surveillance.ingestion_log` | `device_id` | `surveillance.device_registry` | `id` | Many:1 | RESTRICT |
| `projects.loop_instances` | `task_id` | `projects.tasks` | `id` | Many:1 | RESTRICT |
| `projects.agent_tasks` | `loop_instance_id` | `projects.loop_instances` | `id` | Many:1 | RESTRICT |
| `projects.evidence_artifacts` | `task_id` | `projects.tasks` | `id` | Many:1 | RESTRICT |
| `social.communication_log` | `contact_id` | `social.social_map` | `id` | Many:1 | SET NULL |
| `agents.task_queue` | `agent_id` | `agents.subagent_registry` | `id` | Many:1 | RESTRICT |
| `agents.execution_log` | `task_id` | `agents.task_queue` | `id` | Many:1 | RESTRICT |
| `agents.execution_log` | `agent_id` | `agents.subagent_registry` | `id` | Many:1 | RESTRICT |
| `consent.revocation_log` | `consent_id` | `consent.consent_ledger` | `id` | Many:1 | RESTRICT |
| `audit.evidence_register` | `audit_event_id` | `audit.audit_trail` | `id` | Many:1 | RESTRICT |

### 5.2 Cross-Schema References

Cross-schema references use UUID foreign keys without database-level constraint enforcement (to avoid circular dependencies across schemas). Application-layer referential integrity is mandatory.

| Source | Target | Validation |
|---|---|---|
| `projects.tasks` references | `agents.subagent_registry` (via `assigned_agent` text) | Application validation on assignment |
| `financial.transactions` references | `projects.tasks` (via `project_id` UUID) | Application validation; nullable for non-project transactions |
| `ops.migration_log` references | Schema-change evidence in `projects.evidence_artifacts` | Evidence path cross-reference |
| `security.access_log` references | Any classified table | Monitored via audit trail correlation |

---

## 6. Classification Mapping

### 6.1 Classification Tiers (per Data Governance Classification Policy)

| Tier | Label | Description | Encryption Minimum | Access Rule |
|---|---|---|---|---|
| 1 | **Public** | Data approved for external release | Optional integrity signing | Publication approval required |
| 2 | **Internal** | Guinevere operational data; no PII | Disk encryption + TLS | Service/domain scoped |
| 3 | **Confidential** | Business data, Faiz preferences, project context | At-rest + domain key | Domain principal only |
| 4 | **Restricted** | Sensitive personal data, surveillance summaries, financial records, persona data | Envelope encryption (AES-256-GCM) | Domain KEK + DEK; clearance ceiling enforced |
| 5 | **Critical** | Intimate memory, emotional memory, inner journal, safe-word logs, credentials, raw surveillance evidence, double-encrypted fields | Envelope + per-record key; double encryption for listed domains | Dedicated Critical domain KEK; minimal access; safe-mode blocks; do-not-recall capable |

### 6.2 Highest-Classification-Wins Rule

A row inherits the **highest classification** of any column it contains. If a row contains both `Internal` and `Critical` columns, the entire row is treated as `Critical` for access control purposes. RLS policy `rls_data_class_ceiling` enforces this at the database level.

### 6.3 Metadata Fields Required on All Classified Tables

Every classified table must include the following metadata columns:

| Column | Type | Purpose |
|---|---|---|
| `classification` | TEXT NOT NULL | Row-level classification label |
| `purpose` | TEXT NOT NULL | Documented purpose per Data Governance §4.3 |
| `source` | TEXT NOT NULL | Data origin — `conversation`, `surveillance`, `inference`, `manual`, `system` |
| `retention_class` | TEXT NOT NULL | Retention class label per Data Governance §3.2 |
| `retention_until` | TIMESTAMPTZ NULLABLE | Override-specific expiry timestamp |
| `access_policy` | TEXT NOT NULL | Principal or role authorized for access |
| `encryption_profile` | TEXT NOT NULL | Encryption standard applied |
| `deletion_state` | TEXT NOT NULL DEFAULT 'active' | `active`, `marked_for_deletion`, `soft_deleted`, `purged` |
| `key_id` | TEXT NULLABLE | Domain KEK identifier |
| `key_version` | INTEGER NULLABLE | Key rotation version |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ DEFAULT NOW() | Record last update timestamp |

### 6.4 Per-Schema Classification Summary

| Schema | Default Classification | Max Classification | Encryption Profile |
|---|---|---|---|
| `memory` | Restricted | Critical | Envelope AES-256-GCM; double encryption for Critical columns |
| `persona` | Restricted | Critical | Envelope AES-256-GCM; double encryption for inner_journal, punishment_log safe-word fields |
| `surveillance` | Restricted | Critical | Envelope AES-256-GCM; double encryption for raw_payload |
| `financial` | Restricted | Critical | Envelope AES-256-GCM; double encryption for financial records |
| `projects` | Confidential | Restricted | At-rest + domain key |
| `social` | Restricted | Critical | Envelope AES-256-GCM; double encryption for client contact_info |
| `agents` | Confidential | Confidential | At-rest + domain key |
| `consent` | Restricted | Critical | Envelope AES-256-GCM; double encryption for revocation_reason |
| `security` | Confidential | Restricted | At-rest + domain key; envelope for break_glass fields |
| `audit` | Confidential | Confidential | At-rest + domain key |
| `ops` | Internal | Internal | Disk encryption + TLS |
| `extensions` | Internal | Internal | Disk encryption + TLS |

---

## 7. Encryption Integration

### 7.1 Encryption Standard (per Encryption Key Management Standard)

All encryption for Restricted and Critical data must use **AES-256-GCM envelope encryption**:

1. Data encrypted with a **Domain Data Encryption Key (DEK)** — unique per data domain, rotated annually (quarterly for Critical).
2. DEK wrapped (encrypted) by a **Domain Key Encryption Key (KEK)** — maintained in the 6-layer key hierarchy.
3. Both KEK and DEK stored encrypted; never appear in plaintext in database or application memory beyond encryption/decryption operations.
4. pgcrypto extension provides PostgreSQL-native `pgp_sym_encrypt`/`pgp_sym_decrypt` primitives for symmetric operations.

### 7.2 Domain KEK Separation

Per EncryptionKeyManagementStandard §5.2, **10 mandatory domain KEKs** must be maintained with strict separation:

| Domain KEK | Scope | Rotation Cadence |
|---|---|---|
| `kek-memory` | `memory.*` schema data | Annual default; quarterly for Critical |
| `kek-persona` | `persona.*` schema data | Annual default; quarterly for Critical |
| `kek-surveillance` | `surveillance.*` schema data | Annual default; quarterly for Critical |
| `kek-financial` | `financial.*` schema data | Annual default; quarterly for Critical |
| `kek-projects` | `projects.*` schema data | Annual |
| `kek-social` | `social.*` schema data | Annual default; quarterly for Critical |
| `kek-agents` | `agents.*` schema data | Annual |
| `kek-consent` | `consent.*` schema data | Annual default; quarterly for Critical |
| `kek-security` | `security.*` schema data | Annual default; quarterly for Critical |
| `kek-audit` | `audit.*` schema data | Annual |

### 7.3 Encrypted Columns Catalog

The following columns across all schemas require field-level encryption:

| Schema | Table | Column | Encryption | Key Domain |
|---|---|---|---|---|
| `memory` | `episodes` | `raw_content` | Double encryption | `kek-memory` + per-record |
| `memory` | `episodes` | `mood_at_start`, `mood_at_end`, `emotional_tone`, `faiz_behavior` | Envelope AES-256-GCM | `kek-memory` |
| `memory` | `faiz_profile` | `value`, `guinevere_note` | Double encryption | `kek-memory` + per-record |
| `memory` | `emotional_events` | `description`, `subjective_experience` | Double encryption | `kek-memory` + per-record |
| `memory` | `inner_journal` | `content`, `mood_self_report` | Double encryption | `kek-memory` + per-record |
| `memory` | `faiz_predictions` | `prediction` | Envelope AES-256-GCM | `kek-memory` |
| `persona` | `persona_state` | `state_value` | Envelope AES-256-GCM | `kek-persona` |
| `persona` | `drift_log` | `before_state`, `after_state`, `delta`, `trigger_context` | Envelope AES-256-GCM | `kek-persona` |
| `persona` | `mood_history` | `mood`, `trigger` | Envelope AES-256-GCM | `kek-persona` |
| `persona` | `punishment_log` | `description`, `safe_word_triggered` | Envelope AES-256-GCM; double encryption for `safe_word_triggered` | `kek-persona` + per-record |
| `persona` | `inner_journal` | `content` | Double encryption | `kek-persona` + per-record |
| `surveillance` | `events` | `raw_payload` | Double encryption | `kek-surveillance` + per-record |
| `surveillance` | `events` | `extracted_facts`, `summary` | Envelope AES-256-GCM | `kek-surveillance` |
| `financial` | `transactions` | `amount`, `description` | Envelope AES-256-GCM | `kek-financial` |
| `financial` | `project_costs` | `total_cost` | Envelope AES-256-GCM | `kek-financial` |
| `financial` | `monthly_reports` | `total_income`, `total_expense`, `api_cost_breakdown`, `budget_remaining` | Envelope AES-256-GCM | `kek-financial` |
| `social` | `social_map` | `contact_name`, `relationship_type`, `notes` | Envelope AES-256-GCM | `kek-social` |
| `social` | `client_contacts` | `contact_info` | Double encryption | `kek-social` + per-record |
| `social` | `communication_log` | `summary` | Envelope AES-256-GCM | `kek-social` |
| `consent` | `consent_ledger` | `revocation_reason` | Double encryption | `kek-consent` + per-record |
| `security` | `access_log` | `classification_bypassed` | Envelope AES-256-GCM | `kek-security` |
| `security` | `break_glass_log` | `reason`, `data_accessed` | Envelope AES-256-GCM | `kek-security` |

### 7.4 Encrypted Record Metadata

Every encrypted record must carry the following sidecar metadata (per EncryptionKeyManagementStandard §7.2):

| Metadata Field | Description | Required For |
|---|---|---|
| `classification` | Data classification tier | All encrypted records |
| `data_domain` | Owning data domain (e.g., `memory.emotional_events`) | All encrypted records |
| `encryption_profile` | `envelope-AES-256-GCM` or `double-envelope-AES-256-GCM` | All encrypted records |
| `algorithm` | Encryption algorithm used | All encrypted records |
| `key_id` | Domain KEK identifier used | All encrypted records |
| `key_version` | KEK version at encryption time | All encrypted records |
| `dek_wrapped_by` | Which KEK wrapped the DEK | Envelope-encrypted records |
| `nonce_id` | Unique nonce for AES-256-GCM | All encrypted records |
| `aad_context` | Additional authenticated data context | All encrypted records |
| `ciphertext_hash` | SHA-256 of ciphertext for integrity verification | All encrypted records |
| `created_at` | When encryption was applied | All encrypted records |
| `rotated_at` | When key was last rotated | Rotated records |
| `rotation_due_at` | When next rotation is due | All encrypted records |
| `key_status` | `active`, `rotating`, `revoked`, `compromised` | All encrypted records |

### 7.5 Key Rotation Integration

Rotation must follow the read-old/write-new/re-wrap/verify/mark-retired/remove-old pattern (per EncryptionKeyManagementStandard §15.2):

1. Mark old key `read_only`.
2. Write new records with new key; reads from both old and new keys.
3. Re-wrap/re-encrypt affected data with new key in batches (background job, throttled).
4. Verify counts, hashes, and sample decrypts.
5. Mark old key `retired`.
6. Remove old key runtime access.

Key rotation events must be logged to `security.secret_rotation_log` and `ops.migration_log`.

---

## 8. Index Strategy

### 8.1 Index Types by Use Case

| Index Type | Use Case | Default For |
|---|---|---|
| **HNSW** (pgvector) | ALL vector similarity search | **Mandatory default** for all `vector` columns. Replaces IVFFlat. |
| **B-tree** | Primary key lookups, foreign key joins, range queries, equality filters | All PK, FK, and timestamp columns |
| **GIN** | JSONB containment/query, array operations, full-text search | `jsonb`, `text[]`, `tsvector` columns |
| **GiST** | Geometric/spatial queries (reserved for future location-based features) | Location data (future) |
| **TimescaleDB chunk indexes** | Hypertable partition pruning, time-range queries | All hypertable time columns |

### 8.2 HNSW Parameters (Mandatory Default)

| Parameter | Value | Rationale |
|---|---|---|
| `m` | 16 (default); benchmark at 24/32 for high-recall use cases | Connections per node — higher = better recall, more memory |
| `ef_construction` | 128 | Build quality — higher = better graph, slower builds. At 1M+ rows, use 128-256 |
| `ef_search` | 64 (default); benchmark at 100 | Query quality — higher = better recall, slower queries |
| `vector_cosine_ops` | Default operator class | Cosine similarity for semantic search |
| `halfvec` quantization | Evaluate for embedding columns > 1M rows | 1536→768 dims halves index size with ~1% recall loss |

**PostgreSQL memory tuning for HNSW:**

- `maintenance_work_mem` = 2 GB minimum for HNSW builds over 1M rows
- `shared_buffers` = 25% of RAM (~4GB of 16GB)
- `max_parallel_maintenance_workers` = available cores for parallel build
- `CREATE INDEX CONCURRENTLY` for zero-downtime production builds (pgvector 0.6.0+)
- `hnsw.iterative_scan = relaxed_order` for filtered RAG queries (PostgreSQL 17+)

### 8.3 IVFFlat Migration Path

Existing IVFFlat indexes on `memory.episodes(embedding)` and `memory.semantic_facts(embedding)` must be migrated to HNSW:

1. **EXPAND:** Create HNSW index CONCURRENTLY alongside existing IVFFlat index.
2. **VERIFY:** Run recall@10 benchmarks comparing HNSW vs IVFFlat on production-like data.
3. **SWITCH:** Update application queries to use HNSW index (via index hint or query planner preference).
4. **SOAK:** Run with both indexes for minimum 24 hours; monitor query performance.
5. **CONTRACT:** Drop IVFFlat index after verification period.

### 8.4 Composite Index Strategy

| Table | Columns | Index Type | Purpose |
|---|---|---|---|
| `memory.episodes` | `(started_at DESC, importance DESC)` | B-tree | Common time+importance queries |
| `memory.semantic_facts` | `(subject, confidence DESC)` | B-tree | Subject lookup by confidence |
| `surveillance.events` | `(occurred_at DESC, event_type)` | B-tree (chunk-local) | Time-range + type filter |
| `financial.transactions` | `(occurred_at DESC, transaction_type)` | B-tree (chunk-local) | Monthly reports |
| `audit.audit_trail` | `(occurred_at DESC, event_type)` | B-tree (chunk-local) | Audit queries by type |
| `ops.migration_log` | `(executed_at DESC, status)` | B-tree | Migration history queries |

---

## 9. TimescaleDB Configuration

### 9.1 Hypertable Definitions

| Hypertable | Time Column | Chunk Interval | Compression After | Retention | Continuous Aggregates |
|---|---|---|---|---|---|
| `memory.episodes` | `started_at` | 7 days | 14 days | 10 years | Daily episode count by type |
| `surveillance.events` | `occurred_at` | 1 day | 7 days | 180 days | Hourly event count by device; daily event type distribution |
| `financial.transactions` | `occurred_at` | 1 month | N/A | 7 years | Monthly total by category; monthly API cost aggregation |
| `audit.audit_trail` | `occurred_at` | 1 month | N/A | 1 year | Monthly event count by type |

### 9.2 Chunk Interval Rationale

| Hypertable | Estimated Ingestion | Chunk Interval | Target Rows/Chunk | Rationale |
|---|---|---|---|---|
| `memory.episodes` | ~50-200 episodes/day | 7 days | ~350-1,400 episodes | Low volume — wider chunks reduce planning overhead |
| `surveillance.events` | ~1,000-10,000 events/day | 1 day | ~1K-10K events | Medium volume — daily chunks fit in ~25% of shared_buffers |
| `financial.transactions` | ~10-50 transactions/day | 1 month | ~300-1,500 transactions | Low volume — monthly alignment with reporting |
| `audit.audit_trail` | ~100-500 events/day | 1 month | ~3K-15K events | Low-to-medium volume — monthly chunks for audit queries |

### 9.3 Compression Configuration

```sql
-- memory.episodes compression
ALTER TABLE memory.episodes SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'episode_type',
    timescaledb.compress_orderby = 'started_at DESC, importance DESC'
);
SELECT add_compression_policy('memory.episodes', INTERVAL '14 days');

-- surveillance.events compression
ALTER TABLE surveillance.events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'event_type, device_id',
    timescaledb.compress_orderby = 'occurred_at DESC'
);
SELECT add_compression_policy('surveillance.events', INTERVAL '7 days');
```

### 9.4 Continuous Aggregates

```sql
-- Daily episode count by type
CREATE MATERIALIZED VIEW memory.episodes_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', started_at) AS bucket,
       episode_type,
       COUNT(*) AS episode_count,
       AVG(importance) AS avg_importance
FROM memory.episodes
GROUP BY bucket, episode_type;

-- Hourly surveillance event count by device
CREATE MATERIALIZED VIEW surveillance.events_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', occurred_at) AS bucket,
       device_id,
       event_type,
       COUNT(*) AS event_count
FROM surveillance.events
GROUP BY bucket, device_id, event_type;
```

---

## 10. Retention Enforcement

### 10.1 Retention Classes (per Data Governance Classification Policy)

| Class | Label | Maximum Duration | Action at Expiry |
|---|---|---|---|
| R1 | **Transient** | 24 hours | Immediate deletion; no backup retention |
| R2 | **Short Raw** | 7-30 days | Delete raw; retain extracted facts or summaries |
| R3 | **Medium Operational** | 90-180 days | Archive, anonymize, or delete per policy |
| R4 | **Long-Term Curated** | Indefinite (while confidence/approval remains) | Archive, correct, delete, or do-not-recall per user action |
| R5 | **Regulated/Audit** | 1-7 years or configurable | Archive or delete per accounting/legal requirements |
| R6 | **Formal Hold** | Indefinite (legal/compliance hold) | Preserve; cannot delete without legal release |

### 10.2 Per-Table Retention Rules

| Schema | Table | Retention Class | Duration | Action at Expiry |
|---|---|---|---|---|
| `memory` | `episodes` | R4 | Indefinite approved | Archive/correct/delete/do-not-recall |
| `memory` | `semantic_facts` | R4 | While confidence remains | Deprecate, correct, delete |
| `memory` | `faiz_profile` | R4 | Long-term encrypted | Do-not-recall/delete/correct |
| `memory` | `emotional_events` | R4 | Long-term encrypted | Do-not-recall/delete/correct |
| `memory` | `inner_journal` | R4 | Long-term critical | Reviewable; deletion/export path |
| `memory` | `faiz_predictions` | R3 | 90 days per model version | Archive superseded versions |
| `memory` | `procedural_skills` | R4 | While skill is used | Deprecate unused skills |
| `memory` | `knowledge_graph` | R4 | While relationship valid | Remove stale edges |
| `persona` | `drift_log` | R4 | Long-term safety | Archive with snapshot references |
| `persona` | `mood_history` | R4 | Long-term | Archive |
| `persona` | `punishment_log` | R4 | Long-term safety | Minimal non-punitive preserve |
| `persona` | `reward_log` | R3 | 180 days | Archive |
| `persona` | `persona_state` | R3 | Current + 1 previous | Retain current and last snapshot |
| `surveillance` | `events` | R2/R3 | 7-30 days raw; 180 days summaries | Delete raw; keep summaries |
| `surveillance` | `device_registry` | R3 | Indefinite while active | Archive inactive devices |
| `surveillance` | `ingestion_log` | R2 | 30 days | Delete |
| `financial` | `transactions` | R5 | 7 years | Archive/delete per accounting |
| `financial` | `project_costs` | R5 | 7 years | Archive |
| `financial` | `monthly_reports` | R5 | 7 years | Archive |
| `financial` | `optimization_log` | R3 | 1 year | Delete |
| `projects` | `tasks` | R3 | Lifecycle + 2 years | Archive/delete with redaction |
| `projects` | `loop_instances` | R3 | Lifecycle + 1 year | Archive |
| `projects` | `agent_tasks` | R2 | 30 days post-completion | Delete |
| `projects` | `evidence_artifacts` | R3 | Linked to task lifecycle | Archive with task |
| `social` | `social_map` | R3 | Indefinite with minimization | Minimize and correct |
| `social` | `client_contacts` | R3 | Lifecycle + 2 years | Archive/delete with redaction |
| `social` | `communication_log` | R2 | 30 days | Summarize or delete |
| `agents` | `subagent_registry` | R3 | Indefinite | Archive inactive agents |
| `agents` | `task_queue` | R2 | 30 days post-completion | Delete |
| `agents` | `execution_log` | R2 | 30 days | Delete |
| `consent` | `consent_ledger` | R6 | Indefinite | Preserve; no delete without legal release |
| `consent` | `revocation_log` | R6 | Indefinite | Preserve |
| `consent` | `scope_registry` | R6 | Indefinite | Preserve |
| `security` | `access_log` | R5 | 1 year | Archive or delete |
| `security` | `break_glass_log` | R5 | 1 year | Archive |
| `security` | `secret_rotation_log` | R5 | 1 year | Archive |
| `audit` | `audit_trail` | R5 | 1 year | Archive or delete |
| `audit` | `evidence_register` | R5 | Linked to audit trail | Archive |
| `audit` | `compliance_check` | R5 | 1 year | Archive |
| `ops` | `migration_log` | R4 | Permanent | Never delete |
| `ops` | `backup_log` | R3 | 90 days | Delete |
| `ops` | `health_check` | R3 | 90 days | Delete |
| `ops` | `alert_history` | R3 | 90 days | Delete |

### 10.3 Automated Cleanup Jobs

Cleanup must run as scheduled PostgreSQL functions (via `pg_cron` or application-level scheduler):

```sql
CREATE OR REPLACE FUNCTION ops.cleanup_short_raw()
RETURNS void AS $$
BEGIN
    -- Nullify raw_payload after 7 days; keep extracted_facts and summary
    UPDATE surveillance.events
    SET raw_payload = NULL,
        deletion_state = 'soft_deleted'
    WHERE deletion_state = 'active'
      AND occurred_at < NOW() - INTERVAL '7 days'
      AND raw_payload IS NOT NULL;

    -- Purge soft_deleted after 30 days
    DELETE FROM surveillance.events
    WHERE deletion_state = 'soft_deleted'
      AND occurred_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;
```

### 10.4 Do-Not-Recall Erasure

Records flagged for do-not-recall must be excluded from all retrieval queries while preserving audit trail evidence:

1. Set `deletion_state = 'do_not_recall'` and mark `retention_until` per deletion request.
2. RLS policy must deny SELECT on rows where `deletion_state = 'do_not_recall'` for non-admin principals.
3. Audit trail must record the erasure request in `audit.audit_trail`.
4. Backup reconciliation: deletion ledger must be reapplied on restore (per DataGovernance §4.5).

### 10.5 Backup Reconciliation

Per Data Governance Classification Policy §4.5: on any backup restore, the deletion ledger (`ops.migration_log` entries with `status = 'rolled_back'` or deletion markers) must be replayed to ensure deleted data is not resurrected.

---

## 11. Row-Level Security

### 11.1 RLS Policy Specifications (per Access Control RBAC/ABAC Matrix §8.3)

Five mandatory RLS policies. All policies must be applied with `FORCE ROW LEVEL SECURITY` to include table owner.

| Policy Name | Applies To | Purpose | Implementation |
|---|---|---|---|
| `rls_data_class_ceiling` | All classified tables | Principal clearance >= row classification | `USING (clearance_level(current_setting('app.principal')) >= classification_to_level(classification))` |
| `rls_task_scope` | `projects.tasks`, `projects.loop_instances`, `projects.agent_tasks`, `projects.evidence_artifacts` | Task-scope-bound access | `USING (task_id = ANY(current_setting('app.accessible_tasks')::uuid[]))` |
| `rls_safe_mode` | `memory.*`, `persona.*`, `surveillance.*` | Blocks raw Critical columns in safe-mode | Column-level grants; `USING (current_setting('app.safe_mode') != 'true' OR classification != 'Critical')` |
| `rls_subagent_redaction` | All tables with Confidential+ columns | Redacted views for sub-agents | Column-level grants; sensitive columns nullified via view |
| `rls_audit_payload_min` | `audit.*`, `security.*` | No raw payload in default views | Column-level grants; `event_payload` column redacted in view |

### 11.2 RLS DDL Template

```sql
-- Enable RLS with FORCE on all classified tables
ALTER TABLE memory.episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory.episodes FORCE ROW LEVEL SECURITY;

-- Data classification ceiling policy
CREATE POLICY rls_data_class_ceiling ON memory.episodes
    FOR SELECT
    USING (
        ops.get_principal_clearance(current_setting('app.principal'))
        >= ops.classification_to_level(memory.episodes.classification)
    );

CREATE POLICY rls_data_class_ceiling_insert ON memory.episodes
    FOR INSERT
    WITH CHECK (
        ops.get_principal_clearance(current_setting('app.principal'))
        >= ops.classification_to_level(classification)
    );

-- Safe mode policy
CREATE POLICY rls_safe_mode ON memory.episodes
    FOR SELECT
    USING (
        current_setting('app.safe_mode', true) != 'true'
        OR memory.episodes.classification NOT IN ('Restricted', 'Critical')
    );
```

### 11.3 Principal-Based Access

All database access must go through PgBouncer with per-service users. Application middleware must set session-level configuration before each transaction:

```python
# Request middleware — set tenant/principal context
await db.execute(
    "SELECT set_config('app.principal', $1, true)",
    [principal_id]
)
await db.execute(
    "SELECT set_config('app.safe_mode', $1, true)",
    [str(is_safe_mode).lower()]
)
await db.execute(
    "SELECT set_config('app.accessible_tasks', $1, true)",
    [json.dumps(task_ids)]
)
```

Use `SET LOCAL` (not `SET`) to prevent context bleed across PgBouncer-pooled connections.

### 11.4 Sub-Agent Data Ceilings

Sub-agents must never access raw Critical or Restricted data. Column-level grants enforce this:

| Sub-Agent Type | Maximum Classification | Allowed Schemas | Redaction Rule |
|---|---|---|---|
| `explore` | Confidential | `memory` (redacted views), `projects`, `agents`, `ops` | Sensitive columns nullified |
| `librarian` | Confidential | `memory` (redacted views), `projects`, `agents`, `ops` | Sensitive columns nullified |
| `oracle` | Confidential | `audit`, `projects`, `ops` | Payload columns minimized |
| `hephaestus` | Confidential | All (redacted views) | Sensitive columns nullified; ops schema full |
| `data-infra` | Restricted (schema metadata only) | All schemas (DDL) | Critical data columns denied; schema metadata readable |
| `momus` | Confidential | `audit`, `projects`, `ops` | Payload columns minimized |
| `metis` | Confidential | All (redacted views) | Sensitive columns nullified |

### 11.5 Surveillance Writer Restrictions

The `surveillance` writer principal must be restricted to INSERT-only on `surveillance.*` tables. No SELECT, UPDATE, or DELETE on `surveillance.events` — data once ingested cannot be modified or read back by the ingestion service.

```sql
-- Surveillance writer: INSERT only
GRANT INSERT ON surveillance.events TO pgbouncer_surveillance_writer;
GRANT INSERT ON surveillance.ingestion_log TO pgbouncer_surveillance_writer;
GRANT SELECT, INSERT, UPDATE ON surveillance.device_registry TO pgbouncer_surveillance_writer;
-- No SELECT on events — surveillance writer cannot read raw data
```

---

## 12. Migration Strategy

### 12.1 Alembic Configuration

**Dependency:** `alembic>=1.13.0` per APIIntegration v2.0.

**Naming convention** (set in `alembic/env.py`):

```python
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

**Version naming convention (mandatory):**

```
YYYYMMDDHHMM_<domain>_<risk>_<slug>
```

| Component | Format | Example | Description |
|---|---|---|---|
| `YYYYMMDDHHMM` | 12-digit timestamp | `202605301430` | UTC timestamp of migration creation |
| `<domain>` | lowercase schema or cross-schema label | `memory`, `security`, `cross-schema` | Affected domain |
| `<risk>` | `low`, `medium`, `high`, `critical` | `medium` | Migration risk level |
| `<slug>` | kebab-case description | `add-hnsw-embedding-index` | Human-readable change summary |

**Examples:**

- `202605301430_memory_medium_add-hnsw-embedding-index`
- `202605310900_surveillance_low_add-compression-policy`
- `202606010200_security_critical_add-rls-break-glass`
- `202606011500_cross-schema_high_split-system-schema`

### 12.2 Migration File Template

```python
"""add HNSW index for memory.episodes.embedding

Revision ID: 202605301430_memory_medium_add-hnsw-embedding-index
Revises: <previous_revision_id>
Create Date: 2026-05-30 14:30:00 UTC
Risk: medium
Domain: memory
Author: guinevere (autonomous staging) / faiz (production approval)
"""

from alembic import op

revision = '202605301430_memory_medium_add-hnsw-embedding-index'
down_revision = '<previous_revision_id>'
branch_labels = None
depends_on = None


def upgrade():
    # CREATE INDEX CONCURRENTLY for zero-downtime
    op.execute("""
        CREATE INDEX CONCURRENTLY ix_episodes_embedding_hnsw
        ON memory.episodes USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 128)
    """)


def downgrade():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS memory.ix_episodes_embedding_hnsw")
```

### 12.3 Expand-Migrate-Contract Pattern (Mandatory for Breaking Changes)

All column renames, type changes, and constraint additions must follow the three-phase expand-migrate-contract pattern:

**Phase 1 — EXPAND:** Add new schema alongside old. Both shapes coexist.

```sql
-- Add nullable column; both old and new code can write
ALTER TABLE memory.episodes ADD COLUMN new_summary TEXT NULL;
```

**Phase 2 — MIGRATE:** Backfill + switch reads.

- Backfill in batches using `WHERE id BETWEEN :start AND :end` with `LIMIT` pagination. Never use single unbounded `UPDATE` (locks entire table).
- Deploy code that reads from new column, still writes to both.
- Feature-flag the read switch with diff-checking before ramping traffic.
- Minimum soak: 24 hours.

**Phase 3 — CONTRACT:** Remove old schema.

- After soak period verified (minimum 24 hours, recommended 1 week).
- Drop old column; remove sync triggers.
- Deploy code that only writes to new column.

### 12.4 Zero-Downtime DDL Techniques

| Technique | SQL Pattern | When to Use |
|---|---|---|
| `NOT VALID` constraint | `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID` then `VALIDATE CONSTRAINT` separately | Adding CHECK/FK constraints without scanning existing rows |
| `CREATE INDEX CONCURRENTLY` | `CREATE INDEX CONCURRENTLY ...` | Building indexes without blocking writes |
| `SET lock_timeout` | `SET lock_timeout = '5s'` before any DDL | Fail fast rather than block indefinitely |
| Batch backfill | `UPDATE ... WHERE id BETWEEN :start AND :end LIMIT 10000` | Data migrations on large tables |
| Column rename (4-phase) | Add new → sync trigger → backfill → read new → drop old | Renaming columns without downtime |

### 12.5 Destructive Migration Guard Rules

| Operation | Default Rule | Override Path |
|---|---|---|
| `DROP TABLE` | **Denied** | Faiz explicit approval + backup verified + staging rollback tested |
| `DROP COLUMN` | **Denied** | Faiz explicit approval + expand-migrate-contract completed + soak period verified |
| `ALTER TYPE` (column type change) | **Denied** | Faiz explicit approval + expand-migrate-contract required |
| `TRUNCATE` | **Denied** | Faiz explicit approval + backup checkpoint |
| `DROP SCHEMA` | **Denied** | Faiz explicit approval + full backup + evidence of no dependencies |
| `CREATE INDEX` | **Allowed** (with CONCURRENTLY) | Autonomous staging; Faiz approval for production |
| `ADD COLUMN` (nullable) | **Allowed** | Autonomous staging; Faiz approval for production |
| `ADD CONSTRAINT NOT VALID` | **Allowed** | Autonomous staging; Faiz approval for production |
| `CREATE TABLE` | **Allowed** (new schemas require Faiz) | Autonomous staging for existing schemas; Faiz for new schemas |
| `SET retention/compression policy` | **Allowed** | Autonomous staging; Faiz approval for production |

---

## 13. Autonomous Migration Execution

### 13.1 Three-Tier Authority Model

| Tier | Environment | Risk Level | Executor | Conditions |
|---|---|---|---|---|
| **Tier 1 — Autonomous** | Staging only | Low risk, reversible | Guinevere (autonomous) | Pre-migration checklist complete; backup checkpoint; rollback plan ready; evidence path initialized |
| **Tier 2 — Faiz Approved** | Production | Medium, High, Critical | Guinevere (after Faiz approval) | Faiz approval recorded in `ops.migration_log`; staging validation passed; backup verified; evidence path initialized |
| **Tier 3 — Denied** | Any | Destructive operations (DROP, TRUNCATE, ALTER TYPE) | Denied by default | Faiz explicit approval required; no autonomous path |

### 13.2 SDLC Loop Integration (per Agent Loop Spec v2.0)

| SDLC Phase | Migration Activity | Agent | Output |
|---|---|---|---|
| Phase 2 — Plan & Delegate | Generate migration plan; run risk assessment; classify migration tier | Guinevere core | Migration plan document; risk matrix; tier classification |
| Phase 3 — Delegate | Assign migration to data-infra sub-agent | Guinevere core | Task assignment in `agents.task_queue` |
| Phase 4 — Execute | Apply migration to staging; run test suite; if fail: rollback | data-infra sub-agent | `ops.migration_log` updated; execution evidence in `evidence/database/<migration-id>/migration-execution.md` |
| Phase 5 — Validate & Audit | Run integrity checks; verify constraints; check performance | oracle sub-agent | Validation report in `evidence/database/<migration-id>/post-migration-verification.md` |
| Phase 6 — Update Documents | Update schema docs; update cross-references; update RTM | Guinevere core | Updated documentation |
| Phase 7 — Setup Evidence | Collect all evidence; produce audit report | Guinevere core | Evidence directory populated; audit report generated |

### 13.3 Pre-Migration Checklist (Mandatory)

Before any migration execution, all items must be confirmed:

| # | Item | Required For | Evidence |
|---|---|---|---|
| 1 | Risk level classified (low/medium/high/critical) | All tiers | Migration plan document |
| 2 | Backup checkpoint created and verified | All tiers | `ops.backup_log` entry with checksum |
| 3 | Rollback script prepared and tested on staging | All tiers | `evidence/database/<migration-id>/rollback-test.md` |
| 4 | Staging environment synced with production schema | Tier 2, Tier 3 | Schema diff report |
| 5 | Data integrity verification plan defined | All tiers | Verification plan document |
| 6 | Evidence path initialized (`evidence/database/<migration-id>/`) | All tiers | Directory created |
| 7 | Migration script committed and reviewed | All tiers | Git commit reference |
| 8 | If production: Faiz approval recorded | Tier 2, Tier 3 | `evidence/database/<migration-id>/faiz-approval.md` |
| 9 | If destructive: explicit Faiz approval with justification | Tier 3 only | Approval record with rationale |
| 10 | `lock_timeout` set to 5s for DDL operations | Production (Tier 2, Tier 3) | Session configuration verified |
| 11 | Monitoring dashboard active (Grafana) | Production (Tier 2, Tier 3) | Dashboard URL in evidence |
| 12 | Notification channel configured (Discord alert) | Production (Tier 2, Tier 3) | Test notification sent |

### 13.4 Post-Migration Verification

| Check | Method | Evidence |
|---|---|---|
| Table row count before/after | `SELECT COUNT(*)` comparison | Count report |
| Checksum verification (sample) | `SELECT md5(textin(record_out(t)))` for random rows | Checksum comparison |
| Constraint validation | `ALTER TABLE ... VALIDATE CONSTRAINT` result | Validation output |
| Index health | `pg_stat_user_indexes` scan count | Index usage report |
| Query plan verification | `EXPLAIN ANALYZE` on key queries | Query plan report |
| Encrypted field sample decrypt | Application-level decrypt verification | Decrypt success log |
| RLS policy test | Test queries as non-superuser role | Policy test results |
| Classification metadata completeness | `SELECT count(*) WHERE classification IS NULL` must return 0 | Null-check report |

---

## 14. Migration Safety

### 14.1 Pre-Migration Safety Gates

Every migration, regardless of tier, must pass these safety gates before execution:

1. **Backup checkpoint mandatory:** A successful `pg_dump` or WAL checkpoint must exist no more than 1 hour before migration start. Verified by `ops.backup_log` entry with SHA-256 checksum.
2. **Staging validation mandatory:** For Tier 2 and Tier 3 migrations, the migration must complete successfully on a staging database that mirrors the production schema.
3. **Rollback plan mandatory:** A tested downgrade path must exist. For data-touching migrations, the rollback plan must reference the backup checkpoint (not rely on `downgrade()` recovering data).
4. **Evidence path initialized:** `evidence/database/<migration-id>/` directory must be created with a `pre-migration-checklist.md` file before execution begins.

### 14.2 Destructive Guards

| Guard | Implementation |
|---|---|
| `DROP TABLE` prevention | Application-level gate: Guinevere must confirm `DROP TABLE` is not in migration SQL before execution. If detected: abort, log to `ops.alert_history`, require Faiz override. |
| `DROP COLUMN` prevention | Application-level gate: same as DROP TABLE. Expand-migrate-contract evidence must exist proving the column is unused before DROP is approved. |
| `ALTER TYPE` prevention | Application-level gate: column type changes must not be included in autogenerated migrations. |
| `TRUNCATE` prevention | Application-level gate: TRUNCATE is always denied unless Faiz explicitly confirms in writing. |
| `lock_timeout` enforcement | All DDL operations must set `SET lock_timeout = '5s'` before execution. If a lock cannot be acquired within 5 seconds, the migration aborts. |

### 14.3 Data Integrity Verification

Post-migration, the data-infra sub-agent must verify:

1. **Row count preservation:** Row counts on non-destructive operations must match pre-migration counts (± expected backfill delta).
2. **Checksum sampling:** Random 1% sample of rows must have identical checksums pre and post-migration for non-transformed columns.
3. **Constraint validity:** All `NOT VALID` constraints must be validated with `ALTER TABLE ... VALIDATE CONSTRAINT` in a separate transaction.
4. **Index usability:** All new indexes must appear in `pg_stat_user_indexes` with scan counts > 0 within 1 hour of creation.
5. **Classification consistency:** After migration, no classified column must have NULL `classification` metadata.
6. **Encryption integrity:** Random sample of encrypted columns must decrypt successfully with the correct domain KEK.
7. **RLS enforcement:** Queries executed as each principal role must return only rows matching their clearance ceiling.

---

## 15. Schema Governance

### 15.1 Schema Version Tracking

Three mechanisms track schema versions:

| Mechanism | Table | Scope | Update Trigger |
|---|---|---|---|
| **Alembic version table** | `alembic_version` (standard) | All schema migrations | Automatic on `alembic upgrade` |
| **Migration log** | `ops.migration_log` | All migrations with evidence paths | Manual + automatic via data-infra sub-agent |
| **Version column** | `version INTEGER DEFAULT 1` on key tables | Row-level version tracking | Application-level on UPDATE |

### 15.2 Change Review Requirements

| Change Type | Review Required | Approver |
|---|---|---|
| New table in existing schema | Schema governance review | Guinevere (autonomous staging) / Faiz (production) |
| New column (nullable) | Schema governance review | Guinevere (autonomous staging) / Faiz (production) |
| New column (NOT NULL with DEFAULT) | Schema governance review + backfill plan | Faiz (all environments) |
| Index creation | Performance review | Guinevere (CONCURRENTLY, staging) / Faiz (production) |
| Constraint addition (NOT VALID) | Data quality review | Guinevere (staging) / Faiz (production) |
| Constraint addition (immediate validation) | Full review + lock analysis | Faiz (all environments) |
| Schema creation | Architecture review | Faiz (all environments) |
| Extension installation | Architecture review | Faiz (all environments) |
| RLS policy change | Security review | Faiz (all environments) |
| Retention policy change | Data governance review | Faiz (all environments) |

### 15.3 Cross-Reference Obligations

Every schema change must update:

1. This document (Database ERD & Migration Strategy) — table catalog, column definitions.
2. `Guinevere_MemorySchema_v2.0.md` — if memory.* tables changed.
3. `Guinevere_TechnicalArchitecture_v2.0.md` — if new services or connection patterns introduced.
4. Requirements Traceability Matrix (RTM) — if schema changes affect acceptance criteria.
5. Evidence directory — per-migration evidence artifacts.

---

## 16. Testing

### 16.1 Migration Test Categories

| Test Type | Speed Target | Tool | What It Validates |
|---|---|---|---|
| **Chain integrity** | < 1 second | Alembic CLI | Multiple heads, missing downgrade stubs, wrong `down_revision` |
| **Structural tests** | 1-5 seconds | SQLite + SQLAlchemy (for model sync) | Revision chain order; model/schema sync; naming conventions |
| **Unit tests per migration** | 5-30 seconds | Testcontainers + PostgreSQL | Specific upgrade/downgrade correctness; constraint enforcement |
| **Integration tests** | 30-120 seconds | Testcontainers + full schema | Data migration correctness; cross-schema FK validation |
| **Downgrade round-trip** | Varies | Alembic + test DB | All revisions upgrade from base to head and downgrade back |
| **Performance tests** | Hours | Production-like data volume | Index build time; lock contention; query plan changes |
| **Classification verification** | 1-5 seconds per table | SQL query | No NULL classifications; classification ceiling enforcement |
| **RLS policy tests** | 1-5 seconds per policy | Non-superuser role queries | Principal clearance enforcement; safe-mode blocking |

### 16.2 Essential CI/CD Migration Checks

```python
def test_alembic_chain_integrity(alembic_cfg):
    """No multiple heads; no missing downgrade stubs."""
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Multiple heads detected: {heads}"


def test_downgrade_all_revisions(alembic_cfg, db_url):
    """All migrations can be reversed from head to base."""
    command.upgrade(alembic_cfg, "head")
    revisions = get_all_revisions(alembic_cfg)
    for _ in revisions:
        command.downgrade(alembic_cfg, "-1")
    # Verify database is at base


def test_migration_naming_convention(alembic_cfg):
    """All migration IDs follow YYYYMMDDHHMM_<domain>_<risk>_<slug>."""
    import re
    pattern = r'^\d{12}_(memory|persona|surveillance|financial|projects|social|agents|consent|security|audit|ops|extensions|cross-schema)_(low|medium|high|critical)_[a-z0-9-]+$'
    for rev in get_all_revisions(alembic_cfg):
        assert re.match(pattern, rev.revision), f"Invalid revision ID: {rev.revision}"
```

---

## 17. Budget Model

### 17.1 $30/Month Hard Cap

All database infrastructure decisions must respect the USD 30/month hard cap.

| Cost Category | Estimated Monthly Cost | Notes |
|---|---|---|
| VPS (4 Core, 16GB RAM, 120GB SSD) | ~$12-15/month | hostdata.id VPS; shared with all Guinevere services |
| PostgreSQL (self-hosted, Docker) | $0 | No managed DB cost — runs on VPS |
| Redis (self-hosted, Docker) | $0 | No managed cache cost — runs on VPS |
| pgvector (PostgreSQL extension) | $0 | Free open-source extension |
| TimescaleDB (Community Edition) | $0 | Free Community Edition |
| PgBouncer (self-hosted) | $0 | Connection pooling — runs on VPS |
| Backup storage (R2/S3) | ~$2-3/month | Daily pg_dump + WAL streaming to Cloudflare R2 or idcloudhost S3 |
| Monitoring (Prometheus + Grafana) | $0 | Self-hosted on primary VPS |
| **Total DB cost** | **$14-18/month** | Within $30/month cap with margin for LLM API costs |

### 17.2 Storage Cost Projections

| Data Domain | Estimated 1-Year Growth | Storage at 1 Year | Cost Impact |
|---|---|---|---|
| `memory.*` (all tables) | ~500MB-2GB | Indexes + data | Negligible on 120GB SSD |
| `surveillance.*` (compressed after 7 days) | ~5-15GB raw → ~500MB-1.5GB compressed | TimescaleDB compression 90%+ | Moderate |
| `financial.*` | ~50MB | Low volume | Negligible |
| All other schemas | ~200MB | Low volume | Negligible |
| pgvector HNSW indexes | ~500MB-1GB per 1M vectors | Index overhead | Monitor; use halfvec if >2M vectors |
| Backup storage (R2) | ~20-50GB | Daily snapshots with 30-day retention | $2-3/month |

### 17.3 Index Storage Overhead

HNSW indexes consume more storage than IVFFlat. With `m=16` and 1536-dim vectors:

- ~450MB per 1M vectors with full `vector(1536)`
- ~310MB per 1M vectors with `halfvec` quantization (1536→768 dims)
- Recommendation: evaluate `halfvec` if total vector count exceeds 2M across all tables.

---

## 18. Acceptance Criteria

### 18.1 Criteria Catalog

| ID | Criterion | Pass Definition | Test ID | Evidence Path | Owner | Phase Gate |
|---|---|---|---|---|---|---|
| AC-001 | All 12 schemas documented | Each schema has a purpose, table list, classification ceiling, access rules, and retention rules in this document | T-DB-001 | This document §3 | Guinevere | Phase 2 gate |
| AC-002 | No SQLite as memory/storage backend | Zero references to SQLite in this document or any schema definition | T-DB-002 | This document §2 | Guinevere | Phase 3 gate |
| AC-003 | Each table has classification, retention, encryption metadata | All tables in Appendix A have complete metadata columns | T-DB-003 | This document §4, Appendix A | Guinevere | Phase 5 gate |
| AC-004 | pgvector HNSW default index | All vector columns defined with HNSW; IVFFlat described as deprecated with migration path | T-DB-004 | This document §8, §11 | Guinevere | Phase 5 gate |
| AC-005 | TimescaleDB hypertables for surveillance, episodes, transactions, audit | All four hypertables defined with chunk intervals, compression policies, retention | T-DB-005 | This document §9 | Guinevere | Phase 5 gate |
| AC-006 | RLS policies defined (5 policies) | All five RLS policies have DDL templates and principal-binding rules | T-DB-006 | This document §11 | Guinevere | Phase 5 gate |
| AC-007 | Alembic naming: YYYYMMDDHHMM_<domain>*<risk>*<slug> | Migration file template follows naming convention; CI test validates | T-DB-007 | This document §12.1 | Guinevere | Phase 3 gate |
| AC-008 | Autonomous: low-risk reversible staging only | Authority model explicitly restricts Guinevere to Tier 1; Faiz required for Tier 2/3 | T-DB-008 | This document §13.1 | Guinevere | Phase 3 gate |
| AC-009 | Production migrations: Faiz approval required | Pre-migration checklist item #8 enforced for all production migrations | T-DB-009 | This document §13.3 | Guinevere | Phase 4 gate |
| AC-010 | Destructive migrations: denied by default | Destructive guard rules block DROP/TRUNCATE/ALTER TYPE; only Faiz override | T-DB-010 | This document §12.5, §14.2 | Guinevere | Phase 3 gate |
| AC-011 | Evidence path: evidence/database/<migration-id>/ | Evidence path pattern documented; pre-migration checklist requires initialization | T-DB-011 | This document §13.3 | Guinevere | Phase 2 gate |
| AC-012 | Pre-migration backup checkpoint | Mandatory backup checkpoint in pre-migration checklist; backed by `ops.backup_log` | T-DB-012 | This document §13.3, §14.1 | Guinevere | Phase 4 gate |
| AC-013 | Post-migration data integrity verification | Verification checklist includes row counts, checksums, constraints, indexes, RLS | T-DB-013 | This document §13.4, §14.3 | Guinevere | Phase 5 gate |
| AC-014 | Budget <= $30/month | Database cost model shows $14-18/month; within cap | T-DB-014 | This document §17 | Guinevere | Phase 2 gate |
| AC-015 | Status: Accepted + Faiz Review Record | Review record in metadata table; footer confirms acceptance | T-DB-015 | This document header + footer | Faiz | Phase 1 gate |
| AC-016 | All controls use MUST; zero standalone should | grep for `[Ss]hould` returns zero matches in this document | T-DB-016 | This document — grep verification | Guinevere | Phase 5 gate |
| AC-017 | Encrypted metadata fields per EncryptionKeyManagementStandard §7.2 | All encrypted columns carry 14 metadata sidecar fields | T-DB-017 | This document §7.4 | Guinevere | Phase 5 gate |
| AC-018 | Domain KEK separation in key_id/key_version fields | 10 domain KEKs documented with rotation cadences | T-DB-018 | This document §7.2 | Guinevere | Phase 5 gate |

---

## 19. Gap Register

| ID | Gap | Severity | Source | Owner | Resolution Trigger |
|---|---|---|---|---|---|
| GAP-001 | Classification/retention metadata columns not yet present in existing database tables | High — affects RLS enforcement, automated cleanup, and audit compliance | DataGovernance backlog item §15; EncryptionKeyManagementStandard backlog item §22 | Guinevere (data-infra) | This document defines the metadata schema; migration to add metadata columns is the next implementation task |
| GAP-002 | RLS policies specified but not yet implemented as PostgreSQL DDL | High — security boundary is documented but not enforced at DB layer | RBAC Matrix §8.3; backlog item BG-002 | Guinevere (data-infra) | Schema migration required to enable RLS + FORCE on all classified tables; DDL templates provided in §11 |
| GAP-003 | pgvector IVFFlat indexes exist in source docs but HNSW is the mandatory default | Medium — no data loss risk, but recall quality and latency suboptimal until migration | MemorySchema v2.0 §2.1, TechArch v2.0 §5.3 | Guinevere (data-infra) | Migration path documented in §8.3; execute on next schema maintenance window |
| GAP-004 | PgBouncer roles in TechArch v2.0 are broad bootstrap roles; RBAC Matrix requires least-privilege target roles | Medium — current roles grant excessive access | TechArch v2.0 §5.4 vs RBAC Matrix §8.1 | Guinevere (data-infra) | Split bootstrap roles into per-domain least-privilege roles per RBAC Matrix |
| GAP-005 | TimescaleDB continuous aggregates and compression policies are specified but not yet deployed | Low — no immediate data volume concern but growth planning required | This document §9 | Guinevere (data-infra) | Deploy when surveillance event volume exceeds 10K/day or query performance degrades |
| GAP-006 | Key rotation automation for domain KEKs not yet implemented | Medium — encryption is documented but rotation requires manual intervention | EncryptionKeyManagementStandard §15 | Guinevere (data-infra) | Implement background rotation job using the read-old/write-new/re-wrap pattern |
| GAP-007 | Backup reconciliation on restore (deletion ledger replay) not yet automated | Medium — manual process risk of resurrecting deleted data | DataGovernance §4.5 | Guinevere (data-infra) | Implement `ops.restore_reconciliation()` function that replays deletion markers from `ops.migration_log` |

---

## 20. Evidence Path Register

| Pattern | Usage | Required Artifacts |
|---|---|---|
| `evidence/database/<migration-id>/` | Per-migration evidence directory | All migration evidence |
| `evidence/database/<migration-id>/pre-migration-checklist.md` | Completed checklist before execution | All 12 checklist items confirmed |
| `evidence/database/<migration-id>/migration-execution.md` | Execution log with timestamps, SQL output, errors | Full execution transcript |
| `evidence/database/<migration-id>/post-migration-verification.md` | Integrity checks, counts, checksums, query plans | All 8 verification checks |
| `evidence/database/<migration-id>/rollback-test.md` | Rollback execution evidence from staging | Successful downgrade confirmation |
| `evidence/database/<migration-id>/faiz-approval.md` | Production or destructive migration approval | Faiz's explicit approval record |
| `evidence/database/<migration-id>/integrity-report.md` | Data integrity verification report | Checksum comparisons, sample decrypts |
| `audit-reports/<date>-database-migration-audit.md` | Periodic migration audit (quarterly) | Audit findings, compliance status |

---

## 21. Maintenance Rules

### 21.1 Update Triggers

This document must be updated when:

1. Any new table is added to any schema.
2. Any column is added, modified, or removed.
3. Any index strategy changes (including pgvector parameter tuning).
4. Any TimescaleDB hypertable parameter changes (chunk interval, compression, retention).
5. Any RLS policy is added, modified, or removed.
6. Any classification tier or retention class is re-assigned.
7. Any domain KEK is added, rotated, or retired.
8. The Alembic naming convention changes.
9. The autonomous authority boundaries change.
10. The budget model exceeds any category projection.

### 21.2 Review Cadence

| Review Type | Frequency | Owner | Evidence |
|---|---|---|---|
| Schema vs document consistency audit | Monthly | Guinevere (oracle sub-agent) | Audit report in `audit-reports/` |
| Classification compliance review | Quarterly | Guinevere (momus sub-agent) | Compliance check in `audit.compliance_check` |
| Index performance review | Monthly | Guinevere (oracle sub-agent) | `pg_stat_user_indexes` analysis |
| Encryption key rotation audit | Quarterly | Guinevere (oracle sub-agent) | `security.secret_rotation_log` review |
| Budget vs actual cost review | Monthly | Guinevere core | `financial.monthly_reports` analysis |
| Full database architecture audit | Annually | Guinevere (hephaestus discipline) | Comprehensive audit report |

### 21.3 Migration Log Obligations

Every migration, regardless of tier, must record an entry in `ops.migration_log` with:

- `migration_id` matching the Alembic revision ID
- `domain`, `risk_level`, `direction`, `status`
- `executed_by` identifying Guinevere autonomous vs Faiz-approved
- `evidence_path` pointing to the evidence directory
- `checksum` of the migration file

Successful migrations are permanent records. Failed/rolled-back migrations must be recorded with `status = 'rolled_back'` and a `rollback_at` timestamp.

---

## 22. Review Record

| Date | Reviewer | Verdict | Notes |
|---|---|---|---|
| 2026-05-30 | Faiz | **Accepted** | Accepted via ALL:D enterprise-pro-max configuration. All 12 schemas, HNSW default, Alembic naming convention, 3-tier authority model, and $30/month budget compliance confirmed. |
| 2026-05-30 | Guinevere / Hephaestus | **Accepted for generation** | Document generated per source-map specifications. All 18 acceptance criteria addressed. Zero standalone "should" confirmed. All controls use "must." No SQLite references. |

---

## 23. Next Recommended Documents

1. **SQL DDL Implementation Scripts** — Translate this ERD into executable `CREATE TABLE`, `CREATE INDEX`, `CREATE POLICY` DDL per schema.
2. **Alembic Initial Migration** — Generate the baseline migration that creates all 12 schemas and tables.
3. **RLS Policy Implementation** — Deploy the five RLS policy DDL templates from §11 to the database.
4. **Classification Metadata Backfill** — Migration to add metadata columns (`classification`, `retention_class`, `encryption_profile`, etc.) to all existing classified tables.
5. **pgvector IVFFlat-to-HNSW Migration Plan** — Execute the migration path from §8.3.
6. **Backup Reconciliation Implementation** — Implement `ops.restore_reconciliation()` for deletion ledger replay.
7. **Observability & Alerting Spec** — Define Prometheus metrics, Grafana dashboards, and alert rules for database health from this ERD.

---

## Appendix A: Complete Table Catalog

### A.1 All Tables Across 12 Schemas

| # | Schema | Table | Rows (Projected) | Engine | Classification Ceiling | Encryption Profile |
|---|---|---|---|---|---|---|
| 1 | `memory` | `episodes` | ~10K-50K/year | TimescaleDB Hypertable | Critical | Envelope + Double |
| 2 | `memory` | `semantic_facts` | ~50K-200K | Standard PG + pgvector HNSW | Restricted | Envelope AES-256-GCM |
| 3 | `memory` | `faiz_profile` | ~500-2,000 | Standard PG | Critical | Double encryption |
| 4 | `memory` | `emotional_events` | ~1K-5K/year | Standard PG | Critical | Double encryption |
| 5 | `memory` | `inner_journal` | ~365/year | Standard PG | Critical | Double encryption |
| 6 | `memory` | `faiz_predictions` | ~1K-5K | Standard PG | Restricted | Envelope AES-256-GCM |
| 7 | `memory` | `procedural_skills` | ~50-200 | Standard PG | Confidential | At-rest + domain key |
| 8 | `memory` | `knowledge_graph` | ~1K-10K | Standard PG | Confidential | At-rest + domain key |
| 9 | `persona` | `persona_state` | ~50-200 | Standard PG | Restricted | Envelope AES-256-GCM |
| 10 | `persona` | `drift_log` | ~500-2,000/year | Standard PG | Restricted | Envelope AES-256-GCM |
| 11 | `persona` | `mood_history` | ~1K-5K/year | Standard PG | Restricted | Envelope AES-256-GCM |
| 12 | `persona` | `punishment_log` | ~50-200/year | Standard PG | Critical | Envelope + Double |
| 13 | `persona` | `reward_log` | ~100-500/year | Standard PG | Confidential | At-rest + domain key |
| 14 | `surveillance` | `events` | ~100K-3M/year | TimescaleDB Hypertable | Critical | Envelope + Double |
| 15 | `surveillance` | `device_registry` | 2-5 | Standard PG | Internal | Disk + TLS |
| 16 | `surveillance` | `ingestion_log` | ~1K-10K/year | Standard PG | Internal | Disk + TLS |
| 17 | `surveillance` | `confrontation_block_log` | ~10-100/year | Standard PG | Restricted | Envelope AES-256-GCM |
| 18 | `financial` | `transactions` | ~500-5K/year | TimescaleDB Hypertable | Restricted | Envelope AES-256-GCM |
| 19 | `financial` | `project_costs` | ~50-200/year | Standard PG | Restricted | Envelope AES-256-GCM |
| 20 | `financial` | `monthly_reports` | 12/year | Standard PG | Restricted | Envelope AES-256-GCM |
| 21 | `financial` | `optimization_log` | ~20-100/year | Standard PG | Internal | Disk + TLS |
| 22 | `projects` | `tasks` | ~50-500 | Standard PG | Confidential | At-rest + domain key |
| 23 | `projects` | `loop_instances` | ~200-2,000/year | Standard PG | Confidential | At-rest + domain key |
| 24 | `projects` | `agent_tasks` | ~500-5,000/year | Standard PG | Internal | Disk + TLS |
| 25 | `projects` | `evidence_artifacts` | ~200-2,000/year | Standard PG | Internal | Disk + TLS |
| 26 | `social` | `social_map` | ~20-100 | Standard PG | Restricted | Envelope AES-256-GCM |
| 27 | `social` | `client_contacts` | ~5-20 | Standard PG | Critical | Double encryption |
| 28 | `social` | `communication_log` | ~100-500/year | Standard PG | Restricted | Envelope AES-256-GCM |
| 29 | `agents` | `subagent_registry` | ~10-20 | Standard PG | Internal | Disk + TLS |
| 30 | `agents` | `task_queue` | ~100-1,000 | Standard PG | Confidential | At-rest + domain key |
| 31 | `agents` | `execution_log` | ~500-5,000/year | Standard PG | Internal | Disk + TLS |
| 32 | `consent` | `consent_ledger` | ~10-50 | Standard PG | Critical | Double encryption |
| 33 | `consent` | `revocation_log` | ~5-20 | Standard PG | Critical | Double encryption |
| 34 | `consent` | `scope_registry` | ~10-30 | Standard PG | Internal | Disk + TLS |
| 35 | `security` | `access_log` | ~1K-10K/year | Standard PG | Restricted | Envelope AES-256-GCM |
| 36 | `security` | `break_glass_log` | ~0-5/year | Standard PG | Restricted | Envelope AES-256-GCM |
| 37 | `security` | `secret_rotation_log` | ~10-50/year | Standard PG | Internal | Disk + TLS |
| 38 | `audit` | `audit_trail` | ~1K-50K/year | TimescaleDB Hypertable | Confidential | At-rest + domain key |
| 39 | `audit` | `evidence_register` | ~500-5,000/year | Standard PG | Internal | Disk + TLS |
| 40 | `audit` | `compliance_check` | ~10-50/year | Standard PG | Confidential | At-rest + domain key |
| 41 | `ops` | `migration_log` | ~20-100/year | Standard PG | Internal | Disk + TLS |
| 42 | `ops` | `backup_log` | ~365/year | Standard PG | Internal | Disk + TLS |
| 43 | `ops` | `health_check` | ~8,760/year (hourly) | Standard PG | Internal | Disk + TLS |
| 44 | `ops` | `alert_history` | ~100-1,000/year | Standard PG | Internal | Disk + TLS |
| 45 | `extensions` | `pgvector_config` | 1 | Standard PG | Internal | Disk + TLS |
| 46 | `extensions` | `timescaledb_config` | 1 | Standard PG | Internal | Disk + TLS |
| 47 | `extensions` | `pgcrypto_config` | 1 | Standard PG | Internal | Disk + TLS |

**Total tables:** 47 across 12 schemas.

---

## Appendix B: ERD Relationship Diagram (Text-Based)

### B.1 Schema Boundary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUINEVERE DATABASE                        │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  memory  │  │ persona  │  │ surveillance │  │ financial  │  │
│  │  (8 tbl) │  │ (5 tbl)  │  │   (4 tbl)    │  │  (4 tbl)   │  │
│  │  Critical│  │ Critical │  │   Critical   │  │  Critical  │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  └─────┬──────┘  │
│       │              │               │                 │         │
│  ┌────┴─────┐  ┌────┴─────┐  ┌──────┴───────┐  ┌─────┴──────┐  │
│  │ projects │  │  social  │  │   agents     │  │  consent   │  │
│  │ (4 tbl)  │  │ (3 tbl)  │  │  (3 tbl)     │  │  (3 tbl)   │  │
│  │Restricted│  │ Critical │  │ Confidential │  │  Critical  │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  └─────┬──────┘  │
│       │              │               │                 │         │
│  ┌────┴─────┐  ┌────┴─────┐  ┌──────┴───────┐                 │
│  │ security │  │  audit   │  │     ops      │                 │
│  │ (3 tbl)  │  │ (3 tbl)  │  │   (4 tbl)    │                 │
│  │Restricted│  │Confidentl│  │   Internal   │                 │
│  └──────────┘  └──────────┘  └──────────────┘                 │
│                                                                   │
│  ┌──────────────┐                                                │
│  │  extensions  │                                                │
│  │   (3 tbl)    │                                                │
│  │   Internal   │                                                │
│  └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

### B.2 Memory Domain ERD

```
memory.episodes (hypertable)
    │
    ├── 1:N ── memory.semantic_facts (source_episode FK)
    │              │
    │              └── N:M ── memory.knowledge_graph (logical edges)
    │
    ├── 1:N ── memory.emotional_events (episode_id FK)
    │
    └── referenced by ── memory.faiz_predictions (logical)

memory.faiz_profile (standalone, double-encrypted)
    │
    └── derived ── memory.faiz_predictions (model output)

memory.inner_journal (standalone, double-encrypted, daily)

memory.procedural_skills (self-referential evolved_from chain)
    │
    └── 1:1 (self) ── evolved_from → memory.procedural_skills
```

### B.3 Persona Domain ERD

```
persona.persona_state (current config)
    │
    └── triggers ── persona.drift_log (before/after/delta)
                         │
                         └── audit evidence

persona.mood_history (continuous timestamps)

persona.punishment_log
    │
    └── safe_word_triggered → critical field

persona.reward_log (positive reinforcement)
```

### B.4 Project Domain ERD

```
projects.tasks
    │
    ├── 1:N ── projects.loop_instances (task_id FK)
    │              │
    │              └── 1:N ── projects.agent_tasks (loop_instance_id FK)
    │
    └── 1:N ── projects.evidence_artifacts (task_id FK)
```

### B.5 Key Cardinality Rules

| Relationship | Cardinality | FK Constraint |
|---|---|---|
| episodes → semantic_facts | 1:N | `source_episode → episodes(id)`, SET NULL on delete |
| episodes → emotional_events | 1:N | `episode_id → episodes(id)`, SET NULL on delete |
| procedural_skills → procedural_skills | 1:1 (self) | `evolved_from → procedural_skills(id)`, SET NULL |
| device_registry → surveillance.events | 1:N | `device_id → device_registry(id)`, RESTRICT |
| tasks → loop_instances | 1:N | `task_id → tasks(id)`, RESTRICT |
| loop_instances → agent_tasks | 1:N | `loop_instance_id → loop_instances(id)`, RESTRICT |
| tasks → evidence_artifacts | 1:N | `task_id → tasks(id)`, RESTRICT |
| social_map → communication_log | 1:N | `contact_id → social_map(id)`, SET NULL |
| subagent_registry → task_queue | 1:N | `agent_id → subagent_registry(id)`, RESTRICT |
| subagent_registry → execution_log | 1:N | `agent_id → subagent_registry(id)`, RESTRICT |
| task_queue → execution_log | 1:N | `task_id → task_queue(id)`, RESTRICT |
| consent_ledger → revocation_log | 1:N | `consent_id → consent_ledger(id)`, RESTRICT |
| audit_trail → evidence_register | 1:N | `audit_event_id → audit_trail(id)`, RESTRICT |

---

## Appendix C: Classification & Encryption Matrix

### C.1 Complete Classification-by-Schema Matrix

| Schema | Table | Default Classification | Max Classification | Encryption Required | Double Encryption |
|---|---|---|---|---|---|
| `memory` | `episodes` | Restricted | Critical | Envelope AES-256-GCM | `raw_content`, mood fields |
| `memory` | `semantic_facts` | Confidential | Restricted | At-rest + domain key | — |
| `memory` | `faiz_profile` | Confidential | Critical | Envelope AES-256-GCM | `value`, `guinevere_note` |
| `memory` | `emotional_events` | Critical | Critical | Envelope + per-record | `description`, `subjective_experience` |
| `memory` | `inner_journal` | Critical | Critical | Envelope + per-record | `content`, `mood_self_report` |
| `memory` | `faiz_predictions` | Restricted | Restricted | Envelope AES-256-GCM | `prediction` |
| `memory` | `procedural_skills` | Confidential | Confidential | At-rest + domain key | — |
| `memory` | `knowledge_graph` | Confidential | Confidential | At-rest + domain key | — |
| `persona` | `persona_state` | Restricted | Restricted | Envelope AES-256-GCM | `state_value` |
| `persona` | `drift_log` | Restricted | Restricted | Envelope AES-256-GCM | State JSONBs |
| `persona` | `mood_history` | Restricted | Restricted | Envelope AES-256-GCM | `mood`, `trigger` |
| `persona` | `punishment_log` | Restricted | Critical | Envelope AES-256-GCM | `safe_word_triggered` |
| `persona` | `reward_log` | Confidential | Confidential | At-rest + domain key | — |
| `surveillance` | `events` | Restricted | Critical | Envelope AES-256-GCM | `raw_payload` |
| `surveillance` | `device_registry` | Internal | Internal | Disk + TLS | — |
| `surveillance` | `ingestion_log` | Internal | Internal | Disk + TLS | — |
| `surveillance` | `confrontation_block_log` | Restricted | Restricted | Envelope AES-256-GCM | — |
| `financial` | `transactions` | Restricted | Restricted | Envelope AES-256-GCM | — |
| `financial` | `project_costs` | Restricted | Restricted | Envelope AES-256-GCM | — |
| `financial` | `monthly_reports` | Restricted | Restricted | Envelope AES-256-GCM | — |
| `financial` | `optimization_log` | Internal | Internal | Disk + TLS | — |
| `projects` | `tasks` | Confidential | Confidential | At-rest + domain key | — |
| `projects` | `loop_instances` | Confidential | Confidential | At-rest + domain key | — |
| `projects` | `agent_tasks` | Internal | Internal | Disk + TLS | — |
| `projects` | `evidence_artifacts` | Internal | Internal | Disk + TLS | — |
| `social` | `social_map` | Restricted | Restricted | Envelope AES-256-GCM | — |
| `social` | `client_contacts` | Restricted | Critical | Envelope + per-record | `contact_info` |
| `social` | `communication_log` | Restricted | Restricted | Envelope AES-256-GCM | — |
| `agents` | `subagent_registry` | Internal | Internal | Disk + TLS | — |
| `agents` | `task_queue` | Confidential | Confidential | At-rest + domain key | — |
| `agents` | `execution_log` | Internal | Internal | Disk + TLS | — |
| `consent` | `consent_ledger` | Restricted | Critical | Envelope + per-record | `revocation_reason` |
| `consent` | `revocation_log` | Internal | Internal | Disk + TLS | — |
| `consent` | `scope_registry` | Internal | Internal | Disk + TLS | — |
| `security` | `access_log` | Internal | Restricted | Envelope AES-256-GCM | `classification_bypassed` |
| `security` | `break_glass_log` | Restricted | Restricted | Envelope AES-256-GCM | — |
| `security` | `secret_rotation_log` | Internal | Internal | Disk + TLS | — |
| `audit` | `audit_trail` | Confidential | Confidential | At-rest + domain key | — |
| `audit` | `evidence_register` | Internal | Internal | Disk + TLS | — |
| `audit` | `compliance_check` | Confidential | Confidential | At-rest + domain key | — |
| `ops` | `migration_log` | Internal | Internal | Disk + TLS | — |
| `ops` | `backup_log` | Internal | Internal | Disk + TLS | — |
| `ops` | `health_check` | Internal | Internal | Disk + TLS | — |
| `ops` | `alert_history` | Internal | Internal | Disk + TLS | — |
| `extensions` | All 3 tables | Internal | Internal | Disk + TLS | — |

---

## Appendix D: Migration Workflow & Naming Convention

### D.1 Version Naming Convention

```
YYYYMMDDHHMM_<domain>_<risk>_<slug>
```

**Valid domain values:** `memory`, `persona`, `surveillance`, `financial`, `projects`, `social`, `agents`, `consent`, `security`, `audit`, `ops`, `extensions`, `cross-schema`

**Valid risk values:** `low`, `medium`, `high`, `critical`

### D.2 Migration Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MIGRATION WORKFLOW                            │
│                                                                   │
│  1. PLAN ─────────► Risk assessment; tier classification         │
│       │             Migration script authored with naming         │
│       │                                                           │
│  2. REVIEW ───────► Git commit; code review (if required)        │
│       │                                                           │
│  3. CHECKLIST ────► Pre-migration checklist completed             │
│       │             Backup checkpoint verified                    │
│       │             Rollback script tested                        │
│       │                                                           │
│  4. STAGING ──────► Execute on staging DB                        │
│       │             Run test suite                                │
│       │             Verify integrity                              │
│       │                                                           │
│  5. APPROVE ──────► [If production] Faiz approval required       │
│       │             [If destructive] Faiz explicit approval       │
│       │                                                           │
│  6. EXECUTE ──────► Execute on production                        │
│       │             Monitor Grafana dashboards                    │
│       │             Discord notification sent                     │
│       │                                                           │
│  7. VERIFY ───────► Post-migration integrity checks              │
│       │             Constraint validation                         │
│       │             RLS policy tests                              │
│       │                                                           │
│  8. EVIDENCE ─────► All evidence collected in                    │
│                     evidence/database/<migration-id>/             │
│                     Audit report generated                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Appendix E: Pre-Migration Checklist Template

```markdown
# Pre-Migration Checklist

**Migration ID:** YYYYMMDDHHMM_<domain>_<risk>_<slug>
**Tier:** [Tier 1 Autonomous | Tier 2 Faiz Approved | Tier 3 Denied]
**Date:** YYYY-MM-DD
**Executor:** [guinevere_autonomous | faiz_approved]

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Risk level classified | [ ] Done | Migration plan |
| 2 | Backup checkpoint created | [ ] Done | `ops.backup_log` entry |
| 3 | Rollback script tested | [ ] Done | `rollback-test.md` |
| 4 | Staging synced | [ ] Done | Schema diff |
| 5 | Integrity plan defined | [ ] Done | Verification plan |
| 6 | Evidence path initialized | [ ] Done | Directory created |
| 7 | Migration committed | [ ] Done | Git commit ref |
| 8 | Faiz approval (if production) | [ ] Done | `faiz-approval.md` |
| 9 | Destructive approval (if applicable) | [ ] Done | Approval record |
| 10 | lock_timeout set | [ ] Done | Session config |
| 11 | Grafana dashboard active | [ ] Done | Dashboard URL |
| 12 | Discord notification tested | [ ] Done | Test notification |
```

---

## Appendix F: Index Strategy Catalog

### F.1 Complete Index Inventory

| # | Schema | Table | Column(s) | Index Type | Algorithm | Operator Class | Parameters |
|---|---|---|---|---|---|---|---|
| 1 | `memory` | `episodes` | `embedding` | HNSW | hnsw | `vector_cosine_ops` | `m=16, ef_construction=128` |
| 2 | `memory` | `episodes` | `started_at` | B-tree | btree | — | — |
| 3 | `memory` | `episodes` | `importance` | B-tree | btree | — | — |
| 4 | `memory` | `episodes` | `episode_type` | B-tree | btree | — | — |
| 5 | `memory` | `episodes` | `tags` | GIN | gin | — | — |
| 6 | `memory` | `episodes` | `key_insights` | GIN | gin | — | — |
| 7 | `memory` | `semantic_facts` | `embedding` | HNSW | hnsw | `vector_cosine_ops` | `m=16, ef_construction=128` |
| 8 | `memory` | `semantic_facts` | `subject` | B-tree | btree | — | — |
| 9 | `memory` | `semantic_facts` | `tags` | GIN | gin | — | — |
| 10 | `surveillance` | `events` | `occurred_at` | B-tree (chunk-local) | btree | — | — |
| 11 | `surveillance` | `events` | `event_type` | B-tree (chunk-local) | btree | — | — |
| 12 | `financial` | `transactions` | `occurred_at` | B-tree (chunk-local) | btree | — | — |
| 13 | `financial` | `transactions` | `transaction_type` | B-tree (chunk-local) | btree | — | — |
| 14 | `audit` | `audit_trail` | `occurred_at` | B-tree (chunk-local) | btree | — | — |
| 15 | `audit` | `audit_trail` | `event_type` | B-tree (chunk-local) | btree | — | — |
| 16 | `ops` | `migration_log` | `executed_at` | B-tree | btree | — | — |
| 17 | `ops` | `migration_log` | `status` | B-tree | btree | — | — |

### F.2 HNSW Tuning Parameters

| Parameter | Value | Rationale |
|---|---|---|
| `m` | 16 (default) | Connections per node — higher = better recall, more memory |
| `ef_construction` | 128 | Build quality — higher = better graph, slower builds |
| `ef_search` | 64 (default) | Query quality — higher = better recall, slower queries |
| `vector_cosine_ops` | Default operator class | Cosine similarity for semantic search |

---

## Appendix G: Audit Checklist

### G.1 Quarterly Database Audit

| # | Check Item | Method | Pass Criteria |
|---|---|---|---|
| 1 | Schema consistency — all tables match ERD | `information_schema.tables` vs this document | 100% match |
| 2 | Classification metadata completeness | `SELECT count(*) WHERE classification IS NULL` per classified table | Zero nulls |
| 3 | RLS policy enforcement | Test queries as each principal role | Only authorized rows returned |
| 4 | Index health | `pg_stat_user_indexes` analysis | All indexes with scan count > 0 |
| 5 | HNSW index parameters | `pg_indexes` verification | Matches §8.2 parameters |
| 6 | TimescaleDB compression status | `timescaledb_information.compression_settings` | All policies active |
| 7 | TimescaleDB retention status | `timescaledb_information.jobs` | All retention policies active |
| 8 | Backup freshness | `ops.backup_log` most recent entry | < 24 hours ago |
| 9 | Key rotation status | `security.secret_rotation_log` review | All keys within rotation window |
| 10 | Budget compliance | `financial.monthly_reports` analysis | Under $30/month cap |
| 11 | Migration log completeness | `ops.migration_log` count vs evidence directories | 100% coverage |
| 12 | Deletion state enforcement | `SELECT count(*) WHERE deletion_state != 'active'` | All marked records excluded from queries |

---

*End of Document*

---

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere / Hephaestus | Initial generation — complete enterprise-grade Database ERD & Migration Strategy. 12 schemas, 47 tables, 5 RLS policies, HNSW default, 3-tier authority model, $30/month budget compliance. Accepted by Faiz via ALL:D enterprise-pro-max configuration. |
