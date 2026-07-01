# P19 Round-2 Re-Audit — P21/P22 Dependency

**Auditor:** p21-p22-dependency
**Date:** 2026-06-25
**Scope:** Verify all round-1 P21/P22 dependency findings resolved.

## Verdict: PASS

## Round-1 Findings — Resolution Status

| # | Round-1 Finding | Resolution | Status |
|---|---|---|---|
| P21P22-01 [MEDIUM] | `hermes_conversational.py` shared edit with P21 | Plan §P19-008: P19 threads `project_id` additive param first; P21 rebases; combined signature documented `_process_turn_core(..., project_id=None)` | ✅ RESOLVED |
| P21P22-02 [LOW] | Namespace template `p19:` vs `p22:` | Plan §P19-001 ADR: coexist (different domains); documented | ✅ RESOLVED |
| P21P22-03 [LOW] | P17 sync key not in a wave | Plan §P19-001 ADR: P17 deferred; P19 provides dimension; ADR note | ✅ RESOLVED |

## Re-Audit Notes
All 3 P21/P22 dependency findings resolved. The P21P22-01 coordination (shared `hermes_conversational.py` edit) is resolved by sequencing: P19-008 adds `project_id` as an additive parameter (default None) to `_process_and_respond()` FIRST, then P21-003 extracts `_process_turn_core` including the P19 param. The combined signature is documented. Existing `tests/discord/test_hermes_conversational.py` must still pass (no regression from additive param).

Namespace templates coexist (P19-internal `p19:` vs P22-integration `p22:`). P17 is correctly deferred with an ADR note.

The hard-rejection criteria (P21/P22 not ignored, migration chain intact) are mitigated.

## Hard Rejection Check
- P21/P22 dependency ignored: ✅ MITIGATED
- Migration chain breaks P21/P22: ✅ (nullable columns, P19→P21→P22 ordering)
