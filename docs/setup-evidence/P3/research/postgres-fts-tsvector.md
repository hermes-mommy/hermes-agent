# P3-008 Research: PostgreSQL 16 Full-Text Search — tsvector Setup for `memory.episodes`

**Date:** 2026-06-02
**Author:** Guinevere (Librarian — external docs research)
**Target:** PostgreSQL 16.14 (Debian 16.14-1.pgdg13+1) with TimescaleDB + pgvector
**Requirement:** P3-008 — FTS indexes exist, populated tsvector, trigger active; enable hybrid search (vector + FTS)
**Sources:** Official PostgreSQL 16 docs (`/docs/16/textsearch*`), Context7, Crunchy Data, Rivestack, OnGres benchmarks

---

## 1. Actual Schema: `memory.episodes` Column Ground Truth

The model at `src/memory/models.py` (line 85–131) defines:

| Column | Type | Nullable | FTS-relevant? |
|---|---|---|---|
| `id` | `UUID` | NO (PK) | no |
| `started_at` | `TIMESTAMPTZ` | NO (PK, hypertable key) | no |
| `ended_at` | `TIMESTAMPTZ` | YES | no |
| `episode_type` | `TEXT` | NO | maybe — could weight `'A'` |
| `title` | `TEXT` | YES | **YES — weight 'A'** |
| `summary` | `TEXT` | YES | **YES — weight 'B'** |
| `key_insights` | `JSONB` | YES | **YES — weight 'C' (via `coalesce`)** |
| `raw_content` | `TEXT` | YES | **YES — weight 'D' (main body)** |
| `embedding` | `Vector(1536)` | YES | vector search (separate) |
| `tags` | `ARRAY(TEXT)` | YES | **YES — weight 'C' (via `array_to_string`)** |

**Critical naming note:** The column is `raw_content`, **not** `content` as StepPrompts P3-008 line 6191 claims. All SQL must use `raw_content`.

---

## 2. Design Decision: Generated Column vs Trigger

### 2.1 Recommendation: **Stored Generated Column (PostgreSQL 12+ canonical)**

| Aspect | Generated Column | Trigger (`tsvector_update_trigger`) |
|---|---|---|
| PostgreSQL since | 12 (2019) | 8.3 (2008) |
| Syntax | `GENERATED ALWAYS AS (...) STORED` | `CREATE TRIGGER ... EXECUTE FUNCTION tsvector_update_trigger(...)` |
| Performance (INSERT) | **~0.5x faster** than PL/pgSQL trigger (OnGres benchmark) | Slower — trigger overhead |
| Performance (UPDATE) | **~3% faster** than PL/pgSQL trigger | Slightly slower |
| Auto-sync on change | **Yes** — computed on every write | **Yes** — via BEFORE trigger |
| Overrideable | **No** — cannot write to generated column directly | **Yes** — trigger result can be overridden |
| Supports `setweight` + multi-column `coalesce` | **Yes** — arbitrary immutable expression | **Limited** — only basic column list, no `coalesce`, no `setweight` |
| Maintainability | **Declarative** — schema-level, no separate function/trigger objects | **Procedural** — separate function + trigger objects |
| Works with `ALTER TABLE ... ADD COLUMN` | **Yes** — immediate, backfills automatically | **No** — backfill requires separate `UPDATE` |
| Side effect: full-text config locked in expression | **Yes** — must specify `'english'` explicitly in the `GENERATED ALWAYS AS` | **Yes** — config name is trigger argument |

**Official PostgreSQL 16 docs (Section 12.2):**
> **"Another approach is to create a separate `tsvector` column to hold the output of `to_tsvector`. To keep this column automatically up to date with its source data, use a stored generated column."**

**Benchmark evidence (OnGres, PostgreSQL 12 benchmark):**
> Generated Columns outperform PL/pgSQL triggers by ~0.5× on INSERT and ~3% on UPDATE, with leaner syntax and no separate function/trigger management.

**Verdict:** Use **stored generated column**. The trigger approach (`tsvector_update_trigger`) is obsolete for PostgreSQL 16 — it cannot handle `coalesce` for NULL columns, cannot use `setweight` for field-level ranking, and creates more maintenance surface.

### 2.2 What About Expression Indexes?

PostgreSQL also supports:
```sql
CREATE INDEX ON memory.episodes USING GIN (
    to_tsvector('english', coalesce(raw_content, ''))
);
```

**Pros:** No extra column needed, less disk space.
**Cons:**
- Cannot use `setweight` for per-field ranking
- Index verification re-runs `to_tsvector` (slower queries)
- Query must match the exact 2-argument `to_tsvector('english', ...)` to use the index
- No column for manual inspection or debugging

Not recommended for hybrid search where FTS ranking is needed alongside vector ranking. The stored generated column is the better fit.

---

## 3. Proposed Column Definition

### 3.1 `search_vector` — `TSVECTOR` generated column

```sql
ALTER TABLE memory.episodes
    ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')
    ) STORED;
```

**Weight rationale:**
| Weight | Source | Why |
|---|---|---|
| `'A'` | `title` | Highest — titles are the most concise descriptors |
| `'B'` | `summary` | High — summaries capture essence |
| `'D'` | `raw_content` | Baseline — main body text |

`key_insights` (JSONB) and `tags` (`ARRAY(TEXT)`) can be added later if needed, but they are nullable and add complexity:
```sql
-- Optional extension:
setweight(to_tsvector('english', coalesce(array_to_string(tags, ' '), '')), 'C') ||
setweight(to_tsvector('english', coalesce(key_insights::text, '')), 'C')
```

### 3.2 Safe Expression for NULL/JSON Fields

`to_tsvector(NULL)` returns `NULL`, which causes the entire `||` concatenation to become `NULL`. The `coalesce(column, '')` wrapper ensures NULL fields contribute an empty tsvector rather than nullifying the result.

For `key_insights` (JSONB), cast to `text`:
```sql
coalesce(key_insights::text, '')
```
This produces the JSON string representation, which `to_tsvector` will parse as normal text tokens.

### 3.3 GIN Index

```sql
CREATE INDEX IF NOT EXISTS ix_episodes_search_vector_gin
    ON memory.episodes
    USING GIN (search_vector);
```

**Why GIN not GiST** (from official docs Section 12.9):
> "GIN indexes are the preferred text search index type."

| Index Type | Properties |
|---|---|
| GIN | Inverted index — faster search, slower build, no false matches |
| GiST | Lossy (false matches possible), larger, slower search |

GIN index build time can be improved by increasing `maintenance_work_mem`. For the episodes table (expected to be large), schedule this during low-traffic period or batch after backfill.

---

## 4. Query Patterns for Hybrid Search

### 4.1 FTS-only query with `websearch_to_tsquery`

```sql
SELECT id, title, raw_content,
       ts_rank_cd(search_vector, query) AS rank
FROM memory.episodes,
     websearch_to_tsquery('english', 'memory consolidation') query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 10;
```

**`websearch_to_tsquery` advantages** (official docs Section 12.3.2):
- Accepts raw user input without syntax errors
- Supports `"quoted phrase"` → `<->` operator
- Supports `OR` → `|` operator
- Supports `-` prefix → `!` (NOT) operator
- Never raises syntax errors — safe for raw user input

### 4.2 Hybrid search (vector + FTS combined)

```sql
WITH fts_matches AS (
    SELECT id, raw_content,
           ts_rank_cd(search_vector, query) AS fts_score
    FROM memory.episodes,
         websearch_to_tsquery('english', 'memory consolidation') query
    WHERE search_vector @@ query
),
vector_matches AS (
    SELECT id,
           1 - (embedding <=> '[...1536-dim vector...]'::vector) AS vec_score
    FROM memory.episodes
    ORDER BY embedding <=> '[...1536-dim vector...]'::vector
    LIMIT 50
)
SELECT COALESCE(f.id, v.id) AS id,
       e.raw_content,
       COALESCE(f.fts_score, 0) AS fts_score,
       COALESCE(v.vec_score, 0) AS vec_score,
       (COALESCE(f.fts_score, 0) * 0.3 + COALESCE(v.vec_score, 0) * 0.7) AS hybrid_score
FROM fts_matches f
FULL OUTER JOIN vector_matches v ON f.id = v.id
JOIN memory.episodes e ON e.id = COALESCE(f.id, v.id)
ORDER BY hybrid_score DESC
LIMIT 10;
```

**Hybrid scoring notes:**
- Weights (0.3 FTS + 0.7 vector) are tunable — ADR-009 should document the chosen ratio
- `ts_rank_cd` returns values ~0..1+ (normalize with option 32: `ts_rank_cd(..., 32)`)
- Vector cosine similarity returns 0..1 (for `text-embedding-3-small`)
- Both scores need normalization before weighted combination

### 4.3 FTS ranking with `ts_rank_cd`

**Why `ts_rank_cd` over `ts_rank`** (official docs Section 12.3.3):
> "Cover density is similar to ts_rank ranking except that the proximity of matching lexemes to each other is taken into consideration."

`ts_rank_cd` rewards terms that appear close together, which is better for relevance.

**Normalization options (bitmask):**

| Flag | Behavior |
|---|---|
| 0 (default) | Ignore document length |
| 1 | Divide rank by 1 + log(document length) |
| 2 | Divide rank by document length |
| 4 | Divide rank by mean harmonic distance (ts_rank_cd only) |
| 8 | Divide rank by unique word count |
| 16 | Divide rank by 1 + log(unique word count) |
| 32 | Scale to `rank/(rank+1)` → range 0..1 |

Recommended for hybrid search: `ts_rank_cd(search_vector, query, 1|32)` — normalize by log(length) and scale to 0..1.

### 4.4 Alternative: `plainto_tsquery` for simpler queries

```sql
SELECT id, title, ts_rank_cd(search_vector, plainto_tsquery('english', 'memory consolidation')) AS rank
FROM memory.episodes
WHERE search_vector @@ plainto_tsquery('english', 'memory consolidation')
ORDER BY rank DESC;
```

`plainto_tsquery` is simpler than `websearch_to_tsquery` but:
- Inserts `&` (AND) between all words
- Ignores all punctuation and operators
- No OR/NOT/phrase support

**Recommendation:** Use `websearch_to_tsquery` for user-facing search (Discord commands), `plainto_tsquery` for internal/automated queries where you want all terms to match.

---

## 5. Backfill Strategy for Existing Rows

Since `GENERATED ALWAYS AS ... STORED` is declarative, PostgreSQL handles backfill automatically when the column is added:

```sql
-- Step 1: Add the column (PostgreSQL backfills ALL existing rows automatically)
ALTER TABLE memory.episodes
    ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')
    ) STORED;

-- Step 2: Create the GIN index
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_episodes_search_vector_gin
    ON memory.episodes
    USING GIN (search_vector);
```

**Important:** `ALTER TABLE ... ADD COLUMN ... GENERATED ALWAYS AS ... STORED` is a **non-destructive metadata-only operation** for the column definition. PostgreSQL will compute the tsvector values for all existing rows during the `ALTER TABLE`. For very large tables (>1M rows) on the hypertable, this may take time but does not block reads in PG16.

**For trigger-based setups (if generated column is not chosen):**
```sql
-- After adding column and trigger:
UPDATE memory.episodes SET search_vector =
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')
WHERE search_vector IS NULL;
```

---

## 6. Verification SQL

Run these after migration to confirm FTS is working:

### 6.1 Verify column exists and is populated

```sql
-- Check column type and default
SELECT column_name, data_type, is_generated, generation_expression
FROM information_schema.columns
WHERE table_schema = 'memory'
  AND table_name = 'episodes'
  AND column_name = 'search_vector';
```

Expected: `data_type = 'tsvector'`, `is_generated = 'ALWAYS'`.

### 6.2 Check for NULL tsvectors (should be zero)

```sql
SELECT count(*) AS null_search_vectors
FROM memory.episodes
WHERE search_vector IS NULL;
```

Expected: `0`.

### 6.3 Check index exists

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'memory'
  AND tablename = 'episodes'
  AND indexdef LIKE '%search_vector%';
```

Expected: `ix_episodes_search_vector_gin` with `USING gin (search_vector)`.

### 6.4 FTS query works

```sql
SELECT id, title,
       ts_rank_cd(search_vector, websearch_to_tsquery('english', 'test query')) AS rank
FROM memory.episodes
WHERE search_vector @@ websearch_to_tsquery('english', 'test query')
ORDER BY rank DESC
LIMIT 5;
```

Expected: Returns matching rows with rank > 0. Empty result is acceptable if table has no matching data.

### 6.5 Verify generated column updates on INSERT

```sql
-- Insert test row (rollback after)
BEGIN;
INSERT INTO memory.episodes (started_at, episode_type, title, raw_content)
VALUES (now(), 'test', 'Test Episode Title', 'This is the raw content body for testing full text search');
SELECT search_vector FROM memory.episodes WHERE title = 'Test Episode Title';
ROLLBACK;
```

Expected: `search_vector` is non-null and contains lexemes from both title and raw_content.

### 6.6 Verify generated column updates on UPDATE

```sql
BEGIN;
-- Insert, then update title, verify search_vector changed
INSERT INTO memory.episodes (started_at, episode_type, title, raw_content)
VALUES (now(), 'test', 'Original Title', 'Body text');
-- Get search_vector value
SELECT search_vector FROM memory.episodes WHERE title = 'Original Title';
-- Update title
UPDATE memory.episodes SET title = 'Updated Title' WHERE title = 'Original Title';
-- Verify it changed
SELECT search_vector FROM memory.episodes WHERE title = 'Updated Title';
ROLLBACK;
```

Expected: `search_vector` values differ before and after update, reflecting the new title lexemes.

---

## 7. Minimal Migration Strategy (P3-008)

### 7.1 Migration Steps

| Step | SQL/Action | Risk | Reversible? |
|---|---|---|---|
| 1 | Add `search_vector tsvector` to Episodes model in `models.py` | Low — new column only | Yes — revert model change |
| 2 | Generate Alembic revision: `alembic revision --autogenerate -m "add_search_vector_to_episodes"` | Low — autogenerate produces expected DDL | Yes — downgrade removes column |
| 3 | Review generated migration — ensure it matches this doc's ALTER TABLE | Medium — verify column type is `tsvector` not `text` | Yes — review before apply |
| 4 | Run migration: `alembic upgrade head` | Medium — backfill on existing rows | Yes — `alembic downgrade -1` |
| 5 | Create GIN index separately (may need CONCURRENTLY on hypertable) | Medium — long-running, use CONCURRENTLY | Yes — `DROP INDEX` |
| 6 | Run verification SQL (Section 6) | Low — read-only | N/A |

### 7.2 Rollback

```sql
-- Rollback step 1 (index first, then column)
DROP INDEX IF EXISTS memory.ix_episodes_search_vector_gin;
ALTER TABLE memory.episodes DROP COLUMN IF EXISTS search_vector;
```

Alembic downgrade should do the same:
```python
def downgrade():
    op.drop_index("ix_episodes_search_vector_gin", table_name="episodes", schema="memory")
    op.drop_column("search_vector", table_name="episodes", schema="memory")
```

**Rollback is safe** — no data loss, no table rebuild. The column and index are purely derived from existing data.

---

## 8. Section 12 Official PostgreSQL 16 Doc References

| Topic | URL |
|---|---|
| FTS Chapter 12 intro | https://www.postgresql.org/docs/16/textsearch.html |
| Tables & Indexes (Section 12.2) | https://www.postgresql.org/docs/16/textsearch-tables.html |
| Controlling Text Search (Section 12.3) | https://www.postgresql.org/docs/16/textsearch-controls.html |
| Additional Features (Section 12.4) | https://www.postgresql.org/docs/16/textsearch-features.html |
| Text Search Functions (Section 9.13) | https://www.postgresql.org/docs/16/functions-textsearch.html |
| GIN Indexes (Section 12.9) | https://www.postgresql.org/docs/16/textsearch-indexes.html |
| Generated Columns (Section 5.3) | https://www.postgresql.org/docs/16/ddl-generated-columns.html |
| Trigger Functions (Section 9.28) | https://www.postgresql.org/docs/16/functions-trigger.html |

---

## 9. Key Conclusions

1. **Use stored generated column, NOT trigger.** PostgreSQL 16 supports `GENERATED ALWAYS AS ... STORED` which is faster, declarative, and handles NULL safely via `coalesce`.

2. **Column name is `search_vector`** of type `tsvector`. This matches StepPrompts P3-008 convention.

3. **Source column is `raw_content`**, not `content` as StepPrompts claim. Must correct in all SQL.

4. **NULL safety:** `to_tsvector(NULL)` returns NULL. Use `coalesce(raw_content, '')` for all nullable text/JSONB columns.

5. **Weight assignment:** `title='A'`, `summary='B'`, `raw_content='D'` — enables field-specific ranking with `ts_rank_cd`.

6. **GIN index is preferred** over GiST for tsvector (per official docs Section 12.9).

7. **`websearch_to_tsquery`** is recommended for user-facing queries (Discord). It supports phrases, OR, and NOT with no syntax errors.

8. **`ts_rank_cd`** is recommended over `ts_rank` for proximity-aware ranking. Use normalization `1|32` for hybrid search.

9. **Backfill is automatic** with generated columns — PostgreSQL computes tsvector for all existing rows during `ALTER TABLE`.

10. **Rollback is safe** — drop index, drop column. No destructive rebuild.

---

## 10. Open Questions / Caveats

- **TimescaleDB hypertable interaction:** `ALTER TABLE ... ADD COLUMN ... GENERATED ALWAYS AS` on a hypertable should work in TimescaleDB 2.x+ but verify in deployment. TimescaleDB may decompress chunks first.
- **CONCURRENTLY index creation:** GIN index creation on a hypertable may require `CREATE INDEX CONCURRENTLY` to avoid blocking writes. Verify exact syntax for TimescaleDB.
- **Compression:** If `memory.episodes` chunks are compressed in the future, adding a generated column will require decompression → re-compression.
- **`key_insights` (JSONB) and `tags` (ARRAY):** Excluded from initial `search_vector` for simplicity. Can be added in a follow-up migration if FTS recall needs improvement.
- **`do_not_recall` column:** Not yet in the model (per P3-004 readiness report). If added, the search_vector definition does not need to reference it — filtering happens at query time (`WHERE NOT do_not_recall`).