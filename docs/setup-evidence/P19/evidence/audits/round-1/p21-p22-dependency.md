# P19 Round-1 Audit — P21/P22 Dependency

**Auditor:** p21-p22-dependency
**Date:** 2026-06-25
**Scope:** Registry read-only, nullable seam, migration chain, namespace template.

## Verdict: PASS

## Findings

### P21P22-01 [MEDIUM] P21 `_process_turn_core` refactor + P19 project_id threading conflict
**Finding:** P21-003 refactors `src/discord/hermes_conversational.py:427-691` to extract `_process_turn_core`. P19-008 also modifies `hermes_conversational.py` to thread `project_id` into the turn path. Both touch the same function.
**Impact:** Merge conflict; ordering ambiguity.
**Fix:** P19 plan §Collision Scan already notes "Sequence: P19 project_id threading, then P21 refactor (or coordinate)". Refine: P19-008 threads `project_id` as a parameter to `_process_and_respond()` FIRST (additive param, default None). P21-003 then extracts `_process_turn_core(content, ..., project_id=None)` including the P19 param. Document the combined signature.
**Wave:** P19-008 + P21-003 coordination.

### P21P22-02 [LOW] P22 namespace template alignment
**Finding:** P19 uses `p19:{project_slug}:{domain}:{resource-id}`; P22 uses `p22:<domain>:<provider>:<resource-id>` (project-qualified `<project>:p22:...`). The templates differ in prefix (`p19:` vs `p22:`). Is this intentional?
**Fix:** Clarify: P19's `p19:` template is for P19-internal identifiers (project registry entries). P22's `p22:` template is for P22 integration resources. They coexist (different domains). No conflict. Document in P19-001 ADR.
**Wave:** P19-001.

### P21P22-03 [LOW] P17 sync key not in any wave
**Finding:** Plan says P17 references `project_id` in sync key, but no P19 wave implements the sync-key design. P17 is TBD.
**Fix:** Acceptable — P17 is not started; P19 provides the `project_id` dimension; P17 implements sync when it starts. Add a note in P19-001 ADR that P17 should reference `project_id` once both exist.
**Wave:** P19-001 (note only).

## Summary
P21/P22 dependency is well-handled: P19 owns registry (read-only by P22), nullable seam satisfied, migration chain P19→P21→P22, namespace templates coexist. The only real coordination need (P21P22-01) is the `hermes_conversational.py` shared edit, resolved by sequencing P19 project_id param before P21 refactor. P17 is deferred (correct).

## Hard Rejection Check
- P21/P22 dependency ignored: ✅ MITIGATED (registry read-only, nullable seam, migration chain, namespace template)
- Migration chain breaks P21/P22: ✅ (nullable columns, P19→P21→P22 ordering)
