# P19 Round-1 Audit — P20 Integration

**Auditor:** p20-integration
**Date:** 2026-06-25
**Scope:** Non-interference with P20, additive-only, gated on P20 pass, HARD STOP global.

> **HISTORICAL SNAPSHOT (2026-06-25):** Authored when P20 was in "PRODUCTION PASS HOLD (soak)". References to "P20 PRODUCTION PASS", "P20 pass", "24h re-soak", "LK-017" are historical. P20's final status is `P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK`; the P20 axis is satisfied by operator waiver. P19 waves touching P20 production files are held by operator discretion, not a pending soak gate. See `../../p20-waiver-gate-sync.md`. Body retained unchanged for traceability.

## Verdict: PASS (with conditions)

## Findings

### P20-01 [HIGH] P19-005 touches 9 P20 files — blast radius
**Finding:** P19-005 modifies `state.py`, `heartbeat.py`, `graph.py`, `cognition.py`, `dashboard_writer.py`, `redis_client.py`, `session_graph.py`, `self_improve.py`, `core/main.py` — 9 P20 files. P20 is in PRODUCTION PASS HOLD soak. Even additive changes risk regression.
**Impact:** P20 soak regression; production instability.
**Fix:** P19-005 must be split or sequenced: (a) additive `NotRequired` state fields first (zero-risk, checkpoint replay safe); (b) `thread_id` changes behind feature flag `feature:projects:enabled` (off by default, so P20 heartbeat behavior unchanged when off); (c) full project-aware heartbeat only after P20 pass + 24h re-soak. Each sub-step has its own P20 regression test (`tests/life_kernel/` all current focused tests pass; exact count captured in evidence).
**Wave:** P19-005 (split into 005a/005b/005c).

### P20-02 [MEDIUM] `thread_id="heartbeat"` hardcoded in 5 places
**Finding:** Scout confirmed `thread_id="heartbeat"` hardcoded at `heartbeat.py:302, 341, 365, 446, 629`. P19-005 must change all 5 to `heartbeat-{project_id}`. Missing one = isolation leak.
**Fix:** P19-005 scaffold: grep `thread_id.*heartbeat` in `heartbeat.py` must return 0 matches (all converted to `f"heartbeat-{project_id}"`). Add as Forbidden Pattern check.
**Wave:** P19-005.

### P20-03 [MEDIUM] BackgroundCognition per-project resource overhead
**Finding:** Plan P19-005 spawns one `BackgroundCognition` per active project (bounded N=3). Each has 6 asyncio loops → 18 loops for 3 projects. Plus heartbeat loops. Resource overhead on single VPS.
**Fix:** P19-005 scaffold: document CPU/RAM budget (e.g., ≤1 CPU core total for all project cognition loops); idle projects' cognition pauses (not just bounded count). Monitor via `p19_projects_active` gauge.
**Wave:** P19-005.

### P20-04 [LOW] Checkpointer no change — confirm
**Finding:** Plan says checkpointer needs no change (thread_id isolates). Confirm `checkpoint.py` create_postgres/redis_checkpointer uses thread_id as key (LangGraph native).
**Fix:** P19-005 verification: assert checkpoint state for `heartbeat-work` ≠ `heartbeat-personal` (no cross-project checkpoint leak).
**Wave:** P19-005.

## Summary
P20 non-interference is the most critical constraint. P19-005 touching 9 P20 files is the highest-risk wave and must be gated strictly on P20 PRODUCTION PASS, split into sub-steps (additive state → feature-flagged thread_id → full project-aware), with P20 regression tests at each step. HARD STOP stays global (confirmed). The thread_id hardcode (P20-02) must be fully converted with a grep check.

## Hard Rejection Check
- P20 autonomy not project-aware: ✅ MITIGATED (thread_id=heartbeat-{project_id}, per-project cognition)
- HARD STOP not global: ✅ MITIGATED (single key, P19-005 red-team)
- P20 disturbance: ✅ MITIGATED after P20-01 fix (split + feature flag + re-soak)
