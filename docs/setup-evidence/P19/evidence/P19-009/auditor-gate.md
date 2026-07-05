# P19-009 Auditor Gate: Consent/Surveillance Scoped Policy Enforcement

**Date:** 2026-06-25
**Wave/Step:** P19-009

---

## Gate Checklist

### A. Structural Completeness (7 files)

| File | Exists | Notes |
|------|--------|-------|
| `src/surveillance/consent_gate.py` | YES | Modified: project_id param, 3 new scopes, _build_cache_key, _handle_db_status |
| `src/surveillance/consumer.py` | YES | Modified: project_id extraction + passthrough |
| `src/surveillance/models.py` | YES | No change needed (nullable project_id from P19-003) |
| `src/discord/cmd_consent.py` | YES | Modified: project option on grant/revoke/view |
| `tests/projects/test_consent_isolation.py` | YES | 6 red-team test classes + structural invariants |
| `docs/setup-evidence/P19/evidence/P19-009/verification.md` | YES | Full verification |
| `docs/setup-evidence/P19/evidence/P19-009/auditor-gate.md` | YES | This document |

### B. Signature Correctness

| Check | Status |
|-------|--------|
| `check_consent(scope, project_id=None)` signature | PASS |
| `project_id` default = None (legacy) | PASS |
| `ConsentCheckResult.project_id` field with default None | PASS |
| `ConsentChecker` protocol updated | PASS |
| `invalidate_cache(scope, project_id=None)` updated | PASS |
| `_query_ledger(project_id, global_only, max_age_hours)` | PASS |

### C. Scope Design Invariants

| Check | Status |
|-------|--------|
| VALID_SURVEILLANCE_SCOPES unchanged (5 scopes) | PASS |
| VALID_CONSENT_SCOPES has 3 new scopes | PASS |
| `consent.memory.cross_project` in _GLOBAL_ONLY_SCOPES | PASS |
| `consent.emergency.break_glass_project` in _PROJECT_ONLY_SCOPES | PASS |
| `consent.autonomy.high_blast` NOT in _GLOBAL_ONLY_SCOPES | PASS |
| `consent.autonomy.high_blast` NOT in _PROJECT_ONLY_SCOPES | PASS |
| HARD STOP not in _ALL_VALID_SCOPES | PASS |
| `_TIME_BOUND_SCOPES` has break_glass → 4h | PASS |

### D. Safety Invariants

| Check | Status |
|-------|--------|
| SAFE-03: high_blast per-project | PASS |
| SAFE-04: HARD STOP global (not touched) | PASS |
| ARCH-04: cross_project global-only | PASS |
| SEC-04: break_glass project-only, 4h time-bound | PASS |
| Fail-closed preserved | PASS |
| No safety scopes (persona.normal/escalated/y5) project-scoped | PASS |

### E. Hard Rejection Criteria

| Criterion | PASS/FAIL |
|-----------|-----------|
| Consent not per-project | PASS — project_id param, project-scoped query |
| HARD STOP scoped | PASS — not a consent scope |
| Project pause == HARD STOP | PASS — pause only blocks that project |
| Safety scopes project-scoped | PASS — safety scopes not in consent_gate |
| Autonomy auto-resume paused project | PASS — paused → blocked |
| Project autonomy touches core | PASS — high_blast per-project only |
| `# type: ignore` / `as any` / bare except | PASS — 0 matches |
| Evidence missing | PASS — both files present |

### F. Forbidden Pattern Scan

| Pattern | File | Matches |
|---------|------|---------|
| `# type: ignore` | consent_gate.py | 0 |
| `as any` | consent_gate.py | 0 |
| bare `except:` | consent_gate.py | 0 |
| `# type: ignore` | consumer.py | 0 |
| `# type: ignore` | cmd_consent.py | 0 |

---

## Verdict

**PASS**

All structural, safety, and hard-rejection checks pass. Project-scoped consent enforcement is additive (project_id=None preserves legacy). HARD STOP remains global. New scopes correctly classified. Red-team test suite covers all 6 required scenarios.

**Sign-off:** Guinevere (P19-009 implementation agent)
