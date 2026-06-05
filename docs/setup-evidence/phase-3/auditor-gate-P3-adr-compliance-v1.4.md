# Auditor Gate: ADR-035 Phase 3 Compliance — v1.4

**Date**: 2026-06-05  
**Auditor**: Guinevere (Parent) — ADR-035 Compliance Specialist  
**Subject**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md` (v1.4, 742 lines)  
**Canonical Ref**: `adr/ADR-035-hermes-migration.md` (Phase 3: lines 1469-1595, Appendix A: lines 2115-2119, Pillar 2: lines 588-605)  
**Previous Attempts**: v1.1 (PASS with C2/C6 findings — fixed in v1.2), v1.2 & v1.3 re-audits timed out

---

## VERDICT: PASS

All seven audit criteria pass. One minor observation noted (N1) — non-blocking, documentation-only.

---

## Audit Criteria — Point-by-Point

### C1: P3-009 Exists with Full Scaffold ✅ **PASS**

P3-009 scaffold found at plan lines 661-669. All five mandatory scaffold fields populated:

| Field | Present | Content |
|---|---|---|
| Expected Files | ✅ | `hermes-config/config.yaml` (mirrors block), `plugins/memory/guinevere-memory/__init__.py` (extract_key_facts), `tests/hermes/test_mirror_sync.py` |
| Forbidden Patterns | ✅ | `as any`, `@ts-ignore`, `# type: ignore`, empty `except:`, Critical/Confidential in mirrors, DNR in mirrors, PII/intimate data in mirrors, blocking mirror sync |
| Required Commands | ✅ | 5 commands: YAML config assertions (enabled, sync_interval_messages), pytest, grep for classification/DNR, regression |
| Evidence Requirements | ✅ | `verification-P3-009.md`, `auditor-gate-P3-009.md` |
| Hard Rejection Criteria | ✅ | 8 FAIL conditions: mirrors not enabled, sync != 5, extract_key_facts empty, Critical/Confidential content, DNR content, blocking sync, PII/intimate data, dedup failure |

### C2: P3-009 Matches Canonical Step 3.4 ✅ **PASS**

| ADR-035 Step 3.4 Spec (line 1587) | P3-009 Implementation |
|---|---|
| "Configure mirror sync (MEMORY.md/USER.md)" | ✅ `mirrors.enabled: true`, paths configured |
| "Critical facts written to MEMORY.md every 5 messages" | ✅ `sync_interval_messages: 5`, non-blocking daemon thread |
| "no PostgreSQL divergence" | ✅ "Mirror files are read-only for Hermes" (line 550) |
| Files affected: `config/hermes/config.yaml` | ✅ `hermes-config/config.yaml` (same file, plan uses project-local naming) |

**Appendix A path discrepancy (non-blocking observation)**: ADR-035 Appendix A (line 2117-2118) uses paths `config/hermes/MEMORY.md` and `config/hermes/USER.md`. P3-009 uses `~/.hermes/mirrors/MEMORY.md` and `~/.hermes/mirrors/USER.md`. The Phase 3 Step 3.4 spec does **not** mandate specific paths — it only requires "MEMORY.md/USER.md." Both paths are within Hermes-managed territory. The batch plan's choice (`~/.hermes/mirrors/`) is documented and reasonable.

### C3: §13 Gap Mapping Rationale Exists ✅ **PASS**

Found at plan lines 717-730. Table maps all 5 relevant gaps:

| Gap | Original Phase | Phase 3 Step | Rationale Provided |
|---|---|---|---|
| G-B3 (auto-store fails) | Phase 1 | P3-001 | ✅ Depends on G-B1; plugin refactor avoids duplicate work |
| G-B6 (classification enforcement) | Phase 2 | P3-003 | ✅ Requires safety_gates.py from P3-003 |
| G-B7 (hard_stop_handler) | Phase 1 | P3-001, P3-008 | ✅ Already enforced at LLM level; Hermes integration additive |
| G-B9 (DNR enforcement on FTS5) | Phase 2 | P3-003 | ✅ Same as G-B6 — requires safety_gates.py |
| G-B10 (memory consolidation) | Phase 2 | P3-009 | ✅ Depends on mirror sync (P3-009) |

General principle documented (line 729): "All five gaps require the MemoryProvider plugin (P3-001) as a prerequisite."

### C4: 7 src/memory/ Files Preserved Verbatim (ADR-007) ✅ **PASS**

ADR-035 Pillar 2 memory table (lines 588-601) declares ALL src/memory/ components as "Unchanged | 0 lines":

| Component | File | Batch Plan Status |
|---|---|---|
| PostgreSQL schema | N/A (DB) | ✅ No schema changes in any P3 step |
| Classification (5-level) | `src/memory/write_pipeline.py` | ✅ §7.3: NOT MODIFIED (line 173) |
| DNR pipeline | `src/memory/dnr.py` (338 lines) | ✅ §7.3: NOT MODIFIED (line 174) |
| Encrypted profiles | `src/memory/models.py` | ✅ Not in MODIFY list (implicitly preserved) |
| Hybrid ranking (RRF k=60) | `src/memory/read_pipeline.py` (775 lines) | ✅ §7.3: NOT MODIFIED (line 172) |
| Embedding pipeline (1536-dim HNSW) | `src/memory/embeddings.py` (775 lines) | ✅ §7.3: NOT MODIFIED (line 175) |
| Memory recall | `src/memory/read_pipeline.py` | ✅ (same file as above) |
| Memory write | `src/memory/write_pipeline.py` (291 lines) | ✅ (same file as above) |

Additional implicit preservation: `src/memory/consolidation.py` (757 lines, §4.1 line 78) — not touched by any step.

**ADR-007 compliance confirmed**: Hermes SQLite (`~/.hermes/state.db`) is transient session state only, not canonical memory. PostgreSQL remains the single source of truth. All 7 src/memory/ files are preserved verbatim.

### C5: Hermes = Read-Only (Zero PG Writes) ✅ **PASS**

Multi-layer enforcement across three steps:

| Enforcement Layer | Step | Mechanism |
|---|---|---|
| **RBAC** | P3-004 | `hermes_memory_bridge` role: SELECT-only + explicit REVOKE INSERT/UPDATE/DELETE/TRUNCATE (lines 360-361) |
| **RLS** | P3-004 | Classification ceiling + surveillance isolation on all memory tables (lines 368-388) |
| **Audit logging** | P3-007 | `log_statement = 'mod'` for hermes_memory_bridge role (line 465) |
| **Connection monitoring** | P3-007 | Query `pg_stat_activity` for non-SELECT statements → expected 0 rows (lines 479-483) |
| **Code review** | P3-007 | `grep` for INSERT/UPDATE/DELETE in plugin code (line 647) |
| **Integration test** | P3-007 | Full conversation flow verification (line 467) |

ADR-035 Phase 3 Gate (line 1478): "Zero PostgreSQL data modifications from Hermes path." ✅

### C6: P3-009 Does NOT Bypass Classification or DNR ✅ **PASS**

P3-009 safety gates (lines 553-557) enforce classification and DNR on all mirror content:

| Gate | Implementation | Verification |
|---|---|---|
| **Classification filter** | "No Critical/Confidential content in mirrors" | Acceptance criterion: "No Critical/Confidential content in mirror files" (line 570) |
| **DNR exclusion** | "DNR-marked memories must not appear in mirror files" | Acceptance criterion + Hard Rejection (line 571, 668) |
| **PII/intimate data** | "PII redaction gate from write_pipeline applies" | Acceptance criterion + Hard Rejection (line 557, 669) |

Hard rejection criteria include: mirror files contain Critical/Confidential → FAIL, DNR-marked content → FAIL, PII/intimate data → FAIL. All three are fail-on-violation (violation → FAIL), properly fail-closed.

### C7: Hermes = Read-Only (Redundancy Check) ✅ **PASS**

Confirmed across all Phase 3 steps:
- P3-004: RBAC SELECT-only + REVOKE all write privileges (lines 330-331, 360-361)
- P3-007: Multi-layer verification (lines 458-485)
- P3-009: "Mirror files are read-only for Hermes" (line 550); Python writes via write_pipeline (line 551)
- ADR-035 Pillar 2 (line 586): "PostgreSQL+pgvector remains the primary write authority"
- ADR-035 NFR-CP01 (line 1856): "Zero data modification from Hermes"

No redundant check — C5 already covers this in detail. Confirmed.

---

## Observations

### N1 (MINOR — Documentation): P3-009 Scaffold Regression Check Scope

P3-009 scaffold Required Commands include: "All P3-001 through P3-007 verification commands must still pass (regression check)."

Per the dependency map (Wave 2b after P3-003, before Wave 3), at P3-009's execution time, P3-006 and P3-007 have **not yet run**. The regression check should read "All P3-001 through P3-005 verification commands must still pass." This is a documentation-only issue — execution ordering prevents the impossible regression check from actually running. Non-blocking.

**Recommendation**: In a future v1.5 revision, change "P3-007" to "P3-005" in the P3-009 scaffold regression command.

---

## Summary

| Criterion | Result |
|---|---|
| C1: P3-009 full scaffold present | ✅ PASS |
| C2: P3-009 matches ADR-035 Step 3.4 spec | ✅ PASS (paths differ from Appendix A; Phase 3 spec does not mandate paths) |
| C3: §13 Gap Mapping Rationale exists | ✅ PASS |
| C4: 7 src/memory/ files preserved verbatim | ✅ PASS |
| C5: Hermes = read-only (zero PG writes) | ✅ PASS |
| C6: P3-009 classification/DNR not bypassed | ✅ PASS |
| C7: Hermes read-only (redundancy) | ✅ PASS |

**Overall**: **PASS** — v1.4 resolves all findings from v1.1 (C2: mirror sync step added as P3-009; C6: gap mapping rationale added as §13). No blocking issues. One minor documentation observation (N1).

---

## Evidence

- `docs/setup-evidence/phase-3/batch-plan-phase-3.md` (v1.4, 742 lines) — read in full
- `adr/ADR-035-hermes-migration.md` — Phase 3 spec (lines 1469-1595), Pillar 2 memory table (lines 588-605), Appendix A config (lines 2103-2119), NFR table (line 1856), rollback (line 1365) — all read
- `docs/10-governance/17-ADR_Index_v1.0.md` — ADR-035 entry at line 100 — confirmed status "Accepted"