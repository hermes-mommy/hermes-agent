# P3 (Memory Foundation) Evidence and Docs Consistency Audit

**Audit metadata:**
- Date: 2026-06-25
- Auditor: Independent (subagent)
- Mode: READ-ONLY
- Scope: Cross-check CHECKLIST.md, PROGRESS.md, docs index, docs/setup-evidence/P3/*, audit-reports/P3/P3-FINAL-AUDIT/*, src/memory/models.py
- Output: `docs/setup-evidence/legacy-audit/P3/evidences-docs-consistency-audit.md`

---

## 1. Cross-Check: CHECKLIST.md vs PROGRESS.md vs Evidence

### 1.1 19/19 Steps Claim

CHECKLIST.md (Section 5.2) marks all 19 P3 steps as `[x]` verified. PROGRESS.md (line 31) states P3 Memory System "19/19" complete. Both agree.

**Verdict: CONSISTENT** on the 19/19 claim.

### 1.2 Table/Schema Count Claims

| Source | Claim | Actual | Status |
|--------|-------|--------|--------|
| CHECKLIST.md P3-003 | "Table count -> 47; schema count -> 12" | 47 `__tablename__` entries in models.py; 12 schema groups in __table_args__ | CONSISTENT (on count) |
| PROGRESS.md P3 summary | "47 tables migrated, pgvector HNSW indexed" | Matches VPS verification | CONSISTENT |
| models.py docstring | "47 tables across 12 schemas (P3-002)" | Actually 48 ORM classes with __tablename__ (session_summaries added after P3) | **[HIGH] STALE** |
| P3-003 verification.md | "47 application tables across 12 schemas" memory=8 | Current models.py has memory=9 (session_summaries extra) | **[HIGH] STALE** |

The `session_summaries` table (models.py:191) exists in the ORM but was NOT counted in the original P3-003 VPS verification. The models.py docstring copy is stale — it was accurate at P3-002 time but has drifted to 48 tables now.

### 1.3 P3-001 FAIL vs PASS Contradiction

The current file at `docs/setup-evidence/P3/STEP-P3-001/auditor-gate.md` has verdict **PASS** (81/81 checks, line 227: "PASS - P3-001 Alembic setup is fully implemented and verified"). However, the P3 FINAL AUDIT reports claim this file returns FAIL:

- D01-completeness.md: "P3-001 auditor gate returns FAIL" (line 347)
- D01-completeness.md: "Verdict: FAIL" (line 165) — "Alembic NOT installed; src/memory/models.py missing; no alembic.ini"
- P3-FINAL-AUDIT.md: "P3-001 initial FAIL resolved by P3-002" (line 17)
- D11-open-items-caveats.md: "The auditor-gate for P3-001 has verdict FAIL" (line 142)
- D11-open-items-caveats.md: "verification.md was never created because the step failed audit" (line 142)

**[HIGH] The final audit reports reference a file state that no longer exists.** The current P3-001 auditor-gate.md returns PASS and `verification.md` EXISTS in the directory. The narrative of "P3-001 initial FAIL resolved by P3-002" suggests the file was overwritten/updated after the first attempt failed and before P3-002 proceeded. The final audit D11 needs to reference the CURRENT file state, not the historical one.

### 1.4 CHECKLIST Unchecked Items

CHECKLIST.md Section 5.2 has 19 `[x]` items. However, these ancillary sections remain unchecked:
- Section 5.3 Integration Tests: 3 items `[ ]`
- Section 5.4 Security Checks: 4 items `[ ]`
- Section 5.5 Rollback Test: 1 item `[ ]`
- Section 5.6 Phase Complete Criteria: 5 items `[ ]`

The P3 FINAL AUDIT D11 correctly identified these as "VPS-deployment-only verification steps" at line 129-132 of its report. This interpretation is consistent with the pattern used for other phases (P0-P8 similar unchecked deployment items). However, CHECKLIST.md marks all 19 steps as `[x]` while these supporting checks remain `[ ]`. This is a documentation gap but not an implementation gap.

**Verdict: [LOW] COSMETIC** — Consistent with other phases' patterns but could mislead a reviewer.

---

## 2. MiniLM 384-dim vs 1536-dim Embedding Consistency

### 2.1 The Claim

P3-004 verification.md (line 98): "Model dimension: 384" for MiniLM. Documented as "cache evidence only; no vector column writes" (line 6 boundary compliance).

P3-005 verification.md (line 19): Default model `openai/text-embedding-3-small`, dimension 1536 via 9Router-native HTTP.

CHECKLIST.md P3-004: "cache-only, not used for vector(1536) writes".
CHECKLIST.md P3-005: "9Router-native `openai/text-embedding-3-small`; Critical raw memory fails closed; 50/50 mocked verification PASS".

### 2.2 Assessment

All three sources are **internally consistent**. The MiniLM 384-dim is explicitly cache-only evidence. The production path uses 1536-dim via 9Router. The P3-005 verification includes a specific test that 384-dim vectors raise `DimensionMismatchError` (line 111 of P3-005 verification.md).

**Verdict: CONSISTENT** — No contradiction.

---

## 3. HNSW Benchmark Honesty (P3-006/P3-007)

### 3.1 The Claims

P3-006 verification.md: HNSW indexes exist with `m=16`, `ef_construction=128`, `vector_cosine_ops`. Seq Scan expected on empty table. Documented with EXPLAIN evidence.

P3-007 verification.md: "20 rows per table (40 total) is far too small for meaningful p95 analysis" (line 180). "HNSW index was NOT used" (line 82). "p95 not meaningful until real data" (line 183-184).

CHECKLIST.md P3-007: "Seq Scan expected due tiny data; p95 not meaningful until real data; ef_search=100 retained".

### 3.2 Assessment

**[LOW] The benchmark is honest but provides no useful data.** The documentation is transparent about the limitation. However, CHECKLIST.md marks P3-007 as PASS with "auditor PASS" despite the benchmark producing no meaningful performance results. The step is properly documented as a "smoke" benchmark with caveats.

**Verdict: HONEST BUT ESSENTIALLY EMPIRICALLY EMPTY** — The documentation is transparent; the step is a procedural placeholder, not a meaningful performance validation.

---

## 4. Fake Sessions / No Live DB (P3-009/P3-010)

### 4.1 The Claims

P3-009 verification.md: "No live DB insert smoke test. Verification uses a typed fake async session" (line 255). "No live embedding API call — uses fake embedder" (line 256).

P3-010 verification.md: "No live DB query smoke test (deterministic by design)" (line 258).

CHECKLIST.md P3-009: "no live DB write/API call" stated. P3-010: "no live DB/API call".

P3 FINAL AUDIT D11 caveats: #16 "No live DB insert — uses fake session", #17 "No live embedding API call — uses fake embedder", #18 "No live DB query smoke test".

### 4.2 Assessment

This is **transparently documented** across all evidence files. The P3 FINAL AUDIT catalogues these as 3 of 36 caveats. The E2E test (P3-018) provides the first live-pipeline test path, but even that uses fake sessions and fake embedders.

**Verdict: CONSISTENT AND HONEST** — No attempt to claim live verification.

---

## 5. Consolidation Scheduler Wiring

### 5.1 The Claims

P3-015 verification.md (Section 8): "Caveat - service-level scheduler activation" — `register_consolidation_job()` requires runtime DB sessionmaker not available in current main.py.

CHECKLIST.md P3-015: "service-level `systemctl status guinevere-scheduler` remains deployment caveat".

P3 FINAL AUDIT D11 caveat #31: "APScheduler activation requires runtime DB sessionmaker".

### 5.2 Current Code Reality

`src/core/main.py` line 23-54: `register_consolidation_job` is **commented out** with doc instructions:
```python
# P3-015 consolidation scheduler registration (optional -- no DB by default)
# To activate the daily consolidation scheduler at runtime, inject an async
# ...
#   await register_consolidation_job(scheduler, session_factory=AsyncSessionLocal)
#   scheduler.start()
```

Line 119: `report_scheduler.start()` runs for P8 monthly reports. Line 197: `kg_scheduler.start()` runs for P16 KG. But the P3 consolidation scheduler is NOT activated.

### 5.3 Assessment

**[HIGH] The consolidation scheduler is structurally present (implemented + tested) but never started at runtime.** This is consistent between evidence files and code — all three agree the scheduler is not wired. However, this means daily consolidation (episodic-to-semantic conversion) has never run in any environment. The KG scheduler (P16) and report scheduler (P8) ARE started, so the app does have live schedulers — just not for P3.

**Verdict: CONSISTENT ACROSS ALL SOURCES** — Code, evidence, and audit all agree that consolidation is deployed but dormant. This is an intentional deployment caveat, not a discrepancy.

---

## 6. P3 Foundation Markings in Downstream Docs

### 6.1 Assessment

| Document | Reference | Verdict |
|----------|-----------|---------|
| IMPLEMENTATION_GUIDE.md | "Critical path: P0 -> P1 -> P3 -> P5" | P3 is correctly identified as critical path |
| BRD v2.0 | P16 depends on "P3 + P5 + P8", P19 depends on "P3 + P5 + P8" | Consistent |
| P19 plan | "P19 is the foundation that P20... build upon" with deps P3+P5+P8 | Consistent |
| P24 plan | P3 listed as hybrid/local adapter converge target | Consistent |
| AGENTS.md | Lists memory as safety-affecting domain | Consistent |
| P23 plan | References P3 as prerequisite | Consistent |
| P21 plan | References P3 as prerequisite | Consistent |

**Verdict: P3 IS CLEARLY MARKED AS FOUNDATION** across all downstream phase documentation.

---

## 7. Evidence File Completeness

### 7.1 Verification.md Coverage

| Step | verification.md | auditor-gate.md | Status |
|------|----------------|-----------------|--------|
| P3-001 | EXISTS | EXISTS (PASS) | Complete |
| P3-002 | EXISTS | EXISTS (PASS) | Complete |
| P3-003 | EXISTS | EXISTS (PASS) | Complete |
| P3-004 | EXISTS | EXISTS (PASS) | Complete |
| P3-005 | EXISTS | EXISTS (PASS) | Complete |
| P3-006 | EXISTS | EXISTS (PASS) | Complete |
| P3-007 | EXISTS | EXISTS (PASS) | Complete |
| P3-008 | EXISTS | EXISTS (PASS) | Complete |
| P3-009 | EXISTS | EXISTS (PASS) | Complete |
| P3-010 | EXISTS | EXISTS (PASS) | Complete |
| P3-011 | EXISTS | EXISTS (PASS) | Complete |
| P3-012 | EXISTS | EXISTS (PASS) | Complete |
| P3-013 | EXISTS | EXISTS (PASS) | Complete |
| P3-014 | EXISTS | EXISTS (PASS) | Complete |
| P3-015 | EXISTS | EXISTS (PASS) | Complete |
| P3-016-019 | MISSING (combined auditor gate exists) | EXISTS (PASS) | **Doc gap** |

The D11 audit claimed P3-001 verification.md was "MISSING" but the file actually exists on disk at `docs/setup-evidence/P3/STEP-P3-001/verification.md`. This is a stale reference in the final audit.

### 7.2 Auditor Gate Coverage

16/16 step directories have an auditor-gate.md with PASS verdict (15 PASS + 1 PASS after P3-001 file was updated).

---

## 8. Stale / Superseded Document Inventory

| Document | Status | Finding |
|----------|--------|---------|
| `docs/00-core/06-Persona_Document_v3.0.md` | DELETED (git: D) | Removed — no longer in repo. Relevant to P4, not P3 directly. |
| `docs/20-security/hermes-phase-7-blocker-register.md` | DELETED (git: D) | Removed. |
| `docs/setup-evi...` (truncated) | DELETED (git: D) | Appears partially deleted. |
| StepPrompts.md | Stale | P3 FINAL AUDIT D01 found "all P3 sections show Not Started" — known stale. |
| P3 FINAL AUDIT D01/D11 references to P3-001 FAIL | Stale | The current P3-001 auditor-gate.md returns PASS; D11 claims it returns FAIL. File was updated after audit. |
| models.py docstring stale count | Stale | Claims "47 tables across 12 schemas" but ORM now has 48 tables. |

---

## 9. Supersession by P18/P20

### 9.1 P18 (Advanced Memory) Impact

P18 adds:
- `tiers.py` (MemoryTier, TierManager, TIER_DECAY_RATES)
- `spaced_repetition.py` (FSRSScheduler, FSRS-6)
- P3 consolidation extended with `register_decay_job`
- P18 migration `p18_add_memory_tiers_fsrs`

P18 EXTENDS but does NOT SUPERSEDE P3. The P3 read/write pipelines, DNR, safe-mode, context injection, and consolidation engine remain the foundation. P18 adds tiered decay and FSRS scheduling on top.

### 9.2 P20 (Life Kernel) Impact

P20 adds:
- `life_kernel/` directory with heartbeat, dashboard, P16/P18 adapters
- `life_kernel/p18_adapter.py` reads from memory tiers
- P20 migration `p20_001_life_kernel_schema`

P20 CONSUMES P18 (tier data) but does NOT replace P3 functionality.

**Verdict: P3 is EXTENDED but NOT SUPERSEDED by later phases.** The memory foundation remains in place with P18/P20/P19 adding layers on top.

---

## 10. Overall Verdict

### Status Option: **IMPLEMENTED WITH DOC GAPS**

### Summary of Findings

| Severity | Count | Key Issues |
|----------|-------|------------|
| [CRITICAL] | 0 | — |
| [HIGH] | 3 | (1) P3 FINAL AUDIT references stale P3-001 FAIL file state; (2) models.py docstring claims 47 tables when 48 exist; (3) P3-003 verification memory count (8) differs from current ORM (9) |
| [MEDIUM] | 2 | (1) Consolidation scheduler structurally present but never started at runtime; (2) No standalone verification.md for P3-016-019 combined step |
| [LOW] | 3 | (1) CHECKLIST ancillary sections (5.3-5.6) remain unchecked; (2) P3-007 benchmark is procedurally honest but empirically empty; (3) StepPrompts.md stale |

### Strengths

1. **Consistent 19/19 completion claim** across CHECKLIST.md and PROGRESS.md.
2. **Transparent caveat documentation** — fake sessions, tiny benchmarks, consolidation not wired, MiniLM cache-only are all clearly stated.
3. **P3 foundation clearly marked** in all downstream phase documents (P16, P19, P20, P23, P24).
4. **All 16 step directories have auditor-gate.md** with PASS verdict.
5. **P3-004/P3-005 embedding dimension consistency** is correctly documented — no contradiction despite different models.
6. **No plaintext secrets** across all evidence files — SOPS-only password handling confirmed.

### Doc Gaps

1. **P3 FINAL AUDIT D01 and D11 reference outdated file state** for P3-001. The current `STEP-P3-001/auditor-gate.md` returns PASS with verification.md present, but the audit claims FAIL/missing. The final audit narrative of "P3-001 initial FAIL resolved by P3-002" accounts for the historical sequence but the D11 section headings cite the wrong verdict for the current file.
2. **models.py docstring** needs updating from "47 tables across 12 schemas (P3-002)" to reflect current ORM state (48 tables).
3. **CHECKLIST.md P3-003 table count** needs updating from 47 to 48 if session_summaries is a genuinely managed table.
4. **No standalone verification.md** for the P3-016-019 batch — covered by a thorough auditor-gate (283 lines), but inconsistent with the per-step pattern.
5. **P3-007 benchmark caveat about Seq Scan** is well-documented but means P3-007 has never validated HNSW index usage at scale.

### Recommendations

1. Update `src/memory/models.py` docstring to accurately reflect the current table count and include a note that P3 established 47 tables and later phases added more.
2. Resolve the P3 FINAL AUDIT D01/D11 stale reference — either update the audit reports to reference the current file state, or add a note explaining the historical sequence.
3. Consider activating the P3 consolidation scheduler (`register_consolidation_job()`) now that the KG scheduler (P16) is already running — both use the same APScheduler infrastructure.
4. Update CHECKLIST.md P3-003 table count if `session_summaries` is a managed table.
5. No code changes needed — all findings are documentation-staleness issues, not implementation defects.
