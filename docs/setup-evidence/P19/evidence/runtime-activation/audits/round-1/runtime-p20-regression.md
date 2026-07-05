# P19 Runtime Activation — Runtime / P20 Regression Audit

**Round:** 1
**Date:** 2026-06-27 ~12:48 WIB (live verification)
**Auditor:** Independent auditor (subagent)
**Scope:** RUNTIME ACTIVATION / P20 REGRESSION

---

## 1. Meta

| Field | Value |
|---|---|
| Audit type | Live VPS verification + evidence cross-check |
| VPS | guinevere-vps (Tailscale, user guinevere) |
| Core service | guinevere-core.service |
| Activation time (claimed) | 2026-06-27 11:27:57 WIB |
| Audit time | 2026-06-27 ~12:48 WIB (~80 min post-activation soak) |

---

## 2. Scope

Verify P19 runtime activation is live, stable, and has not regressed P20 invariants. Cross-check operator evidence against live VPS state. Confirm: service health, brain activity, graph cycling, no errors, memory health, Redis flag state, dashboard state, recall path integrity, and no unrelated service disruption.

---

## 3. Evidence Sources

| # | File | Purpose |
|---|---|---|
| 1 | `p19-runtime-preflight.md` | Pre-activation baseline + code-load gap discovery |
| 2 | `p19-service-restart-evidence.md` | Controlled restart sequence (3 attempts, partial-deploy fix) |
| 3 | `p19-flag-enable-evidence.md` | Flag ON + LIFE_KERNEL_PROJECT_ID env var |
| 4 | `p19-soak-observation.md` | 5-min post-activation soak (CLEAN) |
| 5 | `p19-p20-non-regression.md` | P20 invariant checklist (all PASS) |

---

## 4. Live VPS Verification

### 4.1 Check Results

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| 1 | `systemctl is-active guinevere-core.service` | active | **active** | PASS |
| 2 | `systemctl show ... -p NRestarts -p ActiveEnterTimestamp` | NRestarts=0, ActiveEnter=11:27:57 WIB | **NRestarts=0, ActiveEnter=Sat 2026-06-27 11:27:57 WIB** | PASS |
| 3 | `grep hermes_brain_think_complete ... tail -2` | recent, model=guinevere | **12:46:11 + 12:46:34, model=guinevere, ~861K-863K total tokens** | PASS |
| 4 | `grep -c hermes_brain_fallback` | 0 | **0** | PASS |
| 5 | `grep graph_invoked_decision ... tail -1` | cycling, hard_stop_requested=None | **cycle_count=99, decision=observe, hard_stop_requested=None, world_model_status=active** | PASS |
| 6 | `grep -ci traceback` | 0 | **0** | PASS |
| 7 | `grep -ci GraphRecursionError` | 0 | **0** | PASS |
| 8 | `systemctl show ... -p MemoryCurrent -p MemoryHigh -p MemoryMax` | healthy | **505.7 MB / 2 GB / 4 GB (24.7% of high)** | PASS |
| 9 | Redis db6 `feature:projects:enabled` | `b'true'` | **`b'true'`** | PASS |
| 10 | Redis db0 `life_kernel:hard_stop` | None | **None** | PASS |
| 11 | Redis db0 `life_kernel:dashboard_message_id` | `b'1519135545501028549'` | **`b'1519135545501028549'`** | PASS |
| 12 | `grep -c recall_degraded` (core journal) | 0 | **0** | PASS |
| 13 | Other services NRestarts | 0 (untouched) | **discord=0, mcp=0, 9router=0, monitoring=0** | PASS (see finding) |

### 4.2 Additional Live Observations

- **Brain token volume:** The most recent think_complete events show ~861K-863K total tokens (401K-475K input, 43K-45K output). This indicates sustained, heavy cognition — the brain is processing large context windows. No truncation or error signals.
- **Graph cycle progression:** cycle_count=99 at audit time. The 5-min soak observation showed cycle_count=9 at 11:37. The brain has continued cycling autonomously for ~70 additional minutes post-soak, reaching 99 cycles. This is genuine sustained autonomous operation.
- **Autonomous goal:** The graph shows `last_autonomous_decision='act on: Knowledge graph seeding — Scan project files/configs/docs to extract entities and relationships for KG population'`. The brain generated and is executing a self-directed knowledge graph population goal. This is emergent autonomous behavior, not a stuck loop.
- **n_observations=100, n_journal_entries=97:** The brain has accumulated 100 observations and 97 journal entries, showing continuous learning and recording.

---

## 5. Audit Checks

### RA-RT-01: Core active post-activation, NRestarts=0

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | `systemctl is-active` = active. NRestarts=0. ActiveEnterTimestamp = Sat 2026-06-27 11:27:57 WIB (matches claimed activation time). No crash-restart cycles. |
| Notes | Clean activation restart. No restarts since. |

### RA-RT-02: Brain think_complete active, 0 fallback

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | Last 2 think_complete entries at 12:46:11 and 12:46:34 WIB (minutes before audit). model=guinevere. Fallback count = 0. Token volume healthy (861K-863K total). |
| Notes | Brain is actively and continuously processing. No fallback to any other model. |

### RA-RT-03: graph_invoked_decision cycling, hard_stop clear

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | Latest graph_invoked_decision at 12:47:45: cycle_count=99, decision=observe, hard_stop_requested=None, world_model_status=active. n_goals=1 (KG seeding). |
| Notes | Graph is cycling and progressing. Not stuck. hard_stop is None (clear). |

### RA-RT-04: No traceback/recursion

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | `grep -ci traceback` = 0. `grep -ci GraphRecursionError` = 0. Zero error signals in the last 500 journal lines. |
| Notes | Clean runtime. No errors of any kind. |

### RA-RT-05: Memory healthy (no OOM risk)

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | MemoryCurrent = 530,235,392 bytes (505.7 MB). MemoryHigh = 2,147,483,648 bytes (2,048 MB). MemoryMax = 4,294,967,296 bytes (4,096 MB). Usage is 24.7% of high limit. 3.8x headroom before high. 8x headroom before max. |
| Notes | Healthy. No OOM risk. The brain has been running for ~80 minutes and memory is stable. |

### RA-RT-06: Flag ON in Redis (db6 = true)

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | `redis GET feature:projects:enabled` in db6 = `b'true'`. db0 also set to `b'true'` (consistency). |
| Notes | Flag is ON and being read by the heartbeat/cognition path (db6 client). |

### RA-RT-07: life_kernel:hard_stop clear

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | `redis GET life_kernel:hard_stop` in db0 = None. Graph log confirms hard_stop_requested=None. |
| Notes | No hard stop. Brain is operating normally. |

### RA-RT-08: dashboard_message_id canonical

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | `redis GET life_kernel:dashboard_message_id` in db0 = `b'1519135545501028549'`. Matches expected canonical ID. |
| Notes | Dashboard message ID is stable and canonical. Dashboard writer is active (dashboard_edited logged during soak). |

### RA-RT-09: P20 recall path not degraded

| Field | Value |
|---|---|
| Status | **PASS** |
| Evidence | `grep -c recall_degraded` in core journal = 0. Soak observation showed memory_recall_success=9 during 5-min window. The kg_recall_degraded and memory_recall_degraded regressions from the partial-deploy incident are fully resolved. |
| Notes | Recall path is working. The partial-deploy regression (project_id keyword argument mismatch) was fixed by syncing all 15 P19 files. No degraded warnings since. |

### RA-RT-10: No unrelated services restarted

| Field | Value |
|---|---|
| Status | **NEEDS-REVIEW** |
| Evidence | guinevere-core ActiveEnter = Sat 2026-06-27 11:27:57 WIB. guinevere-discord ActiveEnter = Sat 2026-06-27 11:27:57 WIB. guinevere-mcp ActiveEnter = Sat 2026-06-27 11:27:57 WIB. guinevere-9router ActiveEnter = Tue 2026-06-23 09:55:08 WIB (untouched). guinevere-monitoring ActiveEnter = Mon 2026-06-08 15:45:49 WIB (untouched). |
| **Finding** | **guinevere-discord and guinevere-mcp share the EXACT same ActiveEnterTimestamp (11:27:57 WIB) as guinevere-core.** The evidence file `p19-service-restart-evidence.md` Section 6 states "Only guinevere-core restarted. All other services untouched." This is **contradicted by live state**. Discord and MCP were also restarted at 11:27:57 — likely as part of the same restart sequence that added `LIFE_KERNEL_PROJECT_ID` to `.env.core`. |
| Impact | **None on P20.** All services show NRestarts=0 and are active. No functionality was lost. Discord, MCP, 9router, and monitoring are all healthy. |
| Root cause | The evidence in Section 6 was likely captured after the 11:17:43 restart (Step 3 in the restart sequence), NOT after the final 11:27:57 restart (Step 4 — env var load). The 11:27:57 restart appears to have been a broader restart event that also cycled discord and mcp. |

---

## 6. Discrepancies / Findings

### 6.1 FINDING: Service restart scope mismatch (RA-RT-10)

**Severity:** LOW (documentation accuracy, no runtime impact)

The evidence claims "Only guinevere-core restarted" but live state shows guinevere-discord and guinevere-mcp also restarted at the same timestamp (11:27:57 WIB). This is a documentation gap, not a runtime issue. All 3 services are healthy with NRestarts=0.

**Recommendation:** Update `p19-service-restart-evidence.md` Section 6 to reflect the actual 11:27:57 restart scope. Clarify whether the broader restart was intentional (e.g., `systemctl restart guinevere-core guinevere-discord guinevere-mcp`) or a side effect of a host-level restart.

### 6.2 FINDING: Pre-existing warnings (acknowledged, not P19)

The soak observation and non-regression evidence correctly identify 4 pre-existing warnings:
- `hermes_bridge.listener_error` (channel permission)
- `loop_manager.resume_pending_loops_failed` (DB auth for different user)
- `Failed to load plugin 'browser-browser-use'` (missing module)
- `hermes_bridge.hmac_disabled` (dev-only)

These are NOT P19 regressions. They existed before activation. No action required for this audit.

### 6.3 OBSERVATION: High token volume

The brain is processing ~861K-863K total tokens per think_complete cycle. This is a very large context window. Not a problem per se (the system is designed for this), but worth monitoring for cost and latency as soak continues.

---

## 7. P20 Regression Assessment

| P20 Invariant | Pre-Activation | Post-Activation (Live) | Regression? |
|---|---|---|---|
| Service active | active, NRestarts=0 | active, NRestarts=0 | NO |
| Brain think_complete | active, model=guinevere | active, model=guinevere, 861K tokens | NO |
| Brain fallback | 0 | 0 | NO |
| Graph cycling | active, hard_stop=False | cycle_count=99, hard_stop=None | NO |
| Traceback | 0 | 0 | NO |
| GraphRecursionError | 0 | 0 | NO |
| Memory healthy | 543M/2G | 505.7M/2G | NO (improved) |
| Dashboard message ID | canonical | canonical (1519135545501028549) | NO |
| Recall path | working | working (0 degraded) | NO (fixed) |
| hard_stop | clear | clear (None) | NO |

**P20 Regression: NONE.** All P20 invariants are maintained or improved. The recall path regression from the partial-deploy incident is fully resolved.

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Flag OFF rollback needed | Low | Low | Instant `DEL feature:projects:enabled` in db6 (no restart). Confirmed in flag evidence. |
| Full rollback needed | Low | Medium | Remove `LIFE_KERNEL_PROJECT_ID` from `.env.core` + restart core. |
| Memory creep over extended soak | Low | Medium | Currently 24.7% of high limit. 3.8x headroom. Monitor if soak extends beyond 24h. |
| Token cost escalation | Low | Low | ~861K tokens/cycle is high but within design parameters. Monitor billing. |
| Service restart scope confusion | Low | Low | Documentation gap (RA-RT-10). No runtime impact. |

---

## 9. Recommendations

1. **REQUIRED:** Update `p19-service-restart-evidence.md` Section 6 to reflect the actual 11:27:57 restart scope (discord + mcp also restarted). This is a documentation accuracy fix, not a code fix.
2. **OPTIONAL:** Monitor token volume (~861K/cycle) over extended soak. If cost becomes a concern, consider context window management.
3. **OPTIONAL:** Document the 4 pre-existing warnings as known technical debt items separate from P19.
4. **NO ACTION:** P20 waiver remains valid. The activation restart is authorized and does not void the waiver.

---

## 10. Verdict

| Check | Status |
|---|---|
| RA-RT-01: Core active, NRestarts=0 | **PASS** |
| RA-RT-02: Brain think_complete, 0 fallback | **PASS** |
| RA-RT-03: Graph cycling, hard_stop clear | **PASS** |
| RA-RT-04: No traceback/recursion | **PASS** |
| RA-RT-05: Memory healthy | **PASS** |
| RA-RT-06: Flag ON (db6) | **PASS** |
| RA-RT-07: hard_stop clear | **PASS** |
| RA-RT-08: dashboard_message_id canonical | **PASS** |
| RA-RT-09: Recall path not degraded | **PASS** |
| RA-RT-10: No unrelated services restarted | **NEEDS-REVIEW** (discord + mcp also restarted; no runtime impact; documentation gap) |

### Overall: **NEEDS-REVIEW**

9 of 10 checks PASS outright. RA-RT-10 is NEEDS-REVIEW due to a documentation discrepancy (evidence claims only core restarted, live state shows discord and mcp also restarted at the same timestamp). This is a **documentation accuracy issue with zero runtime impact** — all services are healthy and no P20 functionality was degraded.

If the operator confirms the broader restart was intentional or acceptable, this audit upgrades to **PASS**.

---

## 11. Sign-off

| Field | Value |
|---|---|
| Auditor | Independent subagent |
| Audit date | 2026-06-27 ~12:48 WIB |
| Verdict | NEEDS-REVIEW (1 documentation discrepancy, 0 runtime regressions) |
| Next action | Operator to confirm restart scope and update evidence file |

---

## 12. Appendix — Raw Data

### A. Service ActiveEnterTimestamps (live)

| Service | ActiveEnterTimestamp | NRestarts |
|---|---|---|
| guinevere-core | Sat 2026-06-27 11:27:57 WIB | 0 |
| guinevere-discord | Sat 2026-06-27 11:27:57 WIB | 0 |
| guinevere-mcp | Sat 2026-06-27 11:27:57 WIB | 0 |
| guinevere-9router | Tue 2026-06-23 09:55:08 WIB | 0 |
| guinevere-monitoring | Mon 2026-06-08 15:45:49 WIB | 0 |

### B. Memory Details

| Metric | Value (bytes) | Value (human) |
|---|---|---|
| MemoryCurrent | 530,235,392 | 505.7 MB |
| MemoryHigh | 2,147,483,648 | 2,048 MB (2 GB) |
| MemoryMax | 4,294,967,296 | 4,096 MB (4 GB) |
| Usage % of High | 24.7% | — |
| Headroom to High | 1,517 MB | 3.0x current |
| Headroom to Max | 3,507 MB | 6.9x current |

### C. Redis State (live, verified with venv python + .env.core)

| DB | Key | Value |
|---|---|---|
| db6 | feature:projects:enabled | b'true' |
| db0 | life_kernel:hard_stop | None |
| db0 | life_kernel:dashboard_message_id | b'1519135545501028549' |

### D. Last graph_invoked_decision (live, raw)

```
2026-06-27 12:47:45 [info] graph_invoked_decision_heartbeat
  act_count=98 cycle_count=99 decision=observe hard_stop_requested=None
  last_autonomous_decision='act on: Knowledge graph seeding
  Scan project files/configs/docs to extract entities and relationships
  for KG population, enabling future autonomous reasoning.'
  n_commitments=0 n_concerns=0 n_goals=1 n_journal_entries=97
  n_observations=100 n_recalled_concepts=0 n_recalled_memories=3
  phase=None world_model_status=active
```

### E. Last hermes_brain_think_complete (live, raw)

```
2026-06-27 12:46:34 [info] hermes_brain_think_complete
  estimated_cost_usd=0.0 input_tokens=475241 model=guinevere
  output_tokens=45110 total_tokens=863007
```
