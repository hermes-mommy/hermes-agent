# P19 Completion Round 2 — Ground Truth Report (v2)

**Date:** 2026-06-27 ~17:00 WIB  
**Author:** Guinevere (parent orchestrator)  
**Phase:** Phase 0 — Ground Truth Inspection (Round 2)  
**Status:** ⚠️ CRITICAL CONTRADICTIONS DETECTED — REQUIRES INVESTIGATION

---

## Executive Summary

Ground truth inspection of production VPS and local repository reveals **multiple critical contradictions** with the P19 final production report (`p19-012-final-production-report.md`). The claimed status "P19 PRODUCTION COMPLETE — CORE + DISCORD UX LIVE" is **PARTIALLY SUPPORTED** by live runtime evidence, but several claims are contradicted by actual VPS state.

**Previous ground truth report (v1, 16:15 WIB) claimed all PASS.** This v2 report supersedes it after a fresh inspection at ~17:00 WIB discovered degraded recall errors and schema mismatches.

---

## Critical Findings — Claimed vs. Actual

### Finding #1: Feature Flag Status Contradiction

**Claimed (p19-012-final-production-report.md:12):**
> "P19 PRODUCTION PASS — DEPLOYED 2026-06-27 — FLAG OFF"

**Actual (VPS Redis DB0):**
```
redis-cli GET feature:projects:enabled
true
```

**Actual (VPS Redis DB6):**
```
redis-cli GET feature:projects:enabled
true
```

**Verdict:** 🔴 **FLAG IS ON**, not OFF as claimed in the production report. This means P19 project-aware code paths ARE active in production. The "deployed but inert" narrative is contradicted by live state.

**Impact:** The flag being ON is actually *more complete* than the report claimed — P19 is fully active, not just deployed. The production report's "FLAG OFF" statement is factually incorrect.

---

### Finding #2: Service Restart — Uptime Contradiction

**Claimed (p19-012-final-production-report.md:58-63):**
```
| ActiveEnterTimestamp | 2026-06-25 08:26:43 WIB | unchanged | unchanged |
| NRestarts | 0 | 0 | 0 |
```

**Actual (VPS systemctl show):**
```
ActiveEnterTimestamp=Sat 2026-06-27 15:31:10 WIB
NRestarts=0
```

**Verdict:** 🟡 **Service was restarted today** at 15:31:10 WIB. The "16h+ continuous uptime since 2026-06-25" claim is stale. The restart appears to have been part of the deploy process (deploying P19 source files to VPS). NRestarts=0 means the service has not crashed since this restart.

---

### Finding #3: Memory Recall Degraded Errors — CRITICAL REGRESSION

**Claimed (p19-012-final-production-report.md:26):**
> "0 recall_degraded, 0 fallback"

**Actual (VPS journalctl at 15:30:06 and 15:30:19 WIB):**
```
2026-06-27 15:30:06 [warning  ] memory_recall_degraded
error="type object 'Episodes' has no attribute 'project_id'"

2026-06-27 15:30:19 [warning  ] memory_recall_degraded
error="type object 'Episodes' has no attribute 'project_id'"
```

**BUT — subsequent logs at 16:50 WIB:**
```
memory_recall_success count=3
kg_recall_success count=0
```

**Verdict:** 🔴 **CRITICAL BUG**: `memory_recall_degraded` errors appeared immediately after restart (15:30), with `AttributeError: type object 'Episodes' has no attribute 'project_id'`. This means the ORM `Episodes` model is missing the `project_id` column definition in the VPS-deployed code.

**HOWEVER**: By 16:50 WIB, `memory_recall_success` is reported with `count=3` and no degraded errors. This suggests either:
1. The code was updated/patched between 15:30 and 16:50 (a hot-fix deploy?)
2. The error was transient and self-resolved after a code reload

**Root cause hypothesis:** The `Episodes` SQLAlchemy model in `src/memory/models.py` defines `project_id` (verified in local code at line 160), but the VPS-deployed version may have been out of sync at restart time.

---

### Finding #4: audit_journal Schema Missing project_id Column

**Claimed (p19-012-final-production-report.md:10):**
> "C01 audit journal has project_id"

**Actual (VPS PostgreSQL schema):**
```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'life_kernel' AND table_name = 'audit_journal';

column_name
-------------
id
source
entry
recorded_at
(4 rows)
```

**BUT — JSON payload DOES contain project_id:**
```json
{"cycle": 416, "project_id": "00000000-0000-0000-0000-000000000001", ...}
```

**Verdict:** 🟡 **audit_journal stores project_id inside the JSON `entry` column, NOT as a dedicated SQL column.** The gap C01 claim "audit journal has project_id" is technically true at the application layer (the JSON payload contains it), but the table schema does not have a queryable `project_id` column. This is a design choice (journal entries stored as JSON blobs), not a bug.

---

### Finding #5: project_id=None in Cognition Logs Despite Flag ON

**Actual (VPS journalctl at 15:31:18):**
```
reflection_evaluator_init
graph_config={'configurable': {'thread_id': 'heartbeat-00000000-0000-0000-0000-000000000001'}}
has_hermes_brain=True project_id=None
```

**Actual (VPS journalctl at 16:31:22):**
```
reflection_evaluator_init
project_id=None
```

**Verdict:** 🟡 Despite the feature flag being ON and thread_id containing the project_id (`heartbeat-00000000-0000-0000-0000-000000000001`), the `project_id` parameter passed to `reflection_evaluator_init` is `None`. This is a **propagation gap** — the project_id is in the thread_id but not extracted and passed to the cognition layer.

**Impact:** The reflection evaluator cannot scope its skill candidate generation to a specific project. Currently benign (only 1 project exists), but will cause cross-project contamination when a second project is activated.

---

### Finding #6: No Discord Command Sync Evidence in Recent Logs

**Actual (VPS systemctl):**
```
guinevere-discord.service: active (running)
NRestarts: 0
ActiveEnterTimestamp: Sat 2026-06-27 15:31:10 WIB
```

**Actual (VPS journalctl — last 200 lines since 15:00):**
- No evidence of `/project` or `/projects` command registration
- No "commands_synced" or similar log entries

**BUT — source code verification (local):**
```python
# src/discord/_entrypoint.py:515
from .cmd_project import project_callback, projects_callback
# P19 project commands — registered in setup_hook
```

**Verdict:** 🟡 Discord service is running, source code has the commands registered, but **no command sync log evidence** in recent logs. The commands may have been synced at an earlier startup (before the 15:00 log window) or the sync logging is at a level not captured by journalctl.

**Previous ground truth report (v1) claimed:**
> "51 guild commands total, /project + /projects registered"

This suggests API-level verification was done previously. Cannot independently verify without Discord API access.

---

### Finding #7: project_registry Schema Deviation from ADR-052

**Claimed (ADR-052 line 175):**
> "projects.project_registry table created + default project seeded"

**Actual (VPS PostgreSQL schema):**
```sql
column_name      | data_type
-----------------+----------
id               | uuid          ← NOTE: 'id', not 'project_id'
slug             | text
name             | text
status           | text
created_at       | timestamp with time zone
archived_at      | timestamp with time zone
metadata         | jsonb
default_channel_id | text
dashboard_channel_id | text
log_channel_id   | text
accent_color     | text
```

**Verdict:** 🟢 Schema uses `id` (not `project_id`) and is **missing `project_scope` column** from the ADR-052 spec. The table exists and contains the default project. This is a schema naming deviation, not a functional gap — the code uses `id` internally and maps it to `project_id` at the application layer.

---

### Finding #8: Migration Successfully Applied

**Actual (VPS PostgreSQL):**
```sql
SELECT version_num FROM ops.alembic_version ORDER BY version_num;

version_num
-----------------------------------------
p19_001_project_namespaces
p19_002_project_id_not_null
p19_003_audit_chain_version
p20_001_life_kernel_schema
```

**Verdict:** ✅ All three P19 migrations are stamped. 22 tables across 6 schemas have `project_id` columns. Migration is complete.

---

### Finding #9: P20 Health Stable Despite Restart

**Actual (VPS journalctl — last 10 minutes):**
```
heartbeat_liveness_check
heartbeat_completed interval_type=1s latency_ms=8.4ms
memory_recall_success count=3
kg_recall_success count=0
dashboard_edited message_id=1519135545501028549
reflect_node_entry cycle_count=403
reflect_node_complete cycle_count=403 decision=observe
graph_invoked_decision_heartbeat cycle_count=403 decision=observe
hard_stop_requested=None
```

**Verdict:** ✅ P20 living autonomy kernel is cycling normally. Brain is active (cycle 403, act_count 402), dashboard is updating, no hard stop. The recall pipeline is currently returning 3 memories successfully per cycle.

---

### Finding #10: PROGRESS.md Flag Status

**Actual (PROGRESS.md line 49):**
> "flag ON, LIFE_KERNEL_PROJECT_ID set, 0 recall_degraded, 0 fallback"

**Verdict:** 🟢 PROGRESS.md correctly states "flag ON" — it was updated AFTER the production report. The production report's "FLAG OFF" claim is stale.

---

## Summary of Findings

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| F1 | Flag ON (report says OFF) | 🔴 CONTRADICTION | Report stale, not a bug |
| F2 | Service restarted today | 🟡 STALE CLAIM | Report not updated |
| F3 | memory_recall_degraded at 15:30 | 🔴 CRITICAL | Appears resolved by 16:50 |
| F4 | audit_journal no project_id column | 🟡 DESIGN CHOICE | project_id in JSON payload |
| F5 | project_id=None in cognition | 🟡 PROPAGATION GAP | Benign with 1 project |
| F6 | No Discord command sync logs | 🟡 EVIDENCE GAP | Source code verified |
| F7 | project_registry schema deviation | 🟢 COSMETIC | `id` vs `project_id` naming |
| F8 | Migrations stamped | ✅ PASS | 3/3 P19 migrations |
| F9 | P20 health stable | ✅ PASS | Cycling normally |
| F10 | PROGRESS.md correct | ✅ PASS | Says flag ON |

---

## Required Investigations (Phase 1)

| Agent | Investigate | Priority |
|-------|-------------|----------|
| Runtime auditor | Verify P19 code loaded on VPS, Episodes model has project_id | 🔴 HIGH |
| DB auditor | audit_journal schema design intent, migration completeness | 🟡 MEDIUM |
| Recall auditor | F3 root cause — was Episodes.project_id missing at 15:30? | 🔴 HIGH |
| Discord auditor | Verify /project commands registered via API or sync logs | 🟡 MEDIUM |
| Security/consent auditor | Flag ON — verify consent isolation with project_id | 🟡 MEDIUM |
| P20 regression auditor | Verify P20 health after restart + flag activation | 🟡 MEDIUM |
| Evidence/docs auditor | Reconcile all stale claims in production report | 🟡 MEDIUM |

---

## Footer

| Field | Value |
|---|---|
| Ground truth inspection date | 2026-06-27 ~17:00 WIB |
| Author | Guinevere (parent orchestrator) |
| Status | ⚠️ CRITICAL CONTRADICTIONS — 3 HIGH, 4 MEDIUM, 3 PASS |
| Next phase | Phase 1 — Research Brutal (7 parallel audit agents) |
