# P3 Memory Foundation — Wave-2 Adversarial Read/Write Pipeline Audit

**Audit Date:** 2026-06-25
**Scope:** `src/memory/write_pipeline.py`, `src/memory/read_pipeline.py`, `src/memory/embeddings.py`, `src/memory/db.py`, `src/hermes/_memory_bridge.py`
**Method:** Adversarial code reading for correctness bugs in the read/write pipeline.

---

## (a) Embedding API DOWN — does store_episode fail-closed or silently write NULL/zero?

### Finding A-1: Write pipeline correctly fails-closed (raises, no NULL/zero vector)

**Severity:** [LOW] — Verified correct behavior; write pipeline DOES NOT write a NULL or zero vector on API failure.

**Evidence:** `src/memory/write_pipeline.py:188-195`:
```python
embedding: list[float] | None = None
if embedding_service is not None:
    embedding = await _compute_embedding(
        service=embedding_service,
        content=content,
        classification=classification,
        summary=summary,
    )
```

When `embedding_service` is `None`, `embedding` stays `None`. When the service is provided but the API is DOWN, `_compute_embedding` (line 298-316) calls `service.aembed()` which raises an exception after 6 retries with exponential backoff (`embeddings.py:684-695`). The exception propagates up through `store_episode`, and the episode is NOT written at all.

**Conclusion:** `store_episode` does NOT silently write a NULL or zero vector on API failure. It raises. This is fail-closed at the episode level: either the episode is written with a valid embedding, or no episode is written. Verified correct.

### Finding A-2: The HermesMemoryBridge ALWAYS passes embedding_service=None for writes

**Severity:** [MEDIUM] — Every conversation turn stored via the bridge has NULL embedding.

**Evidence:** `src/hermes/_memory_bridge.py:279-301`:
```python
# Always pass embedding_service=None for writes.
# 9Router has no embedding models; passing a live service
# causes _compute_embedding() to raise -> entire store crashes.
episode_id = await store_episode(
    session=session,
    ...
    embedding_service=None,
    ...
)
```

**Consequence for recall quality:** When the bridge is constructed with `embedding_service=None` (which is the default AND the documented pattern at line 301), the recall path (`recall_for_context`) passes `self._embedding_service` (which is `None`) to `recall_memories`. At `read_pipeline.py:889-895`:
```python
if embedding_service is not None:
    try:
        query_vector = await embedding_service.aembed(query_text_stripped)
    except Exception:
        _logger.warning("embedding_fallback_keyword", ...)
```

So both write and recall operate in FTS-only mode. This means ALL conversation memories stored through the bridge are only findable by full-text keyword search, never by semantic/vector similarity. This is an intentional architectural decision (documented at bridge line 279-283) but the recall quality degradation is significant: synonym matching, paraphrase matching, and conceptual similarity are all zero.

**Recommendation:** Document this as a known recall quality degradation more prominently. Consider a background backfill task to populate embeddings for bridge-stored episodes when a capable embedding provider becomes available.

### Finding A-3: Read pipeline gracefully degrades when embedding API is DOWN during recall

**Severity:** [LOW] — Verified correct.

**Evidence:** `src/memory/read_pipeline.py:889-895`:
```python
if embedding_service is not None:
    try:
        query_vector = await embedding_service.aembed(query_text_stripped)
    except Exception:
        _logger.warning("embedding_fallback_keyword", ...)
```

When the embedding API fails during recall, the query silently falls back to FTS-only search. `query_vector` stays `None`. At line 907-913, the vector query is only executed if `query_vector is not None`. This is a correct graceful degradation.

**Verdict:** PASS. No zero-vector pollution risk anywhere in the pipeline.

---

## (b) Batch Atomicity — does store_episode_batch partial-commit on error?

### Finding B-1: store_episode_batch has NO batch atomicity — partial commits are possible

**Severity:** [HIGH] — Episodes 1-4 of 10 will remain flushed if episode 5 fails.

**Evidence:** `src/memory/write_pipeline.py:245-277`:
```python
async def store_episode_batch(
    session: EpisodeSession,
    episodes: list[JsonObject],
    *,
    embedding_service: EmbeddingClient | None = None,
) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for ep_data in episodes:
        ep_id = await store_episode(
            session,
            content=_str_field(ep_data, "content"),
            ...
            embedding_service=embedding_service,
            started_at=_opt_dt_field(ep_data, "started_at"),
        )
        ids.append(ep_id)
    return ids
```

Each call to `store_episode` calls `session.add(episode)` then `session.flush()` (line 217-218). The flush sends the INSERT to the database within the current transaction. If episode 5 raises (e.g., `CriticalEmbeddingError` or `EmbeddingAPIError`), episodes 1-4 have already been flushed. Whether they persist depends on the caller's session management:

- If the caller uses `get_async_session()` from `db.py:91-112`, the exception causes the context manager's `except` block to call `session.rollback()`, which rolls back all flushed-but-uncommitted changes. So episodes 1-4 are rolled back.
- If the caller uses a raw `AsyncSession` without the context manager, flushed episodes could persist depending on the session's `autobegin` setting.

**Key problem:** `store_episode_batch` does NOT itself wrap the loop in a transaction or savepoint. The function's docstring does not warn about partial-commit risk.

### Finding B-2: store_episode_batch missing project_id forwarding

See section (g) for detailed analysis. This is a separate but related bug.

---

## (c) RRF/Recency/Importance Math

### Finding C-1: compute_rrf_score is correct — no division-by-zero possible

**Severity:** [COSMETIC] — Verified correct.

**Evidence:** `src/memory/read_pipeline.py:326-350`:
```python
def compute_rrf_score(
    vector_rank: int | None,
    fts_rank: int | None,
    k: int = RRF_K,
    ...
) -> tuple[float, int]:
    score = 0.0
    num_signals = 0
    if vector_rank is not None:
        score += vector_weight / (k + vector_rank)
        num_signals += 1
    if fts_rank is not None:
        score += fts_weight / (k + fts_rank)
        num_signals += 1
    return score, num_signals
```

`k` defaults to 60, `vector_rank` and `fts_rank` are 1-based (set at line 695-698 via `rank_idx + 1`), so the minimum denominator is `60 + 1 = 61`. No division-by-zero is possible. The `if ... is not None` guards ensure None ranks contribute 0.

### Finding C-2: normalize_importance docstring is stale — code clamps, does not "fall back to 0.5"

**Severity:** [LOW] — Docstring says "Falls back to 0.5" but code clamps to [0.1, 1.0].

**Evidence:** `src/memory/read_pipeline.py:353-358`:
```python
def normalize_importance(importance: int) -> float:
    """Normalise importance (1-10) to (0.1, 1.0).

    Falls back to 0.5 if value is out of range.
    """
    return max(0.1, min(1.0, importance / 10.0))
```

For `importance=0`, the result is `max(0.1, min(1.0, 0.0)) = 0.1`, not 0.5. The test at `test_read_pipeline_hybrid.py:353-355` verifies the clamping behavior. The docstring is stale/misleading but the implementation is correct and tested.

### Finding C-3: No NaN risk in the scoring math

**Severity:** [COSMETIC] — Verified safe.

The only floating-point operations are:
- `math.exp(...)` in `RecencyConfig.score()` (line 318): argument is always finite. `days_elapsed` is non-negative (clamped at line 314), `half_life_days_f` is guarded `> 0` (line 316-317). Safe.
- Division in `compute_rrf_score`: denominator is always `>= 61` (see C-1). Safe.
- `normalize_importance`: `importance / 10.0` — always finite. Safe.
- Combined score multiplication (line 760): `rrf_score * recency_boost * importance_boost` — all finite, non-negative floats. Safe.

### Finding C-4: importance_boost effective range is [0.55, 1.0]

**Severity:** [LOW] — Minor: minimum importance_boost is 0.55 (for importance=1), not 0.5.

**Evidence:** `src/memory/read_pipeline.py:757-758`:
```python
imp_norm = normalize_importance(importance_val)
importance_boost = 0.5 + 0.5 * imp_norm
```

For `importance=1`: `imp_norm = 0.1`, `importance_boost = 0.5 + 0.5 * 0.1 = 0.55`.
For `importance=10`: `imp_norm = 1.0`, `importance_boost = 0.5 + 0.5 * 1.0 = 1.0`.

The range is [0.55, 1.0]. This is not a bug — just slightly imprecise documentation.

---

## (d) MAX_CANDIDATE_POOL / EXPANDED_LIMIT_MULTIPLIER — OOM/Latency Risk

### Finding D-1: Constants are safe; MAX_CANDIDATE_POOL=200 caps unbounded growth

**Severity:** [LOW] — Verified safe.

**Evidence:** `src/memory/read_pipeline.py:63,154`:
```python
EXPANDED_LIMIT_MULTIPLIER: int = 3
MAX_CANDIDATE_POOL: int = 200
```

At `read_pipeline.py:901`:
```python
expanded_limit = min(limit * EXPANDED_LIMIT_MULTIPLIER, MAX_CANDIDATE_POOL)
```

With the default `limit=20`, `expanded_limit = min(60, 200) = 60`. Three queries (vector, FTS, recency) each return at most 200 rows. The `merged` dict deduplicates, so at most 600 unique episodes could enter the pool. 600 ORM objects is well within memory limits.

### Finding D-2: N+1 embedding calls in store_episode_batch are unbounded in latency

**Severity:** [MEDIUM] — When embedding_service is provided, each episode in the batch makes a separate HTTP call with its own retry loop.

**Evidence:** `src/memory/write_pipeline.py:261-275`: The loop calls `store_episode` for each episode, which calls `_compute_embedding` -> `service.aembed()`. The async variant at `embeddings.py:593-609` creates a NEW `httpx.AsyncClient` per call.

For a batch of N episodes, this means N sequential API calls. With `MAX_RETRIES=6` and exponential backoff up to 30 seconds per call, a batch of 10 episodes where the API is intermittently failing could take 10 * 6 * 30 = 1800 seconds (30 minutes) before giving up. There is no batch-level timeout.

**Note:** In practice, the HermesMemoryBridge always passes `embedding_service=None` for writes (Finding A-2), so this codepath is not exercised by the primary caller.

### Finding D-3: Async HTTP client created per-request (connection pooling bypassed)

**Severity:** [LOW] — Each `aembed()` call creates and destroys a new httpx.AsyncClient.

**Evidence:** `src/memory/embeddings.py:593-595`:
```python
async with httpx.AsyncClient(
    timeout=httpx.Timeout(self._config.timeout_seconds)
) as client:
```

The sync path reuses `self._http_client` (line 518), but the async path creates a new client per request. This bypasses httpx's connection pooling. For the read pipeline (one embedding per recall), this is acceptable. For batch writes with embedding, this is wasteful but not a correctness bug.

---

## (e) Session Lifecycle — async session leak, unawaited coroutine, connection pool exhaustion

### Finding E-1: HermesMemoryBridge.store_conversation explicit commit is necessary and correct

**Severity:** [LOW] — Verified correct but fragile.

**Evidence:** `src/hermes/_memory_bridge.py:278-307`:
```python
async with self._session_factory() as session:
    episode_id = await store_episode(session=session, ...)
    await session.commit()
```

`store_episode` calls `session.add(episode)` then `session.flush()`. The bridge uses `self._session_factory()` directly (NOT `get_async_session()` from db.py). The explicit `await session.commit()` at line 307 IS necessary because the session factory used by the bridge does not auto-commit.

If someone refactors the bridge to use `get_async_session()`, the double-commit would occur (that context manager also commits on clean exit at `db.py:109`). The bridge's comment at line 304-306 explains the necessity.

### Finding E-2: get_async_session context manager correctly rolls back on error

**Severity:** [COSMETIC] — Verified correct.

**Evidence:** `src/memory/db.py:91-112`:
```python
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

The pattern is correct: yield the session, commit on success, rollback and re-raise on error. No session leak possible.

### Finding E-3: Connection pool is small but adequate — no leak path found

**Severity:** [LOW] — pool_size=5, max_overflow=10 is fine for a single-user Discord bot.

**Evidence:** `src/memory/db.py:56-63`:
```python
_engine = create_async_engine(
    _db_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)
```

Total max connections = 5 + 10 = 15. `pool_pre_ping=True` handles stale connections. The lazy singleton pattern (global `_engine` at line 49) means the engine is created once and reused. No leak path found.

---

## (f) Recency Half-Life — Timezone/UTC Bugs

### Finding F-1: RecencyConfig correctly handles timezone-aware and naive datetimes

**Severity:** [LOW] — Verified correct; naive datetimes are assumed UTC.

**Evidence:** `src/memory/read_pipeline.py:292-318`:
```python
@property
def _ref(self) -> datetime:
    if self.reference_time is not None:
        return self.reference_time
    return datetime.now(timezone.utc)

def score(self, started_at: datetime | None) -> float:
    if started_at is None:
        return 0.0
    ref = self._ref
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    days_elapsed = (ref - started_at).total_seconds() / 86_400.0
    if days_elapsed < 0:
        days_elapsed = 0.0
```

The reference time defaults to `datetime.now(timezone.utc)` — always UTC-aware. Naive `started_at` datetimes from the database are stamped with UTC (line 309). Future timestamps (negative `days_elapsed`) are clamped to 0.

**Potential issue:** If a naive datetime from the database is actually in a non-UTC timezone, the code assumes UTC and will compute an incorrect `days_elapsed`. However, `store_episode` at `write_pipeline.py:198` sets `started_at = datetime.now(timezone.utc)` as the default, so all new episodes have UTC timestamps. Only pre-existing data from before P3 could have non-UTC naive timestamps.

---

## (g) store_episode_batch project_id — does it forward to each episode?

### Finding G-1: store_episode_batch does NOT forward project_id or project_scope

**Severity:** [HIGH] — Batch-written episodes are always project-unscoped, regardless of caller intent.

**Evidence:** `src/memory/write_pipeline.py:245-277`:
```python
async def store_episode_batch(
    session: EpisodeSession,
    episodes: list[JsonObject],
    *,
    embedding_service: EmbeddingClient | None = None,
) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for ep_data in episodes:
        ep_id = await store_episode(
            session,
            content=_str_field(ep_data, "content"),
            source=_str_field(ep_data, "source"),
            ...
            started_at=_opt_dt_field(ep_data, "started_at"),
        )
        ids.append(ep_id)
    return ids
```

The function signature has no `project_id` or `project_scope` parameters. The per-episode `store_episode` call does not pass `project_id` or `project_scope`, so they default to `None` and `"project"` respectively (write_pipeline.py:125-126). With `project_id=None`, the episode has no project tag.

**Impact:** If `ProjectScopedMemoryStore.store()` is used with `store_episode_batch` as the underlying function, the `scope_store_callable` wrapper injects `project_id` as a keyword argument, but `store_episode_batch` does NOT accept `project_id` as a keyword argument. This would cause a `TypeError` at runtime. Alternatively, if the caller passes `project_id` in each episode dict, `store_episode_batch` does not extract it.

**Affected callers:** No current caller passes `project_id` through `store_episode_batch`. But the bug is latent: any future caller attempting project-scoped batch writes will either get a `TypeError` or silently store unscoped episodes.

---

## (h) HermesMemoryBridge.store_conversation passes embedding_service=None — verify and trace consequences

### Finding H-1: Verified — embedding_service=None is hardcoded, not configurable for writes

**Severity:** [MEDIUM] — The bridge is architecturally committed to FTS-only writes regardless of constructor-time embedding_service.

**Evidence:** `src/hermes/_memory_bridge.py:279-301`:
```python
# Always pass embedding_service=None for writes.
# 9Router has no embedding models; passing a live service
# causes _compute_embedding() to raise -> entire store crashes.
episode_id = await store_episode(
    session=session,
    ...
    embedding_service=None,  # <-- hardcoded
    ...
)
```

The constructor accepts `embedding_service` at line 74 and stores it at line 90. This service IS used for the READ path (`recall_for_context` at line 161). But the WRITE path at line 301 ignores it and hardcodes `None`.

**Traced consequences for recall quality:**

1. **Write path:** All bridge-stored episodes have `embedding = NULL` in the database.
2. **Read path with `embedding_service=None` (default):** `recall_memories` gets `embedding_service=None`, skips vector query entirely. Only FTS and recency signals are used.
3. **Read path with `embedding_service=some_service` (custom constructor):** `recall_memories` gets the live service and performs vector similarity on the QUERY, but the vector query (read_pipeline.py:555-559: `Episodes.embedding.isnot(None)`) filters out all bridge-stored episodes because their `embedding` IS NULL.

**Net effect:** The bridge is FTS-only by design. This is correct for the stated constraint ("9Router has no embedding models") but creates a recall quality gap that widens as the episode count grows.

---

## Additional Adversarial Findings

### Finding I-1: _is_safe_mode_blocked_content tag matching has a false-positive risk with list/tuple/set types

**Severity:** [MEDIUM] — List/tuple/set tags are serialized as a single string, causing substring false positives.

**Evidence:** `src/memory/read_pipeline.py:393-394`:
```python
elif isinstance(tags_raw, (list, tuple, set)):
    tags_lower.add(f"{tags_raw}".lower())
```

When `tags_raw` is a list like `["emotional", "personal"]`, this converts the ENTIRE list to its Python string representation: `"['emotional', 'personal']"`. Then at lines 395-398, the `blocked in tag` check is a substring match against this single serialized string.

**Correct behavior for list:** Each element should be checked individually:
```python
elif isinstance(tags_raw, (list, tuple, set)):
    for item in tags_raw:
        tags_lower.add(str(item).strip().lower())
```

**Impact:** Tags containing substrings of blocked words (e.g., "emotional_intelligence_workshop") would be incorrectly blocked in safe mode. The test at `test_safe_mode_memory.py:143-144` passes `tags=["emotional"]` (a list with one element), and the serialization produces `"['emotional']"` which does contain "emotional" — so the test passes despite the bug. But with multi-element lists, the behavior is unpredictable.

### Finding I-2: Substring matching for blocked tags is overly aggressive

**Severity:** [LOW] — Tags like "not_emotional" would be blocked.

**Evidence:** `src/memory/read_pipeline.py:397`:
```python
if blocked in tag:
    return True
```

This uses Python's `in` operator for substring matching, not exact match. The tag `"not_emotional"` would match the blocked word `"emotional"`. This is by design but means safe-mode blocking is broader than strictly necessary.

### Finding J-1: Token budget order of operations is correct

**Severity:** [COSMETIC] — Verified correct order.

**Evidence:** `src/memory/read_pipeline.py:1078-1124`:
1. Classification ceiling filter (line 1078-1096)
2. Limit to requested count (line 1099)
3. Build safe_content (line 1101-1121)
4. Token budget enforcement (line 1124)

The order is correct: ceiling first, then limit, then safe_content, then budget.

### Finding K-1: EmbeddingService async path creates new httpx.AsyncClient per call

**Severity:** [LOW] — Each request properly closes the client via `async with`, no leak, but inefficient.

**Evidence:** `src/memory/embeddings.py:593-609`: The `async with` ensures the client is closed after each request. No actual connection leak occurs. But creating and destroying a client per request bypasses HTTP keep-alive. For the read pipeline (one embedding per recall), this is negligible.

---

## Summary Table

| # | Finding | Severity | File:Line | Bug? |
|---|---------|----------|-----------|------|
| A-1 | Write pipeline correctly fails-closed (raises, no NULL/zero vector) | LOW | write_pipeline.py:188-195 | No |
| A-2 | Bridge always passes embedding_service=None for writes | MEDIUM | _memory_bridge.py:279-301 | Design decision, quality gap |
| A-3 | Read pipeline gracefully degrades on embedding API failure | LOW | read_pipeline.py:889-895 | No |
| B-1 | store_episode_batch has no batch atomicity | HIGH | write_pipeline.py:260-275 | Yes — partial commit risk |
| B-2 | store_episode_batch missing project_id forwarding | HIGH | write_pipeline.py:245-277 | Yes — see G-1 |
| C-1 | RRF math is correct, no division-by-zero | COSMETIC | read_pipeline.py:326-350 | No |
| C-2 | normalize_importance docstring is stale | LOW | read_pipeline.py:353-358 | Doc bug only |
| C-3 | No NaN risk in scoring | COSMETIC | read_pipeline.py:760 | No |
| C-4 | importance_boost range is [0.55, 1.0] | LOW | read_pipeline.py:757-758 | Doc imprecision |
| D-1 | MAX_CANDIDATE_POOL=200 caps pool growth | LOW | read_pipeline.py:154,901 | No |
| D-2 | N+1 embedding calls in batch (no batch-level timeout) | MEDIUM | write_pipeline.py:261-275 | Latency risk |
| D-3 | Async HTTP client created per-request | LOW | embeddings.py:593-595 | Inefficiency |
| E-1 | Double-commit risk if bridge refactored to use get_async_session | MEDIUM | _memory_bridge.py:307 | Fragile, correct today |
| E-2 | get_async_session correctly rolls back on error | COSMETIC | db.py:91-112 | No |
| E-3 | Connection pool is adequate | LOW | db.py:56-63 | No |
| F-1 | Recency half-life handles timezones correctly | LOW | read_pipeline.py:292-318 | No |
| G-1 | store_episode_batch does NOT forward project_id | HIGH | write_pipeline.py:245-277 | Yes — confirmed bug |
| H-1 | Bridge hardcoded embedding_service=None for writes | MEDIUM | _memory_bridge.py:301 | Design, quality gap |
| I-1 | Safe-mode tag matching false-positive with list serialization | MEDIUM | read_pipeline.py:393-394 | Yes — serialization bug |
| I-2 | Substring matching for blocked tags is overly aggressive | LOW | read_pipeline.py:397 | By design, but broad |
| J-1 | Token budget order of operations is correct | COSMETIC | read_pipeline.py:1078-1124 | No |
| K-1 | Async httpx client per-request is inefficient but not leaked | LOW | embeddings.py:593-595 | No |

---

## Status Verdict

**3 HIGH findings, 4 MEDIUM findings, 9 LOW findings, 4 COSMETIC findings.**

### HIGH findings (require action):

1. **B-1 + G-1: `store_episode_batch` has no batch atomicity and no `project_id`/`project_scope` forwarding.** The function is a sequential loop over `store_episode` with no transaction wrapping, no savepoints, and no project-scoping parameters. If any episode in the batch raises, earlier episodes may or may not persist depending on the caller's session management. The function cannot be used with `ProjectScopedMemoryStore.store()` without a `TypeError`.

### MEDIUM findings (should fix):

1. **A-2 + H-1: Bridge is FTS-only for writes.** All conversation memories are stored without embeddings, making them findable only by keyword matching. This is documented and intentional but creates a widening recall quality gap.
2. **D-2: N+1 embedding calls in batch with no batch-level timeout.** Latency risk if a live embedding service is passed to `store_episode_batch`.
3. **E-1: Double-commit fragility in bridge.** Correct today but fragile under refactoring.
4. **I-1: `_is_safe_mode_blocked_content` tag serialization bug.** List/tuple/set tags are converted to a single string representation instead of being iterated element-by-element, causing substring false positives.

### Recommendations:
- Fix `store_episode_batch` to accept and forward `project_id` and `project_scope`, and document the atomicity semantics clearly.
- Fix `_is_safe_mode_blocked_content` to iterate list/tuple/set tags element-by-element instead of serializing to a single string.
- Consider adding a batch-level timeout or batch embedding API call for future batch writes with embedding.
- Correct the stale docstring on `normalize_importance`.
