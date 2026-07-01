# P19 Runtime Activation — Round 2 Re-Audit

**Date:** 2026-06-27 ~13:12 WIB
**Author:** Independent Re-Auditor (subagent)
**Scope:** Verify round-1 findings were actually fixed; re-confirm P20 runtime invariants
**VPS:** guinevere-vps (Tailscale, user guinevere)

---

## 1. Meta

| Field | Value |
|---|---|
| Audit type | Round 2 re-audit (fix verification + live runtime re-confirm) |
| Round 1 date | 2026-06-27 12:48 WIB |
| Re-audit date | 2026-06-27 ~13:12 WIB (~24 min after round 1) |
| Round 1 findings to verify | RA-RT-10 (documentation fix), RA-SC-04 (gap documentation) |
| P20 runtime re-confirm checks | RE-RT-01, RE-RT-02, RE-RT-03, RE-RT-06 |

---

## 2. Round-1 Findings Being Verified

| ID | Round-1 Status | Description |
|---|---|---|
| RA-RT-10 | NEEDS-REVIEW | service-restart evidence §6 claimed "only core restarted" but live state showed discord/mcp shared same ActiveEnterTimestamp. Root cause: systemd dependency cascade (Requires=guinevere-core.service). |
| RA-SC-04 | PASS/INFO | Adapter principal not project-scoped — graph state does not propagate project_id to memory adapter's principal parameter, so it falls back to "guinevere_core". |

---

## 3. Evidence Sources

| # | File | Purpose |
|---|---|---|
| 1 | `round-1/SUMMARY.md` | Round-1 findings and fix status |
| 2 | `round-1/runtime-p20-regression.md` | RA-RT-10 finding detail |
| 3 | `round-1/project-scoping-correctness.md` | RA-SC-04 finding detail |
| 4 | `../p19-service-restart-evidence.md` | Should now document systemd cascade in §6 |
| 5 | Live VPS (SSH) | Runtime state verification |

---

## 4. RE-RT-10: Service-Restart Evidence §6 Corrected

### 4.1 Document Review

**p19-service-restart-evidence.md §6 (current):**

Section 6 now reads (paraphrased):
- guinevere-discord: "auto-restarted (systemd dependency)" — active (depends on guinevere-core per unit file `Requires=`)
- guinevere-mcp: "auto-restarted (systemd dependency)" — active (may share dependency chain)
- guinevere-9router: NOT restarted, active
- guinevere-monitoring: NOT restarted, active

Explicit statement at bottom of §6:
> "Only guinevere-core was intentionally restarted. guinevere-discord and guinevere-mcp share the same ActiveEnterTimestamp (11:27:57 WIB) due to systemd dependency cascade — both services have Requires=guinevere-core.service in their unit files, so they auto-restart when core restarts. This is an expected systemd behavior, not a separate intentional restart."

### 4.2 Live VPS Cross-Check

| Service | ActiveEnterTimestamp | NRestarts |
|---|---|---|
| guinevere-core | Sat 2026-06-27 11:27:57 WIB | 0 |
| guinevere-discord | Sat 2026-06-27 11:27:57 WIB | 0 |
| guinevere-mcp | Sat 2026-06-27 11:27:57 WIB | 0 |

**Live state matches the corrected evidence exactly.** Discord and mcp share core's ActiveEnterTimestamp. The evidence now honestly attributes this to systemd dependency cascade (`Requires=guinevere-core.service`), not to an intentional restart.

### 4.3 Assessment

The round-1 finding was that §6 contradicted live state by claiming "only core restarted." The current §6 no longer makes that misleading claim. It explicitly acknowledges the cascade, explains the mechanism (Requires=), and distinguishes "intentionally restarted" from "auto-restarted (systemd dependency)."

| Field | Value |
|---|---|
| **RE-RT-10** | **PASS** |
| Evidence | §6 corrected: systemd cascade documented, live state matches |

---

## 5. RE-SC-04: Gap Honestly Documented

### 5.1 Document Review

**round-1/project-scoping-correctness.md RA-SC-04 section (lines 140-155):**

The section is titled "RA-SC-04: Memory adapter principal scoped to project:{project_id} — FAIL (Known Gap)". It:
- States clearly: `project_id=None` in graph state, so adapter falls back to `"guinevere_core"`
- Traces the code path: heartbeat.py -> graph input (no project_id) -> state.py (no project_id field) -> observe_node context -> adapter fallback
- Documents impact honestly: single project = no cross-project data leakage, recall works (count=3)
- Classifies as INFO severity, not blocker
- Lists a recommendation for future resolution (add project_id to graph state)

The summary table (line 249) marks it as "FAIL — INFO (known gap, documented)".

### 5.2 Assessment

The gap is **not hidden**. The document:
1. Labels it FAIL (not passing it off as PASS)
2. Explains exactly why the fallback occurs (code trace)
3. Justifies why it is INFO (not HIGH/MEDIUM): single project, no data leak
4. Does not claim the problem is fixed — it is documented as a known gap for future work

| Field | Value |
|---|---|
| **RE-SC-04** | **PASS** (gap honestly documented, not hidden) |

---

## 6. RE-RT-01: Core Active, NRestarts=0

### 6.1 Live VPS Verification

```
$ systemctl is-active guinevere-core.service
active

$ systemctl show guinevere-core.service -p NRestarts -p ActiveEnterTimestamp
NRestarts=0
ActiveEnterTimestamp=Sat 2026-06-27 11:27:57 WIB
```

### 6.2 Assessment

Service is active. NRestarts=0 (no crash-restart cycles). ActiveEnterTimestamp unchanged from activation time (11:27:57 WIB). Approximately 2 hours 45 minutes of continuous uptime since activation.

| Field | Value |
|---|---|
| **RE-RT-01** | **PASS** |
| Uptime | ~2h45m since activation, 0 restarts |

---

## 7. RE-RT-02: Brain Think Complete Active, 0 Fallback

### 7.1 Live VPS Verification

```
$ journalctl -u guinevere-core.service -n 500 -o cat | grep hermes_brain_think_complete | tail -2

2026-06-27 13:10:24 [info] hermes_brain_think_complete
  estimated_cost_usd=0.0 input_tokens=464473 model=guinevere
  output_tokens=57474 total_tokens=1119451

2026-06-27 13:10:57 [info] hermes_brain_think_complete
  estimated_cost_usd=0.0 input_tokens=540421 model=guinevere
  output_tokens=54360 total_tokens=1128541
```

```
$ journalctl -u guinevere-core.service -n 500 -o cat | grep -c hermes_brain_fallback
0
```

### 7.2 Assessment

Brain is actively thinking — last 2 entries are from 13:10:24 and 13:10:57 WIB (minutes before audit). Model=guinevere in both. Token volume has grown to ~1.1M total (up from ~861K at round 1), indicating sustained heavy cognition. Fallback count is 0 (confirmed via exit code 1 = grep found 0 matches).

| Field | Value |
|---|---|
| **RE-RT-02** | **PASS** |
| Model | guinevere (no fallback) |
| Token volume | ~1.1M total tokens per cycle (increased from ~861K at round 1) |

---

## 8. RE-RT-03: Graph Cycling, Hard Stop Clear

### 8.1 Live VPS Verification

```
$ journalctl -u guinevere-core.service -n 500 -o cat | grep graph_invoked_decision | tail -1

2026-06-27 13:11:40 [info] graph_invoked_decision_heartbeat
  act_count=129 cycle_count=130 decision=observe hard_stop_requested=None
  last_autonomous_decision='act on: Knowledge graph seeding\nScan project
  files/configs/docs to extract entities and relationships for KG population,
  enabling future autonomous reasoning.'
  n_commitments=0 n_concerns=0 n_goals=1 n_journal_entries=128
  n_observations=100 n_recalled_concepts=0 n_recalled_memories=3
  phase=None world_model_status=active
```

### 8.2 Assessment

Graph is actively cycling. cycle_count=130 (up from 99 at round 1, +31 cycles in ~24 min). hard_stop_requested=None (clear). world_model_status=active. Brain is executing an autonomous knowledge-graph seeding goal. 128 journal entries, 100 observations. Progressing, not stuck.

| Field | Value |
|---|---|
| **RE-RT-03** | **PASS** |
| Cycle count | 130 (advancing from 99 at round 1) |
| Hard stop | None (clear) |
| World model | active |

---

## 9. RE-RT-06: Flag ON in Redis (db6 = true)

### 9.1 Live VPS Verification

```
$ python3 -c "import redis; r=redis.Redis(host='localhost', port=6380, db=6, password='...'); print(r.get('feature:projects:enabled'))"
b'true'
```

### 9.2 Assessment

Feature flag `feature:projects:enabled` is `b'true'` in Redis db6. Confirmed ON.

| Field | Value |
|---|---|
| **RE-RT-06** | **PASS** |
| Redis key | feature:projects:enabled |
| Redis db | 6 |
| Value | b'true' |

---

## 10. Re-Audit Verdict Matrix

| Check | Description | Verdict |
|---|---|---|
| RE-RT-10 | service-restart evidence §6 corrected (systemd cascade documented) | **PASS** |
| RE-SC-04 | gap honestly documented (not hidden) | **PASS** |
| RE-RT-01 | core active, NRestarts=0 | **PASS** |
| RE-RT-02 | brain think_complete active, 0 fallback | **PASS** |
| RE-RT-03 | graph cycling, hard_stop clear | **PASS** |
| RE-RT-06 | flag ON in redis | **PASS** |

**6/6 PASS. 0 FAIL. 0 NEEDS-REVIEW.**

---

## 11. Observations

### 11.1 Token Volume Increase

Token volume per think_complete cycle has increased from ~861K (round 1) to ~1.1M (round 2, ~24 min later). The brain is accumulating more context as it processes observations and journal entries. Not a problem but worth monitoring for cost.

### 11.2 Cycle Progression

cycle_count advanced from 99 to 130 in ~24 minutes (1.3 cycles/min). The brain is maintaining a steady autonomous rhythm, executing the KG seeding goal.

### 11.3 Journal Entry Growth

n_journal_entries grew from 97 (round 1) to 128 (round 2). n_observations stable at 100 (possibly capped). The brain continues to record and learn.

---

## 12. Final Verdict

| Field | Value |
|---|---|
| Round 1 findings verified | 2/2 (RA-RT-10 fixed, RA-SC-04 documented) |
| P20 runtime re-confirmed | 4/4 (RE-RT-01, RE-RT-02, RE-RT-03, RE-RT-06) |
| Total checks | 6/6 PASS |
| Blockers | 0 |
| Regressions | 0 |
| Verdict | **PASS** |

**Round 2 re-audit: PASS.** All round-1 findings are verified fixed or honestly documented. P20 runtime invariants are maintained. No regressions detected.

---

## Sign-off

| Field | Value |
|---|---|
| Re-auditor | Independent subagent |
| Re-audit date | 2026-06-27 ~13:12 WIB |
| Verdict | **PASS** |
| Next action | None (round-2 re-audit complete) |
