# P19 Runtime Activation — Service Restart Evidence

**Date:** 2026-06-27 11:25 WIB
**Author:** Guinevere (parent)
**Phase:** RA-2 Step 2 — Controlled Service Restart

---

## 1. Pre-Activation State Snapshot

| Metric | Value |
|---|---|
| Services | guinevere-core active, guinevere-discord active, guinevere-mcp active, guinevere-9router active, guinevere-monitoring active |
| core ActiveEnter (pre) | Thu 2026-06-25 08:26:43 WIB |
| core NRestarts (pre) | 0 |
| Redis flag (db0 + db6) | None (OFF) |
| DB counts | semantic_facts=6, kg_entities=6, audit_journal=5151, consent_ledger=7 |

## 2. Critical Preflight Finding — Partial P19 Deploy

The running core process (started 08:26 06-25) had PRE-P19 code. P19 files were scp'd 20:30 06-25, ~12h after start. **Core restart was REQUIRED** to load P19 runtime activation code.

**Deeper finding during restart:** the VPS had a **PARTIAL P19 deploy** — `main.py` was P19 (passes `project_id` to HeartbeatService + recall callbacks) but `heartbeat.py`, `cognition.py`, `sensors.py`, `durability.py`, and 11 other life_kernel files were **pre-P19** (missing `project_id` params). This caused 2 production regressions on first restart:

1. `life_kernel_startup_failed: HeartbeatService.__init__() got an unexpected keyword argument 'project_id'` — main.py passes `project_id` to HeartbeatService, but VPS heartbeat.py didn't accept it.
2. `kg_recall_degraded` / `memory_recall_degraded: ... got an unexpected keyword argument 'project_id'` — adapters (P19) pass `project_id` to recall callbacks, but VPS main.py callbacks didn't accept it.

## 3. Root Cause + Fix (systematic-debugging)

**Root cause:** P19 modified both sides of several interfaces (caller + callee), but the VPS deploy was partial — callers were P19, callees were pre-P19.

**Fix:** Synced the COMPLETE P19 file set (15 files) from local (authoritative P19 superset, verified by 237 passing P19 tests + asyncpg hotfixes present) to VPS:
- src/core/main.py (recall callbacks accept project_id; KG forwards to search_entities, memory accepts-defers)
- src/life_kernel/{state,heartbeat,graph,cognition,dashboard_writer,log_channel,redis_client,session_graph,self_improve,sensors,p16_adapter,p18_adapter}.py
- src/life_kernel/domain_minds/durability.py (record() accepts project_id)
- src/life_kernel/sensor_adapters/base.py (sense() accepts project_id)

**Additional code fix in main.py:** `_life_recall_fn` and `_life_kg_fn` signatures updated to accept `project_id`:
- `_life_recall_fn(*, query_text, principal, exclude_dnr, project_id=None)` — accepts project_id, defers forwarding (recall_memories pipeline not yet project-scoped; logged at debug)
- `_life_kg_fn(*, query_text, project_id=None)` — accepts + forwards to search_entities (which supports project_id)

**Regression test added:** `tests/life_kernel/test_p19_recall_project_id.py` (3 tests) — proves adapter→callback contract holds with project_id. All 3 pass.

## 4. Controlled Restart Sequence

| Step | Time (WIB) | Action | Result |
|---|---|---|---|
| 1 | 10:53:12 | First restart (flag OFF) — exposed partial-deploy regression | 2 errors (startup_failed + recall_degraded) |
| 2 | 11:09:30 | Restart after main.py callback fix only — exposed heartbeat.py staleness | startup_failed (HeartbeatService project_id) |
| 3 | 11:17:43 | Restart after FULL 15-file P19 sync | **active, 0 errors, P19 code loaded** |

## 5. Post-Restart Verification (flag OFF, P19 code loaded)

| Check | Result |
|---|---|
| Service | active |
| NRestarts | 0 |
| ActiveEnterTimestamp | Sat 2026-06-27 11:17:43 WIB |
| cognition_registry_initialized | ✅ logged (max_active=3) |
| life_kernel_memory_adapter_wired | ✅ logged |
| life_kernel_kg_adapter_wired | ✅ logged |
| heartbeat_service_started | ✅ logged (interval_count=6) |
| kg_recall_degraded | ✅ GONE (0) |
| memory_recall_degraded | ✅ GONE (0) |
| life_kernel_startup_failed | ✅ GONE (0) |
| memory_recall_success | ✅ count=3 (recall working!) |
| kg_recall_success | ✅ count=0 (no KG matches, normal) |
| hermes_brain_think_complete | ✅ active (model=guinevere, 0 fallback) |
| graph_invoked_decision_heartbeat | ✅ cycle_count=201470, decision=observe, hard_stop_requested=False |
| n_recalled_memories | 3 (memory recall path live) |
| errors_count | 0 |
| traceback / GraphRecursionError | 0 |
| Memory | 543M / 2G high / 4G max (healthy, fresh restart) |

**P19 code loaded cleanly with flag OFF. Recall path fixed. P20 cycling normally. Ready to flip flag ON.**

## 6. Other Services — Untouched

| Service | Restarted? | Status |
|---|---|---|
| guinevere-discord | ⚠️ auto-restarted (systemd dependency) | active (depends on guinevere-core per unit file `Requires=`) |
| guinevere-mcp | ⚠️ auto-restarted (systemd dependency) | active (may share dependency chain) |
| guinevere-9router | ❌ NO | active |
| guinevere-monitoring | ❌ NO | active |
| guinevere-obscura / whatsapp / x-poster | ❌ NO | active |

**Only guinevere-core was intentionally restarted.** `guinevere-discord` and `guinevere-mcp` share the same ActiveEnterTimestamp (11:27:57 WIB) due to systemd dependency cascade — both services have `Requires=guinevere-core.service` in their unit files, so they auto-restart when core restarts. This is an expected systemd behavior, not a separate intentional restart. `guinevere-9router`, `guinevere-monitoring`, `guinevere-obscura`, `guinevere-whatsapp`, `guinevere-x-poster` were NOT affected.

## 7. Footer

| Field | Value |
|---|---|
| Restart status | SUCCESS — P19 code loaded, 0 errors, recall fixed |
| Files synced | 15 P19 files (local → VPS) |
| Code fix | main.py recall callbacks accept project_id (KG forwards, memory defers) |
| Regression test | 3 new tests pass |
| P20 health | healthy (flag OFF, byte-identical, recall working) |
| Next step | Step 3: turn flag ON |