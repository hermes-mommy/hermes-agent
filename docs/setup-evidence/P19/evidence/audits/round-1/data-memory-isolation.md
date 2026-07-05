# P19 Round-1 Audit — Data & Memory Isolation

**Auditor:** data-memory-isolation
**Date:** 2026-06-25
**Scope:** Memory/KG partition, leak prevention, RLS optional, backfill, principal model.

## Verdict: PASS (with conditions)

## Findings

### DATA-01 [HIGH] `project_scope` default value risk
**Finding:** Plan adds `project_scope TEXT DEFAULT 'project'` to memory tables. But existing rows being backfilled get `project_scope = 'project'` + `project_id = default`. If any existing memory is genuinely global (persona facts stored as episodes), it would be mislabeled as project-scoped and invisible to other projects.
**Impact:** Persona/global memories written before P19 become invisible cross-project → appears like memory loss.
**Fix:** P19-011 backfill: classify existing episodes. Heuristic: episodes with `source` in {persona, adr, safety, operator} → `project_scope = 'global'`; else `project_scope = 'project'`. Document the classification rule. Provide a manual override (`/memory set-scope <id> global`) for misclassified rows.
**Wave:** P19-011.

### DATA-02 [MEDIUM] pgvector filtered similarity performance
**Finding:** Plan says pgvector supports filtered ANN, but for `project_id` filter, the recommended approach (partial ivfflat index per project vs composite filter) is unspecified. For large episode counts, brute-force filtered scan could be slow.
**Fix:** P19-004 scaffold: for single-user scale (thousands of episodes), composite index `(project_id, embedding)` + filtered brute-force is fine. Document the threshold (e.g., >50k episodes/project → partial ivfflat index per project). Not a blocker for MVP.
**Wave:** P19-004.

### DATA-03 [MEDIUM] DNR global vs per-project ambiguity
**Finding:** Plan §11 says global-scope DNR applies to all projects, project DNR is per-project. But `do_not_recall` is a single boolean column. How to distinguish "this row is DNR globally" vs "DNR for project X"?
**Impact:** A project-scoped episode marked DNR — is it DNR only for its project, or globally?
**Fix:** `do_not_recall` on a `project_scope='global'` row = global DNR. `do_not_recall` on a `project_scope='project'` row = project-scoped DNR (only that project's recall blocked). The scope column disambiguates. Document in P19-004.
**Wave:** P19-004.

### DATA-04 [LOW] KG entity resolution cross-project merge risk
**Finding:** Plan says entity resolution scoped by `project_id`. But if the resolver uses a global entity cache or global RCTE, cross-project entities could merge.
**Fix:** P19-004 scaffold: assert entity resolution query includes `WHERE project_id = :pid` (or `project_scope='global'` for shared entities). Test: entity "Alice" in work ≠ "Alice" in personal.
**Wave:** P19-004.

## Summary
Memory/KG isolation design is sound: `project_id` + `project_scope` + wrapper + tests + optional RLS. The HIGH finding (DATA-01, global memory mislabeling on backfill) must be fixed to avoid apparent memory loss for persona facts. DATA-03 (DNR disambiguation) is a documentation gap solved by the scope column.

## Hard Rejection Check
- Shared persona causes cross-project memory leak: ✅ MITIGATED (global scope explicit + wrapper)
- Memory leak across projects: ✅ MITIGATED (wrapper WHERE + isolation tests)
- Namespace flows to memory/KG: ✅ (project_id on all memory/KG tables)
