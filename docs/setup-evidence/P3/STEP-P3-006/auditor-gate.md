# Auditor Gate Report — P3-006 pgvector HNSW Index Verification

**File:** `docs/setup-evidence/P3/STEP-P3-006/auditor-gate.md`
**Status:** ✅ **PASS** — All checks satisfied (1 minor note documented)
**Date:** 2026-06-02
**Author:** DB Implementation Auditor (Independent)
**Step:** P3-006 — Verify existing pgvector HNSW indexes
**Evidence Scope:** `docs/setup-evidence/P3/STEP-P3-006/`

---

## 1 — What Was Audited

Independent audit of the P3-006 verification step. Reviewed all 4 evidence files against 10 mandatory check points:

| # | Check Point | Source |
|---|-------------|--------|
| 1 | HNSW indexes verified on VPS (real runtime evidence) | `hnsw-verification-output.txt` raw output |
| 2 | `ix_episodes_embedding_hnsw`: m=16, ef_construction=128, vector_cosine_ops | `pg_indexes` query output + `src/memory/models.py` |
| 3 | `ix_semantic_facts_embedding_hnsw`: m=16, ef_construction=128, vector_cosine_ops | `pg_indexes` query output + `src/memory/models.py` |
| 4 | No stale `embedding_vec` column or index | `information_schema.columns` + `pg_indexes` queries |
| 5 | No unintended model/schema edits (no `src/` modified) | `verification.md` Section 2 |
| 6 | Cosine EXPLAIN shows Index Scan using HNSW (or documented caveat) | `hnsw-verification-output.txt` Sections 6-8 |
| 7 | Evidence follows plan minimum 12-section schema | `verification.md` structural review |
| 8 | No Aizanta data/service touched beyond `pg_isready` port 5432 | `runtime-prestep-output.txt` + `verification.md` Section 6 |
| 9 | No secrets/passwords exposed in evidence | Full scan of all 3 evidence files |
| 10 | Diagnostics clean for evidence area | LSP + content review of evidence directory |

Cross-reference: `src/memory/models.py` model definitions for `Episodes` and `SemanticFacts` HNSW index parameters, column names, and vector dimensions.

---

## 2 — Audit Results

### 2.1 Check 1: HNSW indexes verified on VPS (real runtime evidence)

**Verdict:** ✅ PASS

**Evidence:** `hnsw-verification-output.txt` contains raw SSH/Docker `psql` session output connecting to Guinevere PostgreSQL on the shared VPS (`guinevere-vps`, Tailscale 100.94.104.22). The `pg_indexes` query in Section 3 returns actual index definitions from the running database. The `runtime-prestep-output.txt` confirms pre-step connectivity via `pg_isready -h 127.0.0.1 -p 5433`.

**Finding:** Real runtime evidence, not local claims. Verified.

### 2.2 Check 2: ix_episodes_embedding_hnsw params

**Verdict:** ✅ PASS

**Evidence (DB):**
```
ix_episodes_embedding_hnsw | CREATE INDEX ix_episodes_embedding_hnsw ON memory.episodes
USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='128')
```

**Evidence (Model — `src/memory/models.py` line 93-99):**
```python
Index(
    "ix_episodes_embedding_hnsw",
    "embedding",
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
    postgresql_with={"m": 16, "ef_construction": 128},
)
```

**Finding:** DB index definition matches model exactly: m=16 ✅, ef_construction=128 ✅, vector_cosine_ops ✅.

### 2.3 Check 3: ix_semantic_facts_embedding_hnsw params

**Verdict:** ✅ PASS

**Evidence (DB):**
```
ix_semantic_facts_embedding_hnsw | CREATE INDEX ix_semantic_facts_embedding_hnsw ON memory.semantic_facts
USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='128')
```

**Evidence (Model — `src/memory/models.py` line 155-161):**
```python
Index(
    "ix_semantic_facts_embedding_hnsw",
    "embedding",
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
    postgresql_with={"m": 16, "ef_construction": 128},
)
```

**Finding:** DB index definition matches model exactly: m=16 ✅, ef_construction=128 ✅, vector_cosine_ops ✅.

### 2.4 Check 4: No stale `embedding_vec` column or index

**Verdict:** ✅ PASS

**Evidence (hnsw-verification-output.txt Section 5):**
- `SELECT column_name FROM information_schema.columns WHERE column_name = 'embedding_vec'` → **0 rows** ✅
- `SELECT indexname FROM pg_indexes WHERE indexname LIKE '%embedding_vec%'` → **0 rows** ✅

**Finding:** Neither an `embedding_vec` column nor index exists in any schema. The model uses `embedding` column only. BD-06 confirmed.

### 2.5 Check 5: No unintended model/schema edits

**Verdict:** ✅ PASS

**Evidence (verification.md Section 2):**
> No source code, model files (src/memory/models.py), PROGRESS.md, or CHECKLIST.md were modified.

**File system scan:** Only 3 files created, all under `docs/setup-evidence/P3/STEP-P3-006/`. No `src/` files touched. Confirmed.

### 2.6 Check 6: Cosine EXPLAIN shows Index Scan using HNSW (or documented caveat)

**Verdict:** ✅ PASS

**semantic_facts (non-empty enough for planner to choose index):**
```
Index Scan using ix_semantic_facts_embedding_hnsw on memory.semantic_facts
Order By: (embedding <=> '[...]'::vector)
```
✅ Direct Index Scan using HNSW confirmed.

**episodes (empty table — 0 rows):**
```
Sort → Result (One-Time Filter: false)
```
Planner chooses Sort+Result over Index Scan because the table has 0 rows. This is correct PostgreSQL behavior for empty tables.

**Documented caveat (verification.md Section 3.6):**
- Explicit explanation that 0-row tables skip index scans
- `enable_seqscan=off` debug proof provided (hnsw-verification-output.txt Section 8)
- Confirms index is valid and will be used once data is populated

**Finding:** EXPLAIN evidence properly documented including the empty-table caveat and debug proof.

### 2.7 Check 7: Evidence follows minimum 12-section schema from plan

**Verdict:** ✅ PASS

| # | Section | Present |
|---|---------|---------|
| 1 | What Was Done | ✅ |
| 2 | Files Changed | ✅ |
| 3 | Validation Results | ✅ (6 subsections) |
| 4 | Evidence Artifacts | ✅ |
| 5 | Doc-Sync Impact | ✅ |
| 6 | Boundary Compliance | ✅ (7-row table) |
| 7 | Rollback / Re-run Safety | ✅ |
| 8 | Design Decisions / Caveats | ✅ (4 BDs + 4 caveats) |
| 9 | Auditor Gate | ✅ (pending — expected pre-audit) |
| 10 | Security Scan | ✅ (6 checks) |
| 11 | Acceptance Criteria Mapping | ✅ (3 ACs) |
| 12 | Footer | ✅ |

**Finding:** All 12 sections present and substantively populated.

### 2.8 Check 8: No Aizanta data/service touched beyond pg_isready on port 5432

**Verdict:** ✅ PASS

**Evidence (runtime-prestep-output.txt Section 1):**
```
127.0.0.1:5432 - accepting connections
```
Only `pg_isready -h 127.0.0.1 -p 5432` was executed against Aizanta PostgreSQL. No Aizanta queries, no Aizanta database accessed.

**verification.md Section 6:** Confirms "Only read-only pg_isready on port 5432; no Aizanta data queried."

### 2.9 Check 9: No secrets/passwords exposed in evidence

**Verdict:** ✅ PASS

**Full evidence scan:** No passwords, API keys, tokens, decrypted values, or credentials found in any of the 3 evidence files. Redis authentication check returns `NOAUTH Authentication required` (standard server response, not a credential leak). Connection method documented as Docker local socket trust — no passwords transmitted.

### 2.10 Check 10: Diagnostics clean for evidence area

**Verdict:** ✅ PASS

**Finding:** Evidence directory contains only `.md` and `.txt` files (no source code). No LSP diagnostics applicable. No code-level warnings or errors in the evidence files themselves.

---

## 3 — Minor Findings (Non-Blocking)

### 3.1 Failed `pg_class.reloptions` Exploration Query

**Location:** `hnsw-verification-output.txt` Section 4

**Issue:** The query used `i.indexrelid` instead of `ix.indexrelid`, causing a PostgreSQL error:
```
ERROR:  column i.indexrelid does not exist
LINE 1: ...x_name, a.attname AS column_name, pg_get_indexdef(i.indexrel...
HINT:  Perhaps you meant to reference the column "ix.indexrelid".
```

**Impact:** Non-critical. The canonical index parameter verification was performed via `pg_indexes` (Section 3) which succeeded and returned the correct DDL. This was an exploration query that used the wrong table alias.

**Recommendation:** Fix the query alias if re-running, but this does not affect the validity of the verification step.

### 3.2 Index Size Query Error (First Attempt)

**Location:** `hnsw-verification-output.txt` Section 10 (first occurrence)

**Issue:**
```
ERROR:  relation "ix_episodes_embedding_hnsw" does not exist
```

**Impact:** Non-critical. The query was repeated in the "Index sizes" section at the bottom of the same file and succeeded, returning 16 kB for both indexes. The first attempt likely failed due to schema qualification.

---

## 4 — Model Alignment Verification

Cross-referenced DB state against `src/memory/models.py`:

| Property | DB Value | Model Value | Match |
|----------|----------|-------------|-------|
| Column name | `embedding` | `embedding` | ✅ |
| Vector dimension | 1536 (atttypmod) | `Vector(1536)` | ✅ |
| Episodes HNSW m | 16 | 16 | ✅ |
| Episodes HNSW ef_construction | 128 | 128 | ✅ |
| Episodes HNSW ops | `vector_cosine_ops` | `vector_cosine_ops` | ✅ |
| SemanticFacts HNSW m | 16 | 16 | ✅ |
| SemanticFacts HNSW ef_construction | 128 | 128 | ✅ |
| SemanticFacts HNSW ops | `vector_cosine_ops` | `vector_cosine_ops` | ✅ |
| `raw_content` column | Present (29 columns listing) | `raw_content` | ✅ |
| No `embedding_vec` | Confirmed | Not in model | ✅ |
| No `content` column | Not in listing | Not in model | ✅ |

**Finding:** 100% alignment between DB state and model definitions.

---

## 5 — Verdict

| Criterion | Result |
|-----------|--------|
| All 10 check points | ✅ PASS |
| Non-blocking findings | 2 minor notes (failed exploration query, first index size query) |
| Model alignment | ✅ 100% |
| Evidence completeness | ✅ 12-section schema followed |

### **Verdict: ✅ PASS**

All 10 mandatory checks satisfied. Evidence is real runtime data from the VPS. HNSW indexes exist with correct parameters. No stale columns, no unintended edits, no secrets exposed. The two minor findings (failed exploration query alias, duplicate index size query) are non-critical script issues that do not affect verification validity.

### Next Action

- If PASS accepted: Mark P3-006 complete, update PROGRESS.md and CHECKLIST.md, proceed to P3-007
- If re-run needed: Fix the `pg_class.reloptions` alias from `i.indexrelid` to `ix.indexrelid` (cosmetic only)

---

## 6 — Footer

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Author** | DB Implementation Auditor (Independent) |
| **Step** | P3-006 |
| **Phase** | P3 (Memory System) — batch 2 of ~6 |
| **Evidence root** | `docs/setup-evidence/P3/STEP-P3-006/` |
| **Verdict** | ✅ **PASS** — All checks satisfied with 2 minor non-blocking notes |
| **Files audited** | `verification.md`, `runtime-prestep-output.txt`, `hnsw-verification-output.txt`, `batch-plan-004-010.md`, `src/memory/models.py` |