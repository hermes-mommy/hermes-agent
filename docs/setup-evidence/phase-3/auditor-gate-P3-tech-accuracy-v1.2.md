# Technical Accuracy Auditor Gate — Phase 3 Batch Plan v1.2 (Re-Audit)

**Verdict**: **NEEDS REVIEW**

**Auditor**: Technical Accuracy Auditor (Parent)  
**Date**: 2026-06-05  
**Plan Version**: v1.2  
**Previous Audit**: v1.1 had 3 findings (T4 SQL table names, T4 RLS classification column, T5 A/B test statistical method)

---

## 1. Previous Findings — Resolution Verification

### T4: SQL Table Names — `memory.episodic_memory` → `memory.episodes`

| Aspect | Status | Evidence |
|---|---|---|
| Plan now uses `memory.episodes` | **RESOLVED** ✅ | Lines 286, 292, 363 all reference `memory.episodes`. Source: `src/memory/models.py` line 92: `__tablename__ = "episodes"` with `{"schema": "memory"}`. |
| RLS policies reference correct table | **RESOLVED** ✅ | P3-004 SQL migration (lines 363-372) uses `memory.episodes`. |
| DNR cache query correct | **RESOLVED** ✅ | P3-003 line 286: `SELECT id FROM memory.episodes WHERE do_not_recall = true`. |
| PG enrichment query correct | **RESOLVED** ✅ | P3-003 line 292: `SELECT id, classification FROM memory.episodes WHERE id IN (...)`. |

### T4: RLS Classification Column — `classification_level` → `classification` with IN-list

| Aspect | Status | Evidence |
|---|---|---|
| Column name is `classification` (not `classification_level`) | **RESOLVED** ✅ | P3-004 SQL lines 364-366: `USING (classification IN ('Public', 'Internal', 'Restricted'))`. Source: `ClassificationMetaMixin` in `src/memory/models.py` line 48: `classification: Mapped[str]`. |
| IN-list approach used instead of string comparison | **RESOLVED** ✅ | Plan explicitly documents rationale at lines 360-362: lexicographic order is wrong for this enum. Confirmed: `CLASSIFICATION_ORDER` dict in `src/memory/embeddings.py` lines 107-113 defines semantic hierarchy Public=0 < Internal=1 < Restricted=2 < Confidential=3 < Critical=4. Lexicographic string comparison would sort as: Confidential < Critical < Internal < Public < Restricted — which does not match semantic order. |
| Same IN-list on all tables | **RESOLVED** ✅ | `memory.faiz_profile` (line 377-378), `memory.emotional_events` (lines 381-383, includes `Confidential` — intentionally higher ceiling for emotional data). |

### T5: A/B Test Statistical Method — `ttest_ind` → `ttest_rel`

| Aspect | Status | Evidence |
|---|---|---|
| Plan specifies `ttest_rel` (paired t-test) | **RESOLVED** ✅ | P3-005 line 422: `scipy.stats.ttest_rel (paired t-test, same queries through both pipelines)`. |
| Rationale documented | **RESOLVED** ✅ | Line 422: "v1.2 FIX (Auditor Tech T5): ttest_ind is wrong — queries are paired/matched samples, not independent." Rationale is correct: the same 100 queries run through both pipelines = matched pairs, not independent samples. |
| P3-006 scaffold criteria consistent | **RESOLVED** ✅ | Lines 634: `FAIL if: p-value < 0.05`. |

**Summary**: All 3 previous findings are correctly and completely resolved. No regressions detected in these areas.

---

## 2. New Findings

### F1: Wrong File Path — `memory_bridge.py` (HIGH)

**Issue**: The plan consistently references `src/hermes/memory/memory_bridge.py` (with a `memory/` subdirectory) but the actual file is at `src/hermes/memory_bridge.py` (no subdirectory).

| Plan Location | Line(s) | Text | Correct Path |
|---|---|---|---|
| §4.1 Known State table | 72 | `src/hermes/memory/memory_bridge.py (295 lines)` | `src/hermes/memory_bridge.py` |
| §7.2 Files to MODIFY | 158 | `src/hermes/memory/memory_bridge.py` | `src/hermes/memory_bridge.py` |
| P3-009 Scaffold Expected Files | 660 | `src/hermes/memory/memory_bridge.py (extract_key_facts implementation)` | `src/hermes/memory_bridge.py` |

**Impact**: All grep/file-path commands referencing the wrong path would fail. The collision scan (§6, line 124) uses short name `memory_bridge.py` and rollback plan (§14, line 732) uses `memory_bridge.py imports` — these are less affected. P3-009 scaffold has no required command that reads this path, but the "Expected Files" listing is inaccurate.

**Evidence**: `glob **/memory_bridge.py` returned exactly one match: `src/hermes/memory_bridge.py`. `glob src/hermes/memory/` returns no `memory_bridge.py` — the `memory/` subdirectory does not exist under `src/hermes/`.

### F2: P3-009 Modifies a File Deprecated by P3-001 (MEDIUM)

**Issue**: P3-001 deprecates `src/hermes/memory_bridge.py` (adding deprecation warning, redirecting to the new plugin). P3-009 scaffold (line 660) then claims to modify this same deprecated file to implement `extract_key_facts()`.

**Contradiction**:
- P3-002 line 262: `extract_key_facts() stub: Implemented in plugin on_pre_compress hook` — says the extraction logic lives in the **plugin**
- P3-009 scaffold line 660: `src/hermes/memory/memory_bridge.py (extract_key_facts implementation)` — says it lives in the **deprecated bridge file**

**Actual code**: `src/hermes/memory_bridge.py` line 266-295: `async def extract_key_facts()` currently returns `[]` as a Phase 3 stub with docstring `"Full LLM-based extraction is deferred to Phase 3."`

**Recommendation**: The `extract_key_facts()` implementation for mirror sync should live in the new plugin module (consistent with P3-002's design), not in the deprecated bridge file. Update P3-009 scaffold "Expected Files" to list the plugin `__init__.py` as the modified file instead.

### F3: Inconsistent File Modification Listing — P3-009 (LOW)

**Issue**: §7.2 "Files to MODIFY" table does not list the files that P3-009 modifies:

| File Modified by P3-009 | Listed in §7.2? | Listed in P3-009 Scaffold? |
|---|---|---|
| `hermes-config/config.yaml` (mirrors block) | ❌ Not listed | ✅ Line 660 |
| `src/hermes/memory_bridge.py` (extract_key_facts) | ❌ Not listed (only P3-001 deprecation is listed) | ✅ Line 660 |
| `tests/hermes/test_mirror_sync.py` (created, not modified — correctly in §7.1) | ✅ Listed in §7.1 | ✅ Line 660 |

**Impact**: Low — the scaffold is the authoritative specification for P3-009, and it correctly lists the files. The §7.2 overview table is incomplete.

### F4: Undocumented `memory_owner` Role in P3-004 SQL (MEDIUM)

**Issue**: P3-004 SQL migration (line 351) uses `ALTER DEFAULT PRIVILEGES FOR ROLE memory_owner IN SCHEMA memory`. The `memory_owner` role is referenced but:
- Never defined or created in the SQL migration
- Not listed as a pre-requisite in the execution checklist (§16)
- Not documented in the secrets table (§10)
- Caveat 8 (line 758) mentions it only to say "verify memory_owner is not superuser"

**Impact**: If `memory_owner` does not exist on the VPS, the `ALTER DEFAULT PRIVILEGES` statement will fail with `ERROR: role "memory_owner" does not exist`. This is a runtime dependency on pre-existing VPS state.

**Recommendation**: Add `memory_owner` role verification to the pre-execution checklist (§16) and document the role's expected existence in Caveat 8.

### F5: `07-MEMORY-BRIDGE-GAP.md` Document Reference (LOW)

**Issue**: The gap mapping rationale (§13, line 714) references `07-MEMORY-BRIDGE-GAP.md`. A grep search in `docs/` finds this file referenced only within the batch plan itself and the ADR compliance auditor report. The document path is `docs/setup-evidence/` for evidence files, not a standard `docs/` subdirectory.

**Impact**: Low — the document exists (confirmed by ADR compliance auditor report citing it as a source). The path is valid.

---

## 3. Positive Verifications (Passed Technical Checks)

All the following technical claims were cross-referenced and verified:

| Claim | Source | Verification |
|---|---|---|
| `read_pipeline.recall_memories()` exists | `src/memory/read_pipeline.py` line 727 | ✅ Function signature matches plan description: `async def recall_memories(session, query_text, limit=20, *, exclude_dnr=True, safe_mode=False, principal='guinevere_core', ...)` |
| `write_pipeline.store_episode()` exists | `src/memory/write_pipeline.py` line 111 | ✅ Function exists as `async def store_episode(...)` |
| `memory_bridge.recall_for_context()` exists | `src/hermes/memory_bridge.py` line 86 | ✅ Function exists |
| `memory_bridge.store_conversation()` exists | `src/hermes/memory_bridge.py` line 165 | ✅ Function exists |
| `memory_bridge.extract_key_facts()` is a stub returning `[]` | `src/hermes/memory_bridge.py` line 266-295 | ✅ Confirmed: returns `[]`, logs "bridge_extract_key_facts_stub" |
| `embeddings.CLASSIFICATION_ORDER` exists with correct values | `src/memory/embeddings.py` line 107-113 | ✅ Public=0, Internal=1, Restricted=2, Confidential=3, Critical=4 |
| `dnr.verify_recall_results_dnr_free()` exists | `src/memory/dnr.py` line 385 | ✅ Function exists |
| `tests/hermes/test_memory_bridge.py` exists | `tests/hermes/test_memory_bridge.py` | ✅ File exists |
| `src/hermes/session_adapter.py` exists | Glob confirmed | ✅ File exists |
| `src/discord/conversational_handler.py` exists | Glob confirmed | ✅ File exists |
| `src/core/services/hard_stop_handler.py` exists | Glob confirmed | ✅ File exists |
| `ClassificationMetaMixin` has `classification`, `purpose`, `source` columns | `src/memory/models.py` lines 43-72 | ✅ All referenced columns exist |
| `Episodes` table has `do_not_recall` column | `src/memory/models.py` line 124 | ✅ `do_not_recall: Mapped[bool]` with `server_default=text("false")` |
| `read_pipeline` imports `CLASSIFICATION_ORDER` from `src/memory/embeddings` | `src/memory/read_pipeline.py` line 31 | ✅ `from src.memory.embeddings import CLASSIFICATION_ORDER, ...` |
| `read_pipeline` has `_CLASSIFICATION_CEILING` dict | `src/memory/read_pipeline.py` lines 135-141 | ✅ guinevere_core=CRITICAL, guinevere_subagent=CONFIDENTIAL, default=RESTRICTED |
| P3-004 `memory.faiz_profile` table exists | `src/memory/models.py` line 331 | ✅ `__tablename__ = "faiz_profile"` with `{"schema": "memory"}` |
| P3-004 `memory.emotional_events` table exists | `src/memory/models.py` line 399 | ✅ `__tablename__ = "emotional_events"` with `{"schema": "memory"}` |
| P3-004 `source` column exists on Episodes | `src/memory/models.py` line 44 (via mixin) | ✅ `source: Mapped[Optional[str]]` in `ClassificationMetaMixin` |
| P3-005 RRF k=60 constant | `src/memory/read_pipeline.py` line 45 | ✅ `RRF_K: int = 60` |
| P3-001 `tests/memory/ -v -k consent` and `tests/memory/ -v -k dnr` | Valid pytest filter patterns | ✅ Pattern syntax is valid (tests to be written during implementation) |

---

## 4. P3-009 Scaffold Technical Correctness

### Required Commands Review

| Command | Technically Correct? | Notes |
|---|---|---|
| `python -c "import yaml; ... assert c['memory']['mirrors']['enabled'] == True"` | ✅ | Valid YAML key path per the planned config structure |
| `python -c "import yaml; ... assert c['memory']['mirrors']['sync_interval_messages'] == 5"` | ✅ | Valid |
| `python -m pytest tests/hermes/test_mirror_sync.py -v` | ✅ | Test file not yet created (to be created during P3-009) |
| `grep -rn 'Critical\|Confidential' ~/.hermes/mirrors/ 2>/dev/null` | ✅ (VPS only) | Linux-specific; runs on VPS not Windows |
| All P3-001 through P3-007 verification commands must still pass | ✅ | Valid regression check |

### Hard Rejection Criteria Review

| Criterion | Technically Correct? | Notes |
|---|---|---|
| mirrors.enabled not true | ✅ | Straightforward config check |
| sync_interval_messages != 5 | ✅ | Straightforward config check |
| extract_key_facts returns empty for test input | ✅ | Valid behavioral test |
| mirror files contain Critical/Confidential content | ✅ | Valid safety gate |
| mirror files contain DNR-marked content | ✅ | Valid safety gate |
| mirror sync blocks conversation (latency > 100ms) | ⚠️ | Latency threshold (100ms) is not justified in any research report; arbitrary but reasonable |
| mirror files contain PII/intimate data | ✅ | Valid safety gate |
| deduplication not working | ✅ | Valid behavioral test |

---

## 5. Gap Mapping Rationale (§13) Technical Accuracy

| Gap | Plan Rationale | Accurate? | Notes |
|---|---|---|---|
| G-B3: Auto-store fails silently → P3-001 | Store failure caused by embedding routing (G-B1), P3-001 refactors with graceful degradation | ✅ | Correct: `memory_bridge.store_conversation()` (line 165) calls write_pipeline which requires embeddings. P3-001 plugin `sync_turn()` is the right refactor point. |
| G-B6: No classification enforcement → P3-003 | Requires safety_gates.py built in P3-003 | ✅ | Correct: `read_pipeline.py` already has classification ceiling for its own path. Hermes FTS5 path needs separate enforcement. |
| G-B7: hard_stop_handler not wired → P3-001, P3-008 | Already enforced by safety_plugin.py at LLM level; Hermes needs plugin lifecycle hooks | ✅ | Correct: `hard_stop_handler.py` exists as a separate module. Plugin integration is additive. |
| G-B9: No DNR on Hermes FTS5 → P3-003 | Same as G-B6: requires safety_gates.py | ✅ | Correct: Hermes FTS5 has no `do_not_recall` column. DNR ID cache approach is P3-003's responsibility. |
| G-B10: Consolidation not Hermes-aware → P3-009 | Depends on mirror sync which is P3-009 | ✅ | Correct: mirror sync is a Phase 3 concern after core plugin and safety gates. |

**Verdict**: The gap mapping rationale is technically accurate and well-justified. All dependencies flow correctly: G-B3 → P3-001 (plugin refactor), G-B6/G-B9 → P3-003 (safety gates), G-B7 → P3-001+008 (hooks + integration), G-B10 → P3-009 (mirror sync).

---

## 6. Design Coherence Check (Cross-Step Consistency)

| Cross-Step Check | Status | Notes |
|---|---|---|
| Hermes classification ceiling: P3-003 FTS5 vs P3-004 RLS | ✅ Consistent | Both use `Restricted` ceiling: IN ('Public', 'Internal', 'Restricted'). P3-003 line 292, P3-004 lines 364-366. |
| `guinevere_core` ceiling in read_pipeline vs Hermes | ✅ Intentional difference | read_pipeline allows Critical (level 4), Hermes is capped at Restricted (level 2) — documented as "external framework principal" in P3-004 line 339. |
| P3-001 plugin dir: `plugins/memory/guinevere-memory/` | ✅ Consistent | Uniformly used across all steps. |
| P3-009 `hermes_config/config.yaml` vs P3-002/P3-003 config path | ⚠️ Naming | Plan uses `hermes-config/config.yaml` for P3-002/P3-003 but P3-009 uses `hermes_config/config.yaml` (underscore vs hyphen). In P3-009 scaffold lines 662-663, the path is `hermes-config/config.yaml` (with hyphen). But P3-009 §8 design shows `hermes-config/config.yaml`. Actually, both variants appear — P3-003 line 270 says `hermes-config/config.yaml`, P3-009 line 525 says `hermes-config/config.yaml`. This appears consistent. |
| DNR enforcement: read_pipeline (query-level WHERE) vs Hermes FTS5 (post-recall cache) | ✅ Correctly differentiated | read_pipeline can use `WHERE do_not_recall = false` in SQL. Hermes FTS5 cannot — cache approach is correct. |

---

## 7. Token/Secret Handling Verification

All secrets follow the documented pattern. No secrets are hardcoded in any plan section. The `env_var` pattern is correctly specified in P3-001 config schema (line 213-214). The P3-007 scaffold includes a grep command to verify connection strings are not logged (line 642-643) — this is correctly specified.

---

## 8. Summary

### Resolved from v1.1
- ✅ T4: SQL table names → `memory.episodes`
- ✅ T4: RLS classification column → `classification` with IN-list
- ✅ T5: A/B test statistical method → `scipy.stats.ttest_rel`

### New Findings Requiring Action

| ID | Severity | Finding | Location | Recommendation |
|---|---|---|---|---|
| **F1** | HIGH | Wrong file path: `src/hermes/memory/memory_bridge.py` → should be `src/hermes/memory_bridge.py` | Lines 72, 158, 660 | Replace all occurrences. The `memory/` subdirectory does not exist under `src/hermes/`. |
| **F2** | MEDIUM | P3-009 modifies deprecated file; `extract_key_facts()` should be in plugin, not deprecated bridge | Line 660 | P3-009 scaffold Expected Files should list plugin `__init__.py` instead of (or in addition to) memory_bridge.py. |
| **F3** | LOW | P3-009 modifications not listed in §7.2 "Files to MODIFY" table | §7.2 entire table | Add hermes-config/config.yaml (mirrors block) and the corrected memory bridge path to §7.2. |
| **F4** | MEDIUM | `memory_owner` role referenced but never defined | Lines 351, 758 | Add role verification to §16 pre-execution checklist. |
| **F5** | LOW | `07-MEMORY-BRIDGE-GAP.md` path not explicitly verified | Line 714 | Document exists (confirmed by ADR auditor). No action needed. |

### Overall Verdict: NEEDS REVIEW

The three v1.1 findings are fully resolved. The plan is substantially more accurate than v1.1. However, the wrong file path (F1) for `memory_bridge.py` appears in 3 locations and is a concrete technical error. Combined with F2 (modifying deprecated file) and F4 (undocumented role), these warrant a correction pass before PASS can be issued.

All other technical claims, function names, import paths, class names, column names, config keys, and classification values have been verified against the actual source code and are correct.

---

## 9. Evidence Artifacts Reviewed

| Artifact | Path | Lines Reviewed |
|---|---|---|
| Batch Plan | `docs/setup-evidence/phase-3/batch-plan-phase-3.md` | Full (823 lines) |
| Memory Models | `src/memory/models.py` | Full (1086 lines) |
| Embeddings Module | `src/memory/embeddings.py` | Full (775 lines) |
| Read Pipeline | `src/memory/read_pipeline.py` | Full (963 lines) |
| Write Pipeline | `src/memory/write_pipeline.py` | grep `store_episode` |
| DNR Module | `src/memory/dnr.py` | grep `verify_recall_results_dnr_free` |
| Memory Bridge | `src/hermes/memory_bridge.py` | grep methods + extract_key_facts body |

---

## 10. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.2 | 2026-06-05 | Technical Accuracy Auditor (Parent) | Re-audit of v1.2. Verified resolution of all 3 v1.1 findings. Found 5 new issues: F1 (wrong file path, HIGH), F2 (modifying deprecated file, MEDIUM), F3 (incomplete §7.2 listing, LOW), F4 (undocumented memory_owner role, MEDIUM), F5 (document path reference, LOW). 18 positive verifications performed against source code. Verdict: NEEDS REVIEW. |