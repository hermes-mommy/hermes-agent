---
title: "ADR-052: Multi-Project Context Architecture"
status: "Accepted"
date: "2026-06-25"
last_modified: "2026-06-25"
owner: "Faiz"
executor: "Guinevere"
format: "MADR with YAML frontmatter"
adr_number: 52
supersedes: "none"
related_adrs: "ADR-007, ADR-009, ADR-024, ADR-030"
phase: "P19 — Multi-Project Context (Expansion)"
risk_level: "CRITICAL"
tags:
  - multi-project
  - context-isolation
  - project-registry
  - memory-namespace
  - p19
  - expansion
related_documents:
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_AgentLoopSpec_v2.0.md
  - Guinevere_SurveillanceDataPolicy_v1.0.md
  - Guinevere_PersonaSafetyPolicy_v1.0.md
  - docs/setup-evidence/P19/plan/p19-multi-project-context-enterprise-plan.md
---
# ADR-052: Multi-Project Context Architecture

## Status

Accepted

## Date

2026-06-25

## Last Modified

2026-06-25

## Deciders

- Faiz (Owner, final approver)
- Guinevere (Executor / autonomous system steward)

## Tags

multi-project, context-isolation, project-registry, memory-namespace, p19, expansion

## Risk Level

CRITICAL

## Supersedes

None. This ADR does not supersede any existing decision. It defines a new orthogonal `project_id` dimension across all project-scoped stores while persona and HARD STOP remain global.

## Related ADRs

| ADR | Relationship |
|---|---|
| [`../ADR-007-memory-storage-backend-selection.md`](../ADR-007-memory-storage-backend-selection.md) | PostgreSQL primary storage — project namespace columns live in the same database instance |
| [`../ADR-009-memory-recall-semantic-search-strategy.md`](../ADR-009-memory-recall-semantic-search-strategy.md) | Memory recall pipeline — `ProjectScopedMemoryStore` filters by `project_id` |
| [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) | Data governance — project classification adds project-scoped sensitivity labels |
| [`../ADR-030-redis-db-assignments.md`](../ADR-030-redis-db-assignments.md) | Redis DB assignments — project-scoped keys prefixed by `p19:{project_slug}:{domain}` pattern |
| [`../ADR-001-persona-safety-ethical-boundary.md`](../ADR-001-persona-safety-ethical-boundary.md) | HARD STOP and consent boundaries remain global; project isolation must not scope the safe word |
| [`../ADR-002-user-autonomy-safe-word-enforcement.md`](../ADR-002-user-autonomy-safe-word-enforcement.md) | Safe word enforcement halts ALL projects — HARD STOP is a single global Redis key |
| [`../ADR-010-surveillance-retention-policy.md`](../ADR-010-surveillance-retention-policy.md) | Surveillance scope — project-scoped sources get `project_id` in `surveillance.*` |
| [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) | Data classification — project-scoped data inherits classification labels at the project level |

## Related Documents

| Document | Relationship |
|---|---|
| [`../../Guinevere_MemorySchema_v2.0.md`](../../Guinevere_MemorySchema_v2.0.md) | Parent memory model — `project_id` column added to all memory- and KG-scoped tables |
| [`../../Guinevere_AgentLoopSpec_v2.0.md`](../../Guinevere_AgentLoopSpec_v2.0.md) | Agent loop context — project-aware session orchestration selects project-scoped stores |
| [`../../Guinevere_SurveillanceDataPolicy_v1.0.md`](../../Guinevere_SurveillanceDataPolicy_v1.0.md) | Surveillance scope — project-scoped sources partitioned by `project_id` |
| [`../../Guinevere_PersonaSafetyPolicy_v1.0.md`](../../Guinevere_PersonaSafetyPolicy_v1.0.md) | Persona safety — shared global persona across all projects; HARD STOP remains global |
| [`../../docs/setup-evidence/P19/plan/p19-multi-project-context-enterprise-plan.md`](../../docs/setup-evidence/P19/plan/p19-multi-project-context-enterprise-plan.md) | P19 enterprise implementation plan — execution waves P19-001 through P19-012 |
| [`../../docs/setup-evidence/P19/research/p19-repo-architecture-inventory.md`](../../docs/setup-evidence/P19/research/p19-repo-architecture-inventory.md) | Repository architecture inventory — 38 files audited for project_id gaps |
| [`../../docs/setup-evidence/P19/research/p19-memory-namespace-research.md`](../../docs/setup-evidence/P19/research/p19-memory-namespace-research.md) | Memory namespace research — global vs. project-scoped design patterns |
| [`../../docs/setup-evidence/P19/research/p19-database-schema-migration-research.md`](../../docs/setup-evidence/P19/research/p19-database-schema-migration-research.md) | Database schema migration research — additive migration strategy for project_id columns |
| [`../../docs/setup-evidence/P19/research/p19-surveillance-consent-scope-research.md`](../../docs/setup-evidence/P19/research/p19-surveillance-consent-scope-research.md) | Surveillance/consent scope research — per-project vs. global scope taxonomy |
| [`../../docs/setup-evidence/P19/research/p19-secrets-boundary-research.md`](../../docs/setup-evidence/P19/research/p19-secrets-boundary-research.md) | Secrets boundary research — per-project encrypted files, in-memory vault isolation |
| [`../../docs/setup-evidence/P19/research/p19-life-kernel-dependency-map.md`](../../docs/setup-evidence/P19/research/p19-life-kernel-dependency-map.md) | Life kernel dependency map — P20 files affected by P19 project context propagation |
| [`../../docs/setup-evidence/P19/research/p19-p21-p22-integration-dependency-map.md`](../../docs/setup-evidence/P19/research/p19-p21-p22-integration-dependency-map.md) | P21/P22 integration dependency map — forward-compat seam for downstream phases |
| [`../../docs/setup-evidence/P19/research/p19-agent-loop-session-isolation-research.md`](../../docs/setup-evidence/P19/research/p19-agent-loop-session-isolation-research.md) | Agent loop / session isolation research — thread_id project encoding patterns |
| [`../../docs/setup-evidence/P19/research/p19-discord-dashboard-project-switcher-research.md`](../../docs/setup-evidence/P19/research/p19-discord-dashboard-project-switcher-research.md) | Discord dashboard / project switcher research — UX patterns for `/project` commands |
| [`../../docs/setup-evidence/P19/research/p19-observability-audit-evidence-research.md`](../../docs/setup-evidence/P19/research/p19-observability-audit-evidence-research.md) | Observability/audit evidence research — project_id labels for Prometheus and audit rows |

## Context

Guinevere currently runs as a single-project autonomous AI companion. All memory, knowledge graph (KG) records, audit trails, consent ledger entries, surveillance source bindings, agenda items, dashboard state, and session data assume a single implicit project. Every store uses a shared namespace with no `project_id` dimension, no partitioning, and no isolation boundary between one project's context and another's. As more projects are added, the risk of cross-contamination grows: a fact recalled for project A could surface during a query for project B; an agenda action intended for project A could fire in the context of project B; surveillance data collected for one project could influence another's decision-making. This is not a hypothetical concern — the P19 enterprise plan identifies 38 source files across 15 stores that lack any project-scoped isolation.

The existing LangGraph `thread_id` provides session-scoped isolation at the conversation level, but this is not equivalent to project-level context isolation. A `thread_id` differentiates one conversation turn from another within the same project, but it has no concept of which project the thread belongs to. Two projects running in the same process share the same memory tables, the same Redis keys, the same audit journal, and the same consent scope. LangGraph's thread isolation is a session mechanism, not a namespace mechanism.

The problem becomes acute when multiple projects coexist in production. P20 Living Autonomy runs the life kernel on a 6-interval schedule with full autonomous cognition. If a second project (P22 Life Integration Hub, for instance) shares the same memory space, autonomous actions intended for one project could read or write memory belonging to the other. The HARD STOP safe word must halt all projects simultaneously — this is non-negotiable for safety — but every other store must be partitioned so that project A's data never leaks into project B's context.

A `project_id` dimension must be added orthogonally to every project-scoped store. This dimension must be backward-compatible with existing unscoped data (which retroactively belongs to a default project). It must not introduce new services, new Docker containers, or separate database instances — the project runs a single PostgreSQL instance on one VPS and must continue to do so. It must keep the persona, HARD STOP, safety policies, and ADRs as global-scope resources that are visible from every project. And it must be feature-flagged so that the rollout can be controlled: flag OFF preserves the legacy P20 behavior with no changes.

## Decision Drivers

- **Non-breaking by construction.** Unscoped data continues to work as the default project. Feature flag `feature:projects:enabled` gates project-aware behavior. When the flag is OFF, all `project_id` filters are omitted and the system behaves exactly as it does today.
- **Bare-metal PostgreSQL only.** No new services, no Docker, no separate process per project. The `project_id` column is additive — it does not require new infrastructure. The same single PostgreSQL instance (ADR-007) serves all projects.
- **HARD STOP stays global.** The safe word `life_kernel:hard_stop` halts ALL projects simultaneously. P19 MUST NOT scope HARD STOP to a single project. This is a hard-rejection criterion: any design that partitions HARD STOP by project is automatically rejected.
- **Consent and safety first.** Safety-critical scopes (persona, emergency, HARD STOP, safe-word) stay global. Project-scoped consent scopes get `project_id` in `consent.consent_ledger`. Consent revocation for a project-scoped scope affects only that project's data. The shared persona must be visible across all projects for consistency of mood, yandere level, punishment state, safe-mode, and drift.
- **Per-project secrets isolation.** In-memory `ProjectSecretsVault` keyed by `project_id` (not environment variables, which do not isolate within a single shared `guinevere-core` process). Per-project secrets live in `secrets/projects/{project_id}/*.enc.yaml` and are decrypted on demand. Each adapter calls `vault.get(project_id, domain)` and only receives its own project's secrets.
- **Project switch is explicit and auditable.** Every `/project` switch writes an `audit.audit_trail` row with `(actor, from_project, to_project, timestamp, channel_id)`. No silent switch. The default project (when Faiz is silent) is determined by configuration or the `default` project UUID.
- **P20 non-interference.** Additive `NotRequired` state fields only. No changes to HARD-STOP loop semantics, the 6-interval schedule, the `life_kernel:hard_stop` key contract, or Hermes conversational core without operator approval. P19 changes to P20 production files are held by operator discretion (P20 axis satisfied by operator waiver — not a pending soak gate).
- **P21/P22/P17 forward-compat.** P19 owns the project registry (read-only by P22). P21 receives a nullable `project_id` seam that becomes a real foreign key after P19 lands. The migration chain is P19 -> P21 -> P22.
- **Sub-agent output discipline.** All research, audit, and implementation sub-agents write a `.md` file to an explicit output path before returning. Inline-only results are considered a failure.

## Considered Options

### Option A: Separate PostgreSQL schemas per project — REJECTED

Each project gets its own PostgreSQL schema (e.g., `project_abc123.*`) with its own set of tables for memory, audit, consent, and surveillance.

**Why rejected:**

- Dynamic schema creation complicates Alembic migrations. Every new project would need a schema creation migration, breaking the linear migration lineage.
- Each schema duplicates the full table set (memory, KG, audit, consent, surveillance), creating N x maintenance burden. A schema change must be applied to every project schema simultaneously.
- No shared persona view without cross-schema queries or views. The global persona (mood, yandere, punishment, safe-mode, drift) would need to live in a separate `public` or `global` schema, and every project query would need to UNION or join across schemas.
- Backup and DR complexity multiplies by N. A single `pg_dump` no longer captures the full system state.
- Violates the bare-metal PostgreSQL principle: schema-per-project adds operational complexity without corresponding isolation benefit for a single-user system.

### Option B: Separate PostgreSQL databases per project — REJECTED

Each project runs in its own PostgreSQL database. A connection router selects the database based on the active project.

**Why rejected:**

- Cannot share persona, ADRs, or safety policies without `dblink` or foreign data wrappers (FDW). Database-level isolation means the global persona must be replicated or accessed remotely, adding latency and failure modes.
- Connection pool explosion. PgBouncer or the application pool must maintain N connection pools (one per database). Each pool consumes memory and file descriptors.
- Backup/DR complexity multiplies by N. Each database needs a separate backup schedule, restore drill, and consistency check.
- Transactional consistency across persona writes and project writes is impossible — a persona mood update and a project memory write cannot commit atomically across databases.
- Violates the bare-metal PostgreSQL principle (ADR-007) and introduces operational surface area that does not exist today.

### Option C: Application-layer project_id dimension — ACCEPTED

A single `project_id UUID` column added to every project-scoped table in `memory.*`, `audit.*`, `consent.*`, `surveillance.*`, and `projects.project_registry`. Global-scope rows use `project_scope = 'global'` with `project_id = NULL`. A thin wrapper (`ProjectScopedMemoryStore`) enforces `WHERE project_id = :pid OR project_scope = 'global'` on every query. The default project UUID is `00000000-0000-0000-0000-000000000001`. Feature flag `feature:projects:enabled` gates thread_id selection (flag OFF = legacy behavior). Per-project secrets are stored in `secrets/projects/{project_id}/*.enc.yaml` and decrypted into an in-memory `ProjectSecretsVault` keyed by `project_id`.

**Why accepted:**

- Zero new services. Zero new infrastructure. The single PostgreSQL instance ADR-007 already provides continues to serve all projects with an additive column change.
- Shared global views without cross-schema joins. Global rows (persona, safety policies, ADRs, HARD STOP) are visible from every project via the `project_scope = 'global'` clause in the same table. No `dblink`, no FDW, no view replication.
- Backward-compatible via default project. Existing unscoped data is backfilled to `project_id = 00000000-0000-0000-0000-000000000001` (the "default" project). All existing queries continue to work because the default project is the active project when no other project is selected.
- Feature-flagged rollout. `feature:projects:enabled = false` preserves legacy P20 behavior with zero code path changes. When the flag is on, `ProjectScopedMemoryStore` adds the `project_id` filter.
- HARD STOP stays global. The single Redis key `life_kernel:hard_stop` is never scoped to a project. P19 code must reject any attempt to scope HARD STOP.
- Project-local pause is a distinct, weaker concept: `project:{project_id}:paused` pauses only that project's autonomous work. This is separate from HARD STOP and must be explicitly modeled.
- Per-project secrets isolation is achieved in-memory, not via environment variables. Env vars (`GUINEVERE_{PROJECT}_{KEY}`) are only for optional single-project systemd units.
- P21 gets a nullable `project_id` seam; P22 reads the project registry read-only. Migration chain is linear and additive.

### Option D: LangGraph thread_id as sole project isolation — REJECTED

Use the existing LangGraph `thread_id` to differentiate projects. Each project gets a dedicated `thread_id` prefix, and thread-level isolation is relied upon for all project separation.

**Why rejected:**

- `thread_id` provides session-scoped isolation only. A thread differentiates one conversation turn from another, but thread IDs are ephemeral and LangGraph does not enforce data partitioning by thread.
- No project-level memory, KG, audit, or consent partitioning. Two threads in the same project share the same database tables. Adding a thread_id column to memory tables would be equivalent to Option C but without the project registry, project-scoped secrets, or deployment boundary enforcement.
- No project registry. There is no canonical source of truth for which projects exist, their metadata, or their lifecycle state.
- No per-project secrets. All secrets live at the process level, accessible from any thread.
- No per-project consent or surveillance scoping. A consent revocation for project A would apply to all projects.
- Cannot support per-project deploy boundaries. A thread cannot gate whether a project's autonomous actions affect another project.

## Decision Outcome

Chosen option: **Option C — Application-layer project_id dimension**. This decision establishes the following key elements that form the P19 Multi-Project Context architecture.

### Key Elements

1. **`projects.project_registry` table** — The canonical project registry owned by P19. Contains `project_id UUID PK`, `slug VARCHAR UNIQUE`, `display_name VARCHAR`, `description TEXT`, `status VARCHAR` (active, paused, archived, deleted), `project_scope VARCHAR` (project or global), `created_at`, `updated_at`, and `metadata JSONB`. Read-only by P22 (P22 reads the registry to tag its own data with `project_id`).

2. **`ProjectScopedMemoryStore`** — A thin wrapper over the existing `MemoryStore`. On every read and write, prepends `WHERE project_id = :active_project_id OR project_scope = 'global'`. The wrapper is feature-gated by `feature:projects:enabled`. When the flag is OFF, the wrapper is transparent (passes through to the underlying `MemoryStore` unchanged).

3. **`ProjectSecretsVault`** — An in-memory dictionary keyed by `project_id`. Secrets are loaded from `secrets/projects/{project_id}/*.enc.yaml` files, decrypted with SOPS/age on startup or on project activation. Each domain adapter (email, finance, gmail, wearable, x) calls `vault.get(project_id, domain)` and receives only its own project's credentials. This avoids the cross-project secret leak that environment variables would allow in a single-process architecture.

4. **Internal namespace template: `p19:{project_slug}:{domain}:{resource-id}`** — Applied to Redis keys, thread IDs, Prometheus metric labels, and audit event types. Example: `p19:my-project:memory:fact:uuid-here`. The prefix ensures no collision between project-scoped and global keys in shared stores.

5. **Default project UUID: `00000000-0000-0000-0000-000000000001`** — The fallback project for all existing unscoped data. Backfill migration sets `project_id = '00000000-0000-0000-0000-000000000001'` on every row that currently has no project context.

6. **Feature flag: `feature:projects:enabled`** — Boolean configuration key. When `false` (the default for legacy compatibility), the `ProjectScopedMemoryStore` is transparent, all `project_id` filters are omitted, and the system behaves exactly as it does today. When `true`, project-aware filtering is active.

7. **HARD STOP: global, single Redis key `life_kernel:hard_stop`** — Halts ALL projects simultaneously. The HARD STOP handler sets this key once; every project's autonomous loop checks it and stops. P19 code must NEVER scope this key to a project. This is a hard-rejection criterion.

8. **Project pause: `project:{project_id}:paused`** — A per-project, weak pause that stops only that project's autonomous work. Persona and other projects are unaffected. This is distinct from HARD STOP and must be explicitly modeled in the life kernel's project-aware loop.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED PERSONA (GLOBAL)                       │
│  mood / yandere / punishment / safe-mode / drift / HARD-STOP     │
│  (one Guinevere across all projects; NOT project-scoped)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │              PROJECT REGISTRY                │
        │  (projects.project_registry — canonical,     │
        │   owned by P19, read-only by P22)            │
        └──────────────────────┬──────────────────────┘
                               │
            ┌──────────────────┼──────────────────────┐
            ▼                  ▼                      ▼
   ┌────────────────┐ ┌────────────────┐ ┌────────────────────┐
   │   Project A    │ │   Project B    │ │   Project C       │
   │   (active)     │ │   (paused)     │ │   (archived)      │
   └───────┬────────┘ └───────┬────────┘ └────────┬───────────┘
           │                  │                    │
           ▼                  ▼                    ▼
   ┌────────────────────────────────────────────────────────────┐
   │                  PROJECT-SCOPED STORES                      │
   │  memory.* / kg.* / audit.* / consent.consent_ledger        │
   │  surveillance.* / agenda.* / dashboard.* / session.*       │
   │  sensor.* / finance.* / email.* / gmail.* / wearable.*     │
   │  (WHERE project_id = :pid OR project_scope = 'global')     │
   └────────────────────────────────────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────────┐
   │                  SHARED INFRASTRUCTURE                      │
   │  PostgreSQL (single instance, single schema, project_id FK) │
   │  Redis      (DB0–5 per ADR-030, keys prefixed p19:*)       │
   │  Secrets    (secrets/projects/{project_id}/*.enc.yaml)      │
   │  Monitoring (Prometheus project_id labels)                  │
   └────────────────────────────────────────────────────────────┘
```

### Isolation Boundaries

| Scope | Store | Isolation |
|---|---|---|
| **Global** | Persona (mood, yandere, punishment, safe-mode, drift) | Shared across all projects |
| **Global** | HARD STOP (`life_kernel:hard_stop`) | Single global key, halts ALL projects |
| **Global** | ADRs, safety policies, system configuration | Shared, no project scope |
| **Project** | `memory.semantic_facts`, `memory.kg_*`, `memory.episodes` | `WHERE project_id = :pid OR project_scope = 'global'` |
| **Project** | `audit.audit_trail`, `audit.recent_actions` | `WHERE project_id = :pid` |
| **Project** | `consent.consent_ledger` (project-scoped scopes) | `WHERE project_id = :pid OR project_id IS NULL` |
| **Project** | `surveillance.*` (sources, raw payloads) | `WHERE project_id = :pid` |
| **Project** | `agenda.*` (items, schedule, execution) | `WHERE project_id = :pid` |
| **Project** | Dashboard state, Discord channel bindings | `WHERE project_id = :pid` |
| **Project** | Session data, background cognition state | `WHERE project_id = :pid` |
| **Project** | Sensor readings, domain actuator state | `WHERE project_id = :pid` |
| **Project** | Secrets (`secrets/projects/{project_id}/*.enc.yaml`) | In-memory vault, `vault.get(project_id, domain)` |

## Consequences

### Positive

- **Per-project memory, KG, audit, consent, surveillance, secrets, and observability isolation.** Every project-scoped store enforces `WHERE project_id = :active_project_id`, preventing cross-contamination of context, memory, and decisions.
- **Backward compatible with existing unscoped data.** The default project (UUID `00000000-0000-0000-0000-000000000001`) serves as the fallback for all existing data. Existing queries continue to work unchanged.
- **Feature-flagged rollout.** `feature:projects:enabled = false` preserves the legacy P20 behavior with zero code path changes. No breaking change at deploy time.
- **Global persona shared across all projects.** One Guinevere persona (mood, yandere, punishment, safe-mode, drift) visible from every project, ensuring personality consistency. This is critical for the user's experience — switching projects should not change how Guinevere behaves or responds.
- **HARD STOP always global.** The safe word halts all projects simultaneously. No design can partition HARD STOP. This is a hard-rejection criterion and is explicitly enforced in code review and testing.
- **Zero new services.** The single PostgreSQL instance (ADR-007) and single Redis instance (ADR-030) serve all projects. The `project_id` column is additive, not infrastructure-changing.
- **P21 gets a nullable `project_id` seam.** P21 Voice can tag its data with `project_id = NULL` (global voice context) or a specific project ID. After P19 lands, the seam becomes a real foreign key.
- **P22 reads the project registry read-only.** P22 Life Integration Hub depends on the registry to discover projects and their metadata. P19 owns writes; P22 reads.
- **Persistent governance across projects.** All ADRs, safety policies, and ethical boundaries remain in effect regardless of the active project. The persona safety policy is global and enforced uniformly.

### Negative

- **Application-layer enforcement.** Without RLS (which is optional and feature-flagged), the isolation depends on the `ProjectScopedMemoryStore` wrapper correctly applying `WHERE project_id = :pid` on every query. A missing filter is a data leak. Mitigation: coverage tests for every store that verify both the scoped and unscoped query paths, plus optional PostgreSQL RLS as defense-in-depth.
- **Existing code must be audited for missing `project_id` propagation.** The P19 enterprise plan identifies 38 source files that must receive a `project_id` parameter. Each file must be individually reviewed and updated. Mitigation: the audit rounds (P19 audit round 1 and round 2) scan every file for incomplete propagation.
- **Migration burden for existing unscoped records.** All existing rows in `memory.*`, `audit.*`, `consent.*`, and `surveillance.*` must be backfilled to the default project UUID. The migration must be idempotent, zero-downtime, and reversible. Mitigation: the backfill runs as an additive Alembic migration with a dry-run mode (P19-011).
- **Test burden.** Every integration test should test both the scoped path (with `feature:projects:enabled = true` and an explicit `project_id`) and the unscoped path (flag OFF). This doubles the test matrix for project-scoped stores. Mitigation: parametrized fixtures that test both paths without duplicating test case code.

### Risks

- **R1 — Missing `project_id` filter.** If a code path reads a project-scoped store without the `WHERE project_id = :pid` clause, it will see data from all projects. Mitigation: P19-004 (memory/KG partition) includes integration tests that assert isolation. Optional RLS (feature-flagged) provides database-level defense-in-depth. A startup-time check verifies that every registered store has a project-scoped query path.
- **R2 — HARD STOP scoping violation.** If any code path scopes HARD STOP to a project (e.g., `life_kernel:hard_stop:{project_id}`), it violates the hard-rejection criterion. Mitigation: code review checklists explicitly list HARD STOP non-scoping as a blocker. Integration tests assert that setting `life_kernel:hard_stop` halts all active projects.
- **R3 — Secret cross-project leak.** If `ProjectSecretsVault` is not correctly isolated, project A's adapter could read project B's credentials. Mitigation: unit tests for `ProjectSecretsVault` assert that `vault.get(project_a_id, domain)` does not return project B's secrets. The vault is initialized with a per-project key mapping and refuses unknown project IDs.
- **R4 — Project switch race.** If two concurrent requests switch to different projects, the global active project could be inconsistent. Mitigation: project switch is serialized through a per-process lock. The active project is stored in a thread-local or asyncio `contextvars.ContextVar`, not a global variable.
- **R5 — P20 production destabilization.** Any P19 change to P20 production files (`heartbeat.py`, `graph.py`, `hermes_brain.py`, `state.py`, `models.py`, `hard_stop_handler.py`, `main.py`) carries risk of destabilizing the production system. Mitigation: P20-axis changes are held by operator discretion. P19 waves that touch P20 files (P19-005a/b/c) require explicit operator approval before execution. NEW files (`src/projects/*`, `tests/projects/*`, `alembic/versions/p19_*.py`, `secrets/projects/*`) and additive migrations are unblocked and ready by operator approval.

## Implementation Plan

The implementation is organized into 12 waves (P19-001 through P19-012), executed sequentially except where noted. Each wave is gated by a verification step that must pass before the next wave begins. Waves touching P20 production files (P19-005) are held by operator discretion.

| Wave | Title | Days | Depends on | Mode | Output path |
|---|---|---|---|---|---|
| P19-001 | Governance: this ADR + docs sync + ADR index update | 1 | none | sequential | `adr/ADR-052-multi-project-context.md` |
| P19-002 | Project registry: `projects.project_registry` table + `ProjectRegistry` class + domain models + unit tests | 2 | P19-001 | sequential | `src/projects/registry.py`, `src/projects/models.py` |
| P19-003 | DB schema + migration: additive `project_id` column migrations for all scoped tables + indexes | 3 | P19-002 | sequential | `alembic/versions/p19_*.py` |
| P19-004 | Memory/KG partition: `ProjectScopedMemoryStore` wrapper + KG namespace filter + isolation tests | 3 | P19-003 | sequential | `src/memory/project_store.py`, `tests/memory/test_project_isolation.py` |
| P19-005 | Life-kernel propagation: additive `NotRequired` state fields in P20 files + Redis key namespace + operator-gate | 2 | P19-004 | **held** | `src/life_kernel/` (additive changes) |
| P19-006a | Project-aware sensors: finance adapter | 1 | P19-004 | parallel | `src/sensors/finance/project.py` |
| P19-006b | Project-aware sensors: email adapter | 1 | P19-004 | parallel | `src/sensors/email/project.py` |
| P19-006c | Project-aware sensors: gmail adapter | 1 | P19-004 | parallel | `src/sensors/gmail/project.py` |
| P19-006d | Project-aware sensors: wearable adapter | 1 | P19-004 | parallel | `src/sensors/wearable/project.py` |
| P19-006e | Project-aware sensors: X/Twitter adapter | 1 | P19-004 | parallel | `src/sensors/x/project.py` |
| P19-007 | Discord UX: `/project` command + per-project dashboard/log channels + project switcher UI | 2 | P19-004 | sequential | `src/discord/project_switcher.py`, `src/discord/dashboard.py` |
| P19-008 | Agent/session orchestration: project-aware session init + background cognition per project + LangGraph thread_id encoding | 3 | P19-004 | sequential | `src/agent_loop/project_session.py` |
| P19-009 | Consent/surveillance scope: `project_id` in `consent.consent_ledger` + project-scoped surveillance source binding + global safety-scope enforcement | 2 | P19-004 | sequential | `src/consent/project_scope.py`, `src/surveillance/project_scope.py` |
| P19-010 | Observability/audit: `project_id` in audit trail rows + Prometheus `project_id` labels + Grafana per-project dashboards | 2 | P19-003 | parallel | `src/observability/project_labels.py` |
| P19-011 | Migration/backfill: Alembic migration backfilling existing unscoped rows to `default` project + dry-run mode + verification | 2 | P19-003 | sequential | `alembic/versions/p19_backfill_default.py` |
| P19-012 | Deploy/soak/gate: canary deploy + soak monitoring + rollback plan + final operator gate | 2 | P19-005..011 | sequential | `docs/setup-evidence/P19/evidence/deploy-gate.md` |

**Total estimate:** 24 person-days mid-point, range 20 to 28.

### Downstream migration chain

After P19 implementation, the following phases receive project-aware capabilities through the seam P19 provides:

- **P21 Voice.** Nullable `project_id` seam on voice clips, voice profiles, and voice settings. After P19 lands, the seam becomes a real foreign key to `projects.project_registry`.
- **P22 Life Integration Hub.** Reads `projects.project_registry` read-only. All P22 data tagged with `project_id` at write time. No write access to the registry.
- **P17 Cross-Device Sync.** Sync keys include `project_id` as a partition dimension. Device-scoped vs. project-scoped sync decisions are deferred to P17.
- **P23 Embodied Operations / Personal OS Action Layer.** P23's executor adapters and action queue carry `project_id` on every action. The P23 action planner (`HermesBrain.think()`) receives the active project context. P23's risk tiers (L1-L4) are project-scoped: deploy of project X requires project-scoped `consent.autonomy.high_blast` or explicit operator approval. P23-012 is gated on P19 namespace contract readiness (P19 definition complete 2026-06-25). P19 owns the registry; P23 reads it.
- **P24 Hermes Fork-First Full Convergence.** P24's owned Hermes fork carries `project_id` through the fork's internal plugin/module system. The P24-002 internal patch (P20 heartbeat) and all convergence waves are gated on P19 namespace contract readiness. P24 reads `projects.project_registry` for project-aware Hermes skill loading and session isolation. P24 implementation is held until P19 namespace contract is deployed to production.

## Compliance

### PersonaSafetyPolicy

The multi-project architecture respects all persona safety boundaries:

- **HARD STOP (global).** The safe word `life_kernel:hard_stop` halts ALL projects simultaneously. No code path may scope HARD STOP to a single project. The HARD STOP handler checks are identical across all projects — one key, one halt.
- **Shared persona.** Mood, yandere level, punishment state, safe-mode, and drift are global. Switching projects does not change the persona. This ensures personality consistency and prevents safety boundary gaming by switching projects.
- **Do Not Remember (DNR).** A DNR marker on a fact applies globally. If a fact is DNR in one project, it is DNR in all projects. The DNR check runs before the `project_id` filter to prevent per-project DNR evasion.
- **Consent revocation.** Project-scoped consent scopes (surveillance sources, project memory, client/financial actions, P22 integrations) get `project_id` in `consent.consent_ledger` (NULL = global). Revoking a project-scoped scope affects only that project's data. Safety-critical scopes (persona, emergency, HARD STOP, safe-word) are global and cannot be project-scoped.
- **No type suppression.** Per project-wide policy, P19 code must not use `as any`, `# type: ignore`, `@ts-ignore`, or `@ts-expect-error`. Type safety is enforced at the package boundary.

### SurveillanceDataPolicy

The multi-project architecture enforces surveillance scope isolation:

- Surveillance-derived data for project A is stored with `project_id = A` and is never visible from project B's context.
- Global surveillance sources (e.g., system-wide resource monitoring) are tagged `project_scope = 'global'` and are visible from all projects.
- Project-scoped surveillance consent grants are recorded in `consent.consent_ledger` with `project_id` set. Revoking a project's surveillance consent stops data collection and soft-deletes collected data for that project only.
- Raw surveillance payloads never cross project boundaries. The `surveillance.*` tables enforce `WHERE project_id = :active_project_id` at query time.

### ADR-001 / ADR-002

- The ethical boundary policy (ADR-001) applies uniformly across all projects. There is no per-project ethical boundary — Guinevere's ethical constraints are global and non-negotiable.
- The safe word (ADR-002) is a global user-autonomy override. Safe-word activation halts all projects immediately, regardless of the active project or any in-flight autonomous action. Project-specific pause (`project:{project_id}:paused`) is a distinct, weaker concept and does not satisfy safe-word requirements.
- Safe-word activation is logged in the audit trail with `project_id = NULL` (global scope) and the affected projects listed in the metadata.

## Review Record

- **Date:** 2026-06-25
- **Reviewer:** Faiz (Owner) + Guinevere (Executor)
- **Decision:** Accepted
- **Evidence:**
  - P19 enterprise plan: `docs/setup-evidence/P19/plan/p19-multi-project-context-enterprise-plan.md` (300+ lines)
  - Repository architecture inventory: `docs/setup-evidence/P19/research/p19-repo-architecture-inventory.md` (38 files audited)
  - Memory namespace research: `docs/setup-evidence/P19/research/p19-memory-namespace-research.md`
  - Database schema migration research: `docs/setup-evidence/P19/research/p19-database-schema-migration-research.md`
  - Surveillance/consent scope research: `docs/setup-evidence/P19/research/p19-surveillance-consent-scope-research.md`
  - Secrets boundary research: `docs/setup-evidence/P19/research/p19-security-secrets-boundary-research.md`
  - Life kernel dependency map: `docs/setup-evidence/P19/research/p19-p20-life-kernel-dependency-map.md`
  - P21/P22 integration dependency map: `docs/setup-evidence/P19/research/p19-p21-p22-integration-dependency-map.md`
  - Agent loop / session isolation research: `docs/setup-evidence/P19/research/p19-agent-loop-session-isolation-research.md`
  - Discord dashboard / project switcher research: `docs/setup-evidence/P19/research/p19-discord-dashboard-project-switcher-research.md`
  - Observability/audit evidence research: `docs/setup-evidence/P19/research/p19-observability-audit-evidence-research.md`
  - Ground truth refresh: `docs/setup-evidence/P19/evidence/implementation/ground-truth-refresh.md`
  - P19 definition verification: `docs/setup-evidence/P19/evidence/p19-definition-verification.md`
  - Audit round 1 (architecture, safety-consent, security-secrets, data-memory-isolation, database-migration, observability-evidence, p20-integration, runtime-deploy-readiness, docs-consistency, p21-p22-dependency): `docs/setup-evidence/P19/evidence/audits/round-1/`
  - Audit round 2 (same categories): `docs/setup-evidence/P19/evidence/audits/round-2/`
  - Auditor gate: `docs/setup-evidence/P19/evidence/auditor-gate.md`
  - P20 waiver gate sync: `docs/setup-evidence/P19/evidence/p20-waiver-gate-sync.md`
- **Notes:**
  - **ADR number is 052, not 041.** ADR-039 through ADR-051 are pre-allocated in the ADR-Index backlog for Prompt Injection, RBAC/ABAC, Secrets Rotation, OpenAPI, Event Schema, ERD, SLO/SLA, Incident Response, Feature Flags, Analytics, Compliance, and Knowledge Graph (ADR-050). ADR-052 is the next free slot after ADR-050 and ADR-051.
  - **Default project UUID.** The default project UUID `00000000-0000-0000-0000-000000000001` is chosen to be easily recognizable in logs and database rows. It is not a valid real UUID (all zeros with trailing `1`), making it distinct from any real project UUID generated by `uuid4()`.
  - **HARD STOP non-scoping is hard-rejection.** Any P19 code or review that scopes HARD STOP to a project must be rejected immediately. This is a safety-critical constraint that overrides all other design considerations.
  - **Project pause vs. HARD STOP.** Project pause (`project:{project_id}:paused`) is a Redis string flag (value: timestamp of pause). It pauses only that project's autonomous work. HARD STOP (`life_kernel:hard_stop`) is a separate, global key that halts all projects. The life kernel's project-aware loop checks both: project pause first (if set, skip this project's tick), then HARD STOP (if set, exit immediately).
  - **Env vars for single-project systemd only.** Environment variables (`GUINEVERE_{PROJECT}_{KEY}`) are an optional optimization for single-project systemd units. The canonical secrets path is `secrets/projects/{project_id}/*.enc.yaml` loaded into `ProjectSecretsVault`.
  - **Feature flag default is OFF.** `feature:projects:enabled = false` is the default. The flag is turned ON only after P19-012 deploy/soak/gate passes with operator approval. This ensures zero disruption to the production P20 system during P19 rollout.
  - **Performance bound.** The `WHERE project_id = :pid` filter is backed by a composite index `(project_id, ...)` on every project-scoped table. The index overhead is minimal because `project_id` is a UUID (16 bytes, high cardinality, good index selectivity). Query performance on the default project (which has the most rows) must not regress by more than 5% at p95. Measured by P19-004 isolation tests.
  - **Sub-agent output discipline.** Every research, audit, and implementation sub-agent writes a `.md` file to an explicit output path before returning. Inline-only results = FAIL. This applies to all P19 implementation waves.
  - **P20 non-interference.** P19 changes to P20 production files (`heartbeat.py`, `graph.py`, `hermes_brain.py`, `state.py`, `models.py`, `hard_stop_handler.py`, `main.py`) are held by operator discretion — not because of a pending P20 soak but to avoid destabilizing a production system under accepted risk. NEW files and additive migrations are unblocked.
  - **RLS is optional, not required.** PostgreSQL Row-Level Security on `project_id` is a defense-in-depth measure, not a correctness requirement. The `ProjectScopedMemoryStore` wrapper is the primary isolation mechanism. RLS requires `feature:projects:rls` flag ON and is enabled by default when `feature:projects:enabled = true`.

## Links

- [`../ADR-001-persona-safety-ethical-boundary.md`](../ADR-001-persona-safety-ethical-boundary.md)
- [`../ADR-002-user-autonomy-safe-word-enforcement.md`](../ADR-002-user-autonomy-safe-word-enforcement.md)
- [`../ADR-007-memory-storage-backend-selection.md`](../ADR-007-memory-storage-backend-selection.md)
- [`../ADR-009-memory-recall-semantic-search-strategy.md`](../ADR-009-memory-recall-semantic-search-strategy.md)
- [`../ADR-010-surveillance-retention-policy.md`](../ADR-010-surveillance-retention-policy.md)
- [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md)
- [`../ADR-030-redis-db-assignments.md`](../ADR-030-redis-db-assignments.md)
- [`../../Guinevere_ADR_Index_v1.0.md`](../../Guinevere_ADR_Index_v1.0.md)
- [`../../Guinevere_MemorySchema_v2.0.md`](../../Guinevere_MemorySchema_v2.0.md)
- [`../../Guinevere_AgentLoopSpec_v2.0.md`](../../Guinevere_AgentLoopSpec_v2.0.md)
- [`../../Guinevere_PersonaSafetyPolicy_v1.0.md`](../../Guinevere_PersonaSafetyPolicy_v1.0.md)
- [`../../Guinevere_SurveillanceDataPolicy_v1.0.md`](../../Guinevere_SurveillanceDataPolicy_v1.0.md)
- [`../../docs/setup-evidence/P19/plan/p19-multi-project-context-enterprise-plan.md`](../../docs/setup-evidence/P19/plan/p19-multi-project-context-enterprise-plan.md)
- [`../../docs/setup-evidence/P19/research/p19-repo-architecture-inventory.md`](../../docs/setup-evidence/P19/research/p19-repo-architecture-inventory.md)
- [`../../docs/setup-evidence/P19/research/p19-memory-namespace-research.md`](../../docs/setup-evidence/P19/research/p19-memory-namespace-research.md)
- [`../../docs/setup-evidence/P19/research/p19-database-schema-migration-research.md`](../../docs/setup-evidence/P19/research/p19-database-schema-migration-research.md)
- [`../../docs/setup-evidence/P19/research/p19-surveillance-consent-scope-research.md`](../../docs/setup-evidence/P19/research/p19-surveillance-consent-scope-research.md)
- [`../../docs/setup-evidence/P19/research/p19-security-secrets-boundary-research.md`](../../docs/setup-evidence/P19/research/p19-security-secrets-boundary-research.md)
- [`../../docs/setup-evidence/P19/research/p19-p20-life-kernel-dependency-map.md`](../../docs/setup-evidence/P19/research/p19-p20-life-kernel-dependency-map.md)
- [`../../docs/setup-evidence/P19/research/p19-p21-p22-integration-dependency-map.md`](../../docs/setup-evidence/P19/research/p19-p21-p22-integration-dependency-map.md)
- [`../../docs/setup-evidence/P19/research/p19-agent-loop-session-isolation-research.md`](../../docs/setup-evidence/P19/research/p19-agent-loop-session-isolation-research.md)
- [`../../docs/setup-evidence/P19/research/p19-discord-dashboard-project-switcher-research.md`](../../docs/setup-evidence/P19/research/p19-discord-dashboard-project-switcher-research.md)
- [`../../docs/setup-evidence/P19/research/p19-observability-audit-evidence-research.md`](../../docs/setup-evidence/P19/research/p19-observability-audit-evidence-research.md)
- [`../../docs/setup-evidence/P19/evidence/p19-definition-verification.md`](../../docs/setup-evidence/P19/evidence/p19-definition-verification.md)
- [`../../docs/setup-evidence/P19/evidence/auditor-gate.md`](../../docs/setup-evidence/P19/evidence/auditor-gate.md)
- [`../../docs/setup-evidence/P19/evidence/p20-waiver-gate-sync.md`](../../docs/setup-evidence/P19/evidence/p20-waiver-gate-sync.md)
