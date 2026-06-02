# Async Memory Pipeline Architecture Research

> **Research Date**: 2026-06-02
> **Scope**: P3-009 (conversation → episodic hypertable write) & P3-010 (query → hybrid ranking read)
> **Purpose**: Authoritative pattern catalog for async Python memory pipeline using SQLAlchemy asyncio/asyncpg, SentenceTransformers, PostgreSQL vector (pgvector) + FTS

---

## Table of Contents

1. [SQLAlchemy AsyncSession Architecture](#1-sqlalchemy-asyncsession-architecture)
2. [asyncpg Bulk Insert Patterns](#2-asyncpg-bulk-insert-patterns)
3. [SentenceTransformers Non-Blocking Inference](#3-sentencetransformers-non-blocking-inference)
4. [pgvector + PostgreSQL FTS Hybrid Search](#4-pgvector--postgresql-fts-hybrid-search)
5. [Strict Typing Patterns](#5-strict-typing-patterns)
6. [Safety: SQL Injection Prevention & Retry Boundaries](#6-safety-sql-injection-prevention--retry-boundaries)
7. [Structured Logging & Resource Throttling](#7-structured-logging--resource-throttling)
8. [Transaction Patterns & Boundaries](#8-transaction-patterns--boundaries)
9. [Testability Patterns](#9-testability-patterns)
10. [Architecture Decision Record](#10-architecture-decision-record)

---

## 1. SQLAlchemy AsyncSession Architecture

### 1.1 Engine & Session Factory Setup

**Source**: [SQLAlchemy 2.0 AsyncIO Docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

The canonical async pipeline uses three layers:

```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
```

**Engine configuration** — create once at application startup:

```python
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host:5432/dbname",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,  # Use structured logging instead
)
```

Key parameters:
- `pool_size`: Permanent connections (default 5; tune to concurrent worker count)
- `max_overflow`: Burst connections allowed beyond pool_size (default 10)
- `pool_pre_ping`: Verify connection health before checkout — critical for long-lived workers
- `pool_recycle`: Recycle connections after N seconds (prevent stale connection drops)
- Using `AsyncAdaptedQueuePool` automatically (no `threading.Lock`) — compatible with asyncio

**Source**: [SQLAlchemy Pooling Docs](https://docs.sqlalchemy.org/en/20/core/pooling.html)

### 1.2 async_sessionmaker Factory

```python
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # CRITICAL: prevents lazy-loading errors in async context
    autoflush=False,         # Explicit control over flush boundaries
)
```

**Why `expire_on_commit=False`**: In async contexts, session.commit() normally expires all ORM objects. Accessing expired attributes triggers lazy-loading (synchronous IO), which raises errors under asyncio. Setting `False` keeps objects usable after commit.

**Source**: Multiple docs confirm this pattern — [FastAPI + SQLAlchemy 2.0](https://leapcell.io/blog/building-high-performance-async-apis-with-fastapi-sqlalchemy-2-0-and-asyncpg), [OneUptime guide](https://oneuptime.com/blog/post/2026-01-27-sqlalchemy-fastapi/view), [nunacode blog](https://medium.com/python-how-to/sqlalchemy-2-0-async-workflows-494fecffd28f)

### 1.3 Session Lifecycle with Dependency Injection

**Best practice — explicit transaction with rollback guard**:

```python
from typing import AsyncGenerator

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Alternative — auto-commit via context manager**:

```python
async with AsyncSessionFactory.begin() as session:
    session.add(some_object)
    # commits transaction, closes session on exit
```

**Source**: [SQLAlchemy AsyncIO Docs — Transactional Context](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), [Session Lifecycle guide](https://async-workflows.com/mastering-sqlalchemy-20-core-and-orm-architecture/session-lifecycle-and-scope-management/)

### 1.4 Concurrent Task Safety

**Rule**: One `AsyncSession` instance per task. Do NOT share across `asyncio.gather()`.

```python
# ✅ CORRECT: Each task gets its own session
async with asyncio.TaskGroup() as tg:
    for chunk in chunks:
        tg.create_task(process_chunk(chunk))  # process_chunk creates its own session

# ❌ WRONG: Shared session across concurrent tasks
# async with AsyncSessionFactory() as session:
#     results = await asyncio.gather(*[task(session) for task in tasks])
```

**Source**: [SQLAlchemy 2.0 — Using AsyncSession with Concurrent Tasks](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

### 1.5 async_scoped_session (for request-scoped sessions)

Only when session must be scoped to a request/coroutine without explicit passing:

```python
from asyncio import current_task
from sqlalchemy.ext.asyncio import async_scoped_session

scoped_session = async_scoped_session(
    AsyncSessionFactory,
    scopefunc=current_task,
)
```

**Source**: [SQLAlchemy AsyncIO — scoped session](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), but note the docs advise: "It is generally not a good idea to use the 'scoped' pattern for new development."

---

## 2. asyncpg Bulk Insert Patterns

### 2.1 Performance Hierarchy

From fastest to slowest, based on benchmarks from [Jacopo Farina's insert benchmarks](https://jacopofarina.eu/posts/ingest-data-into-postgres-fast/) and [asyncpg GitHub issue #346](https://github.com/MagicStack/asyncpg/issues/346):

| Method | Speed | Supports RETURNING | Best For |
|--------|-------|--------------------|----------|
| `copy_records_to_table()` | ~3700+ rows/sec | No (COPY protocol) | Initial bulk load, no-ID-needed inserts |
| `executemany()` with prepared stmt | ~3700 rows/sec | No (discards results) | Batch inserts w/ parameterization |
| `fetch()` with `unnest()` | Fast | ✅ Yes | When RETURNING ids is needed |
| Individual INSERT | Slow (30s for 120k rows) | ✅ Yes | Never for bulk |

### 2.2 copy_records_to_table — Fastest Bulk Insert

**Source**: [asyncpg API Reference](https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.Connection.copy_records_to_table)

Uses PostgreSQL binary COPY protocol — **nearly 1M rows/second** on single connection per [SQLAlchemy issue #11710](https://github.com/sqlalchemy/sqlalchemy/issues/11710).

```python
# Simple direct insert
await conn.copy_records_to_table(
    'episodic_memory',
    records=[
        (msg_id, embedding, content, metadata, created_at),
        (msg_id2, embedding2, content2, metadata2, created_at2),
    ],
    columns=['message_id', 'embedding', 'content', 'metadata', 'created_at'],
)

# Async generator for streaming large datasets
async def record_generator(items):
    for item in items:
        yield (item.message_id, item.embedding, item.content, item.metadata, item.created_at)

await conn.copy_records_to_table(
    'episodic_memory',
    records=record_generator(items),
    columns=['message_id', 'embedding', 'content', 'metadata', 'created_at'],
)
```

**Limitations**:
- Does NOT support `RETURNING` — cannot get auto-generated IDs
- Does NOT support `ON CONFLICT` — use temp table pattern for upserts
- Record order must match table column order (or specify `columns`)

**Upsert workaround** (source: [Schinckel.net](https://schinckel.net/2019/12/13/asyncpg-and-upserting-bulk-data/)):

```python
await conn.execute('CREATE TEMPORARY TABLE _temp (LIKE episodic_memory INCLUDING DEFAULTS)')
await conn.copy_records_to_table('_temp', records=data, columns=['msg_id', 'embedding', 'content'])
await conn.execute('''
    INSERT INTO episodic_memory (msg_id, embedding, content)
    SELECT * FROM _temp
    ON CONFLICT (msg_id)
    DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
    WHERE episodic_memory.content <> EXCLUDED.content
''')
```

### 2.3 executemany — Parameterized Bulk Insert

**Source**: [asyncpg Pool docs](https://magicstack.github.io/asyncpg/current/api/index.html)

Best when prepared statement caching is desired (not for pgbouncer transaction mode):

```python
await conn.executemany(
    'INSERT INTO episodic_memory (message_id, embedding, content) VALUES ($1, $2, $3)',
    [(id1, emb1, txt1), (id2, emb2, txt2)],
    timeout=30.0,
)
```

**pgbouncer compatibility note** ([asyncpg issue #1219](https://github.com/MagicStack/asyncpg/issues/1219)):
Set `statement_cache_size=0` when using pgbouncer transaction pooling to avoid prepared-statement errors.

### 2.4 RETURNING with Bulk Insert (unnest pattern)

**Source**: [Stack Overflow asyncpg best answer](https://stackoverflow.com/questions/43739123/best-way-to-insert-multiple-rows-with-asyncpg)

When IDs are needed:

```python
results = await conn.fetch('''
    INSERT INTO episodic_memory (message_id, embedding, content)
    SELECT * FROM unnest($1::uuid[], $2::vector(384)[], $3::text[])
    RETURNING id
''', message_ids, embeddings_array, contents)
```

**Note**: Requires explicit PostgreSQL type casting — must match actual column types.

### 2.5 SQLAlchemy Bulk Insert Mappings

For ORM-level bulk inserts (slower than raw asyncpg but simpler):

```python
# ✅ bulk_insert_mappings (sync session only, accessible via run_sync)
session.bulk_insert_mappings(MemoryModel, list_of_dicts)

# ✅ ORM bulk via add_all (with chunking)
session.add_all([
    MemoryModel(message_id=id1, embedding=emb1, content=txt1)
    for id1, emb1, txt1 in batch
])
await session.flush()
```

**Source**: [DEV Community — SQLAlchemy Bulk Operations](https://dev.to/uaslimcreate/sqlalchemy-bulk-operations-for-ai-feature-analytics-writing-10k-eventssecond-without-database-5el3)

### 2.6 Recommendation for P3-009 (Write Pipeline)

| Use Case | Method | Rationale |
|----------|--------|-----------|
| Initial bulk history load | `copy_records_to_table()` | Fastest, no RETURNING needed |
| Live conversation writes | ORM `add_all()` + flush | Clean ORM integration, auto-ID |
| High-throughput batch | raw `executemany()` | ~3700 rows/sec, parameterized |
| Upsert (dedup) | Temp table + COPY + ON CONFLICT | Handles existing embeddings |

---

## 3. SentenceTransformers Non-Blocking Inference

### 3.1 The Problem: Blocking the Event Loop

`SentenceTransformer.encode()` is CPU-bound (PyTorch tensor ops) and blocks the event loop. A single `.encode()` call on 512-token text takes **50-500ms** on CPU.

### 3.2 Solution: ThreadPoolExecutor Offloading

**Source**: [Python docs — Developing with asyncio](https://docs.python.org/3/library/asyncio-dev.html), [EngineersOfAI guide](https://engineersofai.com/docs/python/python-intermediate/concurrency/ThreadPoolExecutor)

#### Recommended Pattern: Dedicated ThreadPoolExecutor

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    """Thread-safe embedding service that does not block the event loop."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        max_workers: int = 1,
        device: str = "cpu",
    ):
        # Load model ONCE in main thread before creating executor
        # (avoids per-call reload + tokenizer race conditions)
        self.model = SentenceTransformer(model_name, device=device)
        # Single-worker executor: PyTorch is already internally parallelized
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        # Environment tuning prevents CPU thrash
        os.environ["OMP_NUM_THREADS"] = str(max_workers)
        os.environ["MKL_NUM_THREADS"] = str(max_workers)

    async def encode(self, texts: list[str]) -> list[list[float]]:
        """Non-blocking embedding generation via thread offload."""
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            self._executor,
            self.model.encode,
            texts,
        )
        # SentenceTransformer returns np.ndarray; convert to list of lists
        return embeddings.tolist()

    async def close(self):
        self._executor.shutdown(wait=True)
```

**Key insights**:
- Use `max_workers=1` for single-CPU inference — PyTorch's internal parallelism saturates 1 core
- Use `max_workers=N` for multi-CPU inference (matches `OMP_NUM_THREADS=1` per worker)
- Load model **once** in constructor, not per-request
- Set `OMP_NUM_THREADS` and `TOKENIZERS_PARALLELISM=false` to avoid thread thrashing

**Source**: [Dask SentenceTransformer fix](https://www.technetexperts.com/fix-dask-sentence-transformer-stuck/) — confirms this exact pattern for event-loop safety.

### 3.3 Alternative: asyncio.to_thread() (Python 3.9+)

Simpler but uses the default executor (shared across all callers):

```python
embeddings = await asyncio.to_thread(self.model.encode, texts)
return embeddings.tolist()
```

✅ Pros: Simpler API, context-variable propagation  
⚠️ Cons: Shares default executor, can't control pool sizing

### 3.4 ProcessPoolExecutor Alternative

For pure CPU-bound work, ProcessPoolExecutor bypasses GIL entirely:

```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
    loop = asyncio.get_running_loop()
    embeddings = await loop.run_in_executor(pool, self.model.encode, texts)
```

⚠️ Warning: Model pickling overhead may negate gains for small batches. Only beneficial for large batches (>100 texts).

### 3.5 Memory Leak Concern

**Source**: [SentenceTransformers issue #1854](https://github.com/UKPLab/sentence-transformers/issues/1854)

When running `model.encode()` inside threads, some models (specific tokenizers) may leak memory. Mitigations:
- Use `all-MiniLM-L6-v2` (no leak) over `paraphrase-multilingual-MiniLM-L12-v2` (leak)
- Test with long-running workloads before production deployment
- Consider `model.to('cpu')` + `torch.no_grad()` context
- Periodically recreate the model if memory grows unbounded

### 3.6 Timeout Guard

Prevent indefinite blocking:

```python
async def encode_with_timeout(self, texts, timeout=30.0):
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(self._executor, self.model.encode, texts)
    try:
        result = await asyncio.wait_for(future, timeout=timeout)
        return result.tolist()
    except asyncio.TimeoutError:
        logger.error("Embedding timed out after %ss for %d texts", timeout, len(texts))
        raise
```

### 3.7 Recommendation for P3-009/010

| Component | Pattern | Rationale |
|-----------|---------|-----------|
| Embedding model init | Constructor, `OSThread` level | Once at startup |
| Per-call encode | `run_in_executor(dedicated_pool, ...)` | Isolates from event loop |
| Pool sizing | `max_workers=1` (single core) or `=cpu_count()` (multi) | Match PyTorch parallelism |
| Timeout | `asyncio.wait_for(future, timeout=30)` | Prevents hung pipeline |
| Memory safety | Prefer leak-free models; test under load | See issue #1854 |

---

## 4. pgvector + PostgreSQL FTS Hybrid Search

### 4.1 pgvector with asyncpg

**Source**: [pgvector asyncpg integration](https://deepwiki.com/pgvector/pgvector-python/4.3-asyncpg-integration)

**Registration required before vector operations**:

```python
from pgvector.asyncpg import register_vector

async with pool.acquire() as conn:
    await register_vector(conn)  # Must call per-connection
    await conn.execute(
        "INSERT INTO episodic_memory (embedding) VALUES ($1)",
        embedding_vector  # list or numpy array
    )
```

**For connection pools**: Register vector in `setup` callback:

```python
pool = await asyncpg.create_pool(
    dsn,
    min_size=5,
    max_size=20,
    setup=register_vector,  # Called on each new connection
)
```

**SQLAlchemy integration**:

```python
from pgvector.sqlalchemy import Vector

class EpisodicMemory(Base):
    __tablename__ = "episodic_memory"

    id: Mapped[int] = mapped_column(primary_key=True)
    embedding = mapped_column(Vector(384))  # all-MiniLM-L6-v2 dimension
    content: Mapped[str] = mapped_column(Text)
    # ...
```

### 4.2 Full-Text Search with Generated tsvector

**Source**: [DEV Community — Hybrid Search with RRF](https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk)

```sql
ALTER TABLE episodic_memory
    ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(content, ''))
    ) STORED;

CREATE INDEX idx_memory_fts ON episodic_memory USING gin(search_vector);
CREATE INDEX idx_memory_vector ON episodic_memory
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);
```

### 4.3 Vector Similarity Search (P3-010 Read)

```python
from sqlalchemy import select, func, text

async def vector_search(
    session: AsyncSession,
    query_embedding: list[float],
    workspace_id: uuid.UUID,
    limit: int = 20,
) -> list[SearchResult]:
    stmt = (
        select(
            EpisodicMemory.id,
            EpisodicMemory.content,
            (1 - EpisodicMemory.embedding.cosine_distance(query_embedding)).label("similarity"),
        )
        .where(EpisodicMemory.workspace_id == workspace_id)
        .order_by(EpisodicMemory.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    results = await session.execute(stmt)
    return [
        SearchResult(
            chunk_id=row.id,
            content=row.content,
            score=float(row.similarity),
        )
        for row in results
    ]
```

### 4.4 Full-Text Search (P3-010 Read)

```python
async def fulltext_search(
    session: AsyncSession,
    query: str,
    workspace_id: uuid.UUID,
    limit: int = 20,
) -> list[SearchResult]:
    ts_query = func.plainto_tsquery("english", query)
    stmt = (
        select(
            EpisodicMemory.id,
            EpisodicMemory.content,
            func.ts_rank(EpisodicMemory.search_vector, ts_query).label("relevance"),
        )
        .where(
            EpisodicMemory.workspace_id == workspace_id,
            EpisodicMemory.search_vector.op("@@")(ts_query),
        )
        .order_by(func.ts_rank(EpisodicMemory.search_vector, ts_query).desc())
        .limit(limit)
    )
    results = await session.execute(stmt)
    return [
        SearchResult(
            chunk_id=row.id,
            content=row.content,
            score=float(row.relevance),
        )
        for row in results
    ]
```

### 4.5 Reciprocal Rank Fusion (Hybrid Merge)

**Source**: [DEV Community guide](https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk)

Combines vector and FTS scores without normalization:

```python
def reciprocal_rank_fusion(
    result_lists: list[list[SearchResult]],
    k: int = 60,
) -> list[SearchResult]:
    rrf_scores: dict[uuid.UUID, float] = {}
    results_by_id: dict[uuid.UUID, SearchResult] = {}

    for result_list in result_lists:
        for rank, result in enumerate(result_list, start=1):
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0.0) + 1.0 / (k + rank)
            results_by_id[result.chunk_id] = result

    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
    return [results_by_id[cid] for cid in sorted_ids]
```

### 4.6 Parallel Execution (P3-010)

```python
async def hybrid_search(
    session: AsyncSession,
    query: str,
    query_embedding: list[float],
    workspace_id: uuid.UUID,
    limit: int = 10,
) -> list[SearchResult]:
    semantic, fts = await asyncio.gather(
        vector_search(session, query_embedding, workspace_id, limit=limit * 2),
        fulltext_search(session, query, workspace_id, limit=limit * 2),
    )
    fused = reciprocal_rank_fusion([semantic, fts])
    return fused[:limit]
```

### 4.7 HNSW vs IVFFlat Decision

| Property | HNSW | IVFFlat |
|----------|------|---------|
| Build time | Slower (graph construction) | Fast (k-means centroids) |
| Query speed | Faster (log n) | Depends on probes |
| Recall | Better (no probe tuning) | Requires probe tuning |
| Memory | Higher (graph edges) | Lower |
| Best for | Production RAG | Development/benchmarking |

**Recommendation**: Use **HNSW** for P3-010. Better recall without probe tuning — critical for query accuracy.

---

## 5. Strict Typing Patterns

### 5.1 SQLAlchemy 2.0 Mapped Types

**Source**: [SQLAlchemy 2.0 What's New](https://docs.sqlalchemy.org/changelog/whatsnew_20.html)

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey

class EpisodicMemory(Base):
    __tablename__ = "episodic_memory"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("conversations.id"))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))  # type-aware
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

**No mypy plugin needed** in SQLAlchemy 2.0 — `Mapped[]` is PEP 484 compliant.

### 5.2 AsyncSession Type Annotations

**Source**: [SQLAlchemy discussion #10113](https://github.com/sqlalchemy/sqlalchemy/discussions/10113)

❗ **Common pitfall**: `async_sessionmaker` returns a variable, not a type. For type annotations, use `AsyncSession` directly:

```python
from sqlalchemy.ext.asyncio import AsyncSession

# ✅ Correct type annotation
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    ...

# ✅ Or import as alias to avoid confusion
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
async def get_session() -> AsyncGenerator[_AsyncSession, None]:
    ...
```

The return type of `async_sessionmaker` is correctly inferred since [commit e43e240](https://github.com/sqlalchemy/sqlalchemy/commit/e43e240a0088ac429eb551c7ea1c537c266b4853):
```python
factory = async_sessionmaker(engine)
# Revealed type: async_sessionmaker[AsyncSession]
session = factory()
# Revealed type: AsyncSession
```

### 5.3 Pydantic + ORM Models

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class MemoryWrite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: uuid.UUID
    content: str
    embedding: list[float] | None = None
    metadata: dict | None = None

class MemoryRead(MemoryWrite):
    id: int
    workspace_id: uuid.UUID
    created_at: datetime
```

### 5.4 Forbidden Type Practices

| Pattern | Verdict | Alternative |
|---------|---------|-------------|
| `as Any` | ❌ Forbidden | Use `Mapped[list[float] | None]` |
| `@ts-ignore` | ❌ Forbidden | Correct type annotation |
| `# type: ignore` | ❌ Forbidden (except mypy plugin migration) | Fix root cause |
| `Any` for embedding return | ❌ Forbidden | `list[float]` or `numpy.typing.NDArray` |

---

## 6. Safety: SQL Injection Prevention & Retry Boundaries

### 6.1 NEVER Use f-Strings in SQL

**Source**: [pgvector RAG article](https://codeawake.com/blog/postgresql-vector-database), [FastAPI + SQLAlchemy production guide](https://dev.to/ayush_kaushik_b450595c233/fastapi-sqlalchemy-20-in-production-building-high-performance-async-apis-11ni)

```python
# ❌ DANGEROUS: SQL injection vulnerability
vector_str = f"[{','.join(map(str, embedding))}]"
await conn.execute(f"INSERT INTO t (v) VALUES ({vector_str})")

# ✅ SAFE: Parameterized query
await conn.execute(
    "INSERT INTO t (v) VALUES ($1::vector)",
    embedding,  # asyncpg auto-handles list/numpy to vector conversion
)

# ✅ SAFE: SQLAlchemy ORM
session.add(MemoryModel(embedding=embedding))  # ORM handles escaping

# ✅ SAFE: pgvector register_vector handles conversion
await register_vector(conn)
await conn.execute(
    "INSERT INTO t (embedding) VALUES ($1)",
    embedding,  # list → vector via registered codec
)
```

**Static rule**: If you see `$`, `%s`, or `?` as placeholders → ✅ safe. If you see `{` or `}+`.join → ❌ likely unsafe.

### 6.2 Vector Parameter Safety

When storing vectors, use typed parameters, never string construction:

```python
# ✅ SAFE: pgvector with asyncpg (registered type)
await conn.execute(
    "INSERT INTO memory (embedding) VALUES ($1)",
    embedding_vector,  # Python list → PostgreSQL vector via registered codec
)

# ✅ SAFE: pgvector with SQLAlchemy
from pgvector.sqlalchemy import Vector

class Memory(Base):
    embedding = mapped_column(Vector(384))

# ORM handles type serialization
memory = Memory(embedding=embedding_list)
session.add(memory)
```

**Source**: [pgvector-python asyncpg docs](https://deepwiki.com/pgvector/pgvector-python/4.3-asyncpg-integration)

### 6.3 Retry Boundaries

**Exponential backoff for transient failures**:

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from asyncpg import PostgresError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(PostgresError),
    before_sleep=lambda retry_state: logger.warning(
        "DB retry %d after %s", retry_state.attempt_number, retry_state.outcome.exception()
    ),
)
async def write_memory(session: AsyncSession, memory_data: dict) -> MemoryModel:
    """Write memory with automatic retry on transient DB errors."""
    model = MemoryModel(**memory_data)
    session.add(model)
    await session.flush()
    return model
```

**What NOT to retry** (idempotency matters):
- ✅ `INSERT ... ON CONFLICT DO NOTHING` — safe to retry
- ✅ `SELECT` — always safe
- ❌ Plain `INSERT` without conflict handling — may create duplicates
- ❌ `DELETE` without idempotent filter — may delete wrong rows on partial success

### 6.4 Error Classification

| Error Type | Action | Retry? |
|------------|--------|--------|
| `asyncpg.exceptions.DeadlockDetectedError` | Retry | ✅ 3 attempts |
| `asyncpg.exceptions.SerializationError` | Retry | ✅ 3 attempts |
| `asyncpg.exceptions.UniqueViolationError` | Handle (upsert) | ❌ No retry |
| `asyncpg.exceptions.DataError` | Fix input | ❌ Bug |
| `asyncio.TimeoutError` | Retry or escalate | ⚠️ Depends |
| `sqlalchemy.exc.IntegrityError` | Handle (conflict logic) | ❌ No retry |

---

## 7. Structured Logging & Resource Throttling

### 7.1 Structured Logging Integration

**Pattern**: Use Python `structlog` or standard `logging` with JSON formatting. **Never** `print()` or `logging.debug()` in production.

```python
import structlog

logger = structlog.get_logger(__name__)

# In write pipeline
async def write_batch(session, batch):
    start = time.monotonic()
    try:
        session.add_all(batch)
        await session.flush()
        elapsed = time.monotonic() - start
        logger.info("memory_batch_written", count=len(batch), elapsed_ms=round(elapsed * 1000, 1))
    except Exception:
        elapsed = time.monotonic() - start
        logger.error("memory_batch_failed", count=len(batch), elapsed_ms=round(elapsed * 1000, 1))
        raise
```

**Fields to log**:
- Operation name (e.g., `memory_write`, `memory_search`, `embedding_generate`)
- Duration (ms)
- Count/size
- Error type (if failed)
- Correlation ID (traceable to request)
- NEVER log embedding vectors (high-dim data = noise)

### 7.2 Resource Throttling Patterns

#### Connection Pool Sizing

| Worker Type | Pool Size | Max Overflow | Rationale |
|-------------|-----------|--------------|-----------|
| Write-heavy (P3-009) | 10-20 | 5 | Bulk inserts hold connections longer |
| Read-heavy (P3-010) | 20-30 | 10 | Fast queries, more concurrency |
| Mixed | 15-20 | 10 | Balanced |

#### Embedding Queue Throttle

Prevent embedding service from overwhelming CPU/RAM:

```python
import asyncio

class ThrottledEmbedder:
    def __init__(self, model, max_concurrent: int = 2):
        self.model = model
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def encode(self, texts: list[str]) -> list[list[float]]:
        async with self._semaphore:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(self._executor, self.model.encode, texts)
            return result.tolist()
```

#### Batch Size Throttle

```python
# Write pipeline: flush in chunks of 500
BATCH_SIZE = 500
MAX_WAIT_SECONDS = 5

class MemoryBuffer:
    def __init__(self, batch_size: int = 500, max_wait: int = 5):
        self.buffer: list[dict] = []
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.last_flush = time.monotonic()

    async def add(self, session: AsyncSession, data: dict) -> None:
        self.buffer.append(data)
        if len(self.buffer) >= self.batch_size or \
           (time.monotonic() - self.last_flush) > self.max_wait:
            await self._flush(session)

    async def _flush(self, session: AsyncSession) -> None:
        if not self.buffer:
            return
        batch = self.buffer[:]
        self.buffer.clear()
        self.last_flush = time.monotonic()
        session.add_all([MemoryModel(**d) for d in batch])
        await session.flush()
        logger.info("buffer_flushed", count=len(batch))
```

### 7.3 Engine Disposal on Shutdown

```python
# FastAPI lifespan pattern
@asynccontextmanager
async def lifespan(app):
    # startup
    engine = create_async_engine(...)
    yield
    # shutdown
    await engine.dispose()
```

**Source**: [FastAPI + SQLAlchemy production guide](https://dev.to/ayush_kaushik_b450595c233/fastapi-sqlalchemy-20-in-production-building-high-performance-async-apis-11ni)

---

## 8. Transaction Patterns & Boundaries

### 8.1 Explicit Transaction Pattern (Recommended for P3)

```python
async with AsyncSessionFactory() as session:
    async with session.begin():  # BEGIN
        session.add_all(objects)
        # auto-commits on exit, rolls back on exception
```

**This is the safest pattern**: transaction boundary is explicit, rollback is automatic, session is always closed.

### 8.2 Nested Transactions (Savepoints)

```python
async with session.begin_nested():  # SAVEPOINT
    session.add(some_object)
    # Rollback only this savepoint on error
```

### 8.3 Transaction Isolation for Concurrent Writes

Each concurrent write task should own its session+transaction:

```python
async def write_chunk(text: str, embedding: list[float]) -> None:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            session.add(MemoryModel(content=text, embedding=embedding))
            await session.flush()
```

### 8.4 Read-Only Transactions

```python
# Read-only with explicit isolation level
async with engine.connect() as conn:
    await conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    result = await conn.execute(select(...))
```

For P3-010 read pipeline, use READ ONLY to signal PostgreSQL no-write intent.

---

## 9. Testability Patterns

### 9.1 Dependency Injection for Sessions

```python
# Production
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session

# Test override
async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionFactory(bind=test_engine) as session:
        yield session
```

### 9.2 Inject Embedding Service

```python
from typing import Protocol
import numpy as np

class Embedder(Protocol):
    async def encode(self, texts: list[str]) -> list[list[float]]:
        ...

class FakeEmbedder:
    """Deterministic fake for tests: returns dim-sized zero vector."""

    async def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

class RealEmbedder:
    """Wraps SentenceTransformer with thread pool offloading."""

    async def encode(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(self._executor, self._model.encode, texts)
        return embeddings.tolist()
```

### 9.3 Test Session Fixture

```python
@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost:5432/testdb")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

### 9.4 Testable Pipeline Composition

```python
class MemoryWritePipeline:
    def __init__(self, session_factory, embedder, logger):
        self._session_factory = session_factory
        self._embedder = embedder
        self._logger = logger

    async def write(self, conversation_id: uuid.UUID, content: str) -> int:
        embedding = await self._embedder.encode([content])
        async with self._session_factory() as session:
            async with session.begin():
                mem = MemoryModel(conversation_id=conversation_id, content=content, embedding=embedding[0])
                session.add(mem)
                await session.flush()
                self._logger.info("memory_written", id=mem.id)
                return mem.id
```

---

## 10. Architecture Decision Record

### Key Decisions for P3-009/P3-010

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **ORM vs Raw SQL** | SQLAlchemy ORM for writes; raw asyncpg for bulk reads | ORM gives type safety + schema management; bulk via raw for speed |
| **Bulk insert method** | `session.add_all()` with chunked flush (500/batch) | Clean ORM integration; easily testable; auto-ID support |
| **Embedding model loading** | Process-global singleton with dedicated `ThreadPoolExecutor(1)` | Avoids per-request model load; offload blocks event loop |
| **Vector column type** | `pgvector.sqlalchemy.Vector(384)` | Native PostgreSQL type; HNSW indexable; type-safe through ORM |
| **FTS column** | `tsvector` GENERATED ALWAYS AS (STORED) | Zero application maintenance; always in sync; indexable via GIN |
| **Hybrid search merge** | RRF with k=60 | No score normalization needed; proven (84% recall improvement) |
| **Transaction pattern** | `async with session.begin()` | Explicit boundaries; auto rollback on exception |
| **Connection pool** | `AsyncAdaptedQueuePool` (default with async engine) | Asyncio-native; no threading.Lock |
| **SQL injection prevention** | Parameterized queries + ORM | Never f-string SQL; never string-concatenated vector literals |
| **Logging** | structlog with JSON format | Structured; machine-parseable; no embedding data in logs |
| **Type safety** | `Mapped[]` + Pydantic models | No `Any`; no `# type: ignore`; mypy strict mode compatible |

### Version Pin Recommendations

```toml
# pyproject.toml
[project]
dependencies = [
    "sqlalchemy[asyncio]>=2.0.35,<3.0",
    "asyncpg>=0.29.0,<1.0",
    "pgvector>=0.3.0,<1.0",
    "sentence-transformers>=3.0,<4.0",
    "structlog>=24.0,<25.0",
    "tenacity>=9.0,<10.0",
]
```

**asyncpg note**: Pin `asyncpg<0.29.0` if using SQLAlchemy 2.0.x (some reports of incompatibility with `create_async_engine` on 0.29.0+). For 2.1+, latest asyncpg should be fine.

---

## References

| Source | URL |
|--------|-----|
| SQLAlchemy AsyncIO Docs | https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html |
| SQLAlchemy Pooling | https://docs.sqlalchemy.org/en/20/core/pooling.html |
| asyncpg API Reference | https://magicstack.github.io/asyncpg/current/api/index.html |
| asyncpg Bulk Insert Issue | https://github.com/MagicStack/asyncpg/issues/346 |
| pgvector asyncpg Integration | https://deepwiki.com/pgvector/pgvector-python/4.3-asyncpg-integration |
| pgvector SQLAlchemy Integration | https://deepwiki.com/pgvector/pgvector-python/3.1-sqlalchemy-integration |
| SentenceTransformers Memory Leak | https://github.com/UKPLab/sentence-transformers/issues/1854 |
| Dask + SentenceTransformers Fix | https://www.technetexperts.com/fix-dask-sentence-transformer-stuck/ |
| Hybrid Search + RRF Guide | https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk |
| SQLAlchemy 2.0 Typing Fix | https://github.com/sqlalchemy/sqlalchemy/commit/e43e240a0088ac429eb551c7ea1c537c266b4853 |
| SQLAlchemy AsyncSession Typing | https://github.com/sqlalchemy/sqlalchemy/discussions/10113 |
| FastAPI + SQLAlchemy 2.0 (2026) | https://dev.to/ayush_kaushik_b450595c233/fastapi-sqlalchemy-20-in-production-building-high-performance-async-apis-11ni |
| Batch insert performance benchmark | https://jacopofarina.eu/posts/ingest-data-into-postgres-fast/ |
| Upsert via COPY + temp table | https://schinckel.net/2019/12/13/asyncpg-and-upserting-bulk-data/ |
| asyncio + ThreadPoolExecutor guide | https://engineersofai.com/docs/python/python-intermediate/concurrency/ThreadPoolExecutor |
| SQLAlchemy Bulk Operations | https://dev.to/uaslimcreate/sqlalchemy-bulk-operations-for-ai-feature-analytics-writing-10k-eventssecond-without-database-5el3 |

---

*Research document generated for P3-009/P3-010 async memory pipeline architecture. This document contains zero secrets, zero code in repo, and adheres to all consent-safety and type-safety constraints.*