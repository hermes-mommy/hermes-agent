# Architecture Audit Report — Phase 3 Planner Gate

**Auditor**: Architecture/Code Quality  
**Date**: 2026-06-04  
**Document Reviewed**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md` (641 lines)  
**Reference Files**: `src/hermes/memory_bridge.py` (295 lines), `src/memory/read_pipeline.py` (963 lines), `src/memory/write_pipeline.py` (359 lines), `src/memory/dnr.py` (418 lines), `src/discord/conversational_handler.py` (631 lines), `docs/setup-evidence/hermes-migration/batch-plan-migration.md` (Phase 3 section, lines 997–1126)

---

## Verdict: **NEEDS REVIEW** (3 items flagged, all fixable without redesign)

---

## Checklist Results

| # | Check | Verdict | Finding |
|---|---|---|---|
| 1 | Step Atomicity | PASS | All 8 steps are coherent units of work. P3-001 is large (5+ methods, 3 new files, 2 modified files) but architecturally cohesive as a single refactor. |
| 2 | Dependency Map | PASS | Graph correctly reflects build order. P3-007 only depends on P3-001 + P3-004 (not P3-006), so it could be parallel with P3-006 — planner's conservative sequential ordering in Wave 3 is acceptable. No circular dependencies. |
| 3 | Parallelism Safety | **NEEDS REVIEW** | **Plugin file collision**: P3-002 tests `plugins/memory/guinevere-memory/__init__.py` while P3-003 writes additional safety gate code to the same file. Wave 2 marks them as parallel, but P3-003 adding code to a file P3-002 is testing creates a read-after-write hazard. See Detailed Findings §3. |
| 4 | Method Mapping | PASS | `recall_for_context() → prefetch()` correctly delegates to `recall_memories()` with `principal=guinevere_core`, `exclude_dnr=True`, `safe_mode` from state, `limit=5`, `token_budget=800`. `store_conversation() → sync_turn()` correctly wraps `store_episode()` with `classification=RESTRICTED` (fail-closed), `embedding_service=None`. All safety gates (DNR, classification ceiling, safe-mode substitution, anti-hallucination guard) preserved. The conversational_handler calling pattern verified at lines 446 and 595 — matches planner spec exactly. |
| 5 | File Plan | **NEEDS REVIEW** | Section 7.2 lists 6 files to modify but omits `plugins/memory/guinevere-memory/__init__.py` which P3-003 must modify to add post-recall DNR gate code, classification ceiling filters, anti-hallucination guard, and safe-mode content substitution logic. See Detailed Findings §5. |
| 6 | Collision Scan | PASS | All 7 enumerated items correctly resolved. Section 6 accurately identifies: P3-001 owns `memory_bridge.py`, P3-002 is read-only on config, P3-003 writes session_search block, P3-005 is read-only consumer of `read_pipeline.py`, parent handles shared docs, P3-004 owns PostgreSQL schema changes, P3-005 owns `requirements.txt`. |
| 7 | Verification Scaffolds | PASS | All 8 scaffolds are machine-checkable with concrete expected files, forbidden patterns (grep-able), exact exit-code requirements, and binary pass/fail hard rejection criteria. P3-003's `grep` for `verify_recall_results_dnr_free` is measurable. P3-001's `python -c` import assertion is compile-time verifiable. P3-004's SQL queries produce numeric row counts. |
| 8 | Rollback Plan | PASS | All 6 scenarios + full rollback are achievable within the stated time estimates (< 10 minutes total). `DROP ROLE`, `hermes config set ... false`, git checkout for source files — all are single-command reversals. Full rollback restoring `skip_memory=True` in `session_adapter.py` is correctly scoped. |
| 9 | Binding Decisions | PASS | All 8 decisions are traceable to specific research reports (R-01 through R-08). Decision 5 (post-recall DNR gate) correctly identifies that Hermes FTS5 has no SQL WHERE exposure, making Pre-filter impossible — post-recall `verify_recall_results_dnr_free()` is the correct architecture. Decision 8 (sqlite-utils) aligns with Research R-08 findings. |
| 10 | Caveats | PASS | All 6 caveats appropriately flagged with mitigation strategies. Caveat 1 (VPS state unknown) is a genuine pre-requisite blocker. Caveat 3 (Hermes agent version) correctly identifies ABC interface version risk. No missing safety-critical risks. |

---

## Detailed Findings

### Finding 1 — Parallelism Safety: Plugin File Collision (NEEDS REVIEW)

**Observation**: P3-002 (compression verification) and P3-003 (FTS5 safety gates) are both in Wave 2 and marked `parallel`. P3-002 reads/verifies `plugins/memory/guinevere-memory/__init__.py` (the plugin created in P3-001) since it must confirm the `on_pre_compress` hook is registered and correctly extracts key facts. P3-003 writes additional code to the same `__init__.py` file to add post-recall DNR gates (`verify_recall_results_dnr_free`), classification ceiling filters, anti-hallucination guard injection, and safe-mode content substitution.

**Evidence from document**:
- P3-002 scaffold explicitly tests `on_pre_compress` hook behavior and requires it registered in `plugin.yaml`.
- P3-003 design states "Safety Gates (MUST implement in plugin)" for all 4 safety gates.
- Collision scan §6 does not list `plugins/memory/guinevere-memory/__init__.py` as a collision surface.

**Risk**: If P3-003 executes before or concurrently with P3-002, P3-002's verification tests may encounter incomplete or different plugin code, producing false failures or false passes.

**Recommended fix**: 
- Option A (preferred): Make P3-002 → P3-003 sequential. P3-003 adds safety gate code after P3-002's verification passes, then P3-002 would need a follow-up test. This creates a dependency cycle.
- **Option B (recommended)**: Move P3-003's safety gate code to a separate module (`plugins/memory/guinevere-memory/safety_gates.py`) imported by the plugin. P3-002 tests the plugin, P3-003 writes the separate module. Both can remain parallel since they touch different files.
- Option C: Merge P3-002 and P3-003 into a single step (loses granularity).

### Finding 2 — File Plan: Missing Plugin Modify Entry (NEEDS REVIEW)

**Observation**: Section 7.2 ("Files to MODIFY") lists 6 files but does not include `plugins/memory/guinevere-memory/__init__.py`. P3-003's implementation design explicitly states it must add safety gate code to the plugin:
- "Post-Recall DNR Verification: Call verify_recall_results_dnr_free(results) on ALL session_search results before injecting into LLM context"
- "Classification Ceiling Filtering"
- "Anti-Hallucination Guard"
- "Safe-Mode Content Substitution"

**Evidence from document**: P3-003 Implementation Design §8 architecture diagram shows all 4 post-recall gates as part of the plugin pipeline.

**Recommended fix**: Add `plugins/memory/guinevere-memory/__init__.py` to the MODIFY table in §7.2 with owner P3-003, noting the safety gate additions. This also feeds into the collision scan (see Finding 1).

### Finding 3 — Collision Scan: Implicit Plugin File Contention (NEEDS REVIEW)

**Observation**: The collision scan in §6 correctly identifies 7 collision surfaces but misses the implicit contention on `plugins/memory/guinevere-memory/__init__.py` between P3-001 (creator/owner), P3-002 (reader/verifier), and P3-003 (modifier/writer). While P3-001 owns the file and P3-002/P3-003 are sequential after P3-001, the parallel marking of P3-002 and P3-003 creates risk.

**Evidence from document**:
- Collision scan row 1 only covers `memory_bridge.py` (P3-001 owns).
- Collision scan row 2 covers `hermes-config/config.yaml` (P3-002 read, P3-003 write).
- No row covers `plugins/memory/guinevere-memory/__init__.py`.

**Recommended fix**: Add a row to the collision scan table for the plugin init file with the same mitigation pattern used for config.yaml: "P3-002 is read-only verify. P3-003 adds safety gate code. If parallel execution: make P3-003 write safety gates to a separate module to avoid read-after-write hazard."

---

## Positive Observations

1. **Method mapping fidelity**: The planner correctly traces every parameter from the current `recall_for_context()` and `store_conversation()` call sites in `conversational_handler.py` (verified at lines 446 and 595) to the new plugin hooks. Safety parameters (`principal=guinevere_core`, `exclude_dnr=True`, `classification=RESTRICTED`, `embedding_service=None`) are all explicitly preserved.

2. **Research-grounded decisions**: Every binding decision (§5) is traceable to a specific research report (R-01 through R-08), which is itself grounded in codebase analysis (§4). Decision 5 on post-recall DNR gate correctly identifies the architectural constraint: Hermes FTS5 does not expose SQL WHERE clauses, making pre-filtering impossible — the post-recall `verify_recall_results_dnr_free()` approach is correct.

3. **Scaffold quality**: All 8 verification scaffolds have concrete, machine-checkable criteria. P3-003's `grep` for `verify_recall_results_dnr_free`, P3-004's SQL `SELECT count(*) WHERE` queries, and P3-007's combined code grep + VPS SQL query provide binary pass/fail checks that a verifier sub-agent can execute without interpretation.

4. **Rollback discipline**: Every step has a rollback procedure under 5 minutes. The full rollback restoring `skip_memory=True` correctly scopes to the Phase 2 state. The `DROP ROLE hermes_memory_bridge` for P3-004 is appropriately atomic.

5. **Token/secret handling**: §10 correctly identifies all 4 secrets and confirms the env_var pattern in plugin config schema — no secrets will be committed to the repo.

---

## Summary

The Phase 3 planner gate is well-structured with correct method mappings, research-grounded decisions, machine-checkable scaffolds, and fast rollback procedures. Three items need attention: (1) a plugin file write collision between P3-002 (testing) and P3-003 (adding safety gate code) in Wave 2 that the collision scan missed, (2) the file plan omitting the plugin init file as a P3-003 modify target, and (3) the implicit parallelism hazard on the shared plugin file. All three are resolved by either making P3-003's safety gate additions live in a separate module (`safety_gates.py`) or sequencing P3-002 → P3-003. No fundamental redesign is required — the dependency graph, method mappings, safety gate architecture, and rollback plan are all sound.