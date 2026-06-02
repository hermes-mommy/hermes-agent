# P3-008 Auditor Gate Report

**File:** `docs/setup-evidence/P3/STEP-P3-008/auditor-gate.md`
**Step:** P3-008 — tsvector FTS + `do_not_recall` Migration
**Date:** 2026-06-02
**Auditor:** Independent Gate Auditor (Sisyphus-Junior)
**Status:** ✅ **PASS** — All checks satisfied

---

## Verdict

| Criterion | Result |
|-----------|--------|
| Model artifacts match plan | ✅ PASS |
| Migration file correct | ✅ PASS |
| DB evidence matches claims | ✅ PASS |
| Shell scripts use approved SOPS pattern | ✅ PASS |
| FTS verified working | ✅ PASS |
| `raw_content` used, not stale `content` | ✅ PASS |
| No trigger approach | ✅ PASS |
| No HNSW/index rebuild beyond GIN | ✅ PASS |
| No P3-009/P3-010 scope creep | ✅ PASS |
| No Aizanta data beyond health checks | ✅ PASS |
| No secrets / decrypted values in artifacts | ✅ PASS |
| Diagnostics: no new errors introduced | ✅ PASS |
| **OVERALL VERDICT** | ✅ **PASS** |

---

## Checkpoint Table

| # | Check | Detail | Status |
|---|-------|--------|--------|
| 1 | `EPISODES_SEARCH_VECTOR_EXPRESSION` constant | Defined at `models.py:28-32`, uses `raw_content`, no stale `content` | ✅ |
| 2 | `search_vector` as TSVECTOR Computed | `Computed(EPISODES_SEARCH_VECTOR_EXPRESSION)` at line 132-136, `TSVECTOR` dialect type, nullable=True | ✅ |
| 3 | `do_not_recall` boolean default false | `server_default=text("false")`, `nullable=False` at line 137-139 | ✅ |
| 4 | GIN index `ix_episodes_search_vector_gin` | `postgresql_using="gin"` on `search_vector` at lines 102-106 | ✅ |
| 5 | Migration `65f863220922` head | Alembic output shows `65f863220922 (head)`, revises `e401bb5fd274` | ✅ |
| 6 | Migration uses `raw_content` | Line 24 of migration: `coalesce(raw_content, '')` — not `content` | ✅ |
| 7 | GIN index in migration | `op.create_index(..., postgresql_using='gin')` at migration line 26 | ✅ |
| 8 | Proper downgrade | Drops index, `do_not_recall`, `search_vector` — all reversible | ✅ |
| 9 | Shell scripts use approved SOPS pattern | Both scripts: `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt sops --decrypt` | ✅ |
| 10 | Shell scripts DO NOT print password/length | No `echo $PW`, no `${#PW}`, no password length output | ✅ |
| 11 | FTS query returns true | `fts-verification-output.txt` line 19: `t` | ✅ |
| 12 | Generated column produces correct weights | Rollback test: A=title, B=summary, D=raw_content all present | ✅ |
| 13 | Rollback test rows not persisted | Both test inserts wrapped in `BEGIN; ... ROLLBACK;` | ✅ |
| 14 | No trigger approach | Uses `GENERATED ALWAYS AS STORED` via `Computed()` — confirmed in model and migration | ✅ |
| 15 | No HNSW/index rebuild/drop beyond GIN | Only `ix_episodes_search_vector_gin` created; HNSW `ix_episodes_embedding_hnsw` untouched | ✅ |
| 16 | No Aizanta data beyond health checks | Only `pg_isready -h 127.0.0.1 -p 5432`; no Aizanta data queries | ✅ |
| 17 | No P3-009/P3-010 scope creep | No write_pipeline, read_pipeline, or embedding pipeline code | ✅ |
| 18 | No secrets/API keys/decrypted values in artifacts | All plaintext outputs show no passwords or keys | ✅ |
| 19 | LSP diagnostics: no new errors | All 624 diagnostics are pre-existing (unresolved imports: pgvector, sqlalchemy, etc.) | ✅ |
| 20 | No implicit string concatenation issue | Expression is a single string constant — not split across string literals | ✅ |

---

## Detailed Findings

### 1. Model Artifacts (`src/memory/models.py`)

All P3-008 model additions verified:

- **Constant defined:** `EPISODES_SEARCH_VECTOR_EXPRESSION` at lines 28-32 uses explicit string concatenation (not implicit), referencing `title`, `summary`, and `raw_content` with correct `setweight` calls (A, B, D).
- **`search_vector` column:** Lines 132-136 use `TSVECTOR` dialect type with `Computed(EPISODES_SEARCH_VECTOR_EXPRESSION)`, nullable=True. Correct `GENERATED ALWAYS AS STORED` semantics.
- **`do_not_recall` column:** Lines 137-139 use `Boolean`, `nullable=False`, `server_default=text("false")`. Correct.
- **GIN index:** Lines 102-106 define `ix_episodes_search_vector_gin` with `postgresql_using="gin"` on `search_vector`. Correct.
- **Imports:** `Computed` at line 9, `TSVECTOR` at line 23. Both present.

### 2. Migration File (`65f863220922_add_search_vector_do_not_recall.py`)

- Head revision `65f863220922`, revises `e401bb5fd274`.
- `upgrade()` creates `search_vector` with `sa.Computed(...)` using `raw_content`, creates `do_not_recall` boolean with `server_default=sa.text('false')`, creates GIN index.
- `downgrade()` reverses all three operations in correct dependency order.
- No trigger approach — uses SQLAlchemy `Computed()` which maps to PostgreSQL `GENERATED ALWAYS AS STORED`.

### 3. DB Evidence

- `migration-output-raw.txt`: Confirms autogenerate detected `search_vector`, `do_not_recall`, and GIN index. Upgrade ran successfully.
- `fts-verification-output.txt`: Columns verified (`search_vector` tsvector, `do_not_recall` boolean NO default false). GIN index verified. FTS query returns `t`. Generated column rollback test shows correct tsvector output with A/B/D weights. `do_not_recall` default verified `f`. Alembic head confirmed `65f863220922`.
- `verification.md`: 12-section schema complete. Audit trail, boundary compliance, security scan all documented.

### 4. Shell Script Security

- **`p3-008-migration.sh`:** Uses `SOPS_AGE_KEY_FILE=... sops --decrypt` to extract password; exports via `GUINEVERE_DB_PASSWORD="$PW"`. Does not echo `$PW` or its length.
- **`p3-008-verify.sh`:** Same SOPS pattern; exports `PGPASSWORD="$PW"` and `GUINEVERE_DB_PASSWORD="$PW"`. Does not echo `$PW` or its length.
- Both scripts follow the approved age-key path (`/home/guinevere/secrets/age-key.txt`).

### 5. FTS Verification

FTS query `SELECT to_tsvector('english', 'Guinevere remembers everything') @@ to_tsquery('english', 'remember')` returns `t` (true). Generated column rollback test confirms:
- `'hello':1A 'world':2A` — title with A weight
- `'summari':5B 'test':4B` — summary with B weight
- `'everyth':8 'faiz':10 'guinever':6 'rememb':7` — raw_content with D weight

### 6. Scope Boundary

No HNSW index modifications. No Aizanta data queried beyond `pg_isready`. No write pipeline, read pipeline, or embedding service code. Pure DDL migration.

### 7. Diagnostics

`lsp_diagnostics` on `src/memory/models.py` returns 624 warnings/errors, ALL pre-existing:
- `reportMissingImports`: `pgvector.sqlalchemy`, `sqlalchemy`, `sqlalchemy.dialects.postgresql`, `sqlalchemy.orm`, `sqlalchemy.sql` — local venv not installed on this machine
- `reportUnknownVariableType`: Cascading from unresolvable imports
- `reportDeprecated`: `Optional[T]` style (Python 3.10+ `T | None`)
- `reportUnannotatedClassAttribute`: `__tablename__`, `__table_args__` — SQLAlchemy pattern

**No new errors introduced by P3-008.** No implicit string concatenation diagnostic present.

---

## Caveats

1. **Empty FTS index:** Both `memory.episodes` and `memory.semantic_facts` contain 0 rows. The GIN index exists but has no data to index. This is expected at this stage — P3-009/P3-013 will populate data.
2. **Local Alembic gap:** Alembic `versions/` directory exists only on VPS. The migration file was SCP'd back as evidence. Cannot run `alembic current` locally.
3. **LSP noise:** All diagnostics are pre-existing and unrelated to P3-008 changes. The project dependencies are not installed in the local environment.
4. **`AC-MEM-005` partial:** The `do_not_recall` column exists but the actual filter logic is deferred to P3-010 (read pipeline). This is correctly documented in the verification report.

---

## Boundary Compliance

| Boundary | Status | Evidence |
|----------|--------|----------|
| No persona drift | ✅ PASS | No persona schema/code touched |
| No consent violation | ✅ PASS | No consent data accessed |
| No Y6 / safety boundary bypass | ✅ PASS | DDL migration only |
| No HARD STOP bypass | ✅ PASS | Not applicable |
| No Aizanta data/service touched | ✅ PASS | Read-only `pg_isready` on 5432 only |
| `raw_content` used, not `content` | ✅ PASS | All expression references use `raw_content` |
| No secrets exposed | ✅ PASS | No passwords/keys/decrypted values in evidence |
| No trigger approach | ✅ PASS | `GENERATED ALWAYS AS STORED` via `Computed()` |

---

## Footer

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Auditor** | Independent Gate Auditor (Sisyphus-Junior) |
| **Step** | P3-008 |
| **Phase** | P3 (Memory System) |
| **Verdict** | ✅ **PASS** |
| **Next action** | Parent syncs PROGRESS.md/CHECKLIST.md, proceeds to P3-009 |