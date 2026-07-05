# P19-012 Audit: Observability / Evidence

**Date:** 2026-06-27
**Auditor:** Independent (sub-agent)
**Scope:** OBSERVABILITY / EVIDENCE
**Phase:** Round 1
**Operator:** Faiz

---

## 1. Audit Scope

Verify that the P19-012 production deploy produced complete, honest, file-based evidence and that P19 observability (audit trail project_id labels, chain_version, Grafana dashboard) is sound.

**Files reviewed:**
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-runtime-preflight.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-deploy-plan.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-backup-evidence.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-schema-migration-evidence.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-service-deploy-evidence.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-smoke-test.md`
- `monitoring/grafana/dashboards/guinevere-p19-projects.json`
- `monitoring/prometheus/prometheus.yml`
- `monitoring/compose.monitoring.yml`
- `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- `src/life_kernel/cognition.py`
- `src/loops/audit_writer.py`
- `src/life_kernel/metrics.py`
- `src/loops/metrics.py`
- `alembic/versions/p19_001_project_namespaces.py`
- `alembic/versions/p19_003_audit_chain_version.py`
- `scripts/p19_001_deploy.py`
- `scripts/p19_002_003_deploy.py`

---

## 2. Methodology

- Static file review of all 6 evidence files + source code + deploy scripts + monitoring config
- Cross-reference of statement counts between migration evidence and deploy scripts
- Cross-reference of column definitions between alembic migrations, deploy scripts, and source code
- Cross-reference of Prometheus scrape config with dashboard metric names
- Chain-version semantics verification against p19_003 docstring and AuditWriter source
- No SSH access to VPS performed (no remote execution); live VPS checks rely on evidence-file claims + smoke-test corroboration

---

## 3. Findings

### OBS-01: All 6 Core Evidence Files Exist

**PASS**

| # | File | Exists | Sections |
|---|---|---|---|
| 1 | `p19-012-runtime-preflight.md` | YES | 8 sections (VPS status, services, P20 health, DB state, Redis, readiness, corrections, footer) |
| 2 | `p19-012-deploy-plan.md` | YES | 10 sections (summary, strategy, DDL, stamps, rollback, stop conditions, runtime, smoke plan, deliverables, footer) |
| 3 | `p19-012-backup-evidence.md` | YES | 5 sections (details, verification, rollback, evidence, footer) |
| 4 | `p19-012-schema-migration-evidence.md` | YES | 6 sections (summary, deviations, schema verification, runtime contract, P20 health, footer) |
| 5 | `p19-012-service-deploy-evidence.md` | YES | 6 sections (strategy, files deployed, imports, service status, restart decision, footer) |
| 6 | `p19-012-smoke-test.md` | YES | 5 sections (smoke tests, P19 test suite, Discord UX, P20 cycle, footer) |

Later-phase files (pending, not yet expected):
- `audits/round-1/*.md` -- this file is the first
- `audits/round-2/*.md` -- Phase 10
- `p19-012-final-production-report.md` -- Phase 11
- `p19-012-auditor-gate.md` -- Phase 11

### OBS-02: Evidence Honestly Documents Runbook Deviations

**PASS**

The schema-migration-evidence.md (Section 2) explicitly documents three deviations:

| # | Deviation | Honest? | Cross-check |
|---|---|---|---|
| 1 | `memory.knowledge_graph` does NOT exist in production; replaced by `kg_entities`, `kg_edges`, `kg_episodes`, `kg_consent_audit` | YES | Confirmed: `p19_001_deploy.py` uses `kg_entities`/`kg_edges`/`kg_episodes`/`kg_consent_audit` (13 tables, not 14). Alembic migration references `memory.knowledge_graph` (14 tables). Deploy script adapted correctly. |
| 2 | DB is `guinevere`, not `guinevere_core` | YES | Confirmed: preflight (Section 4) and backup evidence both use `guinevere`. Deploy scripts load `.env.core` which points to `guinevere` DB. |
| 3 | `ops.alembic_version` already exists with `p20_001` | YES | Confirmed: preflight (Section 4) documents this. Stamps were INSERTed alongside existing row, not CREATE TABLE. |

The 67/67 claim is consistent with deploy scripts:

| Script | Statements | Count |
|---|---|---|
| Phase 1 (registry + seed) | CREATE TABLE + INSERT | 2 |
| `p19_001_deploy.py` | 13 ADD project_id + 4 ADD project_scope + 14 BACKFILL | 31 |
| `p19_002_003_deploy.py` | 13 composite idx + 3 pgvector idx + 1 unique swap + 1 pre-check + 11 NOT NULL + 1 chain_version + 1 index + 3 stamps | 34 |
| **TOTAL** | | **67** |

No destructive DDL (DROP, TRUNCATE, DELETE without WHERE) found in either deploy script. All statements use `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` guards.

### OBS-03: audit.audit_trail Has project_id + chain_version + Indexes

**NEEDS-REVIEW** (no direct VPS access in this audit)

Evidence from source files (strong indirect confirmation):

| Check | Evidence | Verdict |
|---|---|---|
| `project_id UUID` column | `p19_001_deploy.py` line 22: `audit.audit_trail` in `remaining` list; `p19_001_project_namespaces.py` line 96: `ALTER TABLE audit.audit_trail ADD COLUMN IF NOT EXISTS project_id UUID` | Column added |
| `chain_version SMALLINT NOT NULL DEFAULT 1` | `p19_002_003_deploy.py` line 95: `ALTER TABLE audit.audit_trail ADD COLUMN IF NOT EXISTS chain_version SMALLINT NOT NULL DEFAULT 1` | Column added |
| `ix_audit_trail_project_id_created_at` | `p19_002_003_deploy.py` line 33: `CREATE INDEX IF NOT EXISTS ix_audit_trail_project_id_created_at ON audit.audit_trail (project_id, created_at)` | Index created |
| `ix_audit_trail_chain_version` | `p19_002_003_deploy.py` line 97: `CREATE INDEX IF NOT EXISTS ix_audit_trail_chain_version ON audit.audit_trail (chain_version)` | Index created |

Smoke test corroboration: `p19-012-smoke-test.md` SMOKE 5 confirms `audit.audit_trail` is accessible and `chain_version` column accepts default.

**Caveat:** This audit did not SSH to the VPS to run `\d audit.audit_trail`. The schema-migration-evidence.md (Section 3.5) claims the column exists with `smallint NOT NULL DEFAULT 1`. This is corroborated by deploy scripts and smoke tests, but not independently verified with a live DDL inspection. A round-2 audit with SSH access is recommended.

### OBS-04: Grafana P19 Dashboard Exists (6 Panels)

**PASS**

File `monitoring/grafana/dashboards/guinevere-p19-projects.json` exists locally with exactly 6 panels:

| Panel ID | Title | Type | Metric(s) |
|---|---|---|---|
| 1 | Heartbeat Health | stat | `guinevere_lk_heartbeat_healthy{project_id}` |
| 2 | Loop Cycles Rate (per project) | timeseries | `guinevere_loop_cycles_total{project_id}` |
| 3 | Loop Events by Type | timeseries | `guinevere_loop_events_total{event_type, project_id}` |
| 4 | Life Kernel Records by Source | timeseries | `guinevere_lk_records_total{source, project_id}` |
| 5 | Loop Phase Duration (p95) | timeseries | `guinevere_loop_phase_duration_seconds_bucket{phase, project_id}` |
| 6 | Cognition Cycles Rate (per project) | timeseries | `guinevere_lk_cognition_cycles_total{project_id}` |

All 6 panels include `project_id` label filtering via a dashboard template variable (`label_values(guinevere_loop_events_total, project_id)`).

Dashboard provisioning path: `monitoring/grafana/dashboards/` is mounted to `/var/lib/grafana/dashboards` in `compose.monitoring.yml` (line 55), and `dashboards.yml` provisioning config points to that path. Auto-provisioning is configured.

All Prometheus metric names in the dashboard match the metric definitions in source:
- `src/life_kernel/metrics.py`: defines `guinevere_lk_records_total`, `guinevere_lk_heartbeat_healthy`, `guinevere_lk_cognition_cycles_total` -- all with `project_id` label
- `src/loops/metrics.py`: defines `guinevere_loop_events_total`, `guinevere_loop_cycles_total`, `guinevere_loop_phase_duration_seconds` -- all with `project_id` label

### OBS-05: Prometheus Monitoring Active

**PASS**

`monitoring/prometheus/prometheus.yml` configures 8 scrape jobs. The `fastapi` job (line 45-48) scrapes `localhost:8000/metrics`, which is guinevere-core's FastAPI endpoint. All P19 metric names (`guinevere_loop_*`, `guinevere_lk_*`) are exposed via this endpoint.

The preflight (`p19-012-runtime-preflight.md` Section 2) confirms `guinevere-monitoring` service is **active** on the VPS, meaning Prometheus, Grafana, and Loki are all running.

No separate `guinevere-core` scrape job exists in `prometheus.yml` -- the `fastapi` job covers it. This is correct since guinevere-core IS the FastAPI service on port 8000.

### OBS-06: chain_version Semantics Correct

**PASS**

Three independent sources confirm consistent semantics:

**Source 1: `alembic/versions/p19_003_audit_chain_version.py` (docstring lines 1-15)**
```
chain_version = 1  (default, legacy): rows created before P19.
  Canonical payload does NOT include project_id.
  Hash is computed with the original algorithm.

chain_version = 2  (P19+): rows created after P19-010 deployment.
  Canonical payload MAY include project_id (NULL = global).
  Hash includes chain_version in the canonical input.

Existing rows are backfilled to chain_version=1 (no hash recomputation).
New rows written by AuditWriter use chain_version=2.
```

**Source 2: `src/loops/audit_writer.py` (line 32, line 100, line 112)**
- `AuditEvent` dataclass: `chain_version: int = 2` (default for new events)
- `write_event()` creates `AuditEvent(... chain_version=2)` explicitly
- `write_event()` creates `AuditTrail(... chain_version=2)` for DB row explicitly
- Comment on line 100: `# P19-010: all new events are v2`

**Source 3: `alembic/versions/p19_003_audit_chain_version.py` (upgrade, line 44)**
- `ADD COLUMN IF NOT EXISTS chain_version SMALLINT NOT NULL DEFAULT 1`
- DEFAULT 1 backfills existing rows atomically, no hash recomputation

**Consistency:** All three sources agree:
- v1 = legacy (no project_id in payload, no hash recomputation during migration)
- v2 = P19+ (project_id may be in payload, AuditWriter always writes v2)
- Migration only sets DEFAULT 1 (backfill), never recomputes hashes

The `verify_chain()` method in `AuditWriter` (line 127-174) reads `chain_version` per row but does NOT branch on it -- it re-verifies using the stored `event_payload` as-is. This is correct: v1 rows have no `project_id` in payload, v2 rows may have it, and the hash is computed over the payload that was stored. No cross-contamination.

### OBS-07: Evidence Is File-Based

**PASS**

All 6 evidence files are standalone markdown files under `docs/setup-evidence/P19/evidence/production-deploy/`. None are inline-only (e.g., pasted into a chat or issue comment). Each file has:
- Title header with date, author, phase
- Structured sections with tables
- Footer with status + next step

Files follow a consistent schema (not exactly 12-section, but each has 5-10 substantive sections + footer). This is acceptable -- the 12-section schema is aspirational for final reports; intermediate evidence files have appropriate structure for their phase.

### OBS-08: No Premature Claims

**PASS**

The evidence files do NOT contain a "PRODUCTION PASS" or "P19 COMPLETE" claim. The status progression is:
- Preflight: "Deployable: YES"
- Deploy plan: "Plan status: READY TO EXECUTE"
- Backup: "Backup status: SUCCESS"
- Schema migration: "Migration status: SUCCESS -- 67/67 statements OK"
- Service deploy: "Deploy status: SUCCESS"
- Smoke test: "Next step: Phase 8: Audit 1 (6 dimensions)"

The deploy plan (Section 10, Evidence Deliverables) explicitly lists audits (round-1, round-2) and final-report as separate deliverables in phases 8-11, after smoke tests. No premature finalization claim.

---

## 4. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| OBS-03 relies on indirect evidence (no live DDL inspection via SSH) | LOW | Deploy scripts + smoke tests corroborate; round-2 SSH audit recommended |
| `feature:projects:enabled` is OFF -- P19 code paths never execute in production yet | INFO | This is by design (surgical, flag-gated); not a defect |
| Grafana dashboard not verified live (local file only) | LOW | Provisioning is configured in compose + dashboards.yml; dashboard will load on next Grafana restart |

---

## 5. Recommendations

1. **Round-2 SSH verification (OBS-03):** An auditor with SSH access should run `\d audit.audit_trail` and `SELECT indexname FROM pg_indexes WHERE tablename = 'audit_trail' AND schemaname = 'audit'` to independently confirm columns + indexes.
2. **Grafana live check:** After the next `guinevere-monitoring` restart (or `docker compose up -d` in the monitoring directory), verify the P19 dashboard appears in Grafana UI under the "Guinevere" folder.
3. **Prometheus target check:** Verify `http://localhost:9090/targets` shows the `fastapi` job as UP with last scrape successful.

---

## 6. Audit Verdicts Summary

| ID | Check | Verdict | Evidence |
|---|---|---|---|
| OBS-01 | All 6 core evidence files exist | **PASS** | All 6 files present under `production-deploy/` |
| OBS-02 | Evidence honestly documents runbook deviations | **PASS** | 3 deviations documented; 67/67 count verified against deploy scripts; no destructive DDL |
| OBS-03 | audit.audit_trail has project_id + chain_version + indexes | **NEEDS-REVIEW** | Deploy scripts + smoke tests corroborate; no live SSH DDL inspection |
| OBS-04 | Grafana P19 dashboard exists (6 panels) | **PASS** | 6 panels with project_id label filtering; provisioning configured |
| OBS-05 | Prometheus monitoring active | **PASS** | guinevere-monitoring active; fastapi job scrapes guinevere-core :8000 |
| OBS-06 | chain_version semantics correct | **PASS** | v1 legacy no-recompute, v2 new rows; confirmed in migration, AuditWriter, and docstrings |
| OBS-07 | Evidence is file-based (not inline-only) | **PASS** | All 6 files are standalone .md files with structured sections |
| OBS-08 | No premature claims | **PASS** | No PRODUCTION PASS claim; audits explicitly listed as future deliverables |

---

## 7. Overall Verdict

**PASS (with 1 NEEDS-REVIEW)**

7/8 checks PASS. 1/8 (OBS-03) is NEEDS-REVIEW due to no live VPS DDL inspection in this audit. The indirect evidence (deploy scripts, alembic migrations, smoke tests) is strong and internally consistent. A round-2 SSH-based audit would resolve OBS-03 to PASS.

---

## 8. Files Produced by This Audit

- This file: `docs/setup-evidence/P19/evidence/production-deploy/audits/round-1/observability-evidence.md`

---

## 9. Pending Deliverables (Later Phases)

- `audits/round-1/` -- 5 more audit dimensions (to be produced)
- `audits/round-2/` -- re-audit after findings addressed
- `p19-012-final-production-report.md` -- Phase 11
- `p19-012-auditor-gate.md` -- Phase 11

---

## 10. References

- ADR-052: project_id-on-every-scoped-store contract
- p19_001 migration: `alembic/versions/p19_001_project_namespaces.py`
- p19_003 migration: `alembic/versions/p19_003_audit_chain_version.py`
- AuditWriter: `src/loops/audit_writer.py`
- Cognition registry: `src/life_kernel/cognition.py`
- Life kernel metrics: `src/life_kernel/metrics.py`
- Loop metrics: `src/loops/metrics.py`
- Deploy scripts: `scripts/p19_001_deploy.py`, `scripts/p19_002_003_deploy.py`

---

## 11. Footer

| Field | Value |
|---|---|
| Audit status | COMPLETE |
| Verdict | PASS (7/8) + NEEDS-REVIEW (1/8: OBS-03) |
| Blocking findings | NONE |
| Round-2 recommended | YES (SSH-based OBS-03 resolution) |
