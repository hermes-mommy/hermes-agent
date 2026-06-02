# P3-006 Research: pgvector HNSW Index — Cosine, vector(1536), m=16, ef_construction=128

> **Session**: P3-006 — Auditor verification of `ix_episodes_embedding_hnsw` and `ix_semantic_facts_embedding_hnsw`
>
> **Date**: 2026-06-02
>
> **Scope**: Exact SQL for HNSW index creation with `vector_cosine_ops`, `m=16`, `ef_construction=128`, `hnsw.ef_search`, concurrent index caveats, resource guidance for 4C/16GB VPS, Timescale hypertable implications, and verification queries.

---

## 1. Official Sources

| Source | URL | Version |
|--------|-----|---------|
| pgvector README (canonical) | <https://github.com/pgvector/pgvector/blob/master/README.md> | 0.8.x |
| pgvector HNSW docs | <https://github.com/pgvector/pgvector#hnsw> | 0.8.x |
| Supabase HNSW guide | <https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes> | 2026-05 |
| Neon HNSW tuning guide | <https://neon.com/docs/ai/ai-vector-search-optimization> | 2026 |
| Timescale pgvector docs | <https://docs.timescale.com/ai/latest/sql-interface-for-pgvector-and-timescale-vector/> | 2026 |
| DigitalOcean index tuning | <https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/index-and-tune/> | 2026-04 |
| pgvector GitHub Issues (build memory) | <https://github.com/pgvector/pgvector/issues/844> | 2025–2026 |
| pgvector GitHub Issues (parallel build) | <https://github.com/pgvector/pgvector/issues/409> | 2024 |
| Crunchy Data HNSW blog | <https://www.crunchydata.com/blog/hnsw-indexes-with-postgres-and-pgvector> | 2023-09 |
| DBI Services DBA guide | <https://www.dbi-services.com/blog/pgvector-a-guide-for-dba-part-2-indexes-update-march-2026/> | 2026-03 |

---

## 2. Exact SQL: HNSW Index with vector_cosine_ops

### 2.1 Extension check

```sql
-- Verify pgvector is installed and version >= 0.5.0 (HNSW added in 0.5.0)
SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- Expected: >= 0.5.0 (ideally 0.7.4+ for parallel build support)
```

### 2.2 Column type verification

The embedding column must be typed `vector(N)` where `N <= 2000` for HNSW indexes on the `vector` type:

```sql
-- Verify the column type and dimensions
SELECT column_name, udt_name, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'episodes' AND column_name = 'embedding';
-- Expected: udt_name = 'vector', character_maximum_length = 1536

SELECT column_name, udt_name, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'semantic_facts' AND column_name = 'embedding';
```

> **Constraint**: HNSW on `vector` type supports up to **2000 dimensions** ([pgvector README](https://github.com/pgvector/pgvector#hnsw)). If dimensions > 2000, use `halfvec` type with `halfvec_cosine_ops`. OpenAI `text-embedding-3-small` (1536) and `text-embedding-ada-002` (1536) are within this limit. `text-embedding-3-large` (3072) requires `halfvec`.

### 2.3 Correct CREATE INDEX SQL (non-concurrent)

```sql
CREATE INDEX IF NOT EXISTS ix_episodes_embedding_hnsw
    ON episodes
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);
```

```sql
CREATE INDEX IF NOT EXISTS ix_semantic_facts_embedding_hnsw
    ON semantic_facts
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);
```

### 2.4 Recommended: CREATE INDEX CONCURRENTLY (production-safe)

```sql
-- Cannot be run inside a transaction block
-- Set these BEFORE the CREATE INDEX statement
SET maintenance_work_mem = '4GB';          -- see §5 for sizing
SET max_parallel_maintenance_workers = 4;  -- match VPS core count
SET min_parallel_table_scan_size = 1;      -- ensure parallelism kicks in

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_episodes_embedding_hnsw
    ON episodes
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);
```

> **Critical**: `CREATE INDEX CONCURRENTLY` cannot run inside a `BEGIN ... COMMIT` block. It must be the only statement in its transaction. If a previous non-concurrent build left an INVALID index, drop it first:
>
> ```sql
> DROP INDEX IF EXISTS ix_episodes_embedding_hnsw;
> ```

### 2.5 About duplicate `embedding_vec` column

The user question asks whether adding a duplicate `embedding_vec` column is wrong when the existing schema already has `embedding vector(1536)`.

**Answer**: If a column named `embedding` of type `vector(1536)` already exists, **do NOT add a duplicate column** named `embedding_vec`. This would:

- Create two independent vector columns with identical data, doubling storage (each 1536-dim vector = ~6 KB)
- Require application-level syncing — any insert/update must set both columns
- Risk drift — if only one column gets updated, queries return incorrect results
- Waste index build time — you'd need HNSW indexes on both columns
- Confuse the query planner — which column does the `<=>` operator query against?

**The correct approach**: The existing `embedding` column is already of type `vector(1536)`. Build the HNSW index on that single column. If the migration code or ORM model defines `embedding_vec` as an alias or computed column, verify it's not a separate physical column. Check:

```sql
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'episodes' AND column_name LIKE 'embedding%';
```

If both `embedding` and `embedding_vec` appear as separate `vector(1536)` columns, one should be removed to eliminate data duplication risk.

---

## 3. Parameter Reference

### 3.1 Build-time parameters (set in WITH clause, immutable after creation)

| Parameter | Default | User value | Valid range | Effect |
|-----------|---------|------------|-------------|--------|
| `m` | 16 | **16** | 2–100 | Max bidirectional connections per layer. Higher = denser graph, better recall, larger index. |
| `ef_construction` | 64 | **128** | 4–1000, must be ≥ 2×m | Dynamic candidate list size during build. Higher = better graph quality, slower build. |

> **`m=16` rationale**: Default value (16) is the pgvector-recommended starting point. The original HNSW paper suggests 5–48 as the reasonable range. At `m=16`, each vector stores connections to up to 16 neighbors per layer, producing approximately 4–6 KB of graph overhead per 1536-dim vector ([Timescale pgvector guide](https://github.com/timescale/pg-aiguide/blob/main/skills/pgvector-semantic-search/SKILL.md)).
>
> **`ef_construction=128` rationale**: Double the default (64). Produces a higher-quality graph at the cost of ~2× build time. Well-justified for indexes built once and queried frequently. pgvector docs state: *"A higher value of ef_construction provides better recall at the cost of index build time / insert speed"* ([pgvector README](https://github.com/pgvector/pgvector#hnsw)). Neon tuning guide recommends starting with `ef_construction` equal to `ef_search` and incrementing ([Neon docs](https://neon.com/docs/ai/ai-vector-search-optimization)).

### 3.2 Query-time parameter: `hnsw.ef_search`

| Parameter | Default | Recommended range | Effect |
|-----------|---------|-------------------|--------|
| `hnsw.ef_search` | 40 | 40–200 (must be ≥ LIMIT) | Dynamic candidate list during search. Higher = better recall, slower. |

```sql
-- Session-level (persists until disconnect or RESET)
SET hnsw.ef_search = 100;

-- Transaction-level (auto-resets after COMMIT/ROLLBACK)
BEGIN;
SET LOCAL hnsw.ef_search = 100;
SELECT * FROM episodes
ORDER BY embedding <=> '[0.001, 0.002, ...]'::vector(1536)
LIMIT 10;
COMMIT;

-- Check current value
SHOW hnsw.ef_search;
```

> **Constraint**: `ef_search` must be ≥ `LIMIT`. If `ef_search = 40` and `LIMIT = 50`, only 40 rows can be returned ([Queryplane tuning guide](https://queryplane.com/docs/blog/tuning-pgvector-query-accuracy)).
>
> **Rule of thumb**: For high-recall use cases (RAG), use `ef_search = 100`–`200`. For latency-sensitive apps, start at `ef_search = 40` and increase until recall meets requirements.

### 3.3 Iterative scan parameters (pgvector 0.8.0+, for filtered queries)

```sql
SET hnsw.iterative_scan = strict_order;   -- exact distance order, best recall
SET hnsw.iterative_scan = relaxed_order;  -- approximate order, better for selective filters
SET hnsw.max_scan_tuples = 20000;         -- limit tuples scanned
SET hnsw.scan_mem_multiplier = 2;         -- memory multiplier for iterative scan
```

Default: `off`. Enable when queries include `WHERE` clauses that may filter out top-k results ([Supabase HNSW docs](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes)).

---

## 4. Cosine Query Pattern (SQL)

### 4.1 Basic ANN query using HNSW index

```sql
SET hnsw.ef_search = 100;

SELECT id, title, embedding <=> '[0.001, 0.002, ...]'::vector(1536) AS cosine_distance
FROM episodes
ORDER BY embedding <=> '[0.001, 0.002, ...]'::vector(1536)
LIMIT 10;
```

> **Operator-operator class matching is REQUIRED**:
> - `vector_cosine_ops` ↔ `<=>` (cosine distance)
> - `vector_l2_ops` ↔ `<->` (Euclidean/L2 distance)
> - `vector_ip_ops` ↔ `<#>` (negative inner product)
>
> A mismatch causes the planner to silently fall back to `Seq Scan` ([Stack Overflow](https://stackoverflow.com/questions/77757239/select-query-not-using-pgvector-hnsw-index)).

### 4.2 EXPLAIN verification

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, title, embedding <=> '[0.001, 0.002, ...]'::vector(1536) AS cosine_distance
FROM episodes
ORDER BY embedding <=> '[0.001, 0.002, ...]'::vector(1536)
LIMIT 10;
```

**Expected output**: `Index Scan using ix_episodes_embedding_hnsw` (or similar).

**If you see `Seq Scan`**, common causes ([Dev.to guide](https://dev.to/philip_mcclarence_2ef9475/your-pgvector-queries-are-doing-sequential-scans-heres-why-52ae)):
1. Operator class mismatch (cosine_ops requires `<=>`, not `<->`)
2. Missing `ORDER BY` + `LIMIT` — HNSW index requires both
3. Table too small for planner to choose index — `SET enable_seqscan = off;` to test
4. Expression/cast mismatch — if the index uses `(embedding::vector(1536))`, the query must match

```sql
-- Force index usage to verify (debug only, not for production)
BEGIN;
SET LOCAL enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM episodes
ORDER BY embedding <=> '[0.001, 0.002, ...]'::vector(1536)
LIMIT 10;
COMMIT;
```

### 4.3 Python/SQLAlchemy/asyncpg integration

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def search_similar(db: AsyncSession, query_embedding: list[float], limit: int = 10):
    # Option A: set ef_search via raw SQL execution
    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))
    
    # Option B: pass in the query itself
    sql = text("""
        SELECT id, title, 1 - (embedding <=> :query_vec::vector(1536)) AS cosine_similarity
        FROM episodes
        ORDER BY embedding <=> :query_vec::vector(1536)
        LIMIT :limit
    """)
    result = await db.execute(sql, {
        "query_vec": str(query_embedding),  # pgvector accepts string representation
        "limit": limit
    })
    return result.fetchall()
```

> **asyncpg note**: pgvector supports `asyncpg` natively via the `pgvector` Python package. The `register_vector(conn)` call is only required for `psycopg2`. With `asyncpg`, vector values can be passed as lists or strings:
>
> ```python
> import asyncpg
> # asyncpg auto-detects vector type
> await conn.fetch(
>     "SELECT * FROM items ORDER BY embedding <=> $1::vector LIMIT $2",
>     query_embedding,  # list[float] works
>     10
> )
> ```

---

## 5. Index Verification Queries

### 5.1 List indexes and their definitions

```sql
-- Shows index name, type, access method, and WITH options
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('episodes', 'semantic_facts')
  AND indexname LIKE '%hnsw%'
ORDER BY tablename, indexname;
```

**Expected for episodes**:
```
ix_episodes_embedding_hnsw | CREATE INDEX ... ON episodes USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=128)
```

**Expected for semantic_facts**:
```
ix_semantic_facts_embedding_hnsw | CREATE INDEX ... ON semantic_facts USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=128)
```

### 5.2 Verify HNSW access method and WITH options

```sql
-- Confirm HNSW amname and extract reloptions (m, ef_construction)
SELECT
    i.indexname,
    c.reloptions,
    am.amname AS access_method
FROM pg_indexes i
JOIN pg_class c ON c.relname = i.indexname
JOIN pg_am am ON am.oid = c.relam
WHERE i.tablename IN ('episodes', 'semantic_facts')
  AND am.amname = 'hnsw';
```

`reloptions` may appear as `{m=16,ef_construction=128}` or be `NULL` if built with defaults (which would mean `m=16, ef_construction=64` — **not compliant with P3-006 spec**) ([MonPG monitoring guide](https://monpg.app/pgvector-monitoring)).

### 5.3 Index size

```sql
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_indexes
JOIN pg_class c ON c.relname = indexname
JOIN pg_index ON pg_index.indexrelid = c.oid
WHERE tablename IN ('episodes', 'semantic_facts')
  AND indexname LIKE '%hnsw%';
```

> **Size estimate**: For 1536-dim vectors with `m=16`, expect roughly:
> - 1M vectors → ~6 GB index (just HNSW graph, excluding table data)
> - The index is roughly the same size as the table data itself
> - Formula: ~`4 × m × dimensions` bytes per vector for graph overhead, plus `4 × dimensions` for vector storage ([blog: pgvector tuning](https://muhammadamal.my.id/blog/pgvector-tuning-in-2024-hnsw-and-ivfflat-in-production/))

### 5.4 Build progress monitoring (during CREATE INDEX)

```sql
SELECT phase,
       round(100.0 * blocks_done / nullif(blocks_total, 0), 1) AS pct_complete,
       tuples_done,
       tuples_total,
       current_locker_wait,
       lockers_total
FROM pg_stat_progress_create_index;
```

---

## 6. Resource Caveats for 4C/16GB VPS

### 6.1 Memory sizing for HNSW build

The HNSW build has two phases ([pgvector hnswbuild.c](https://github.com/pgvector/pgvector/blob/master/src/hnswbuild.c)):

1. **In-memory phase**: Graph held in `maintenance_work_mem`. Fast.
2. **On-disk phase**: Graph spills to disk when it exceeds `maintenance_work_mem`. Dramatically slower (hours vs. minutes).

**Estimated memory needed** for fast in-memory build:

```
Per vector overhead ≈ sizeof(HnswElementData) + sizeof(HnswNeighborArray) * layers
                     + sizeof(HnswCandidate) * m * layers
                     + sizeof(ItemPointerData) + VECTOR_SIZE(dimensions)

For 1536-dim, m=16: ~6–8 KB per vector (empirical)

10,000  vectors → ~60–80  MB
100,000 vectors → ~600–800 MB
1,000,000 vectors → ~6–8 GB
```

Source: [pgvector GitHub Issue #844](https://github.com/pgvector/pgvector/issues/844) and [`HnswGetMaxInMemoryElements`](https://github.com/pgvector/pgvector/issues/745).

### 6.2 Recommended settings for 4C/16GB VPS

| Setting | Value | Rationale |
|---------|-------|-----------|
| `maintenance_work_mem` | **4 GB** | Max safe allocation on 16 GB box (leaves 12 GB for OS, PG shared_buffers, app). Increase if dataset > 500K vectors. |
| `max_parallel_maintenance_workers` | **4** | Match VCPU count. Parallel builds added in pgvector 0.7.4. |
| `shared_buffers` (general PG setting) | 4 GB | 25% of RAM standard recommendation. |
| `work_mem` | 64 MB | Sufficient for vector sort operations. |
| `max_worker_processes` | ≥ 8 | Must be ≥ `max_parallel_maintenance_workers`. |

### 6.3 When HNSW graph exceeds maintenance_work_mem

pgvector emits this notice:

```
NOTICE:  hnsw graph no longer fits into maintenance_work_mem after NNNNNNN tuples
DETAIL:  Building will take significantly more time.
HINT:  Increase maintenance_work_mem to speed up builds.
```

**If you see this on 4C/16GB VPS**:
- The build continues but switches to on-disk mode (much slower)
- For a 1M-row, 1536-dim dataset, a disk-spilling build can take **12+ hours** ([CYBERTEC blog](https://www.cybertec-postgresql.com/en/indexing-vectors-in-postgresql/))
- Solutions:
  1. Increase `maintenance_work_mem` if other processes can spare memory
  2. Build on an empty table first, then bulk-insert (inserts into HNSW are single-vector, still fast)
  3. Use `halfvec` to halve memory footprint
  4. Consider partitioning the table

### 6.4 Off-peak / safe build guidance

1. **Schedule during low-traffic window**: HNSW build is CPU- and memory-intensive. On a 4C/16GB VPS, expect:
   - 100K vectors (1536-dim): ~2–5 minutes with parallel build
   - 500K vectors: ~10–30 minutes
   - 1M vectors: ~20–60 minutes (in-memory) or 6–12+ hours (disk-spilling)
   
2. **Monitor resources during build**:
   ```sql
   -- From another session, check build progress
   SELECT phase, tuples_done, tuples_total,
          round(100.0 * tuples_done / nullif(tuples_total, 0), 1) AS pct
   FROM pg_stat_progress_create_index;
   ```
   
   ```bash
   # From shell, monitor system resources
   top                          # CPU and memory
   ps aux --sort=-%mem | head   # PostgreSQL processes
   iostat -x 5                  # I/O pressure (disk-spilling is I/O heavy)
   ```

3. **Use `CREATE INDEX CONCURRENTLY`**: Allows `INSERT`/`UPDATE`/`DELETE` to continue during the build. The build takes longer (two table scans + waiting for concurrent transactions), but production reads/writes are not blocked. This is the standard recommendation for production environments.

4. **Do NOT run multiple concurrent HNSW builds**: Each build consumes `maintenance_work_mem`. Running two simultaneously on a 4C/16GB VPS risks OOM or severe swapping. Build indexes sequentially.

### 6.5 Docker/Cgroup shm_size caveat

If running PostgreSQL in Docker, the default `shm_size` (64 MB) is too small for parallel HNSW builds. Set:

```yaml
# docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:0.8.2-pg16
    shm_size: 4gb  # Must be >= maintenance_work_mem
```

Without this, `CREATE INDEX` fails with: `ERROR: could not resize shared memory segment` ([pgvector Issue #409](https://github.com/pgvector/pgvector/issues/409)).

---

## 7. Timescale Hypertable & Composite PK Implications

### 7.1 Hypertable constraints on unique indexes

When the target table is a TimescaleDB hypertable:

- **Unique indexes (including PRIMARY KEY) MUST include all partitioning columns** (typically `time`) ([Timescale docs](https://github.com/timescale/docs/blob/latest/use-timescale/hypertables/hypertables-and-unique-indexes.md))
- A composite PK of `(id, time)` or similar is required for hypertables
- This does NOT affect HNSW indexes — HNSW is a non-unique, non-btree index and does not need to include the partitioning column
- HNSW indexes on hypertables are **per-chunk indexes**. The planner automatically only scans relevant chunks based on time constraints

### 7.2 What this means for P3-006

- The existing `ix_episodes_embedding_hnsw` on a hypertable is perfectly valid
- Time-based chunk pruning works independently of the HNSW index
- Query pattern: `WHERE time >= '2026-01-01' ORDER BY embedding <=> [...] LIMIT 10` — the planner prunes chunks by time, then uses HNSW per-chunk for vector search
- No multi-column vector indexes are possible with pgvector — HNSW indexes are single-column only ([pgvectorscale Issue #134](https://github.com/timescale/pgvectorscale/issues/134))

### 7.3 Composite PK and vector column

If the table has a composite PK `(id, time)` or `(uuid, time)`:
- The PK is a btree index — completely independent from the HNSW index
- Both indexes coexist peacefully
- The PK does not need to cover the vector column

---

## 8. IVFFlat vs HNSW Decision Matrix

| Factor | HNSW (selected) | IVFFlat (fallback, NOT selected) |
|--------|-----------------|----------------------------------|
| Query speed | Faster (3–5× vs IVFFlat) | Slower |
| Build time | Slower (minutes to hours) | Faster |
| Memory during build | Graph held in `maintenance_work_mem` | Lower (no graph) |
| Training step | None (build on empty table OK) | Requires `lists` param, data-dependent |
| Recall | Higher at comparable parameters | Lower, tunable via `probes` |
| Memory at query time | Graph should be resident | Lower |
| Index size | ~same as table | ~same as table |
| CONCURRENTLY support | Yes (pgvector 0.5.1+) | Yes |

**Verdict**: HNSW is the correct choice for P3-006. IVFFlat is only recommended for write-heavy or extremely memory-constrained workloads.

---

## 9. Complete Verification Checklist

Use this checklist during P3-006 auditor review:

- [ ] `pg_extension` shows `vector` with `extversion >= 0.5.0`
- [ ] Columns `episodes.embedding` and `semantic_facts.embedding` are typed `vector(1536)`
- [ ] No duplicate `embedding_vec` column exists alongside `embedding`
- [ ] `pg_indexes` shows both `ix_episodes_embedding_hnsw` and `ix_semantic_facts_embedding_hnsw`
- [ ] `indexdef` confirms `USING hnsw (embedding vector_cosine_ops)` on both
- [ ] `reloptions` on `pg_class` shows `m=16, ef_construction=128` (or index was dropped and recreated)
- [ ] `EXPLAIN (ANALYZE, BUFFERS)` shows `Index Scan` for cosine queries with `ORDER BY embedding <=> [...] LIMIT N`
- [ ] `Seq Scan` is NOT present for vector search queries
- [ ] Build-time notice about `hnsw graph no longer fits into maintenance_work_mem` was not observed (or was addressed)
- [ ] Hypertable partitioning column (`time`) is NOT included in the HNSW index (correct — not needed)
- [ ] Composite PK does not conflict with HNSW index

---

## 10. References

1. pgvector README — HNSW section: <https://github.com/pgvector/pgvector#hnsw>
2. pgvector README — CREATE INDEX CONCURRENTLY: <https://github.com/pgvector/pgvector#indexing>
3. pgvector build source (hnswbuild.c): <https://github.com/pgvector/pgvector/blob/master/src/hnswbuild.c>
4. Supabase HNSW docs: <https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes>
5. Neon pgvector optimization: <https://neon.com/docs/ai/ai-vector-search-optimization>
6. Timescale pgvector HNSW docs: <https://docs.timescale.com/ai/latest/sql-interface-for-pgvector-and-timescale-vector/>
7. DigitalOcean index tuning: <https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/index-and-tune/>
8. Crunchy Data — HNSW tradeoffs: <https://www.crunchydata.com/blog/hnsw-indexes-with-postgres-and-pgvector>
9. Timescale hypertable unique indexes: <https://github.com/timescale/docs/blob/latest/use-timescale/hypertables/hypertables-and-unique-indexes.md>
10. pgvectorscale Issue #134 — multi-column ANN: <https://github.com/timescale/pgvectorscale/issues/134>
11. pgvector Issue #844 — memory estimation: <https://github.com/pgvector/pgvector/issues/844>
12. pgvector Issue #409 — parallel builds: <https://github.com/pgvector/pgvector/issues/409>
13. pgvector Issue #745 — memory estimation formula: <https://github.com/pgvector/pgvector/issues/745>
14. pgvector Issue #569 — duplicate index name error with CONCURRENTLY: <https://github.com/pgvector/pgvector/issues/569>
15. DBI Services — pgvector DBA guide (2026): <https://www.dbi-services.com/blog/pgvector-a-guide-for-dba-part-2-indexes-update-march-2026/>
16. MonPG — HNSW monitoring/inspection: <https://monpg.app/pgvector-monitoring>
17. NerdLevelTech — pgvector production tuning (2026): <https://nerdleveltech.com/pgvector-hnsw-postgres-18-production-tuning-tutorial>
18. Queryplane — ef_search tuning: <https://queryplane.com/docs/blog/tuning-pgvector-query-accuracy>
19. pgvector test suite (HNSW): <https://github.com/pgvector/pgvector/blob/master/test/sql/hnsw_vector.sql>
20. Timescale pg-aiguide: <https://github.com/timescale/pg-aiguide/blob/main/skills/pgvector-semantic-search/SKILL.md>