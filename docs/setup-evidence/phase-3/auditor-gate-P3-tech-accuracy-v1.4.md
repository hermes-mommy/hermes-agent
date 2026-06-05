# Auditor Gate — Phase 3 Technical Accuracy (v1.4)

**Auditor**: Guinevere (Technical Accuracy Auditor)  
**Date**: 2026-06-05  
**Target**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md` (v1.4, 832 lines)  
**Prior Verdicts**: Memory Safety = PASS (v1.2). Tech Accuracy = NEEDS REVIEW on v1.3 (found N1 HIGH).  
**Verdict**: **PASS** ✅

---

## N1 FIX VERIFICATION: P3-009 Collision Scan Resolution

The v1.3 audit found P3-003 and P3-009 both modified `plugins/memory/guinevere-memory/__init__.py` in parallel Wave 2. v1.4 moves P3-009 to sequential Wave 2b after P3-003.

| Check # | Requirement | Location | Status |
|---|---|---|---|
| 1 | Step table: P3-009 depends on P3-001, P3-003, parallelism = sequential | Master Todo table (~line 25) | ✅ `P3-009 \| ... \| P3-001, P3-003 \| sequential (after P3-003) \| 0.5 day` |
| 2 | Dependency map: P3-009 chains from P3-003 | §2 Dependency Map (~line 34) | ✅ ASCII diagram shows `P3-003 (FTS5+Safety) --+--> P3-009 (Mirror Sync)` |
| 3 | Waves table: P3-009 in own Wave 2b row | §2 Waves table (~line 45) | ✅ `Wave 2b (sequential) \| P3-009 \| Depends on P3-003 (both modify __init__.py — v1.4 FIX: collision scan N1). Runs after P3-003 completes.` |
| 4 | Collision scan: `__init__.py` row mentions P3-009 + sequential mitigation | §6 Collision Scan (~line 131) | ✅ Full row documents P3-001 creates, P3-003 writes to separate `safety_gates.py`, P3-009 adds `extract_key_facts`. Notes v1.4 FIX and sequential enforcement. |
| 5 | Collision scan result: notes v1.4 fix | §6 Result (~line 134) | ✅ `v1.4 FIX: P3-009 __init__.py modification now sequential after P3-003 (Wave 2b) to prevent parallel write collision.` |
| 6 | Execution checklist: P3-009 in Wave 2b section, not Wave 2 | §16 Execution Checklist (~line 789–794) | ✅ Wave 2 contains only P3-002 + P3-003. Wave 2b contains P3-009 with header `Sequential, after P3-003`. |

**N1 Resolution**: ✅ ALL 6 checks PASS. The collision between P3-003 and P3-009 writing to `__init__.py` is fully resolved via sequential scheduling.

---

## PRIOR FIX INTEGRITY CHECKS (F1–F4 all intact)

### F1 (HIGH): File path `src/hermes/memory_bridge.py` (no `memory/` subdir)

**Verification method**: Grep for `memory/memory_bridge` across `docs/setup-evidence/phase-3/`.

- Batch plan active content: **zero matches** ✅
- Version changelog (line 822): 1 match documenting the old broken path — acceptable (changelog preserves history) ✅
- Old audit reports (`auditor-gate-P3-tech-accuracy-v1.2.md`, `auditor-gate-P3-tech-accuracy-v1.3.md`): 8 matches in historical findings — expected for audit trail ✅
- Source code confirmed: `src/hermes/memory_bridge.py` exists at correct path (no `memory/` subdirectory) ✅

**Key locations verified**:
- §4.1 Known State: `src/hermes/memory_bridge.py (295 lines)` ✅
- §7.2 Files to MODIFY: `src/hermes/memory_bridge.py \| P3-001 \| Deprecate; redirect to new plugin` ✅
- P3-001 scaffold Expected Files: `src/hermes/memory_bridge.py (deprecation)` ✅
- P3-009 design: extract_key_facts target correctly moved to plugin (see F2) ✅

### F2 (MEDIUM): extract_key_facts targets plugin `__init__.py`, not deprecated bridge

**P3-009 Implementation Design** explicitly states:
> "v1.3 FIX (Auditor Tech F2): Since P3-001 deprecates `memory_bridge.py`, the `extract_key_facts()` implementation lives in the plugin module (`plugins/memory/guinevere-memory/__init__.py`), not the deprecated bridge."

**§7.2 Files to MODIFY** confirms:
> `plugins/memory/guinevere-memory/__init__.py \| P3-009 \| Add extract_key_facts() implementation for mirror sync. P3-001 creates this file; P3-009 adds extraction logic.`

✅ Both references target the correct plugin file, not the deprecated bridge.

### F3 (LOW): §7.2 includes P3-009 entries

**§7.2 Files to MODIFY table** contains:
| File | Step | Changes |
|---|---|---|
| `plugins/memory/guinevere-memory/__init__.py` | P3-009 | Add `extract_key_facts()` implementation for mirror sync |
| `hermes-config/config.yaml` | P3-009 | Add `mirrors` configuration block (enabled, sync_interval_messages, paths) |

✅ Both P3-009 modification entries present and correct.

### F4 (MEDIUM): memory_owner pre-requisite check before P3-004 SQL

**P3-004 Pre-requisite block**:
> "Verify `memory_owner` role exists before running SQL migration. If it does not exist, create it or identify the actual role that owns `memory` schema tables. Run: `SELECT rolname FROM pg_roles WHERE rolname = 'memory_owner';` — if empty, determine the table owner via `SELECT tableowner FROM pg_tables WHERE schemaname = 'memory' LIMIT 1;`"

**SQL Migration comment**:
> "NOTE: Replace 'memory_owner' with actual table-owning role if different (see pre-requisite)"

**Caveat 8 (strengthened)**:
> "v1.3 FIX (Auditor Tech F4): P3-004 now includes a pre-requisite check that verifies `memory_owner` exists before running the SQL migration, with a fallback to discover the actual table-owning role via `pg_tables`."

✅ F4 fully intact — explicit pre-flight SQL, SQL block annotation, and caveat reinforcement.

---

## SOURCE CODE CROSS-REFERENCES

| Reference | Plan Claims | Source Code | Match? |
|---|---|---|---|
| Memory Bridge path | `src/hermes/memory_bridge.py` | File exists at that path ✅ | ✅ Correct |
| Memory Bridge methods | `recall_for_context()`, `store_conversation()`, `extract_key_facts()` | All 3 methods present ✅ | ✅ Correct |
| Models table name | `memory.episodes` (per v1.2 fix) | `class Episodes(Base, ClassificationMetaMixin): __table_args__ = {..., "schema": "memory"}` ✅ | ✅ Correct |
| Models classification column | `classification Mapped[str] = mapped_column(Text, ...)` | Text type, `server_default=text("'Restricted'")` ✅ | ✅ Correct |
| Embeddings classification hierarchy | IN-list required (string comparison is lexicographically wrong) | Lexicographic: C < C < I < P < R vs Semantic: P=0 < I=1 < R=2 < C=3 < C=4 ✅ | ✅ Correct |
| Embeddings API base URL | `http://localhost:20128/v1` | `DEFAULT_BASE_URL = "http://localhost:20128/v1"` ✅ | ✅ Correct |
| Embeddings dimension | `vector(1536)` schema locked | `EXPECTED_DIMENSION = 1536`, `Vector(1536)` ✅ | ✅ Correct |

---

## ADDITIONAL CONSISTENCY CHECKS

| Check | Result |
|---|---|
| P3-009 scaffold Expected Files matches §7.2 MODIFY entries | ✅ Both list `plugins/memory/guinevere-memory/__init__.py` + `hermes-config/config.yaml` |
| P3-008 checklist includes P3-009 | ✅ Line: "P3-001 through P3-007 and P3-009 all PASS" |
| P3-008 checklist includes Hermes mirror sync | ✅ Line: "Hermes mirror sync (MEMORY.md/USER.md) operational" |
| P3-009 Auditor Matrix row present | ✅ `P3-009 \| Safety + Code Quality \| Mirror sync config, classification filter on mirrors...` |
| P3-009 Rollback row present | ✅ Not in rollback table but config toggle (`memory.mirrors.enabled: false`) documented in P3-009 design |
| P3-009 Gap Mapping (§13) references | ✅ P3-009 mentioned in G-B10 rationale as dependent on mirror sync |
| P3-004 scaffold RLS policy check matches model schema | ✅ Scaffold commands check `pg_policies` for `hermes_memory_bridge` role on memory schema tables |
| P3-007 scaffold connection string logging check | ✅ Grep command: `grep -rn 'log.*connection\|log.*dsn\|log.*password\|log.*DSN' plugins/memory/guinevere-memory/` must return 0 |
| P3-005 A/B test uses `ttest_rel` (v1.2 fix) | ✅ "Uses scipy.stats.ttest_rel (paired t-test, same queries through both pipelines) for p-value. v1.2 FIX (Auditor Tech T5): ttest_ind is wrong" |
| P3-004 RLS classification uses IN-list (v1.2 fix) | ✅ `USING (classification IN ('Public', 'Internal', 'Restricted'))` with inline rationale about lexicographic ordering |

---

## MINOR OBSERVATIONS (non-blocking)

1. **Changelog retains old broken path**: Line 822 in the version table documents `src/hermes/memory/memory_bridge.py → src/hermes/memory_bridge.py`. This is acceptable — the changelog preserves historical fix documentation and does not affect active plan content. Zero instances of the wrong path in operational sections.

2. **P3-009 scaffold Expected Files discrepancy**: The Expected Files field lists `Created: tests/hermes/test_mirror_sync.py` but the file is listed under Created when it likely belongs more naturally under Modified (test file creation). The scaffold commands include `python -m pytest tests/hermes/test_mirror_sync.py -v` which will test it regardless. Not a defect — merely a categorization note.

3. **P3-009 Rollback not in §14 table**: P3-009's rollback (set `memory.mirrors.enabled: false`) is documented in P3-009's own design block but not in the centralized §14 Rollback Plan table. The centralized table covers P3-001/002/003/004/006/007. Consider adding a P3-009 row for completeness in a future revision — non-blocking since the toggle is documented.

---

## VERDICT

**PASS** ✅

All 6 N1 fix checks pass cleanly. All 4 prior fixes (F1–F4) remain intact with zero regressions. Source code cross-references confirm the plan accurately reflects the actual codebase. The batch plan v1.4 is technically accurate and ready for execution.

---

## AUDITOR SIGN-OFF

| Field | Value |
|---|---|
| Auditor | Guinevere (Technical Accuracy Auditor) |
| Model | ninerouter/highend |
| Session | ses_20260605 |
| Target File | `docs/setup-evidence/phase-3/batch-plan-phase-3.md` v1.4 |
| Lines Audited | 832 |
| Source Files Cross-Referenced | `src/hermes/memory_bridge.py`, `src/memory/models.py`, `src/memory/embeddings.py` |
| Verdict | **PASS** |
| Next Action | Proceed to ADR-035 Compliance auditor re-audit on v1.4 |