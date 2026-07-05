# P19 Multi-Project Context — Enterprise Implementation Plan

> **For agentic workers:** This plan defines future implementation waves (P19-001..P19-012). Per the P19 phase objective, **NO implementation/deploy/restart is performed in the planning phase.** The P20 axis is **satisfied by operator waiver** (P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK, 2026-06-25); P19 no longer waits on a P20 soak gate. Waves touching P20 production files are held **by operator discretion** (to avoid destabilizing a production system under accepted risk). When execution begins (by operator approval), use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement wave-by-wave. Steps use checkbox (`- [ ]`) syntax for tracking. See `evidence/p20-waiver-gate-sync.md`.

**Goal:** Enable Guinevere to run many projects in parallel without cross-contamination of context, memory, agenda, evidence, consent, surveillance scope, runtime action, and deployment boundary — while sharing one persona and one core brain. P19 is the foundation that P20 Living Autonomy, P21 Voice, P22 Life Integration Hub, and P17 Cross-Device Sync build upon for project-aware behavior.

**Architecture:** A `project_id` dimension is added orthogonally to every project-scoped store (memory, KG, audit, consent, surveillance, agenda, dashboard, session, sensor). The shared persona (mood/yandere/punishment/safe-mode/HARD-STOP) stays **global**. Project isolation is enforced by an application-layer wrapper (`ProjectScopedMemoryStore`) + composite indexes + isolation tests + optional PostgreSQL RLS (defense-in-depth, feature-flagged). LangGraph's native `thread_id` isolation is reused by encoding project into thread IDs. Redis keys are project-prefixed. Per-project secrets live in `secrets/projects/{project_id}/`. Per-project deploy boundaries are gated by project-scoped `consent.autonomy.high_blast` or explicit Faiz approval.

**Tech Stack:** Python/FastAPI, LangGraph (4-node life-mind graph + session subgraphs), PostgreSQL 16 (pgvector, RLS optional), Redis (DB0-5 per ADR-030, key-prefix per project), SOPS/age secrets (per-project files), Prometheus + Grafana (project_id labels), discord.py (`/project` switcher), systemd (per-project config optional).

---

## Global Constraints

(These apply to every wave. Each wave's requirements implicitly include this section.)

- **Planning-only this phase:** NO runtime code, NO deploy, NO restart of production services in P19 planning. Waves execute later, by operator approval (P20 axis satisfied by operator waiver — see `evidence/p20-waiver-gate-sync.md`).
- **Implementation HOLD:** Waves touching P20 production files (`src/life_kernel/heartbeat.py`, `graph.py`, `hermes_brain.py`, `state.py`, `models.py`, `src/core/services/hard_stop_handler.py`, `src/core/main.py`) are **held by operator discretion** — the P20 axis is satisfied by operator waiver (P20 accepted-risk pass, 2026-06-25); these waves are held not because of a pending P20 soak but to avoid destabilizing a production system under accepted risk. NEW files (`src/projects/*`, `tests/projects/*`, `alembic/versions/p19_*.py`, `secrets/projects/*`) and additive migrations are unblocked and ready by operator approval.
- **HARD STOP stays GLOBAL:** `life_kernel:hard_stop` is a single global Redis key. A spoken safe-word halts ALL projects + persona. P19 MUST NOT scope HARD STOP. This is a hard-rejection criterion.
- **Project-local pause ≠ HARD STOP:** `/project pause <name>` sets `project:{project_id}:paused` (per-project, weak — pauses only that project's autonomous work; persona and other projects unaffected). This is distinct from global HARD STOP. Both must be modeled explicitly.
- **Shared persona, isolated context:** One Guinevere persona (mood/yandere/punishment/safe-mode/drift) shared across all projects. Project context (memory/KG/audit/agenda/dashboard/session/sensor) is partitioned per project. Global-scope memories (persona facts, ADRs, safety policies) are visible from every project; project-scoped memories are isolated.
- **Namespace flows everywhere:** `project_id` must flow to memory, KG, audit journal, agenda, dashboard, Discord thread/channel, sensors, deploy actions, finance/email/tasks, and P22 integrations. Any store without `project_id` flow = FAIL.
- **Project switch is explicit and auditable:** Every `/project` switch writes an `audit.audit_trail` row (`project_switched`) with `(actor, from_project, to_project, timestamp, channel_id)`. No silent switch.
- **Consent/surveillance per-project:** Project-scoped consent scopes (surveillance sources, project memory, client/financial actions, P22 integrations) get `project_id` in `consent.consent_ledger` (NULL = global). Safety-critical scopes (persona, emergency, HARD STOP, safe-word) stay global.
- **No cross-project secret leak:** Project A's adapter cannot decrypt/read project B's `secrets/projects/{project_B}/*.enc.yaml`. Secrets are decrypted into an in-memory `ProjectSecretsVault` keyed by `project_id` (NOT env vars — env vars don't isolate within a single shared `guinevere-core` process; SEC-01). Each adapter calls `vault.get(project_id, domain)` and only receives its own. Env vars (`GUINEVERE_{PROJECT}_{KEY}`) are only for optional single-project systemd units.
- **Deploy boundary:** Deploy of project X requires project-scoped `consent.autonomy.high_blast` or explicit Faiz approval. Deploy of one project cannot touch Guinevere core or another project without a policy gate.
- **P20 non-interference:** P19 changes to life_kernel are strictly additive (new `NotRequired` state fields, new columns via migration, new Redis key variants). MUST NOT alter HARD-STOP loop semantics, the 6-interval schedule, the `life_kernel:hard_stop` key contract, `hermes_brain.py`, `graph.py` topology, or the Hermes conversational core without operator approval (P20 axis satisfied by waiver; held to protect production-under-accepted-risk).
- **P21/P22/P17 forward-compat:** P19 owns the project registry; P21/P22/P17 read it and tag data with `project_id`. P21's nullable `project_id` seam becomes a real FK after P19 lands. Migration chain: P19 → P21 → P22.
- **Backfill to `default`:** Existing unscoped data backfills to `project_id = 'default'` (matches P22's default namespace). Idempotent, zero-downtime.
- **Type safety:** No `# type: ignore`, `as any`, bare `except`, empty catch. Pydantic models + typed `ProjectId` (UUID). Strict checks.
- **Single-user:** Faiz-only. RBAC is about data isolation, not user roles. Sub-agents get task-scoped access to one project's data.
- **Sub-agent output discipline:** Every research/audit/implementation sub-agent writes a `.md` file to an explicit `output_path` before returning. Inline-only = FAIL.

---

## Source-of-Truth Documents

| Document | Relationship |
|---|---|
| `AGENTS.md` | Operating contract (§0.1 autonomy exception, §2.5 planner scaffold, §2.9 file-based output) |
| `docs/10-governance/17-ADR_Index_v1.0.md` | ADR registry (P19 ADR to be added) |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Persona safety (F-01..F-15, safe-word global) |
| `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` | Surveillance scope (Appendix A/B/C) |
| `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | Consent taxonomy (§4) |
| `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md` | Migration strategy |
| `adr/ADR-030-redis-db-assignments.md` | Redis DB0-5 assignments |
| `adr/ADR-001/002/003` | Persona safety, safe-word, drift |
| `adr/ADR-010/024` | Surveillance retention, data governance |
| `docs/setup-evidence/P20/` (plan + evidence/continuation) | P20 Living Autonomy Kernel (PRODUCTION PASS HOLD) |
| `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` | P21 (nullable project_id seam) |
| `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` | P22 (P19 Project-Namespace Dependency Map) |
| `docs/setup-evidence/P19/research/*.md` (11 files) | P19 research inputs (this phase) |

---

## P19 Final Name and Mission

**Final name:** **P19 Multi-Project Context**.

**Mission:** Guinevere must run many projects in parallel without cross-contamination of context, memory, agenda, evidence, consent, surveillance scope, runtime action, and deployment boundary. P19 is the foundation so P20 Living Autonomy, P21 Voice, P22 Life Integration Hub, and all future projects can coexist with isolated namespaces but the same shared persona and core brain. Project switching is explicit, auditable, and reversible. The default project is determined when Faiz is silent. HARD STOP remains global. Project-local pause is a distinct, weaker concept.

---

## Scope and Non-Scope

### In Scope
- Project registry (`projects.project_registry` table + `ProjectRegistry` class).
- `project_id` dimension on all project-scoped stores (memory, KG, audit, consent, surveillance, agenda, dashboard, session, sensor, domain actuators).
- Per-project memory/KG partitioning with global-scope memories shared.
- Per-project consent/surveillance scope (project-scoped scopes; safety scopes stay global).
- Project-aware agent loop / session / background cognition.
- Discord `/project` switcher + per-project dashboard/log channels.
- P20 life-kernel project context propagation (additive; held by operator discretion — P20 axis satisfied by waiver).
- Per-project secrets (`secrets/projects/{project_id}/`).
- Per-project observability (Prometheus `project_id` labels).
- Per-project deploy boundaries (policy-gated).
- Migration/backfill from existing unscoped state to `default` project.
- P21/P22/P17 forward-compat (registry read-only, migration chain).

### Non-Scope
- P21 Voice implementation (P19 only provides the `project_id` seam + `/voice project` switcher design).
- P22 Life Integration Hub implementation (P19 only provides the registry + `project_id` columns P22 reads).
- P17 Cross-Device Sync implementation (P19 only provides `project_id` in sync key design).
- P20 Living Autonomy Kernel runtime changes without operator approval (P20 axis satisfied by waiver — not a pending soak gate).
- Runtime code/deploy/restart in this planning phase.
- New LLM providers, new surveillance sources, new integrations beyond what P22 defines.

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED PERSONA (GLOBAL)                       │
│  mood / yandere / punishment / safe-mode / drift / HARD-STOP     │
│  (one Guinevere across all projects; NOT project-scoped)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │              PROJECT REGISTRY                │
        │  projects.project_registry (default, work, personal..) │
        └──────────────────────┬──────────────────────┘
                               │ project_id dimension
        ┌──────────┬───────────┼───────────┬──────────┐
        ▼          ▼           ▼           ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │ MEMORY │ │   KG   │ │ AUDIT  │ │CONSENT │ │SURVEIL.│
   │ prj_id │ │ prj_id │ │ prj_id │ │ prj_id │ │ prj_id │
   │+global │ │+global │ │+global │ │+global │ │+global │
   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
        │          │           │           │          │
        └──────────┴───────────┴───────────┴──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │           LIFE-KERNEL (P20, additive)        │
        │  heartbeat-{prj_id} | session-{prj_id}-...   │
        │  dashboard:{prj_id} | cognition-{prj_id}     │
        └──────────────────────┬──────────────────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        ▼          ▼           ▼           ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │DISCORD │ │ HERMES │ │  LOOP  │ │SENSORS │ │DEPLOY  │
   │/project│ │session:│ │LoopCtx │ │ prj_id │ │ prj_id │
   │switcher│ │{u}:{p} │ │.prj_id │ │ obs    │ │ gate   │
   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

**Key principle:** `project_id` is an orthogonal dimension. Global-scope data (persona, ADRs, safety) is visible from every project. Project-scoped data is isolated by the `ProjectScopedMemoryStore` wrapper + composite indexes + isolation tests + optional RLS.

---

## Project Registry Model

**Table:** `projects.project_registry` (see `p19-database-schema-migration-research.md` §4).

| Field | Type | Purpose |
|---|---|---|
| `id` | UUID PK | Project identity (fixed UUID for `default`: `00000000-0000-0000-0000-000000000001`) |
| `slug` | TEXT UNIQUE | Human-readable (e.g., `work`, `personal`, `default`) |
| `name` | TEXT | Display name |
| `status` | TEXT | `active` / `paused` / `archived` |
| `created_at` / `archived_at` | TIMESTAMPTZ | Lifecycle |
| `metadata` | JSONB | retention policy, integrations config, etc. |
| `default_channel_id` | TEXT | Discord channel default for this project |
| `dashboard_channel_id` | TEXT | Per-project dashboard channel (nullable) |
| `log_channel_id` | TEXT | Per-project log channel (nullable) |
| `accent_color` | TEXT | Optional Discord embed accent |

**Class:** `src/projects/registry.py` — `ProjectRegistry` (create/list/archive/resolve/get). Faiz-only operations (auth-gated, audited).

---

## Namespace Model

**Internal identifier template:** `p19:{project_slug}:{domain}:{resource-id}` (mirrors P22's `p22:<domain>:<provider>:<resource-id>` pattern).

Examples:
- `p19:default:memory:episode:<uuid>`
- `p19:work:kg:entity:<uuid>`
- `p19:personal:audit:event:<uuid>`

**Namespace inheritance rules (aligns with P22 plan §P19):**
1. Unqualified resources fall back to `default` until explicitly reassigned.
2. Project-specific resources are prefixed with the project slug.
3. P19 owns the project registry; P21/P22/P17 read it read-only.
4. No P21/P22/P17 code may create/rename/delete P19 namespaces.

---

## Project Context State Model

**`LifeMindState`** (P20, additive `NotRequired` fields):
- `project_id: NotRequired[Optional[str]]` — current project.
- (existing fields `observations`, `goals`, `commitments`, `concerns`, `decision_context`, `journal_entries`, `recalled_concepts`, `recalled_memories`, `memory_status`, `current_focus` are now per-project via the `project_id`-keyed graph state).

**`SessionState`** (additive):
- `project_id: NotRequired[Optional[str]]`.

**`LoopContext`** (additive):
- `project_id: Optional[UUID] = None` — current project for the loop.

**Active project resolution (priority):**
1. Explicit `/project <name>` (Redis DB0 `project:active:{channel_id}`).
2. Channel-bound mapping (`projects.project_registry.default_channel_id`).
3. `default` project fallback.

---

## Memory Partition Model

(See `p19-memory-namespace-research.md`.)

- `project_id UUID` + `project_scope TEXT DEFAULT 'project'` on `memory.episodes`, `semantic_memories`, `procedural_skills`, `session_summaries`, `kg_entities`, `kg_edges`, `kg_consent_audit`.
- `project_scope = 'global'` for persona/ADR/safety memories (shared).
- `project_scope = 'project'` for project-specific memories (isolated).
- `ProjectScopedMemoryStore` wrapper enforces `WHERE project_id = :pid OR project_scope = 'global'`.
- Composite indexes `(project_id, created_at)`, `(project_id, embedding)`.
- Optional RLS behind feature flag `project:rls_enabled`.

---

## KG Partition Model

- `project_id` on `memory.kg_entities`, `memory.kg_edges`.
- Entity resolution scoped by `project_id` (entity "Alice" in `work` is distinct from `personal`).
- `RecallContextAssembler.assemble(..., project_id)` (in `src/knowledge_graph/query/context.py`) + `KGQueryEngine.search_entities(..., project_id)` (in `src/knowledge_graph/query/engine.py`) filter by project; fusion (`rrf_fusion.py`) + PPR walk (`ppr.py`) carry `project_id`.
- Global-scope KG entities (persona facts, ADR concepts) tagged `project_scope = 'global'`.

---

## Audit Journal Model

- `project_id` on `audit.audit_trail`, `life_kernel.audit_journal`, `memory.kg_consent_audit` (nullable; NULL = global safety event).
- Global hash chain (single chain, `project_id` in canonical payload).
- `write_event()` / `record()` signatures gain `project_id` param (default None = global).
- Audit queryable per-project.

---

## Agenda / Todo Model

- `projects.loop_instances` + `projects.tasks` get `project_id`.
- Goals/commitments/concerns in `LifeMindState` are per-project (graph state keyed by `heartbeat-{project_id}`).
- P20 idle autonomy picks the top-priority project's agenda when Faiz is silent, labeled with the project.

---

## Discord UX Model

(See `p19-discord-dashboard-project-switcher-research.md`.)

- `/project <name>` switcher (mirrors `/focus`/`/casual`; Redis DB0 `project:active:{channel_id}`).
- `/projects list|create|archive|info`.
- Per-project dashboards: `life_kernel:dashboard_message_id:{project_id}` (top-N active).
- Per-project log channels (top-3 dedicated, rest tagged `[project:slug]`).
- Presence: "Working on: work 🛠️" / "[work] Loop active 🔄".
- Every switch audited (`project_switched`).

---

## Dashboard / Log Model

- `DashboardWriter` uses `life_kernel:dashboard_message_id:{project_id}` (was global).
- `DashboardRenderer` renders per-project `LifeMindState`.
- `LogChannel` prefix `[project:slug]` or per-project channel.
- Bounded to top-N active projects to avoid spam.

---

## P20 Life-Kernel Wiring Model

(See `p19-p20-life-kernel-dependency-map.md`.)

- `thread_id = f"heartbeat-{project_id}"` (was hardcoded `"heartbeat"`).
- `thread_id = f"session-{project_id}-{session_id}-{uuid}"`.
- `thread_id = f"cognition-{project_id}"`.
- One `BackgroundCognition` per active project (bounded to N=3).
- `life_kernel:dashboard_message_id:{project_id}` (was global).
- `life_kernel:{project_id}:world:{key}` (was `life_kernel:world:{key}`).
- HARD STOP `life_kernel:hard_stop` STAYS GLOBAL.
- All changes additive; P20 axis satisfied by operator waiver (held by operator discretion for P20 production files).

---

## P21 Voice Dependency Map

(See `p19-p21-p22-integration-dependency-map.md` §2.)

- P21 voice episodes carry nullable `project_id` (P21 forward-compat seam).
- P19 makes the seam meaningful: voice memory partitioned by `project_id`.
- `/voice project <name>` switcher OR voice channel per project.
- Proactive voice brief per-project.
- P21 does NOT depend on P19 landing first (nullable works); P19 enhances it.

---

## P22 Integration Dependency Map

(See `p19-p21-p22-integration-dependency-map.md` §3 + P22 plan §P19.)

- P19 owns `projects.project_registry`; P22 reads it read-only.
- `project_id` on `audit.integration_api_log` + P22 world-model tables.
- Namespace resolution API: `resolve_project(slug) -> project_id`.
- P22 template `p22:<domain>:<provider>:<resource-id>` → project-qualified `<project>:p22:...`.
- Migration chain P19 → P22.

---

## P17 Cross-Device Dependency Map

- P17 syncs state across devices; `project_id` is part of the sync key.
- P19 provides `project_id` in sync message design + registry as source of truth.
- P17 lands independently; references `project_id` once P19 exists.

---

## Consent / Surveillance Boundary

(See `p19-surveillance-consent-scope-research.md`.)

- `consent.consent_ledger` gets `project_id UUID NULL` (NULL = global).
- `check_consent(scope, project_id=None)` — project-scoped row wins over global.
- Redis cache: `consent:{project_id}:{scope}` (DB2) + `consent:{scope}` (global).
- Project-scoped scopes: surveillance sources, project memory, client/financial actions, P22 integrations, project autonomy.
- Global scopes (stay global): persona.normal/escalated/y5, emergency, HARD-STOP/safe-word/distress/crisis, autonomy.high_blast (unless project-scoped).
- Surveillance events get `project_id` (nullable; NULL → `default`).
- Revocation cascade: project-scoped for project consents; global for persona/safety consents.
- Surveillance confrontation block stays GLOBAL (safe-mode/distress/crisis).

---

## Security / Secrets Model

(See `p19-security-secrets-boundary-research.md`.)

- `secrets/projects/{project_id}/{domain}.enc.yaml` (least-privilege, independent rotation).
- Env vars: `GUINEVERE_{PROJECT}_{KEY}` (process-scoped).
- Shared age recipient (Faiz's key) — OK (per-file encryption).
- Per-project deploy boundary: `consent.autonomy.high_blast` (project-scoped) or Faiz approval.
- Deploy of one project cannot touch Guinevere core or another project without policy gate.
- Key compromise isolates to one project (separate secret files).

---

## DB Schema Plan

(See `p19-database-schema-migration-research.md`.)

- `projects.project_registry` (new).
- `project_id` column on ~14 tables across 7 schemas.
- `project_scope` on memory/KG tables.
- Composite indexes.
- Optional RLS (feature-flagged).
- Two migrations: `p19_001_project_namespaces` (nullable + backfill), `p19_002_project_id_not_null` (NOT NULL with DEFAULT after backfill verified).

---

## Redis Key Model

| Key | Scope | DB |
|---|---|---|
| `life_kernel:hard_stop` | **GLOBAL** (unchanged) | (per P20) |
| `life_kernel:dashboard_message_id:{project_id}` | per-project | (per P20) |
| `life_kernel:{project_id}:world:{key}` | per-project | (per P20) |
| `project:active:{channel_id}` | per-channel active project | DB0 |
| `project:{project_id}:paused` | per-project pause flag | DB0 |
| `consent:{project_id}:{scope}` | per-project consent cache | DB2 |
| `consent:{scope}` | global consent cache (unchanged) | DB2 |
| `hermes:session:{user_id}:{project_id}` | per-project session | DB4 |
| `feature:projects:enabled` | P19 feature flag | DB5 |

---

## Migration Plan

1. `p19_001_project_namespaces` (down_revision `p20_001_life_kernel_schema`): create `projects.project_registry` + seed `default`; add nullable `project_id` (+ `project_scope` on memory/KG); composite indexes; batched backfill to `default`.
2. `p19_002_project_id_not_null` (down_revision `p19_001`): make `project_id` NOT NULL with DEFAULT for life_kernel/memory/projects tables (consent/audit/surveillance stay nullable).
- Idempotent (`IF NOT EXISTS`, `WHERE project_id IS NULL` guard).
- Non-breaking to P20 (additive).

---

## Rollback Plan

- `alembic downgrade p20_001_life_kernel_schema` removes P19 migrations (drops `project_id`/`project_scope` columns + `projects.project_registry` table). **Base rows are preserved** (episodes/kg_entities/audit rows remain), but the `project_id` partitioning data and the `default`-project assignment are **lost** on downgrade (the columns are dropped). Re-running `p19_001` re-adds columns and re-backfills to `default`. This is NOT "data intact" for the P19 partitioning dimension — only base (non-P19) data is preserved.
- Feature flag `feature:projects:enabled = false` disables project-scoping at runtime (degrades to global behavior, `project_id = default`).
- `/project default` resets active project.
- P20 unaffected (additive changes only).

---

## Observability / Metrics / Logging Plan

(See `p19-observability-audit-evidence-research.md`.)

- `project_id` Prometheus label on relevant metrics (recall, agent-loop, audit, llm-cost, surveillance).
- Global metrics stay unlabeled (HARD-STOP, persona, infra).
- Grafana dashboards updated to filter/aggregate by `project_id`.
- Alertmanager rules filter by `project_id`.
- Per-project retention policies (`projects.project_registry.metadata.retention`).
- Per-project log channels / `[project:slug]` prefix.

---

## Testing Strategy

- **Isolation tests:** `test_memory_isolation` (write A, recall B → empty), `test_session_isolation`, `test_kg_entity_isolation`, `test_consent_isolation`, `test_secret_isolation`, `test_audit_project_id`.
- **Migration tests:** `test_migration_preserves_p20_state`, `test_migration_idempotent`, `test_default_project_seeded`, `test_backfill_complete`, `test_fk_integrity`.
- **Regression:** P20 `tests/life_kernel/` must still pass (all current focused tests pass; exact count captured in evidence).
- **Red-team:** attempt cross-project memory leak via recall, dashboard, session, KG entity resolution.
- **Boundary:** HARD STOP global (test: project pause does NOT halt other projects); safe-word halts all.

---

## Soak Strategy

- P19-012 soak: operator-defined duration (P20's 24h soak was waived by operator; P19 defines its own soak per operator approval, not inherited from LK-017).
- Track: `p19_projects_active`, `p19_memory_isolation_test_pass_total`, `p19_project_switch_total`, per-project recall latency, audit write latency.
- P20 kernel metrics must NOT regress (additive labels only).
- HARD STOP tested: `redis SET life_kernel:hard_stop 1` → all projects halt; `DEL` → recovery.

---

## Deployment Strategy (for future implementation)

- Feature-flag gated (`feature:projects:enabled`, default OFF).
- Config-gated rollout (no blue-green for single-user): flag-on → migrate → smoke → soak → flag-stays-on.
- P20 non-interference: deploy P19 changes to `guinevere-core` by operator approval (P20 axis satisfied by waiver); restart ONLY core; verify other services undisturbed.
- Per-project deploy boundaries documented but not exercised in P19 definition phase.

---

## Hard Rejection Criteria (binary FAIL)

1. Plan does not guarantee `project_id` flows to memory/KG/audit/agenda/dashboard/sensors/actions → **FAIL**.
2. Project switch not explicit and auditable → **FAIL**.
3. Shared persona causes cross-project memory leak → **FAIL**.
4. Consent/surveillance scope not per-project → **FAIL**.
5. HARD STOP not global → **FAIL**.
6. Project pause conflated with HARD STOP global without clear model → **FAIL**.
7. P20 autonomy not project-aware → **FAIL**.
8. P21/P22 dependency ignored → **FAIL**.
9. Deploy of another project can touch Guinevere without policy gate → **FAIL**.
10. Secrets/env can leak between projects → **FAIL**.
11. Implementation waves do not reach deploy/soak/final production gate → **FAIL**.
12. Sub-agent output inline-only without file → **FAIL**.
13. "Complete" claimed without evidence + double audit → **FAIL**.

All mitigated in this plan (see per-section ✅ MITIGATED notes and wave scaffolds).

---

## Dependency Map

```text
P19-001 (governance + ADR + docs sync) ──────────────────────┐
P19-002 (project registry / domain models) ◄── 001 ──────────┤
P19-003 (DB schema + migrations) ◄── 002 ────────────────────┤
P19-004 (memory/KG namespace partition) ◄── 003 ─────────────┤
P19-005 (P20 life-kernel project context) ◄── 003 [held by operator — P20 axis satisfied by waiver] ─┤
P19-006 (project-aware sensors and actions) ◄── 004,005 ─────┤
P19-007 (Discord dashboard/log/switcher UX) ◄── 002,006 ─────┤
P19-008 (project-aware agent/session orchestration) ◄── 004,006 ─┤
P19-009 (consent/surveillance scoped enforcement) ◄── 003,004 ─┤
P19-010 (observability/audit/evidence integration) ◄── 005..009 ─┤
P19-011 (migration/backfill from unscoped state) ◄── 003 ────┤
P19-012 (deploy/canary/rollback/soak/final gate) ◄── ALL ────┘
```

---

## Parallelism Map (per AGENTS.md §2.4)

- **P19-001**: parallel (governance/docs, no code conflict).
- **P19-002**: sequential after 001 (registry is foundation).
- **P19-003**: sequential after 002 (migration needs registry).
- **P19-004**: parallel with 005-prep (memory/KG partition is independent of life-kernel wiring) but depends on 003.
- **P19-005**: sequential after 003; **held by operator discretion** (touches P20 production files; P20 axis satisfied by waiver — not a pending soak gate).
- **P19-006**: parallel with 007/008/009 after 004+005 (independent surfaces: sensors vs Discord vs agent-loop vs consent).
- **P19-007**: parallel with 006/008/009.
- **P19-008**: parallel with 006/007/009.
- **P19-009**: parallel with 006/007/008.
- **P19-010**: sequential after 005-009 (observability integrates all).
- **P19-011**: parallel with 010 (backfill is independent of observability) but depends on 003.
- **P19-012**: sequential after ALL (deploy/soak/final gate).

Default if not marked: sequential (safer).

---

## Collision Scan

| Shared Resource | Collision Rule |
|---|---|
| `src/life_kernel/state.py` | P19 adds `project_id` NotRequired; P21 adds voice fields. Both additive. **P19 first; P21 rebases.** |
| `src/memory/models.py` | P19 owns `project_id` column; P21's nullable seam satisfied by P19's column. **P19 owns.** |
| `alembic/versions/` | Chain P19 → P21 → P22. **P19 first.** |
| `docs/10-governance/17-ADR_Index_v1.0.md` | Parent-only single-owner; P19 ADR pointer added in 001. |
| `docs/setup-evidence/P19/README.md` | Single-owner (this phase). |
| `src/life_kernel/heartbeat.py` | P19 additive `thread_id` change; **held by operator discretion (P20 axis satisfied by waiver).** |
| `src/discord/hermes_conversational.py` | P19 adds `project_id` to turn path; P21 extracts `_process_turn_core`. **Sequence: P19 project_id threading, then P21 refactor** (or coordinate). |
| `secrets/` | P19 adds `secrets/projects/`; no conflict with existing. |
| `CHECKLIST.md` / `PROGRESS.md` | Parent-only; updated in finalize. |

**0 HIGH collision risk** (all changes additive or sequenced). P20 production files touched only by operator approval (P20 axis satisfied by waiver).

---

## Implementation Waves (for later — NOT executed this phase)

Each wave below is a future implementation step with its own verification scaffold. **P20-production-file waves held by operator discretion (P20 axis satisfied by waiver); NEW files + additive migrations unblocked and ready by operator approval — but not executed in this planning phase.**

### Wave P19-001: Governance + ADR + Docs Sync
- **Files:** `adr/ADR-052-multi-project-context.md` (new — ADR-039 is reserved for Consent & Revocation Policy per `17-ADR_Index_v1.0.md:127`; next free after ADR-050 implemented is ADR-052, since ADR-051 is reserved for Compliance & Data Residency), `docs/10-governance/17-ADR_Index_v1.0.md` (pointer), `docs/setup-evidence/P19/README.md` (status update), `CHECKLIST.md`/`PROGRESS.md` (P19 rows).
- **Parallel:** parallel (governance/docs).
- **Scaffold:**
  - Expected Files: as above.
  - Forbidden Patterns: ADR number `ADR-039`/`ADR-040`..`ADR-051` (reserved backlog); ADR without P20/P21/P22 cross-refs; status without "P20 AXIS SATISFIED BY OPERATOR WAIVER — IMPLEMENTATION HOLD BY OPERATOR / READY FOR P19 IMPLEMENTATION WAVES" (or unqualified historical "P20 production-pass" in current-status text).
  - Required Commands: `grep -c "P19" CHECKLIST.md` → ≥1; `test -f adr/ADR-052-multi-project-context.md` → exit 0; `grep ADR-052 docs/10-governance/17-ADR_Index_v1.0.md` → ≥1.
  - Evidence: `docs/setup-evidence/P19/evidence/P19-001/verification.md`, `auditor-gate.md`.
  - Hard Rejection: ADR uses reserved backlog number; ADR missing P20/P21/P22 dependency notes; status not held.
  - Rollback/Re-run: revert ADR + README; idempotent.
  - Parent Verification: `cat adr/ADR-052-multi-project-context.md`; `grep ADR-052 docs/10-governance/17-ADR_Index_v1.0.md`.
  - Auditor Assignment: docs-consistency.
- **ADR content requirements (round-1 fixes DOC-01/DOC-05/OBS-03):** Cross-refs P20 (non-interference, gated on pass), P21 (nullable project_id seam → real FK), P22 (registry read-only, `p22:` namespace template maps to P19 `default` sentinel UUID `00000000-0000-0000-0000-000000000001`), P17 (sync key references project_id once both exist). Documents evidence root convention: `docs/setup-evidence/` for Guinevere-core phases; `evidence/projects/{project_id}/` for runtime projects.

### Wave P19-002: Project Registry / Domain Models
- **Files:** `src/projects/__init__.py`, `src/projects/registry.py` (`ProjectRegistry`), `src/projects/types.py` (`ProjectId`, `Project`, `ProjectStatus`), `src/projects/exceptions.py`, `tests/projects/test_registry.py`.
- **Depends on:** P19-001. **Parallel:** sequential after 001.
- **Scaffold:**
  - Expected Files: as above.
  - Forbidden Patterns: `# type: ignore`, `as any`, bare `except`, untyped `project_id` (must be UUID/ProjectId).
  - Required Commands: `python -m pytest tests/projects/test_registry.py -v` → exit 0.
  - Evidence: `P19-002/verification.md`, `auditor-gate.md`.
  - Hard Rejection: registry without audit on create/archive; no `default` seed support.
  - Rollback/Re-run: delete `src/projects/`; idempotent.
  - Parent Verification: `python -m pytest tests/projects/ -v`.
  - Auditor Assignment: architecture, data-memory-isolation.

### Wave P19-003: Database Schema + Migrations
- **Files:** `alembic/versions/p19_001_project_namespaces.py`, `alembic/versions/p19_002_project_id_not_null.py` (NOT NULL applied in P19-011 after backfill), `tests/projects/test_migration_*.py`.
- **Depends on:** P19-002. **Parallel:** sequential after 002.
- **Round-1 fixes:**
  - DB-02 (hypertables): `surveillance.events` and `health.*` are TimescaleDB hypertables. `project_id` is a plain column with a btree index (NOT a partition key for MVP). Chunk-by-project partitioning is a future optimization. Test migration on a hypertable without error.
  - DB-03 (`domain_mind_state` unique constraint swap): `domain` UNIQUE → `(project_id, domain)` UNIQUE. Do the constraint swap inside a transaction: backfill `project_id = default` BEFORE `DROP CONSTRAINT domain_unique`, then `ADD CONSTRAINT (project_id, domain)`. Document ordering.
  - DB-04 (sentinel UUID): document the fixed `default` UUID `00000000-0000-0000-0000-000000000001` in P19-001 ADR so backfill references it deterministically.
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: DROP/RENAME of existing columns (except constraint swap inside transaction); non-idempotent DDL; missing `IF NOT EXISTS`; NOT NULL applied before backfill (belongs in P19-011/p19_002 with pre-check); hypertable migration error.
  - Required Commands: `alembic upgrade head` → exit 0; `alembic downgrade p20_001_life_kernel_schema && alembic upgrade head` → exit 0; `python -m pytest tests/life_kernel/ -q` → all current focused tests pass; exact count captured in evidence (P20 regression); `psql -c "\d life_kernel.domain_mind_state"` shows `(project_id, domain)` unique; hypertable migration test passes; **verification-tooling note**: use `matches=$(find ... -name "*p19*"); [ -n "$matches" ]` to check file existence, NOT `find ... && echo EXISTS` (find exits 0 on no-match — see `evidence/migration-false-positive-investigation.md`).
  - Evidence: `P19-003/verification.md`, `auditor-gate.md`.
  - Hard Rejection: migration breaks P20; non-idempotent; `default` not seeded; FK integrity broken; hypertable migration fails; constraint swap outside transaction (DB-03).
  - Rollback/Re-run: `alembic downgrade p20_001_life_kernel_schema`.
  - Parent Verification: `alembic current`; `psql -c "SELECT slug FROM projects.project_registry"`; `psql -c "\d life_kernel.domain_mind_state"`.
  - Auditor Assignment: database-migration, data-memory-isolation.

### Wave P19-004: Memory / KG Namespace Partition
- **Files:** `src/projects/memory_store.py` (`ProjectScopedMemoryStore` wrapper), modify `src/hermes/_memory_bridge.py` (add `project_id` to `recall_for_context` + `store_conversation`), `src/life_kernel/p18_adapter.py` (add `project_id`, remove hardcoded `principal="guinevere_core"` in favor of project-aware principal), `src/life_kernel/p16_adapter.py` (add `project_id`), `src/knowledge_graph/query/context.py` (`RecallContextAssembler.assemble(..., project_id)` — add `project_id` filter), `src/knowledge_graph/query/engine.py` (`KGQueryEngine.search_entities(..., project_id)` — add `project_id` filter to entity/edge queries), `src/knowledge_graph/query/rrf_fusion.py` (carry `project_id` through fusion), `src/knowledge_graph/query/ppr.py` (scope PPR walk by `project_id`), `tests/projects/test_memory_isolation.py`, `tests/projects/test_kg_isolation.py`.
- **KG target-path note (P19-000 fix 2):** the original plan referenced a non-existent `src/knowledge_graph/recall.py`. The actual runtime KG recall path is: `src/hermes/_memory_bridge.py:recall_for_context` → `src/knowledge_graph/query/engine.py:KGQueryEngine.search_entities` + `src/knowledge_graph/query/context.py:RecallContextAssembler.assemble`, with fusion in `rrf_fusion.py` and graph walk in `ppr.py`. P19 threads `project_id` through these real files (no orphan KG file created).
- **Depends on:** P19-003. **Parallel:** parallel with 005-prep.
- **Round-1 fixes:**
  - DATA-02 (pgvector threshold): for single-user scale (thousands of episodes), composite index `(project_id, embedding)` + filtered brute-force is fine. Document threshold: >50k episodes/project → partial ivfflat index per project. Not a blocker for MVP.
  - DATA-03 (DNR disambiguation): `do_not_recall` on a `project_scope='global'` row = global DNR (all projects' recall blocked). `do_not_recall` on a `project_scope='project'` row = project-scoped DNR (only that project's recall blocked). The `project_scope` column disambiguates. Document.
  - DATA-04 (KG entity resolution): entity resolution query includes `WHERE project_id = :pid OR project_scope='global'`. Test: entity "Alice" in `work` ≠ "Alice" in `personal` (distinct entity rows).
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: recall query without `project_id`/`project_scope` filter; `principal="guinevere_core"` hardcoded without project fallback; cross-project JOIN; KG entity resolution without `project_id` filter (DATA-04).
  - Required Commands: `python -m pytest tests/projects/test_memory_isolation.py tests/projects/test_kg_isolation.py -v` → exit 0; `test_kg_entity_isolation`: entity "Alice" in work ≠ personal.
  - Evidence: `P19-004/verification.md`, `auditor-gate.md`.
  - Hard Rejection: memory leak across projects (test fails); global memories not visible from projects; KG entity cross-project merge (DATA-04); DNR scope ambiguous (DATA-03 — resolved by scope column).
  - Rollback/Re-run: revert wrapper; `project_id=None` default (global behavior).
  - Parent Verification: run isolation tests + KG entity isolation test.
  - Auditor Assignment: data-memory-isolation, architecture.

### Wave P19-005: P20 Life-Kernel Project Context Propagation (split into 005a/005b/005c — round-1 fix P20-01/DEPLOY-01/P20-02)
- **Files:** modify `src/life_kernel/state.py` (additive `project_id` NotRequired), `src/life_kernel/heartbeat.py` (`thread_id=f"heartbeat-{project_id}"` when flag on), `src/life_kernel/graph.py` (project_id in state + per-project adapter instances, no shared `_ADAPTERS` mutation), `src/life_kernel/cognition.py` (per-project instances, bounded N=3, CPU/RAM budget ≤1 core total, idle projects pause), `src/life_kernel/dashboard_writer.py` (`dashboard_message_id:{project_id}`), `src/life_kernel/redis_client.py` (`{project_id}:world:`), `src/life_kernel/session_graph.py` (`session-{project_id}-...`), `src/life_kernel/self_improve.py`, `src/core/main.py` (project-aware lifespan), `tests/life_kernel/test_project_context.py`, `tests/life_kernel/test_checkpoint_isolation.py`.
- **Depends on:** P19-003. **Parallel:** sequential. **Held by operator discretion** (P20 production files — 9 files touched, highest-risk wave; P20 axis satisfied by waiver — not a pending soak gate).
- **Sub-waves (round-1 fix P20-01 — split to bound blast radius):**
  - **P19-005a (zero-risk additive):** Add `NotRequired[Optional[str]] project_id` to `LifeMindState`/`SessionState` only. Checkpoint-replay-safe (fields default absent). P20 regression test must pass.
  - **P19-005b (feature-flagged thread_id):** Change `thread_id` selection to be conditional on `feature:projects:enabled`. When OFF → `thread_id="heartbeat"` (legacy, P20-compatible). When ON → `thread_id=f"heartbeat-{project_id}"`. **DEPLOY-01 fix:** the flag gates the actual behavior change, not just surface features. P20 regression test with flag OFF must pass (legacy behavior).
  - **P19-005c (full project-aware):** Per-project `BackgroundCognition` (bounded N=3), per-project dashboard/log, per-project world-state keys. Only after operator approval to touch P20 production files (P20 axis satisfied by waiver; 005b feature-flag-gated re-soak by operator-defined duration).
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: HARD STOP scoped per project; `thread_id.*=.*"heartbeat"$` hardcoded unconditionally (must be conditional on flag — grep `heartbeat.py` for bare `thread_id="heartbeat"` returns 0 when flag-aware code written); P20 semantics altered when flag OFF; `_ADAPTERS` global mutated unsafely across projects (must use per-project adapter instances OR `recall(context)` reads project_id from context).
  - Required Commands: `python -m pytest tests/life_kernel/ -q` → all current focused tests pass; exact count captured in evidence (P20 regression, flag OFF); `grep -nE 'thread_id\s*=\s*"heartbeat"' src/life_kernel/heartbeat.py` → 0 unconditional matches (all flag-conditional); `redis SET life_kernel:hard_stop 1` → ALL projects halt; `DEL` → recovery; checkpoint isolation test (`heartbeat-work` state ≠ `heartbeat-personal`).
  - Evidence: `P19-005/verification.md`, `auditor-gate.md`.
  - Hard Rejection: HARD STOP not global; P20 regression with flag OFF; heartbeat not project-aware when flag ON; bare `thread_id="heartbeat"` unconditional; `_ADAPTERS` cross-project leak.
  - Rollback/Re-run: `redis SET feature:projects:enabled false` (restores legacy behavior); revert life_kernel changes.
  - Parent Verification: `python -m pytest tests/life_kernel/ -q`; live Discord per-project dashboard; `grep thread_id src/life_kernel/heartbeat.py`.
  - Auditor Assignment: P20-integration, runtime-deploy-readiness, safety-consent.

### Wave P19-006: Project-Aware Sensors and Actions (split into 006a-006e — P19-000 fix 6; one sub-agent per sub-wave)

Per P19-000 fix 6, P19-006 is split into 5 sub-waves, each owned by exactly one implementation sub-agent. SEC-01 fix (process-scoped env vars don't isolate within one process): secrets are NOT loaded into env vars for in-process multi-project; `ProjectSecretsVault` decrypts per-project secret files into an in-memory dict keyed by `project_id`; each adapter calls `vault.get(project_id, domain)` and only receives its own. Env vars (`GUINEVERE_{PROJECT}_*`) are only for optional single-project systemd units. Depends on: P19-004, P19-005. Parallel: sub-waves 006b-006e parallel after 006a.

#### Wave P19-006a: Secrets Vault (`src/projects/secrets_vault.py`)
- **Files:** `src/projects/secrets_vault.py` (`ProjectSecretsVault` — in-memory dict keyed by `project_id`; `get(project_id, domain)`, `load(project_id, path)`), `tests/projects/test_secret_isolation.py`.
- **Sub-agent:** exactly one implementer.
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: adapter reading another project's secret from env (must use vault); secret loaded into shared env for in-process multi-project; `# type: ignore`; bare `except`.
  - Required Commands: `python -m pytest tests/projects/test_secret_isolation.py -v` → exit 0; `test_secret_isolation`: project A `vault.get(project_A, "gmail")` returns project A's token; `vault.get(project_B, "gmail")` returns project B's (or None); project A cannot access project B's token.
  - Evidence: `P19-006a/verification.md`, `auditor-gate.md`.
  - Hard Rejection: cross-project secret read (SEC-01).
  - Rollback/Re-run: `project_id=None` default (global vault behavior).
  - Parent Verification: run `test_secret_isolation.py`.
  - Auditor Assignment: security-secrets.

#### Wave P19-006b: Sensors (`src/life_kernel/sensors.py` + sensor_adapters)
- **Files:** modify `src/life_kernel/sensors.py` (project_id in observation), `src/life_kernel/sensor_adapters/*.py` (project_id payload), `tests/projects/test_sensor_isolation.py`.
- **Sub-agent:** exactly one implementer.
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: sensor observation without `project_id`; global-only sensor registry for multi-project.
  - Required Commands: `python -m pytest tests/projects/test_sensor_isolation.py -v` → exit 0.
  - Evidence: `P19-006b/verification.md`, `auditor-gate.md`.
  - Hard Rejection: sensor data leaks across projects.
  - Rollback/Re-run: `project_id=None` default.
  - Parent Verification: run `test_sensor_isolation.py`.
  - Auditor Assignment: data-memory-isolation, P20-integration.

#### Wave P19-006c: Finance (`src/finance/plugin.py`)
- **Files:** modify `src/finance/plugin.py` (project_id in transaction recording; use `financial.transactions.project_id` which already exists), `tests/projects/test_finance_project_aware.py`.
- **Sub-agent:** exactly one implementer.
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: finance transaction without `project_id`; global-only finance config for multi-project.
  - Required Commands: `python -m pytest tests/projects/test_finance_project_aware.py -v` → exit 0.
  - Evidence: `P19-006c/verification.md`, `auditor-gate.md`.
  - Hard Rejection: finance data not project-aware.
  - Rollback/Re-run: `project_id=None` default.
  - Parent Verification: run `test_finance_project_aware.py`.
  - Auditor Assignment: data-memory-isolation.

#### Wave P19-006d: Gmail (`src/gmail/*`)
- **Files:** modify `src/gmail/consent_manager.py` (project_id in consent check — `check_consent(scope, project_id)`), `src/gmail/router.py` (project_id in pipeline), `src/gmail/metrics.py` (project_id label), `tests/projects/test_gmail_project_aware.py`.
- **Sub-agent:** exactly one implementer.
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: gmail consent check without `project_id`; gmail metrics without `project_id` label.
  - Required Commands: `python -m pytest tests/projects/test_gmail_project_aware.py -v` → exit 0.
  - Evidence: `P19-006d/verification.md`, `auditor-gate.md`.
  - Hard Rejection: gmail not project-aware; consent check ignores project_id.
  - Rollback/Re-run: `project_id=None` default.
  - Parent Verification: run `test_gmail_project_aware.py`.
  - Auditor Assignment: safety-consent, data-memory-isolation.

#### Wave P19-006e: Wearable + X Poster (`src/wearable/*`, `src/x_poster/*`)
- **Files:** modify `src/wearable/health_consent.py` (project_id), `src/wearable/metrics.py` (project_id label), `src/x_poster/config.py` (project_id), `src/x_poster/metrics.py` (project_id label), `tests/projects/test_wearable_xposter_project_aware.py`.
- **Sub-agent:** exactly one implementer.
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: wearable/x_poster metrics without `project_id` label; wearable consent without `project_id`.
  - Required Commands: `python -m pytest tests/projects/test_wearable_xposter_project_aware.py -v` → exit 0.
  - Evidence: `P19-006e/verification.md`, `auditor-gate.md`.
  - Hard Rejection: wearable/x_poster not project-aware.
  - Rollback/Re-run: `project_id=None` default.
  - Parent Verification: run `test_wearable_xposter_project_aware.py`.
  - Auditor Assignment: data-memory-isolation.

### Wave P19-007: Discord Dashboard / Log / Project Switcher UX
- **Files:** `src/discord/cmd_project.py` (`/project`, `/projects`), modify `src/discord/_command_registry.py` (register), `src/life_kernel/dashboard.py` (per-project render), `src/life_kernel/log_channel.py` (project prefix), `tests/projects/test_project_switcher.py`, `tests/projects/test_dashboard_isolation.py`.
- **Depends on:** P19-002, P19-006. **Parallel:** parallel with 006/008/009.
- **Round-1 fixes:** ARCH-03 (dashboard top-N=3 + LRU eviction for dashboards beyond N, matching log channel top-3); SAFE-04 (`/project` checks `life_kernel:hard_stop` BEFORE applying switch; if HARD STOP active, refuse switch + neutral ack).
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: `/project` switch without audit row; dashboard cross-project leak; no `default` fallback; `/project` switch applied during active HARD STOP; dashboard count unbounded (must cap N=3 + LRU).
  - Required Commands: `python -m pytest tests/projects/test_project_switcher.py tests/projects/test_dashboard_isolation.py -v` → exit 0; red-team: (a) `/project work` writes `project_switched` audit row; (b) `redis SET life_kernel:hard_stop 1` then `/project personal` → refused + neutral ack.
  - Evidence: `P19-007/verification.md`, `auditor-gate.md`.
  - Hard Rejection: non-auditable switch; dashboard leak; undefined default; switch during HARD STOP (SAFE-04); unbounded dashboards (ARCH-03).
  - Rollback/Re-run: `/project default`; feature flag off.
  - Parent Verification: `/projects list`; `/project work`; `psql -c "SELECT * FROM audit.audit_trail WHERE event_type='project_switched' LIMIT 1"`.
  - Auditor Assignment: docs-consistency (UX), safety-consent (audit).

### Wave P19-008: Project-Aware Agent / Session Orchestration
- **Files:** modify `src/loops/context.py` (`LoopContext.project_id`), `src/loops/prompts.py` (project in volatile tier), `src/loops/state_store.py` (persist project_id), `src/hermes/_session_adapter.py` (`hermes:session:{user_id}:{project_id}`), `src/discord/hermes_conversational.py` (project_id in turn path — additive param, default None), `tests/projects/test_session_isolation.py`, `tests/projects/test_agent_loop_project.py`.
- **Depends on:** P19-004, P19-006. **Parallel:** parallel with 006/007/009.
- **Round-1 fix P21P22-01 (coordination with P21-003 refactor):** P19-008 threads `project_id` as an additive parameter to `_process_and_respond()` FIRST (default None = global). P21-003 then extracts `_process_turn_core(content, ..., project_id=None)` including the P19 param. Combined signature documented: `_process_turn_core(*, content, author_id, channel_id, session_factory, shadow_pipeline, source_type="discord", project_id=None) -> ProcessedTurn`. Sequence: P19 project_id param → P21 refactor (P21 rebases onto P19).
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: session key without `project_id`; `LoopContext` without `project_id`; recall not project-filtered; `_process_and_respond` without `project_id` param (additive).
  - Required Commands: `python -m pytest tests/projects/test_session_isolation.py tests/projects/test_agent_loop_project.py -v` → exit 0; existing `tests/discord/test_hermes_conversational.py` still pass (no regression from additive param).
  - Evidence: `P19-008/verification.md`, `auditor-gate.md`.
  - Hard Rejection: session leak across projects; agent loop not project-aware; P21 refactor coordination broken (signature incompatible).
  - Rollback/Re-run: `project_id=None` default (global behavior).
  - Parent Verification: run session isolation tests; `tests/discord/test_hermes_conversational.py` pass.
  - Auditor Assignment: architecture, data-memory-isolation, P20-integration.

### Wave P19-009: Consent / Surveillance Scoped Policy Enforcement
- **Files:** modify `src/surveillance/consent_gate.py` (`check_consent(scope, project_id)`), `src/surveillance/consumer.py` (pass project_id), `src/surveillance/models.py` (project_id on events), `src/discord/cmd_consent.py` (project arg), `src/wearable/health_consent.py`, `src/gmail/consent_manager.py`, `tests/projects/test_consent_isolation.py`.
- **Depends on:** P19-003, P19-004. **Parallel:** parallel with 006/007/008.
- **Round-1 fixes:**
  - SAFE-01 (project pause restoration): `/project resume <name>` requires explicit Faiz readiness (mirrors safe-word restore). P20 idle autonomy may NOT auto-resume a paused project; it skips paused projects and picks the next active one.
  - SAFE-03 (`consent.autonomy.high_blast` scope): becomes **per-project** (project-scoped row). A project's high-blast autonomy applies ONLY to that project's deploy scope. Guinevere core deploy is NEVER covered by project autonomy — always requires explicit Faiz approval (AGENTS.md §0.1).
  - ARCH-04 (cross-project recall consent): add `consent.memory.cross_project` as a new global scope (Faiz-approved, audited) for `recall_across_projects()`. Reuse `consent.autonomy.high_blast` as fallback if cross_project scope not granted.
  - SEC-04 (break-glass per-project): add `consent.emergency.break_glass_project` scope (project-scoped, time-bound max 4h, audited).
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: `check_consent` without `project_id` param; safety scopes (persona.normal/escalated/y5, emergency.minimum_necessary) scoped per project; HARD STOP scoped; consent cache not fail-closed; P20 autonomy auto-resuming a paused project (SAFE-01); project high_blast autonomy covering Guinevere core deploy (SAFE-03).
  - Required Commands: `python -m pytest tests/projects/test_consent_isolation.py -v` → exit 0; red-team: (a) `/project pause work` does NOT halt personal (only `project:work:paused` set; persona + other projects unaffected); (b) safe-word halts ALL projects (`life_kernel:hard_stop` global); (c) revoke project consent cascades only that project; (d) during global safe-mode, surveillance confrontation blocked for ALL projects (SAFE-02); (e) P20 idle autonomy skips paused project and picks next active (SAFE-01); (f) project high_blast autonomy cannot deploy Guinevere core (SAFE-03).
  - Evidence: `P19-009/verification.md`, `auditor-gate.md`.
  - Hard Rejection: consent not per-project; HARD STOP scoped; project pause == HARD STOP; safety scopes project-scoped; autonomy auto-resume paused project; project autonomy touches core.
  - Rollback/Re-run: `project_id=None` (global-only behavior).
  - Parent Verification: run consent isolation + red-team tests (a)-(f).
  - Auditor Assignment: safety-consent, security-secrets, data-memory-isolation.

### Wave P19-010: Observability / Audit / Evidence Integration
- **Files:** modify `src/loops/audit_writer.py` (project_id), `src/life_kernel/domain_minds/durability.py` (project_id), `src/knowledge_graph/consent/audit.py` (project_id), metrics modules (project_id labels), `monitoring/grafana/dashboards/guinevere-p19-projects.json` (new — round-1 fix OBS-04) or panel in `guinevere-agent-loop.json`, `tests/projects/test_audit_project_id.py`.
- **Depends on:** P19-005..009. **Parallel:** sequential after 005-009.
- **Round-1 fixes:**
  - OBS-01 (cardinality cap): `project_id` label only for metrics where project is meaningful AND cap to active projects. Paused/archived projects' metrics stop emitting (or bucket `project_id="archived"`). Document cardinality budget (≤5 active projects × existing labels).
  - OBS-02 (hash chain versioning): NEW rows' canonical payload includes `project_id` (nullable → "global" string for global events). Add `chain_version` field (`=1` legacy, `=2` P19). Existing rows keep old hash + `chain_version=1` (NOT re-verified against new format). Verification job respects chain_version.
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: project audit row without `project_id` (for project events); HARD STOP audit with non-null project_id (should be NULL/global); hash chain broken for same `chain_version`; unbounded metric cardinality.
  - Required Commands: `python -m pytest tests/projects/test_audit_project_id.py -v` → exit 0; `curl /metrics` includes `project_id` labels; `psql -c "SELECT chain_version, count(*) FROM audit.audit_trail GROUP BY chain_version"` → both versions present (legacy + P19).
  - Evidence: `P19-010/verification.md`, `auditor-gate.md`.
  - Hard Rejection: audit without project_id; global safety event with project_id; hash chain broken within a chain_version; metric cardinality unbounded.
  - Rollback/Re-run: `project_id=None` default; `chain_version=1` legacy rows unaffected.
  - Parent Verification: `psql -c "SELECT project_id, event_type, chain_version FROM audit.audit_trail LIMIT 5"`.
  - Auditor Assignment: observability-evidence, docs-consistency.

### Wave P19-011: Migration / Backfill from Existing Unscoped State
- **Files:** `scripts/p19_backfill.py` (batched backfill), `alembic/versions/p19_002_project_id_not_null.py` (NOT NULL with pre-check), `tests/projects/test_backfill.py`.
- **Depends on:** P19-003. **Parallel:** parallel with 010.
- **Round-1 fixes:**
  - DATA-01 (global memory mislabeling): backfill classifies existing episodes. Heuristic: episodes with `source` IN (persona, adr, safety, operator, system) → `project_scope = 'global'`; else → `project_scope = 'project'`. Both get `project_id = default`. Provide manual override `/memory set-scope <id> global` for misclassified rows. Document the classification rule.
  - DB-01 (NOT NULL timing pre-check): `p19_002` upgrade asserts `SELECT count(*) FROM <table> WHERE project_id IS NULL` = 0 for each scoped table BEFORE applying NOT NULL; if >0, abort with "backfill incomplete for <table>" error (not silent fail).
- **Scaffold:**
  - Expected files: as above.
  - Forbidden Patterns: non-batched backfill (long lock); backfill without `WHERE project_id IS NULL` guard; NOT NULL applied before backfill complete (no pre-check assertion); global memories mislabeled as project-scoped (DATA-01).
  - Required Commands: `python scripts/p19_backfill.py` → exit 0; `alembic upgrade head` → exit 0; `psql -c "SELECT count(*) FROM memory.episodes WHERE project_id IS NULL"` → 0 (for memory/life_kernel/projects); `psql -c "SELECT count(*) FROM memory.episodes WHERE project_scope='global' AND source IN ('persona','adr','safety')"` → >0 (global classification applied).
  - Evidence: `P19-011/verification.md`, `auditor-gate.md`.
  - Hard Rejection: backfill locks DB; NOT NULL before backfill (no pre-check); data loss; global memories mislabeled (apparent memory loss cross-project).
  - Rollback/Re-run: `alembic downgrade p19_001`; re-run backfill (idempotent — `WHERE project_id IS NULL` guard).
  - Parent Verification: NULL count = 0 for scoped tables; global classification spot-check.
  - Auditor Assignment: database-migration, data-memory-isolation.

### Wave P19-012: Deploy / Canary / Rollback / Soak / Final Production Gate
- **Files:** `deploy/p19-rollout.md` (runbook), `systemd/` (no new units for MVP — single `guinevere-core` process handles multi-project via vault + thread_id; per-project units are future optimization — round-1 fix DEPLOY-04), final evidence.
- **Depends on:** ALL. **Parallel:** sequential.
- **Round-1 fixes:**
  - DEPLOY-02 (canary steps): (1) flag on with `default` project only (no real multi-project); (2) create test project `p19-canary`; (3) run isolation tests; (4) HARD STOP global test; (5) operator-defined soak (P20's 24h soak was waived; P19 defines its own duration by operator approval); (6) flag stays on. Document each step.
  - DEPLOY-03 (rollback with NOT NULL): rollback procedure = (1) `redis SET feature:projects:enabled false`; (2) `alembic downgrade p20_001_life_kernel_schema` (drops p19_002 then p19_001, removing columns); (3) verify P20 tests pass. Data in `project_id` columns lost on rollback (acceptable — re-derivable from `default`).
  - SEC-02 (age key rotation verification): verify age rotation runbook works (SecretsRotationRunbook §10, Faiz-only).
  - SEC-03 (deploy boundary test): red-team — deploy project X does NOT restart `guinevere-core` (unless X is core project); `systemctl is-active` for other services unchanged.
- **Scaffold:**
  - Expected files: runbook + final evidence.
  - Forbidden Patterns: deploy without feature flag; deploy without smoke; deploy disturbing P20 (other services down); no rollback verification; project deploy restarting core without policy gate (SEC-03).
  - Required Commands: `redis SET feature:projects:enabled true`; canary steps (1)-(6) above; `systemctl restart guinevere-core` (by operator approval — P20 axis satisfied by waiver); operator-defined soak; `python -m pytest tests/projects/ tests/life_kernel/ -v` → exit 0; deploy boundary test (SEC-03); age rotation dry-run (SEC-02).
  - Evidence: `P19-012/verification.md`, `auditor-gate.md`, `final-p19-planning-report.md`.
  - Hard Rejection: deploy/restart in planning phase; soak shows P20 regression; any hard-rejection criterion unmet; deploy boundary violated (SEC-03).
  - Rollback/Re-run: `redis SET feature:projects:enabled false`; `alembic downgrade p20_001_life_kernel_schema`; verify P20 tests pass.
  - Parent Verification: live Discord proof (per-project dashboard + switch); soak metrics green; deploy boundary test pass.
  - Auditor Assignment: runtime-deploy-readiness, observability-evidence, safety-consent, security-secrets.

---

## Per-Step Verification Scaffold (summary)

Every wave's `verification.md` follows AGENTS.md §11 12-section schema: What Was Done · Files Changed · Validation Results · Evidence Artifacts · Doc-Sync Impact · Boundary Compliance · Rollback/Re-run Safety · Design Decisions/Caveats · Auditor Gate · Security Scan · Acceptance Criteria Mapping · Footer. Scaffold fields (Expected Files / Forbidden Patterns / Required Commands / Evidence Requirements / Hard Rejection Criteria / Rollback/Re-run Safety / Parent Verification Commands / Auditor Assignment) are per-wave above. Parent re-runs every scaffold command after sub-agent claims done (AGENTS.md §2.5 rule 5).

---

## Evidence Paths

| Wave | Verification | Auditor gate |
|---|---|---|
| P19-001..012 | `docs/setup-evidence/P19/evidence/P19-0XX/verification.md` | `docs/setup-evidence/P19/evidence/P19-0XX/auditor-gate.md` |
| Round-1 audits | `docs/setup-evidence/P19/evidence/audits/round-1/<dimension>.md` | — |
| Round-2 audits | `docs/setup-evidence/P19/evidence/audits/round-2/<dimension>.md` | — |
| Final | `docs/setup-evidence/P19/evidence/{p19-definition-verification,auditor-gate,final-p19-planning-report}.md` | — |

---

## Auditor Matrix (for the audit waves + future per-wave gates)

| Dimension | Scope | Key checks |
|---|---|---|
| Architecture | Namespace flow, wrapper correctness, thread_id strategy, additive-only | `project_id` flows everywhere; LangGraph thread_id encodes project; no global mutable state |
| Safety-consent | HARD STOP global, project pause distinct, safe-word global, consent per-project | HARD STOP single key; project pause ≠ HARD STOP; safety scopes global; F-01..F-15 preserved |
| Security-secrets | Per-project secrets, env isolation, deploy boundary, no cross-project read | `secrets/projects/{id}/`; `GUINEVERE_{PROJECT}_` env; deploy gate; secret isolation test |
| Data-memory-isolation | Memory/KG partition, leak prevention, RLS optional, backfill | `project_id`+`project_scope`; wrapper WHERE; isolation tests; `default` backfill |
| P20-integration | Non-interference, additive, P20 axis satisfied by waiver, HARD STOP global | P20 production files untouched without operator approval; all current focused tests pass; exact count captured in evidence; HARD STOP global |
| P21/P22-dependency | Registry read-only, nullable seam, migration chain, namespace template | P22 reads registry; P21 nullable satisfied; chain P19→P21→P22; `p22:...` template |
| Database-migration | Additive, idempotent, FK integrity, backfill, rollback-safe | `IF NOT EXISTS`; `upgrade/downgrade/upgrade`; `default` seeded; no P20 break |
| Runtime-deploy-readiness | Feature flag, canary, smoke, rollback, operator-defined soak, P20 non-disturbance | `feature:projects:enabled`; operator-defined soak; P20 undisturbed (axis satisfied by waiver); rollback verified |
| Observability-evidence | project_id labels, audit project_id, hash chain, evidence roots | Metrics labeled; audit project_id; chain intact; per-project evidence |
| Docs-consistency | ADR, README, CHECKLIST, PROGRESS, cross-refs, status held | ADR-039 added; status held; P19 rows updated; file/line counts consistent |

---

## Hard Rejection Criteria (binary FAIL conditions) — consolidated

1. Plan is sidecar-only without evaluating core integration → **FAIL**. (Mitigated: P19 threads `project_id` through core memory/loop/life_kernel, not a sidecar.)
2. HARD STOP scoped per project → **FAIL**. (Mitigated: §Consent/Surveillance Boundary + P19-005 scaffold; `life_kernel:hard_stop` stays global.)
3. Project pause conflated with HARD STOP → **FAIL**. (Mitigated: `project:{id}:paused` vs `life_kernel:hard_stop`; P19-009 red-team test.)
4. Namespace does not flow to memory/KG/audit/agenda/dashboard/sensors/actions → **FAIL**. (Mitigated: every wave threads `project_id`; §Architecture Overview.)
5. Project switch not explicit/auditable → **FAIL**. (Mitigated: `/project` + `project_switched` audit; P19-007.)
6. Shared persona causes cross-project memory leak → **FAIL**. (Mitigated: `project_scope='global'` explicit; wrapper WHERE; isolation tests; P19-004.)
7. Consent/surveillance not per-project → **FAIL**. (Mitigated: `consent.consent_ledger.project_id`; `check_consent(scope, project_id)`; P19-009.)
8. P20 autonomy not project-aware → **FAIL**. (Mitigated: `thread_id=heartbeat-{project_id}`; per-project cognition; P19-005.)
9. P21/P22 dependency ignored → **FAIL**. (Mitigated: §P21/P22 maps; migration chain; P19-002/006.)
10. Deploy of another project can touch Guinevere without policy gate → **FAIL**. (Mitigated: §Security/Secrets Model; project-scoped `consent.autonomy.high_blast`; P19-012.)
11. Secrets/env leak between projects → **FAIL**. (Mitigated: `secrets/projects/{id}/`; `GUINEVERE_{PROJECT}_` env; P19-006 secret isolation test.)
12. Implementation waves don't reach deploy/soak/final gate → **FAIL**. (Mitigated: P19-012 deploy+soak+final gate.)
13. Sub-agent output inline-only without file → **FAIL**. (Mitigated: 11 research files + plan on disk; this planning phase parent-authored after workflow agents hit rate limits — all outputs file-based.)
14. "Complete" claimed without evidence + double audit → **FAIL**. (Mitigated: 2 audit rounds, definition-verification, auditor-gate, final report.)

---

## Round-1 Audit Amendments (consolidated from 10 round-1 auditors)

Round-1 verdicts: architecture **PASS (conditions)**, safety-consent **PASS (conditions)**, security-secrets **PASS (conditions)**, data-memory-isolation **PASS (conditions)**, p20-integration **PASS (conditions)**, p21-p22-dependency **PASS**, database-migration **PASS (conditions)**, runtime-deploy-readiness **PASS (conditions)**, observability-evidence **PASS (conditions)**, docs-consistency **PASS (conditions)**. No hard-rejection criterion is unmitigated after the amendments below. All findings (8 HIGH, 18 MEDIUM, 14 LOW = 40 total) are specification/enforcement items folded into wave scaffolds; none invalidate the design.

| # | Finding (auditor) | Amendment | Wave |
|---|---|---|---|
| ARCH-01/DOC-01 | ADR-039 collides with reserved backlog slot | Use **ADR-052** (next free after ADR-050; ADR-051 reserved) | 001 |
| ARCH-02 | `_ADAPTERS` global in graph.py cross-project risk | P19-005: per-project adapter instances OR `recall(context)` reads project_id (documented choice) | 005 |
| ARCH-03 | Dashboard top-N unspecified | P19-007: N=3 + LRU eviction | 007 |
| ARCH-04 | Cross-project recall consent scope undefined | P19-009: add `consent.memory.cross_project` global scope | 009 |
| SAFE-01 | Project pause restoration gate | `/project resume` requires explicit Faiz; autonomy skips paused projects | 009 |
| SAFE-02 | Surveillance confrontation global untested | P19-009 red-team (d): blocked for ALL projects in safe-mode | 009 |
| SAFE-03 | `consent.autonomy.high_blast` scope ambiguity | Per-project; core deploy never covered by project autonomy | 009 |
| SAFE-04 | Safe-word during project-switch | `/project` checks HARD STOP before applying | 007 |
| SEC-01 | Process-scoped env vars don't isolate in-process | `ProjectSecretsVault` in-memory keyed by project_id | 006 |
| SEC-02 | Shared age key blast radius | Accepted single-user risk; age rotation runbook verified in soak | 012 |
| SEC-03 | Deploy boundary test missing | P19-012 red-team: project deploy ≠ core restart | 012 |
| SEC-04 | Break-glass per-project scope | `consent.emergency.break_glass_project` (project-scoped, 4h) | 009 |
| DATA-01 | Global memory mislabeling on backfill | Classify by source (persona/adr/safety → global); `/memory set-scope` override | 011 |
| DATA-02 | pgvector filtered similarity perf | Composite index; >50k/project → partial ivfflat; document threshold | 004 |
| DATA-03 | DNR global vs per-project ambiguity | `project_scope` column disambiguates; document | 004 |
| DATA-04 | KG entity resolution cross-project merge | `WHERE project_id` in resolver; entity isolation test | 004 |
| P20-01 | P19-005 touches 9 P20 files | Split into 005a/005b/005c (additive → flag-thread_id → full) | 005 |
| P20-02 | `thread_id="heartbeat"` hardcoded 5 places | grep check: 0 unconditional matches; all flag-conditional | 005 |
| P20-03 | BackgroundCognition resource overhead | Bounded N=3; ≤1 core total; idle projects pause | 005 |
| P20-04 | Checkpointer no-change confirm | Checkpoint isolation test added | 005 |
| P21P22-01 | `hermes_conversational.py` shared edit with P21 | P19 project_id param first; P21 rebases; combined signature | 008 |
| P21P22-02 | Namespace template `p19:` vs `p22:` | Coexist (different domains); document in ADR | 001 |
| P21P22-03 | P17 sync key not in a wave | P17 deferred; P19 provides dimension; ADR note | 001 |
| DB-01 | NOT NULL migration timing | p19_002 pre-check assertion (NULL count = 0 before NOT NULL) | 011 |
| DB-02 | Hypertable composite index | Plain column + btree; chunk-by-project future | 003 |
| DB-03 | `domain_mind_state` unique constraint swap | Transactional: backfill before DROP+ADD constraint | 003 |
| DB-04 | Sentinel UUID for default | Fixed UUID documented in ADR | 001 |
| DEPLOY-01 | Feature flag gates behavior not surface | thread_id conditional on flag; flag OFF = legacy | 005 |
| DEPLOY-02 | No canary defined | 6-step canary (default-only → test project → isolation → HARD STOP → soak → flag-on) | 012 |
| DEPLOY-03 | Rollback with NOT NULL columns | flag off → alembic downgrade → P20 tests pass; document | 012 |
| DEPLOY-04 | systemd per-project config optional | No new units for MVP; single process + vault + thread_id | 012 |
| OBS-01 | Prometheus label cardinality | Cap to active projects; paused stop emitting; budget ≤5×labels | 010 |
| OBS-02 | Audit hash chain versioning | `chain_version` field (1=legacy, 2=P19); new payload includes project_id | 010 |
| OBS-03 | Per-project evidence root path | Convention documented in ADR | 001 |
| OBS-04 | Soak metrics dashboard | `guinevere-p19-projects.json` or panel in agent-loop | 010 |
| DOC-02 | P19 README NOT STARTED + 5 steps | Finalize: 12 waves, DEFINITION COMPLETE status | finalize |
| DOC-03 | CHECKLIST/PROGRESS P19 TBD | Finalize: 12 steps, definition complete, held | finalize |
| DOC-04 | File/line count consistency | Final report cites counts | finalize |
| DOC-05 | P22 default namespace ↔ P19 default UUID | ADR documents alignment | 001 |

These amendments are binding for future implementation waves. They do NOT change the planning-phase status (no implementation occurs now).

---

## Self-Review (writing-plans skill)

- **Spec coverage:** Every P19 objective maps to a wave — registry (002), schema (003), memory/KG (004), life-kernel (005), sensors (006), Discord (007), agent-loop (008), consent (009), observability (010), migration (011), deploy/soak (012), governance (001). ✅
- **Placeholder scan:** No "TBD"/"implement later" without a wave. Wave scaffolds have concrete Expected Files, Forbidden Patterns (regex/grep), Required Commands, Hard Rejection, Rollback, Parent Verification, Auditor Assignment. (Wave execution TDD steps deferred to execution time per planning-only constraint — out-of-scope, not placeholders.) ✅
- **Type consistency:** `ProjectId` (UUID) used by registry, memory_store, LoopContext, session keys; `project_scope` ('global'|'project') consistent across memory/KG; `life_kernel:hard_stop` key name consistent (global); `project:{project_id}:paused` consistent (per-project). ✅
- **Dependency ordering:** P20 axis satisfied by operator waiver (P19 no longer waits on a P20 soak); P19 before P21/P22 impl; migration chain P19→P21→P22. ✅

---

## Final Allowed Status

**P19 MULTI-PROJECT CONTEXT DEFINITION COMPLETE — P20 AXIS SATISFIED BY OPERATOR WAIVER — IMPLEMENTATION HOLD BY OPERATOR / READY FOR P19 IMPLEMENTATION WAVES.**

This plan is the definition. The P20 axis is satisfied by operator waiver (P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK, 2026-06-25); P19 no longer waits on a P20 soak gate. Implementation waves P19-001..012 execute later, by operator approval. Waves 001-004 + 011 (NEW files + additive migrations) are unblocked and ready by operator approval — but NOT executed in this planning phase per the P19 objective. Waves 005-010, 012 touch P20 production files or deploy — held by operator discretion (to avoid destabilizing production-under-accepted-risk), not by a pending P20 gate.
