# Auditor Gate — Technical Accuracy Re-Audit v1.3

**Auditor**: Technical Accuracy Auditor  
**Plan under review**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md` v1.3 (829 lines)  
**Previous audit**: v1.2 — 4 findings (F1-F4), all claimed fixed in v1.3  
**Date**: 2026-06-05  
**Verdict**: **NEEDS REVIEW** — 4 prior findings resolved, 1 NEW finding (HIGH)

---

## 1. Prior Findings — Verification

### F1 (HIGH): File path `src/hermes/memory/memory_bridge.py` → `src/hermes/memory_bridge.py`

**Claim**: Fixed at 4 locations in active plan text.

| Location | Line | Text | Status |
|---|---|---|---|
| §4.1 Known State table | 72 | `src/hermes/memory_bridge.py (295 lines)` | ✅ **FIXED** |
| §7.2 Files to MODIFY | 158 | `src/hermes/memory_bridge.py \| P3-001 \| Deprecate` | ✅ **FIXED** |
| P3-001 Scaffold Expected Files | 585 | `Modified: src/hermes/memory_bridge.py (deprecation)` | ✅ **FIXED** |
| P3-009 Scaffold Expected Files | 665 | `plugins/memory/guinevere-memory/__init__.py` — no stale bridge ref | ✅ **FIXED** |

**Cross-reference**: `src/hermes/memory_bridge.py` confirmed at that path (295 lines, contains `recall_for_context`, `store_conversation`, `extract_key_facts`). No `src/hermes/memory/` subdirectory exists.

**Grep verification**: `src/hermes/memory/memory_bridge` returns **exactly 1 match** — line 820 in the version changelog (documenting the old broken path). Zero matches in active plan content. ✅

**Verdict**: **RESOLVED**

---

### F2 (MEDIUM): P3-009 scaffold targets deprecated `memory_bridge.py`

**Claim**: `extract_key_facts()` implementation now targets `plugins/memory/guinevere-memory/__init__.py` (plugin), not the deprecated bridge.

| Location | Line | Text | Status |
|---|---|---|---|
| P3-009 design | 542 | `v1.3 FIX (Auditor Tech F2): …the extract_key_facts() implementation lives in the plugin module (plugins/memory/guinevere-memory/__init__.py), not the deprecated bridge.` | ✅ **FIXED** |
| §7.2 Files to MODIFY | 164 | `plugins/memory/guinevere-memory/__init__.py \| P3-009 \| Add extract_key_facts()` | ✅ **FIXED** |
| P3-009 Scaffold Expected Files | 665 | `Modified: …plugins/memory/guinevere-memory/__init__.py (extract_key_facts implementation for mirror sync)` | ✅ **FIXED** |

**Verdict**: **RESOLVED**

---

### F3 (LOW): §7.2 Files to MODIFY missing P3-009 entries

**Claim**: §7.2 now includes P3-009 entries for plugin `__init__.py` and `config.yaml`.

| Entry | Line | Status |
|---|---|---|
| `plugins/memory/guinevere-memory/__init__.py \| P3-009 \| Add extract_key_facts()` | 164 | ✅ **ADDED** |
| `hermes-config/config.yaml \| P3-009 \| Add mirrors config block` | 165 | ✅ **ADDED** |

**Verdict**: **RESOLVED**

---

### F4 (MEDIUM): No pre-requisite check for `memory_owner` role existence

**Claim**: P3-004 now has a pre-requisite check with `pg_tables` fallback.

| Location | Line | Text | Status |
|---|---|---|---|
| P3-004 Pre-requisite block | 345 | `Verify memory_owner role exists…SELECT rolname FROM pg_roles…if empty, determine the table owner via SELECT tableowner FROM pg_tables WHERE schemaname = 'memory' LIMIT 1;` | ✅ **FIXED** |
| SQL migration NOTE comment | 355-356 | `-- NOTE: Replace 'memory_owner' with actual table-owning role if different` | ✅ **FIXED** |
| Caveat 8 strengthened | 764 | `v1.3 FIX (Auditor Tech F4): P3-004 now includes a pre-requisite check…with a fallback to discover the actual table-owning role via pg_tables.` | ✅ **FIXED** |

**Verdict**: **RESOLVED**

---

## 2. Source Code Cross-Reference — All PASS

| Plan Claim | Source File | Actual | Match |
|---|---|---|---|
| Table `episodes` in `memory` schema | `src/memory/models.py` L95 | `__tablename__ = "episodes"`, `__table_args__ = {"schema": "memory"}` | ✅ |
| Table `semantic_facts` in `memory` schema | `src/memory/models.py` L135 | `__tablename__ = "semantic_facts"`, schema memory | ✅ |
| Table `faiz_profile` in `memory` schema | `src/memory/models.py` L170 | `__tablename__ = "faiz_profile"`, schema memory | ✅ |
| Table `emotional_events` in `memory` schema | `src/memory/models.py` L192 | `__tablename__ = "emotional_events"`, schema memory | ✅ |
| `CLASSIFICATION_ORDER` mapping | `src/memory/embeddings.py` L107-113 | Public=0, Internal=1, Restricted=2, Confidential=3, Critical=4 | ✅ |
| `_CLASSIFICATION_CEILING` mapping | `src/memory/read_pipeline.py` L135-139 | guinevere_core→Critical, guinevere_subagent→Confidential, default→Restricted | ✅ |
| `recall_memories()` signature | `src/memory/read_pipeline.py` L727 | `exclude_dnr`, `safe_mode`, `principal`, `embedding_service` params | ✅ |
| `verify_recall_results_dnr_free()` existence | `src/memory/dnr.py` L385 | Checks `entry.get("do_not_recall")` | ✅ |
| `store_episode()` signature | `src/memory/write_pipeline.py` L111 | `classification`, `importance`, `source`, `embedding_service` params | ✅ |
| `memory_bridge.py` at correct path | `src/hermes/memory_bridge.py` | File exists, 295 lines, `HermesMemoryBridge` class | ✅ |

**Memory schema table scan**: `src/memory/` contains 8 files: `__init__.py`, `consolidation.py`, `dnr.py`, `embeddings.py`, `models.py`, `read_pipeline.py`, `write_pipeline.py`. All files referenced in the plan exist and match described functionality. ✅

---

## 3. New Findings

### N1 (HIGH): Wave 2 Parallel Collision — P3-003 and P3-009 both modify `__init__.py`

**Location**: §2 Dependency Map (line 45), §6 Collision Scan (line 131-132), §7.2 (lines 160, 164)

**Finding**: The plan declares Wave 2 steps (P3-002, P3-003, P3-009) as parallel with "No shared files" (line 45). However:

- **P3-003** modifies `plugins/memory/guinevere-memory/__init__.py` — adds `from .safety_gates import ...` (line 160)
- **P3-009** modifies `plugins/memory/guinevere-memory/__init__.py` — adds `extract_key_facts()` (line 164)

Both are in **Wave 2 (parallel)** and target the **same file for modification**.

**§6 Collision Scan gap**: The collision scan table addresses `__init__.py` only in the context of P3-001 (creates), P3-002 (reads), and P3-003 (modifies via import). It explicitly states "No collision" because P3-003 safety gate code lives in `safety_gates.py`. But it **never considers P3-009**, which also writes to `__init__.py`. The scan says P3-009 has "no shared files" with Wave 2 peers — this is false.

**Concrete race condition**: If P3-003 and P3-009 run in parallel (per the plan's Wave 2 definition), both sub-agents will independently read and write `__init__.py`. The last writer wins; one modification will be silently overwritten.

**Severity**: HIGH. This would cause either the safety gate import or `extract_key_facts()` to be lost at runtime, depending on write ordering. The plan's own collision scan rules (§6) would flag this if the check had included P3-009.

**Recommended fix (choose one)**:
- **Option A (simplest)**: Make P3-009 sequential — move it to Wave 3 (after P3-003 completes). P3-009 depends on P3-001 only, and P3-001 completes before Wave 2, so P3-009 in Wave 3 is still valid. Update §2 dependency map and Wave table.
- **Option B (consistent with existing pattern)**: Extract `extract_key_facts()` into a separate module (e.g., `plugins/memory/guinevere-memory/extraction.py`) — same pattern as `safety_gates.py`. Then `__init__.py` only adds an import for P3-009's module. However, this still has the same collision: both P3-003 and P3-009 would modify `__init__.py` to add their respective imports. So Option A is cleaner.

**Affected plan lines to update**:
- Line 45: Wave 2 table — remove P3-009 from parallel wave or reorder
- Lines 131-132: §6 Collision Scan — add P3-009 entry for `__init__.py`
- Line 34-35: §2 Dependency Map — verify diagram still correct
- Line 25: §1 Master Todo — change P3-009 Parallelism column if sequential

---

## 4. No Other New Findings

Scanned for but found zero instances of:
- Stale references to `src/hermes/memory/memory_bridge.py` in active plan text (only in changelog — acceptable) ✅
- Incorrect SQL table names (all 4 memory tables verified against models.py) ✅
- Wrong classification enum values (IN-list syntax correct) ✅
- Wrong statistical test (ttest_rel confirmed in P3-005) ✅
- Missing or incorrect function signatures (all 4 verified) ✅
- Secret exposure in plan text (no plaintext secrets, all use env_var pattern) ✅
- Type safety bypass patterns (`as any`, `@ts-ignore`) in plan scaffolds — all correctly listed as Forbidden ✅
- Missing P3-009 entries in any plan section ✅

---

## 5. Summary

| Category | Count | Details |
|---|---|---|
| Prior findings resolved | 4/4 | F1 (HIGH), F2 (MEDIUM), F3 (LOW), F4 (MEDIUM) — all confirmed fixed |
| New findings | 1 | N1 (HIGH): P3-003/P3-009 parallel collision on `__init__.py` |
| Source cross-refs verified | 10/10 | All table names, function signatures, constants match source code |
| Stale references | 0 | Only in changelog (documentation of fix — acceptable) |

**Overall Verdict**: **NEEDS REVIEW** — v1.3 correctly resolves all 4 v1.2 findings, but introduces a new parallel-write collision between P3-003 and P3-009 on `plugins/memory/guinevere-memory/__init__.py`. This must be resolved before Wave 2 execution. The fix is straightforward (reorder P3-009 to sequential after P3-003, or move to Wave 3).

---

## 6. Footer

**Auditor**: Technical Accuracy Auditor  
**Tooling**: Manual review via `filesystem_read_text_file`, `grep`, `read` across all referenced source files  
**Evidence**: Plan file 829 lines read in full; 5 source files cross-referenced; 4 function/constant definitions verified; 1 stale-path grep executed  
**Next action**: Parent to apply collision fix and re-submit for final PASS verification