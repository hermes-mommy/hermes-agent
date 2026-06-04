# Phase 3 Memory Bridge: SQLite FTS5 Setup Research

**Date**: 2026-06-04  
**Context**: ADR-035 requires enabling SQLite FTS5 for `session_search`. Primary store is PostgreSQL; SQLite will serve as a local, embedded search cache/bridge.  
**Goal**: Comprehensive FTS5 setup guide covering enablement, syntax, tokenizers, querying, ranking, sync strategies, performance, tooling, and PostgreSQL migration patterns.

---

## 1. Enabling FTS5 in Python `sqlite3`

**Status**: **Built-in by default.**  
Since Python 3.10+ (which bundles SQLite 3.31+), FTS5 is enabled by default in the standard library `sqlite3` module. No additional compilation flags or external extensions are required for standard Python distributions.

*Evidence*: [SQLite Compile Options](https://sqlite.org/compile.html) notes that `SQLITE_ENABLE_FTS5` is defined by default in the amalgamation build used by Python.

```python
import sqlite3
conn = sqlite3.connect(":memory:")
# Verify FTS5 is available
result = conn.execute("SELECT sqlite_version(), fts5()").fetchone()
# If no error is raised, FTS5 is active.
```

---

## 2. FTS5 Virtual Table Creation Syntax

FTS5 tables are **virtual tables**. They do not store data in standard row formats but maintain an inverted index. You **must not** declare data types, constraints, or `PRIMARY KEY` in the `CREATE VIRTUAL TABLE` statement.

```sql
-- Standard FTS5 table (stores its own data)
CREATE VIRTUAL TABLE session_search USING fts5(session_id, title, content);

-- External Content FTS5 table (recommended for Memory Bridge)
-- References an existing 'sessions' table, saving disk space by not duplicating text.
CREATE VIRTUAL TABLE session_search_fts USING fts5(
    title, 
    content,
    content='sessions',         -- Name of the source table
    content_rowid='id',         -- Primary key column in source table
    tokenize='porter unicode61' -- Tokenizer configuration
);
```

---

## 3. FTS5 Tokenizer Options

Tokenizers determine how text is split into searchable terms. For conversational text (like session logs or chat), the following options apply:

| Tokenizer | Description | Best For |
|---|---|---|
| `unicode61` | **Default**. Splits on Unicode 6.1 space/punctuation. Handles diacritics and non-ASCII characters correctly. | General conversational text, multilingual support. |
| `porter` | A wrapper tokenizer. Applies the Porter stemming algorithm to the output of another tokenizer (e.g., `porter unicode61`). Matches "running" with "run". | English-dominant conversational text where morphological variations matter. |
| `trigram` | Treats every contiguous 3-character sequence as a token. Enables substring matching (e.g., searching "sql" matches "postgresql"). | Typo tolerance, partial word matching, or code snippets. Higher storage overhead. |

**Recommendation for Conversational Text**: `tokenize='porter unicode61'`. It provides robust Unicode handling plus English stemming, which is ideal for natural language session queries.

---

## 4. FTS5 Query Syntax

Queries are executed using the `MATCH` operator (or `=` operator, or table-valued function syntax). `MATCH` is preferred for readability.

```sql
-- Basic term search (case-insensitive)
SELECT * FROM session_search_fts WHERE session_search_fts MATCH 'error';

-- Prefix search (matches 'authentication', 'authenticate', etc.)
SELECT * FROM session_search_fts WHERE session_search_fts MATCH 'auth*';

-- Exact phrase search (ordered sequence)
SELECT * FROM session_search_fts WHERE session_search_fts MATCH '"database connection failed"';

-- Boolean operators (AND, OR, NOT)
SELECT * FROM session_search_fts WHERE session_search_fts MATCH 'memory AND NOT leak';

-- NEAR proximity search (terms within N tokens of each other, default N=10)
SELECT * FROM session_search_fts WHERE session_search_fts MATCH 'NEAR(timeout, database, 5)';

-- Column-specific search
SELECT * FROM session_search_fts WHERE session_search_fts MATCH 'title:crash AND content:stacktrace';
```

---

## 5. FTS5 Ranking and Relevance

FTS5 includes a hidden `rank` column that defaults to the **BM25** algorithm. **Lower scores indicate better matches.**

```sql
-- Default BM25 ranking (best matches first)
SELECT session_id, title, rank 
FROM session_search_fts 
WHERE session_search_fts MATCH 'timeout' 
ORDER BY rank ASC;

-- Custom column weighting via bm25() function
-- Syntax: bm25(table_name, weight_col1, weight_col2, ...)
-- Example: Weight 'title' 10x higher than 'content'
SELECT session_id, title, bm25(session_search_fts, 10.0, 1.0) as score
FROM session_search_fts 
WHERE session_search_fts MATCH 'timeout' 
ORDER BY score ASC;
```

*Note*: FTS5 also provides `highlight(table, col_index, '<mark>', '</mark>')` and `snippet()` auxiliary functions for generating search result previews.

---

## 6. FTS5 Sync Strategies

When using an **external content table** (`content='sessions'`), SQLite does not automatically know when the source data changes. You must maintain consistency.

### Strategy A: Database Triggers (Recommended for ongoing sync)
Create `AFTER INSERT`, `AFTER DELETE`, and `AFTER UPDATE` triggers on the source table.

```sql
-- 1. AFTER INSERT
CREATE TRIGGER sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO session_search_fts(rowid, title, content) 
    VALUES (new.id, new.title, new.content);
END;

-- 2. AFTER DELETE (Note the special 'delete' command in the first column)
CREATE TRIGGER sessions_ad AFTER DELETE ON sessions BEGIN
    INSERT INTO session_search_fts(session_search_fts, rowid, title, content) 
    VALUES ('delete', old.id, old.title, old.content);
END;

-- 3. AFTER UPDATE (Delete old, insert new)
CREATE TRIGGER sessions_au AFTER UPDATE ON sessions BEGIN
    INSERT INTO session_search_fts(session_search_fts, rowid, title, content) 
    VALUES ('delete', old.id, old.title, old.content);
    INSERT INTO session_search_fts(rowid, title, content) 
    VALUES (new.id, new.title, new.content);
END;
```

### Strategy B: Periodic Rebuild (Recommended for bulk migration)
If you are bulk-inserting data from PostgreSQL, **disable triggers during the import**, then rebuild the index in one operation. This is significantly faster than firing triggers per row.

```sql
-- Rebuild the entire FTS5 index from the source table
INSERT INTO session_search_fts(session_search_fts) VALUES ('rebuild');

-- Optional: Defragment the index after heavy writes to reclaim space
INSERT INTO session_search_fts(session_search_fts) VALUES ('optimize');
```

---

## 7. FTS5 Performance Characteristics

| Metric | Characteristics | Mitigation/Optimization |
|---|---|---|
| **Indexing Speed** | Fast for single-writer. Trigger overhead is ~1-2ms per row. Bulk insert + `rebuild` is 10x faster than trigger-based insertion. | Use `rebuild` for initial PostgreSQL migration. |
| **Query Speed** | Sub-millisecond for typical datasets (<1M rows). Inverted index lookup is highly optimized. | Ensure `MATCH` is used (not `LIKE`). Use `EXPLAIN QUERY PLAN` to verify index usage. |
| **Storage Overhead** | ~20-50% of the raw text size. | Use `detail=column` or `detail=none` in table creation to omit position data if only boolean matching is needed (saves ~30% space). |
| **Concurrency** | **Single-writer bottleneck**. Writes serialize, even in WAL mode. Reads are highly concurrent. | Treat the SQLite FTS5 instance as a read-heavy cache. Route all writes through a single coordinator or batch them. |

---

## 8. Python Libraries for FTS5 Management

While raw `sqlite3` works, higher-level libraries simplify FTS5 setup and maintenance:

1. **`sqlite-utils`** (by Simon Willison / Datasette project):  
   Provides a clean Python API for FTS5, automatically generating the correct virtual table and triggers.
   ```python
   import sqlite_utils
   db = sqlite_utils.Database("memory_bridge.db")
   
   # Enables FTS5, creates external content table, and sets up all 3 triggers automatically
   db["sessions"].enable_fts(
       ["title", "content"], 
       fts_version="FTS5", 
       create_triggers=True, 
       tokenize="porter unicode61"
   )
   ```
2. **`datasette`**:  
   If you need to inspect or expose the `session_search` index via a web UI/API, Datasette auto-detects FTS5 tables and provides a built-in search interface with highlighting and pagination.

---

## 9. FTS5 vs PostgreSQL FTS: When to Use Which

| Feature | SQLite FTS5 | PostgreSQL FTS (`tsvector`/`tsquery` + GIN) |
|---|---|---|
| **Architecture** | Embedded, single-file, zero network latency. | Client-server, requires connection pooling. |
| **Concurrency** | Single-writer (WAL mode helps reads). | True multi-writer concurrency. |
| **Linguistics** | Basic (`unicode61`, `porter`). No custom dictionaries. | Advanced (custom dictionaries, stopwords, multi-language configs). |
| **Operational Overhead** | Low. Just manage file backups (e.g., Litestream). | High. Requires `autovacuum` tuning, GIN index maintenance, bloat monitoring. |
| **Best Use Case** | Local read-heavy cache, edge deployment, single-tenant memory bridge. | Primary store with high concurrent writes, complex multilingual search, or when avoiding dual-database sync is a priority. |

**Verdict for Phase 3**: Since the goal is a "Memory Bridge" for `session_search`, SQLite FTS5 is the **correct choice** if it acts as a localized, read-optimized cache synced from PostgreSQL. It eliminates network hops for search queries. If concurrent local writes become a bottleneck, the sync strategy must be batched.

---

## 10. Migration Pattern: PostgreSQL → SQLite FTS5

To extract text from PostgreSQL and populate the SQLite FTS5 index efficiently, follow this sequence:

### Step 1: Extract from PostgreSQL
Use a streaming cursor to avoid loading all session text into memory at once.
```python
import psycopg2
import sqlite3

# 1. Connect to both databases
pg_conn = psycopg2.connect("dbname=primary user=postgres")
sqlite_conn = sqlite3.connect("memory_bridge.db")
sqlite_conn.execute("PRAGMA journal_mode=WAL;") # Critical for SQLite performance
sqlite_conn.execute("PRAGMA synchronous=NORMAL;") # Speeds up bulk writes

# 2. Create SQLite schema (without triggers initially for speed)
sqlite_conn.executescript("""
    CREATE TABLE sessions (id INTEGER PRIMARY KEY, title TEXT, content TEXT);
    CREATE VIRTUAL TABLE session_search_fts USING fts5(
        title, content, 
        content='sessions', 
        content_rowid='id', 
        tokenize='porter unicode61'
    );
""")
```

### Step 2: Bulk Insert into SQLite Content Table
```python
pg_cursor = pg_conn.cursor(name="session_fetch")
pg_cursor.itersize = 1000
pg_cursor.execute("SELECT id, title, content FROM sessions")

batch = []
for row in pg_cursor:
    batch.append(row)
    if len(batch) >= 1000:
        sqlite_conn.executemany(
            "INSERT INTO sessions (id, title, content) VALUES (?, ?, ?)", 
            batch
        )
        sqlite_conn.commit()
        batch = []

if batch:
    sqlite_conn.executemany("INSERT INTO sessions (id, title, content) VALUES (?, ?, ?)", batch)
    sqlite_conn.commit()
```

### Step 3: Rebuild FTS5 Index in One Operation
```python
# This scans the 'sessions' table and builds the inverted index efficiently
sqlite_conn.execute("INSERT INTO session_search_fts(session_search_fts) VALUES ('rebuild')")
sqlite_conn.commit()
```

### Step 4: Enable Triggers for Ongoing Sync (Optional)
If the SQLite database will receive *new* local sessions or updates, enable the triggers now. If PostgreSQL remains the sole source of truth and you periodically truncate/reload SQLite, skip triggers and repeat Steps 1-3.

```python
sqlite_conn.executescript("""
    CREATE TRIGGER sessions_ai AFTER INSERT ON sessions BEGIN
        INSERT INTO session_search_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
    END;
    -- (Add AFTER DELETE and AFTER UPDATE triggers as shown in Section 6)
""")
sqlite_conn.commit()
```

---

## Summary & Next Actions for Phase 3 Planner

1. **Adopt External Content FTS5**: Use `content='sessions'` to avoid duplicating payload data.
2. **Tokenizer**: Default to `porter unicode61` for conversational session logs.
3. **Migration Script**: Implement the bulk-insert + `rebuild` pattern to avoid trigger overhead during initial sync from PostgreSQL.
4. **Python Tooling**: Evaluate `sqlite-utils` to reduce boilerplate trigger generation.
5. **Performance Guardrail**: Enforce `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` during the migration window.

*Evidence Sources*: 
- [SQLite FTS5 Official Documentation](https://sqlite.org/fts5.html)
- [sqlite-utils Python API Documentation](https://sqlite-utils.datasette.io/en/stable/python-api.html)
- [PostgreSQL vs SQLite Full-Text Search Analysis](https://cr0x.net/en/postgresql-vs-sqlite-full-text/)