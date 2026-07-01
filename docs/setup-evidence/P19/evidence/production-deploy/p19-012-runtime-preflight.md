# P19-012 Runtime Preflight

**Date:** 2026-06-26 21:40 WIB
**Author:** Guinevere (parent)
**Operator:** Faiz
**Phase:** 1 — Runtime Preflight

---

## 1. VPS Status

| Check | Result |
|---|---|
| System uptime | 34 days, 11:03 |
| Load average | 0.55, 0.62, 0.62 |
| Disk | 53G used / 99G total (57%) — 41G available |
| Kernel | Ubuntu 24.04 |

## 2. Service Status

| Service | Status | Notes |
|---|---|---|
| guinevere-core | **active (running)** | Since 2026-06-25 08:26:43 WIB (1d 13h+) |
| guinevere-mcp | active | MCP gateway |
| guinevere-gateway | **inactive** | Expected — Hermes gateway not running |
| guinevere-discord | active | Discord bot |
| guinevere-9router | active | 9Router LLM proxy |
| guinevere-monitoring | active | Prometheus/Grafana/Loki |
| guinevere-obscura | active | CDP server |
| guinevere-whatsapp | active | WhatsApp channel |
| guinevere-x-poster | active | X poster |

## 3. P20 Health (Pre-Deploy)

| Metric | Value |
|---|---|
| hard_stop_requested | **False** |
| cycle_count | 200,334 |
| NRestarts | 0 |
| Memory | 1008.9M / 2.0G high / 4.0G max |
| Brain think_complete | **active** (model=guinevere, 0 fallback) |
| Decision | observe (healthy idle) |
| Last autonomous decision | "act on: Finance Health Check" |
| Errors | 0 |
| Uptime | 1d 13h continuous |

**P20 is HEALTHY. No errors, no crashes, no fallback, no hard stop.**

## 4. Database State — `guinevere` DB

### ⚠️ CRITICAL FINDING: Production DB is `guinevere`, NOT `guinevere_core`

The runbook (`p19-012-deploy-runbook.md`) assumed prod DB was `guinevere_core` provisioned via raw SQL. Ground truth from VPS:

- **DATABASE_URL** points to `guinevere` DB (confirmed from `.env.core`)
- `guinevere_core` DB exists but contains only `life_kernel.audit_journal` (1 table)
- All production tables are in `guinevere` DB

### Schema State

| Schema | Tables | Has project_id? |
|---|---|---|
| memory | semantic_facts, episodes, procedural_skills, session_summaries, knowledge_graph | **NO** |
| life_kernel | life_mind_state, domain_mind_state, heartbeat_record | **NO** |
| audit | audit_trail | **NO** |
| consent | consent_ledger | **NO** |
| surveillance | events | **NO** |
| projects | agent_tasks, loop_instances, tasks, evidence_artifacts | **NO** |
| projects | project_registry | **MISSING** |

### Alembic Version

- `ops.alembic_version` table: **EXISTS**
- Stamped version: `p20_001_life_kernel_schema` (single entry)
- No `description` column (older alembic format)

### P19 DDL Status

- `project_id` columns: **NONE** (only `financial.transactions.project_id` exists — unrelated)
- `project_scope` columns: **NONE**
- `chain_version` column: **NONE**
- `projects.project_registry` table: **MISSING**
- P19 composite indexes: **NONE**

**P19 DDL has NOT been applied to production. This is a clean, pre-deploy state.**

## 5. Redis State

| Key | Value |
|---|---|
| feature:projects:enabled | **None** (not set) |
| feature:projects:rls | **None** (not set) |
| life_kernel:hard_stop | **None** (not set) |
| p19:* keys | **0** found |
| dbsize | 97 keys |

## 6. Deploy Readiness Assessment

| Gate | Status |
|---|---|
| P20 healthy | ✅ PASS |
| No hard stop | ✅ PASS |
| DB accessible | ✅ PASS |
| Alembic version exists | ✅ YES — `p20_001_life_kernel_schema` |
| P19 DDL not yet applied | ✅ Confirmed — clean slate |
| Redis accessible | ✅ PASS |
| Disk space for backup | ✅ 41G available |
| All 8 services running | ✅ 7 active + 1 expected-inactive (gateway) |

## 7. Runbook Correction Notes

The original runbook assumed:
1. ❌ DB is `guinevere_core` → **ACTUAL: `guinevere`**
2. ❌ No `ops.alembic_version` table → **ACTUAL: Exists with `p20_001`**
3. ✅ Surgical approach needed → **CONFIRMED: alembic table exists but schema was provisioned non-alembic**

Deploy strategy adapts: backup `guinevere` DB, stamp `p19_001` → `p19_002` → `p19_003` via targeted SQL, NOT `alembic upgrade head`.

## 8. Footer

| Field | Value |
|---|---|
| Preflight status | PASS |
| Deployable | YES |
| Next step | Write deploy execution plan |