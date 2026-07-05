# P19 Round-1 Audit — Runtime / Deploy Readiness

**Auditor:** runtime-deploy-readiness
**Date:** 2026-06-25
**Scope:** Feature flag, canary, smoke, rollback, soak, P20 non-disturbance.

> **HISTORICAL SNAPSHOT (2026-06-25):** Authored when P20 was in "PRODUCTION PASS HOLD (soak)". References to "P20 pass", "24h soak", "re-soak" are historical. P20's final status is `P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK`; the P20 axis is satisfied by operator waiver. P19's own soak is operator-defined (P20's 24h soak was waived, not inherited). See `../../p20-waiver-gate-sync.md`. Body retained unchanged for traceability.

## Verdict: PASS (with conditions)

## Findings

### DEPLOY-01 [HIGH] Feature flag default + P20 heartbeat behavior when off
**Finding:** Plan uses `feature:projects:enabled` (default OFF). But when OFF, does `heartbeat.py` use `thread_id="heartbeat"` (legacy global) or `heartbeat-default`? If the thread_id change is unconditional, turning the flag off doesn't restore legacy behavior.
**Impact:** P20 soak regression even with flag off.
**Fix:** P19-005 scaffold: thread_id selection is conditional on the flag. When `feature:projects:enabled=false`, `thread_id="heartbeat"` (legacy, P20-compatible). When true, `thread_id=f"heartbeat-{project_id}"`. The flag gates the actual behavior change, not just surface features. Document explicitly.
**Wave:** P19-005.

### DEPLOY-02 [MEDIUM] No canary defined for single-user
**Finding:** Plan says "config-gated rollout (no blue-green for single-user)" but doesn't define the canary steps.
**Fix:** P19-012 scaffold: canary = (1) flag on in dev/staging if available, else (2) flag on in prod with `default` project only (no real multi-project), (3) create test project `p19-canary`, (4) run isolation tests, (5) HARD STOP test, (6) 24h soak, (7) flag stays on. Document each step.
**Wave:** P19-012.

### DEPLOY-03 [MEDIUM] Rollback with NOT NULL columns
**Finding:** If `p19_002` (NOT NULL) has run, rollback to `p20_001` must drop the NOT NULL constraint AND the column. If data exists, dropping is fine (additive column), but must be ordered.
**Fix:** P19-012 scaffold: rollback procedure = (1) `redis SET feature:projects:enabled false`; (2) `alembic downgrade p20_001_life_kernel_schema` (drops p19_002 then p19_001, removing columns); (3) verify P20 tests pass. Document that data in `project_id` columns is lost on rollback (acceptable — re-derivable from `default`).
**Wave:** P19-012.

### DEPLOY-04 [LOW] systemd per-project config optional
**Finding:** Plan mentions per-project systemd config optional. For single-process multi-project, no new units needed. Confirm.
**Fix:** P19-012: confirm no new systemd units required for P19 MVP (single `guinevere-core` process handles multiple projects via in-process vault + thread_id). Per-project units are a future optimization. Document.
**Wave:** P19-012.

## Summary
Deploy readiness is sound: feature-flag gated, config-gated rollout, 24h soak, rollback via alembic. The HIGH finding (DEPLOY-01, feature flag must gate thread_id behavior not just surface) is critical to avoid P20 regression with flag off. Canary steps (DEPLOY-02) and rollback ordering (DEPLOY-03) need documentation.

## Hard Rejection Check
- Implementation waves don't reach deploy/soak/final gate: ✅ MITIGATED (P19-012 deploy+soak+final gate)
- Deploy disturbs P20: ✅ MITIGATED after DEPLOY-01 fix (flag gates behavior; P20 pass required)
- No rollback verification: ✅ MITIGATED (P19-012 rollback procedure)
