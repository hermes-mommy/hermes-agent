# P3 Memory Foundation — Read/Write Pipeline Correctness Audit

**Audit ID:** P3-wave-1-read-write-pipeline
**Date:** 2026-06-25
**Scope:** `src/memory/write_pipeline.py`, `src/memory/read_pipeline.py`, `src/memory/embeddings.py`, `src/hermes/_memory_bridge.py`, `src/memory/models.py`, `src/memory/spaced_repetition.py`, downstream callers
**Methodology:** Full source read, cross-reference against docstring contracts, caller analysis, adversarial scenario tracing

---

## Executive Summary

The P3 memory read/write pipelines are **implemented and structurally sound**. Fail-closed guards, DNR filtering, classification ceilings, safe-mode content substitution, token budget enforcement, and hybrid RRF ranking are all present and correct. However, there is one **critical design defect** in the main conversational write path (HermesMemoryBridge always passes `embedding_service=None`), two **medium-severity bugs** in batch writes and KG-episode ID join, and several **low-severity** issues around FSRS signal design and commit lifecycle. The pipelines are safe for production use in FTS-only mode, but the 5-signal RRF claim is not fully materialized for the primary write path.

**Status Verdict:** `IMPLEMENTED WITH BUGS`

---

## Files Audited

| File | Lines | Role |
|---|---|---|
| `src/memory/write_pipeline.py` | 369 | store_episode, store_episode_batch, classification guards |
| `src/memory/read_pipeline.py` | 1198 | recall_memories, hybrid ranking, safe-mode, token budget |
| `src/memory/embeddings.py` | 775 | EmbeddingService, redaction, classification hierarchy |
| `src/hermes/_memory_bridge.py` | 362 | HermesMemoryBridge — main conversational agent entry point |
| `src/memory/models.py` | 1285 | Episodes ORM model, FSRS columns, search_vector |
| `src/memory/spaced_repetition.py` | 603 | FSRSScheduler, retrievability formula, episode adapter |

---

## Findings Table

| # | Finding | Severity | File:Line | Status |
|---|---------|----------|-----------|--------|
| F-01 | HermesMemoryBridge.store_conversation passes embedding_service=None — all conversational episodes have embedding=NULL, 5-signal RRF collapses to FTS-only | [CRITICAL] | `_memory_bridge.py:279-301` | Confirmed design defect |
| F-02 | store_episode_batch does not forward project_id or project_scope | [MEDIUM] | `write_pipeline.py:260-277` | Confirmed omission |
| F-03 | KG rank map keys are fact_ids, joined against episode_ids — mismatch causes silent no-op | [MEDIUM] | `read_pipeline.py:962-1023` | Confirmed design flaw |
| F-04 | FSRS retrievability signal uses fixed rank=1 for all episodes — differentiates only by retrievability value, not ranking position | [LOW] | `read_pipeline.py:1050-1066` | Design choice, not bug |
| F-05 | FSRS update_episode_state mutates ORM objects without explicit flush — relies on session auto-commit lifecycle | [LOW] | `read_pipeline.py:1033-1066` | Latent lifecycle risk |
| F-06 | FTS query hardcoded to English text search configuration | [LOW] | `read_pipeline.py:591` | Limits non-English recall |
| F-07 | Token budget excludes episode metadata (id, classification, importance, timestamps) from token count | [LOW] | `read_pipeline.py:493-523` | Underestimates actual token usage |
| F-08 | _is_safe_mode_blocked_content stringifies tags list as repr — substring matching unreliable | [LOW] | `read_pipeline.py:394` | May miss or false-match tags |
| F-09 | store_episode flushes but never commits — caller must commit or data is silently lost | [LOW] | `write_pipeline.py:217-218` | Documented, but risky for new callers |
| F-10 | cmd_memory_add.py and hermes memory_add.py do not commit session explicitly | [LOW] | `cmd_memory_add.py:387-396`, `hermes memory_add.py:91-100` | Relies on session factory auto-commit |
| F-11 | Embedding API down → write silently skips embedding (embedding=NULL) — recall degrades to FTS-only without alert | [LOW] | `write_pipeline.py:189-195` | Graceful but silent |
| F-12 | Episodes model has composite ORM primary_key=(id, started_at) but pipelines treat id as sole key | [COSMETIC] | `models.py:111-117` | Works in practice, ORM quirk |
| F-13 | No content-level dedup on write — repeated conversations stored as separate episodes | [COSMETIC] | `write_pipeline.py:111-237` | By design for episodic memory |
| F-14 | EmbeddingService instances created fresh per invocation in Discord/Hermes memory-add | [COSMETIC] | `cmd_memory_add.py:385`, `hermes memory_add.py:89` | Wasteful but functional |

---

## Detailed Findings

### F-01 [CRITICAL] HermesMemoryBridge always passes embedding_service=None

**Location:** `src/hermes/_memory_bridge.py:279-301`

**Evidence:**
```python
# Lines 279-284 (comment block):
# Always pass embedding_service=None for writes.
# 9Router has no embedding models; passing a live service
# causes _compute_embedding() to raise → entire store crashes.
# Episodes are persisted without embedding vectors (FTS-only
# recall).  A backfill job can generate embeddings later when
# a capable provider is configured.

# Line 301:
embedding_service=None,
```

**Impact:** Every episode written via the main conversational agent (the primary write path — every Discord message, every Hermes chat turn) is stored with `embedding=NULL`. This means:

1. `build_vector_query()` at `read_pipeline.py:557` filters `Episodes.embedding.isnot(None)`, so ALL conversational episodes are invisible to the vector similarity signal.
2. The 5-signal RRF fusion (vector + FTS + recency + KG + FSRS) effectively collapses to 3-signal (FTS + recency + KG) or even 2-signal (FTS + recency) for conversational memories.
3. The `BOTH_SIGNAL_BONUS` (1.25x multiplier at `read_pipeline.py:144`) can never apply to conversational episodes, since they can never appear in the vector results.
4. The "backfill job" mentioned in the comment (`_memory_bridge.py:283`) does not appear to exist in the codebase — no evidence of a backfill command or scheduled task for generating missing embeddings.

**Confirmation of the task's "KEY GAP" claim:** Verified. The comment at line 279 explicitly acknowledges this is intentional due to "9Router has no embedding models", but the consequence is that the main write path is FTS-only by design.

**Downstream callers that DO get embeddings:**
- `src/discord/cmd_memory_add.py:385-396` — creates `EmbeddingService()` and passes it to `store_episode()`
- `src/hermes_plugins/commands_memory/memory_add.py:89-100` — same pattern

So manual `/memory-add` commands get embeddings, but the main conversational flow does not.

**Severity justification:** CRITICAL because the core recall path for conversational context is degraded from 5-signal hybrid to 2-3 signal FTS-dominant, directly impacting recall quality for the primary use case.

---

### F-02 [MEDIUM] store_episode_batch does not forward project_id or project_scope

**Location:** `src/memory/write_pipeline.py:260-277`

**Evidence:**
```python
async def store_episode_batch(
    session: EpisodeSession,
    episodes: list[JsonObject],
    *,
    embedding_service: EmbeddingClient | None = None,
) -> list[uuid.UUID]:
    # ...
    for ep_data in episodes:
        ep_id = await store_episode(
            session,
            content=_str_field(ep_data, "content"),
            source=_str_field(ep_data, "source"),
            classification=_str_field(ep_data, "classification", RESTRICTED),
            importance=_int_field(ep_data, "importance", 5),
            title=_opt_str_field(ep_data, "title"),
            summary=_opt_str_field(ep_data, "summary"),
            episode_type=_str_field(ep_data, "episode_type", "conversation"),
            tags=_opt_list_field(ep_data, "tags"),
            metadata=_opt_dict_field(ep_data, "metadata"),
            embedding_service=embedding_service,
            started_at=_opt_dt_field(ep_data, "started_at"),
            # NOTE: project_id and project_scope are NOT forwarded
        )
```

**Impact:** `store_episode()` accepts `project_id` and `project_scope` parameters (`write_pipeline.py:125-126`), but `store_episode_batch()` never extracts or forwards them from the `ep_data` dict. Any batch caller that sets `"project_id"` in the dict will have it silently ignored. Episodes stored via batch are always global-scoped.

This is a P19 (multi-project namespace) integration gap. The P19 wrapper `ProjectScopedMemoryStore` at `src/projects/memory_store.py:63-83` wraps `store_episode` individually but `store_episode_batch` bypasses that wrapper entirely.

**Severity justification:** MEDIUM because batch writes are not the primary write path (conversational flow uses `store_episode` directly), but any future batch import tool will silently produce global-scoped episodes.

---

### F-03 [MEDIUM] KG rank map uses fact_ids but is joined against episode_ids

**Location:** `src/memory/read_pipeline.py:962-1023`

**Evidence:**
```python
# Lines 962-975: KG returns {fact_id: graph_score}
_graph_scores = await _kg_fusion_obj.compute_graph_scores(
    query_text_stripped, top_k=expanded_limit,
)
# Builds: {str(fact_id): rank}
kg_rank_map = {
    str(fact_id): rank
    for rank, (fact_id, _) in enumerate(_ordered_facts, start=1)
}

# Lines 1011-1019: Looked up by episode_id
for r in scored:
    ep_id = str(r.get("id", ""))  # This is an episode UUID
    kg_rank = kg_rank_map.get(ep_id)  # Looking up episode_id in fact_id map
```

**Impact:** The KG module (`KGRRFFusion.compute_graph_scores`) returns scores keyed by `fact_id` (UUIDs from `memory.kg_edges.source_fact_id`), but the RRF adjustment loop looks up by `episode.id` (UUIDs from `memory.episodes.id`). These are different ID spaces. Unless facts and episodes happen to share the same UUID (which would be a coincidence), `kg_rank_map.get(ep_id)` will always return `None`, making the entire KG signal a no-op.

The `kg_enabled=True` path will log `kg_recall_signal_failed` or silently produce a non-empty `kg_rank_map`, but the join against episode IDs will fail to match, so no episode ever receives a KG boost.

**Severity justification:** MEDIUM because the KG signal is optional (default `kg_enabled=False` in `recall_memories`, line 799), so the core pipeline is unaffected. But when enabled, it silently contributes nothing.

---

### F-04 [LOW] FSRS retrievability signal uses fixed rank=1 for all episodes

**Location:** `src/memory/read_pipeline.py:1050-1066`

**Evidence:**
```python
# Line 1059: rank is hardcoded to 1
fsrs_signal = FSRS_WEIGHT * retrievability / (RRF_K + 1)
```

**Impact:** All episodes receive the same FSRS rank (1), so the RRF denominator `RRF_K + 1 = 61` is identical for all. The only differentiator is the `retrievability` attribute (0.0-1.0). This means FSRS functions as a weighted importance boost rather than a true RRF rank signal. High-retrievability episodes get a slightly higher combined_score bonus, but the signal cannot rank episodes relative to each other.

For comparison, the vector and FTS signals use proper 1-based rank positions, where rank 1 gets a much higher RRF contribution than rank 10.

**Severity justification:** LOW because the effect size is tiny (max `0.15 * 1.0 / 61 = 0.00246`, compared to vector rank-1 `0.5 / 61 = 0.00820`), and the signal primarily serves as a mild retrievability-based tiebreaker.

---

### F-05 [LOW] FSRS update_episode_state mutates ORM objects without explicit flush

**Location:** `src/memory/read_pipeline.py:1033-1066`

**Evidence:**
```python
# Lines 1037-1048: ORM mutation inside recall path
_fsrs_scheduler = FSRSScheduler()
for r in scored:
    ep_id = str(r.get("id", ""))
    cand_entry = merged.get(ep_id)
    if cand_entry is not None:
        episode = cand_entry.episode
        _fsrs_scheduler.update_episode_state(episode, GRADE_GOOD)
```

**Impact:** `FSRSScheduler.update_episode_state()` (spaced_repetition.py:525-587) sets ORM attributes like `episode.fsrs_state`, `episode.last_reviewed_at`, `episode.retrievability` etc. These are in-memory mutations on the ORM objects loaded by the recall query. There is no explicit `session.flush()` or `session.commit()` within the recall path.

The mutations persist only if the session's context manager auto-commits on exit. In the `HermesMemoryBridge.recall_for_context` flow (`_memory_bridge.py:152-163`), the `async with self._session_factory() as session:` block exits after recall returns, and the `AsyncSessionFactory` protocol (which maps to SQLAlchemy's `async_sessionmaker`) auto-commits on successful exit. So in practice this works.

However, if a caller passes a session that does NOT auto-commit (e.g., manual session management), the FSRS mutations are silently lost.

**Severity justification:** LOW because the primary caller (HermesMemoryBridge) uses auto-commit session factories, and the `getattr` defensive writes in spaced_repetition.py:562-585 prevent crashes even when attributes are missing.

---

### F-06 [LOW] FTS query hardcoded to English

**Location:** `src/memory/read_pipeline.py:591`

**Evidence:**
```python
fts_query = func.plainto_tsquery("english", query_text)
```

**Impact:** All FTS queries use the `'english'` PostgreSQL text search configuration. Non-English content (e.g., Indonesian text common in this codebase based on persona strings like "Mommy simpan catatannya, Darling") will not be properly stemmed or stop-word filtered, reducing FTS recall quality for multilingual content.

The `search_vector` computed column in the model (`models.py:29-33`) also uses `'english'`:
```python
EPISODES_SEARCH_VECTOR_EXPRESSION = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || ..."
)
```

This is consistent (both write and read use English), but limits recall for non-English queries.

**Severity justification:** LOW because the limitation is consistent (both sides use English), and the primary content language appears to be English-based with Indonesian phrases as persona flavor.

---

### F-07 [LOW] Token budget underestimates actual token usage

**Location:** `src/memory/read_pipeline.py:493-523`

**Evidence:**
```python
def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN  # 4 chars per token

def apply_token_budget(results, budget):
    for r in results:
        safe_content = str(r.get("safe_content", ""))
        estimated = estimate_tokens(safe_content)
        # Only counts safe_content tokens
```

**Impact:** The token budget counts only `safe_content` characters. Each result dict also contains `id` (36-char UUID string), `classification`, `importance`, `created_at` (datetime), `combined_score` (float), and `is_summarized` (bool). When these are serialized to JSON for the LLM context window, they add approximately 80-100 tokens per result that are not counted against the budget.

With the default `token_budget=4000` and `CHARS_PER_TOKEN=4`, this means up to ~25 result metadata tokens per episode are uncounted. For 20 results, that is ~500 tokens of unaccounted overhead.

**Severity justification:** LOW because the default budget of 4000 tokens has enough slack, and LLM context windows are typically 8K-128K tokens. The undercount matters only at tight budget settings.

---

### F-08 [LOW] _is_safe_mode_blocked_content stringifies tags as repr

**Location:** `src/memory/read_pipeline.py:394`

**Evidence:**
```python
elif isinstance(tags_raw, (list, tuple, set)):
    tags_lower.add(f"{tags_raw}".lower())
```

**Impact:** When `tags_raw` is a list like `["emotional", "discord"]`, `f"{tags_raw}"` produces `"['emotional', 'discord']"` (Python repr). The substring check `blocked in tag` then checks if e.g. `"emotional"` is in `"['emotional', 'discord']"`, which works because Python `in` checks substrings. However, it also matches partial substrings: a tag like `"monitoring"` would match `"monitor"` from the blocked set, and a tag containing `"mode"` would match `"mode"` from the `"silent_mode"` blocked entry (though `"silent_mode"` is the blocked string, not `"mode"`).

The actual risk is low because the substring matching is intentionally fuzzy (the blocked set contains common substrings), but the `f"{tags_raw}"` approach creates a single string from the entire list rather than iterating individual tags. This means:
- A tag like `"sentiment_analysis"` correctly matches `"sentiment"` in the blocked set.
- But `tags_lower` contains only ONE entry (the stringified list), not individual tag strings. This means all blocked-set checks run against a single string representation.

For a list `["emotional", "discord"]`, the check `for tag in tags_lower` iterates once with `tag = "['emotional', 'discord']"`. The inner loop `for blocked in _SAFE_MODE_BLOCKED_CONTENT_TAGS` checks if `"emotional" in "['emotional', 'discord']"`, which is True. So it works by accident for single-element or compound matches, but would fail if the blocked substring is split across the repr boundary (unlikely in practice).

**Severity justification:** LOW because the accidental substring matching works for the existing blocked set, and the defensive `getattr` pattern prevents crashes.

---

### F-09 [LOW] store_episode flushes but never commits

**Location:** `src/memory/write_pipeline.py:217-218`

**Evidence:**
```python
session.add(episode)
await session.flush()
# No session.commit()
```

**Impact:** After `session.flush()`, the episode is written to the database (visible within the session) but not committed. If the caller's session context manager exits without committing, the episode is rolled back. This is by design (the pipeline docstring says "flush but does not commit"), but it means:

1. `HermesMemoryBridge.store_conversation()` explicitly adds `await session.commit()` after `store_episode()` (`_memory_bridge.py:307`), correctly handling this.
2. `cmd_memory_add.py` and `hermes memory_add.py` use `async with session_factory() as session:` which auto-commits on exit — correct.
3. Any new caller that does NOT auto-commit will silently lose data.

**Severity justification:** LOW because the primary callers are correct, and the behavior is documented in the bridge comment at line 304-306.

---

### F-10 [LOW] Discord/Hermes memory-add relies on session factory auto-commit

**Location:** `src/discord/cmd_memory_add.py:387-396`, `src/hermes_plugins/commands_memory/memory_add.py:91-100`

**Evidence:**
```python
# cmd_memory_add.py lines 387-396:
async with session_factory() as session:
    episode_uuid = await store_episode(
        session, note, source="discord_manual",
        classification="Restricted", importance=5,
        episode_type="conversation",
        embedding_service=embedding_service,
    )
# session exits here, auto-commits if no exception
```

Neither caller adds an explicit `await session.commit()`. They rely entirely on the session factory's context manager behavior (SQLAlchemy `AsyncSession` auto-commits on `__aexit__` success). This is the standard SQLAlchemy 2.0 async pattern and works correctly, but contrasts with `HermesMemoryBridge.store_conversation()` which adds an explicit commit.

**Severity justification:** LOW because auto-commit is the standard SQLAlchemy async pattern and works correctly with `async_sessionmaker`.

---

### F-11 [LOW] Embedding API failure silently degrades to embedding=NULL

**Location:** `src/memory/write_pipeline.py:189-195`

**Evidence:**
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

When `embedding_service` is provided but the API call fails (timeout, rate limit, server error), the exception propagates from `_compute_embedding` up through `store_episode`, which raises `WritePipelineError` (or a subclass). This is fail-closed for write-path callers that have an embedding service.

However, the `EmbeddingService` itself has retry logic (`_acall_with_retry` at embeddings.py:678-695, up to 6 retries with exponential backoff). After retries are exhausted, the exception propagates. The write pipeline does NOT catch this — it raises. So when a live embedding service is passed but the API is down, the entire write fails (fail-closed).

When `embedding_service=None` (the bridge path), embedding is silently skipped (no embedding stored). This is the documented graceful degradation path.

**Severity justification:** LOW because the behavior is correct: fail-closed when a service is expected, graceful skip when none is configured.

---

### F-12 [COSMETIC] Episodes model composite ORM primary_key quirk

**Location:** `src/memory/models.py:111-117`

**Evidence:**
```python
id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), primary_key=True,
    server_default=text("gen_random_uuid()"),
)
started_at: Mapped[datetime] = mapped_column(
    TIMESTAMP(timezone=True), primary_key=True, nullable=False
)
```

Both `id` and `started_at` are declared with `primary_key=True` in the ORM, making them a composite primary key in SQLAlchemy's view. However, the database DDL (via migrations) may define only `id` as the actual primary key, with `started_at` being a separate NOT NULL column. The pipelines treat `id` as the sole key, and the `cast(EpisodeRow, episode)` at `write_pipeline.py:222` reads only `episode.id`.

**Severity justification:** COSMETIC because all pipelines work correctly with `id` as the effective key, and the composite PK declaration is an ORM artifact that does not affect queries.

---

### F-13 [COSMETIC] No content-level dedup on write

**Location:** `src/memory/write_pipeline.py:111-237`

**Evidence:** There is no deduplication check before storing. If the same content is submitted twice (e.g., due to retry or duplicate event), two separate episodes are created with different UUIDs and timestamps. This contrasts with the Gmail memory store (`src/gmail/memory_store.py:298`) which has Redis-based dedup.

For episodic memory, this is arguably correct — each conversation turn is a distinct event even if the content is similar. But it means the FTS index will return duplicate-relevant results, and the RRF fusion will give them independent scores.

**Severity justification:** COSMETIC because episodic memory semantics accept duplicate events, and the RRF ranking naturally surfaces the most recent one.

---

### F-14 [COSMETIC] EmbeddingService created fresh per invocation

**Location:** `src/discord/cmd_memory_add.py:385`, `src/hermes_plugins/commands_memory/memory_add.py:89`

**Evidence:**
```python
embedding_service = EmbeddingService()
```

Each `/memory-add` command creates a new `EmbeddingService` instance, which creates a new `httpx.Client` and loads API keys from environment. The singleton `_default_service` at `embeddings.py:709` exists but is not used by these callers. This is wasteful but not harmful — `httpx.Client` creation is cheap, and the service is short-lived.

**Severity justification:** COSMETIC because the overhead is negligible for infrequent manual commands.

---

## Safety Properties Verified

### DNR (Do Not Recall) Filtering — ABSOLUTE

DNR filtering is applied at the SQL query level in all three signal queries:
- `build_vector_query()` — `read_pipeline.py:561-562`: `Episodes.do_not_recall.is_(False)`
- `build_fts_query()` — `read_pipeline.py:598-599`: `Episodes.do_not_recall.is_(False)`
- `build_recency_query()` — `read_pipeline.py:635-636`: `Episodes.do_not_recall.is_(False)`

This is absolute: episodes with `do_not_recall=True` are excluded from ALL three query result sets before RRF fusion. They cannot appear in the merged candidate pool. Verified.

### Classification Ceiling — CORRECT

The classification ceiling is applied after scoring and before content building:
- `read_pipeline.py:1078-1089`: Filters `ep_class_level <= ceil_level`
- `classification_level()` at `read_pipeline.py:361-369`: Maps unknown/null to level 5 (beyond Critical) — fail-closed
- `_resolve_ceiling()` at `read_pipeline.py:177-191`: Safe mode uses stricter ceiling

Classification hierarchy (`embeddings.py:107-113`):
```
Public(0) < Internal(1) < Restricted(2) < Confidential(3) < Critical(4)
```

Ceiling per principal (normal mode):
- `guinevere_core` → Critical (4) — sees everything
- `guinevere_subagent` → Confidential (3) — no Critical
- default → Restricted (2) — fail-closed for unknown principals

Safe mode ceiling:
- `guinevere_core` → Internal (1) — Restricted+ blocked
- `guinevere_subagent` → Public (0) — Internal+ blocked
- default → Public (0) — fail-closed

Verified: no classification leak.

### Safe-Mode Content Substitution — CORRECT

`build_safe_content()` at `read_pipeline.py:419-475`:
- Critical → `SAFE_MODE_PLACEHOLDER` (always)
- Restricted/Confidential → summary if available, else `SAFE_MODE_RESTRICTED_PLACEHOLDER` (raw content NEVER returned)
- Public/Internal → checked for emotional/surveillance tags, blocked if found; otherwise summary or raw
- Unknown → `SAFE_MODE_PLACEHOLDER` (fail-closed)

Raw `raw_content` is NEVER returned for Restricted, Confidential, Critical, or blocked-content episodes in safe mode. Verified.

### Fail-Closed Behavior — CORRECT

1. Critical classification without summary → `WritePipelineCriticalError` at `write_pipeline.py:291-295`
2. Unknown classification → level 5 (beyond Critical), blocked by ceiling at `read_pipeline.py:366-369`
3. Embedding API failure with live service → exception propagates, write fails at `write_pipeline.py:189-195`
4. All candidates filtered by ceiling → `ReadPipelineSafetyError` at `read_pipeline.py:1091-1096`
5. Embedding service not configured → embedding silently skipped (graceful degradation, not fail-closed — but documented)

### Logging Safety — CORRECT

All log statements use metadata only:
- `write_pipeline.py:225-235`: episode_id, classification, source, has_embedding, char_count — no raw content
- `read_pipeline.py:882-886`: query_hash (SHA256[:16]), query_length — no raw query text
- `read_pipeline.py:1132-1149`: counts, flags, hashes — no raw content
- `_memory_bridge.py:201-208`: query_length, results_count, flags — no raw content
- `embeddings.py:537-542`: classification, redaction_applied, char_count — no raw text

Verified: no raw content, vector values, secrets, or decrypted values in any log statement.

### Embedding Privacy Guards — CORRECT

- Critical classification: fails closed with `CriticalEmbeddingError` unless `sanitized_summary` is provided (`embeddings.py:237-248`)
- Restricted/Confidential: deterministic regex-based redaction of PII patterns (`embeddings.py:159-188`): API keys, emails, phone numbers, URLs with credentials, long hex strings
- Public/Internal: no redaction needed
- Dimension validation: 1536 expected, `DimensionMismatchError` on mismatch (`embeddings.py:566-571`)
- Retry: exponential backoff up to 6 retries for 429/5xx/timeout (`embeddings.py:372-394`, `678-695`)

### Token Budget Enforcement — CORRECT

`apply_token_budget()` at `read_pipeline.py:493-523`:
- Trims from the bottom (lowest-ranked items first)
- Uses `estimate_tokens(text) = len(text) // 4` approximation
- Logs trim event with budget, counts before/after
- Returns empty list if even the first item exceeds budget (with warning)

### Project Isolation (P19) — CORRECT for single writes

All three query builders (`build_vector_query`, `build_fts_query`, `build_recency_query`) accept `project_id` and apply:
```python
WHERE project_id = :project_id OR project_scope = 'global'
```

`store_episode()` accepts `project_id` and `project_scope` and passes them to the ORM object.

Exception: `store_episode_batch()` does NOT forward these (F-02).

---

## Hybrid Ranking Pipeline — Correctness

### Signal Weights (verified against code)

| Signal | Weight | Source |
|---|---|---|
| Vector cosine | 0.50 | `read_pipeline.py:110` (VECTOR_WEIGHT) |
| FTS relevance | 0.50 | `read_pipeline.py:114` (FTS_WEIGHT) |
| Both-signal bonus | 1.25x | `read_pipeline.py:144` (BOTH_SIGNAL_BONUS) |
| Recency boost | max 10% | `read_pipeline.py:148` (RECENCY_MAX_BOOST) |
| KG (optional) | 0.20 | `read_pipeline.py:120` (KG_WEIGHT) |
| FSRS (optional) | 0.15 | `read_pipeline.py:136` (FSRS_WEIGHT) |

### RRF Fusion — CORRECT

`compute_rrf_score()` at `read_pipeline.py:326-350`:
- Weighted RRF: `score = vector_weight / (k + vector_rank) + fts_weight / (k + fts_rank)`
- k=60 (standard RRF constant)
- Returns `(score, num_signals)` for both-signal bonus application

### Combined Score Formula

```
combined = rrf_score * recency_boost * importance_boost
```

Where:
- `rrf_score` = weighted RRF with both-signal bonus (1.25x if both signals found the episode)
- `recency_boost` = `1.0 + 0.10 * exp(-days * ln2 / 90)` — max 10% boost, 90-day half-life
- `importance_boost` = `0.5 + 0.5 * (importance / 10)` — range [0.55, 1.0]

Then KG and FSRS signals are additively applied (not multiplicative).

### Expanded Limit — CORRECT

`expanded_limit = min(limit * 3, 200)` at `read_pipeline.py:901`. Each signal query fetches up to `expanded_limit` candidates, ensuring RRF has enough overlap to produce meaningful rankings.

### Candidate Pool Hard Cap — CORRECT

`MAX_CANDIDATE_POOL = 200` at `read_pipeline.py:155`. Prevents unbounded memory/CPU from large requested limits.

---

## Session Lifecycle Analysis

### write_pipeline.store_episode
- Calls `session.add(episode)` then `session.flush()` (line 217-218)
- Does NOT commit — caller must commit
- Flush populates server-default UUID via SQLAlchemy refresh-on-flush

### HermesMemoryBridge.store_conversation
- Uses `async with self._session_factory() as session:` (line 278)
- Calls `store_episode(session, ...)` which flushes
- Explicitly calls `await session.commit()` (line 307)
- On exception: catch-all returns None (line 319-328), session context manager auto-rolls-back

### HermesMemoryBridge.recall_for_context
- Uses `async with self._session_factory() as session:` (line 152)
- Calls `recall_memories(session, ...)` which loads ORM objects
- FSRS side-effect mutations happen on loaded ORM objects (if fsrs_enabled)
- On successful exit: session auto-commits (FSRS mutations persisted)
- On exception: catch-all returns [] (line 212-221), session auto-rolls-back

### cmd_memory_add.py / hermes memory_add.py
- Uses `async with session_factory() as session:` (line 387 / line 91)
- Calls `store_episode(session, ...)` which flushes
- No explicit commit — relies on session factory auto-commit
- On exception: caught by outer try/except, session auto-rolls-back

---

## Recommendations

1. **[CRITICAL fix]** Wire `embedding_service` into `HermesMemoryBridge.store_conversation()` when an embedding provider is configured. Add a configuration flag or environment variable to control whether embeddings are generated on write. Implement or schedule the backfill job mentioned in the comment at `_memory_bridge.py:283`.

2. **[MEDIUM fix]** Add `project_id` and `project_scope` extraction to `store_episode_batch()` at `write_pipeline.py:260-277`. Either extract from each `ep_data` dict or add keyword parameters to the batch function signature.

3. **[MEDIUM fix]** Fix the KG rank map join by converting fact_ids to episode_ids (or vice versa) before the RRF adjustment loop at `read_pipeline.py:1011-1019`. This likely requires the KG module to return episode-level scores, not fact-level scores.

4. **[LOW fix]** Refactor `_is_safe_mode_blocked_content` tag matching at `read_pipeline.py:393-395` to iterate individual tags rather than stringifying the entire list.

5. **[LOW fix]** Add metadata token overhead to `apply_token_budget` estimate, or increase the default budget to account for per-result metadata.

---

## Status Verdict

**`IMPLEMENTED WITH BUGS`**

The P3 memory read/write pipelines are implemented, structurally sound, and safe. Fail-closed guards, DNR filtering, classification ceilings, safe-mode content substitution, token budget enforcement, and hybrid RRF ranking all work correctly. The critical embedding gap in the conversational write path (F-01) is a design defect that degrades recall quality but does not compromise safety. The batch write project_id omission (F-02) and KG-episode ID join mismatch (F-03) are medium-severity bugs that affect specific features but not the core pipeline.
