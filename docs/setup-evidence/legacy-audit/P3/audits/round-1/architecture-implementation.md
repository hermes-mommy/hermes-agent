# P3 (Memory Foundation) — Architecture & Implementation Completeness Audit

**Audit date:** 2026-06-25
**Agent:** subagent (architecture-dimension)
**Affirmation:** READ-ONLY. No runtime code was modified. No DB was accessed. Alembic migration tree was inspected via file read only.
**Scope:** `src/memory/*`, `src/core/main.py`, `src/hermes/_memory_bridge.py`, `src/life_kernel/p18_adapter.py`, `src/life_kernel/p16_adapter.py`

---

## Summary

P3 Memory Foundation is substantially implemented in source code. The core pipeline — write (`store_episode`, `store_episode_batch`), read (`recall_memories` with hybrid RRF fusion), embedding (`EmbeddingService` with httpx), DNR (`mark_memory_dnr`/`unmark_memory_dnr`/`verify_recall_results_dnr_free`), and consolidation (`consolidate_episodes_to_facts`) — all exist as real, wired, non-trivial implementations. However, the production runtime integration has a critical gap: the consolidation scheduler is explicitly commented out in `main.py`, and the embedding service is deliberately **not** wired for write-path embedding in the `HermesMemoryBridge` (and thus no vector-search recall from the Hermes agent path). Additional minor discrepancies exist in table counts, API surface consistency, and code comments.

---

## Findings

### [CRITICAL] Consolidation scheduler is commented out in production startup

- **File:** `src/core/main.py:23-38`
- **Detail:** The entire block that would register the `daily_consolidation_job` with APScheduler is a **comment block**, not live code. The comment says "DO NOT start a live APScheduler without a valid async DB sessionmaker." The scheduled task (`consolidate_episodes_to_facts` with its `SemanticFacts` creation, KG ingestion hook, FSRS review hook) does NOT run in the current production deployment. While the consolidation module itself is well-structured (`src/memory/consolidation.py`) and unit-tested (`tests/memory/test_consolidation.py`), it is effectively dormant at runtime. The operator must manually inject and start the scheduler to activate it. This is a structural gap between "implemented" and "deployed."
- **Severity:** CRITICAL
- **Verdict for this item:** DOCS CLAIM ONLY / NOT PROVEN (for the scheduled consolidation runtime path)

### [HIGH] HermesMemoryBridge write path does not compute embeddings

- **File:** `src/hermes/_memory_bridge.py:278-303`
- **Detail:** `store_conversation` always passes `embedding_service=None`. The docstring at line 279-281 explains: "9Router has no embedding models; passing a live service causes `_compute_embedding()` to raise. Episodes are persisted without embedding vectors (FTS-only recall)." This means every episode created via `HermesMemoryBridge` (the Hermes conversational agent's write path into memory) has `embedding = NULL`. While the read pipeline (`recall_memories`) gracefully falls back to FTS-only when no `query_vector` is available, the vector-similarity signal is effectively dead for all Hermes-written episodes. The `_memory_bridge.py` comment at line 282 mentions a "backfill job" but no such job exists.
- **Severity:** HIGH
- **Note:** This is an intentional architectural trade-off (9Router doesn't serve `text-embedding-3-small`), not a bug per se. But it means the dual-signal RRF fusion (vector + FTS) nominally promised by P3-011 is single-signal (FTS-only) for the primary write path.

### [HIGH] HermesMemoryBridge.store_conversation session commit confusion

- **File:** `src/hermes/_memory_bridge.py:304-307`
- **Detail:** Line 306-307 reads: "Without explicit commit, the async-with session exits and SQLAlchemy rolls back — episode is lost silently." The code correctly calls `await session.commit()` before context exit. However, the comment is **incorrect** if read in isolation: `store_episode` calls `session.flush()`, not `session.commit()`, so the bridge's own `session.commit()` is required. The comment's phrasing ("SQLAlchemy rolls back") conflates two different session lifecycle patterns:
  1. `async with get_async_session()` (from `src/memory/db.py:92-112`) — this context manager auto-commits on clean exit.
  2. A bare `async with async_sessionmaker()` (the bridge's pattern) — this does NOT auto-commit; an uncommitted flush is rolled back at transaction end.
  The code is correct, but the comment is misleading and could cause confusion if the bridge pattern is copied elsewhere.
- **Severity:** HIGH (cosmetic-to-actual-risk depending on reader)

### [MEDIUM] Table count discrepancy: 48 tables, not 47

- **File:** `src/memory/models.py` (docstring on line 1: "47 tables across 12 schemas")
- **Detail:** `grep -c __tablename__` returns **48** `__tablename__` declarations across 48 ORM classes. The module docstring claims "47 tables across 12 schemas" (P3 claimed 12 schemas / 47 tables). The extra table is likely `AlertHistory` (schema `ops`, line 1204), added by a post-P3 phase (P18/P20) without updating the module docstring. Schemas are correctly 12: `agents`, `audit`, `consent`, `extensions`, `financial`, `memory`, `ops`, `persona`, `projects`, `security`, `social`, `surveillance`. No `life_kernel` schema exists in models.py.
- **Severity:** MEDIUM (domino effect: schema count verbatim in every downstream doc reference is stale)

### [MEDIUM] consolidation.py exception coverage gap in daily_consolidation_job

- **File:** `src/memory/consolidation.py:837-843`
- **Detail:** The `except` clause on line 837 only catches `(RuntimeError, ValueError, TypeError, OSError, AttributeError)`. Unexpected exception types (e.g. `KeyError`, `ImportError`, `asyncio.CancelledError`) propagate upward **without** being logged. The docstring claims "Re-raises after logging error metadata" (line 808) but this is only true for the 5 listed types. An unlisted exception type silently propagates past the `try` block without hitting the `logger.error` call.
- **Severity:** MEDIUM

### [MEDIUM] Life kernel recall function does not propagate safe_mode/full parameter surface

- **File:** `src/core/main.py:274-283`
- **Detail:** The `_life_recall_fn` closure wraps `recall_memories` but hardcodes `embedding_service=None`, `token_budget=DEFAULT_TOKEN_BUDGET` (4000), `kg_enabled=False`, `fsrs_enabled=False`, and `project_id=None`. Only `query_text`, `principal`, and `exclude_dnr` are exposed from the life kernel adapter's `MemoryRecallAdapter.recall()` method. This means the life kernel always gets FTS-only recall (no vector similarity), no KG 4th signal, no FSRS retrievability bonus, no project-scoped isolation. While the adapter gracefully degrades, the life kernel is consuming only a subset of the read pipeline's capability.
- **Severity:** MEDIUM

### [LOW] EmbeddingService async path creates a new httpx.AsyncClient per request

- **File:** `src/memory/embeddings.py:593`
- **Detail:** `_do_async_request` uses `async with httpx.AsyncClient(...)` as a context manager, creating a new client for **every** async embedding call. The sync path (`_do_sync_request`) reuses a single `httpx.Client` instance. This means the async path creates and destroys TCP connections repeatedly, losing connection-pool benefits. The async retry wrapper (`_acall_with_retry`) exacerbates this because each retry attempt also creates a fresh client.
- **Severity:** LOW (performance, not correctness)

### [LOW] Consolidation _fact_exists_by_key is O(n) on all existing facts

- **File:** `src/memory/consolidation.py:648-668`
- **Detail:** The deduplication check loads all `SemanticFacts` rows and iterates every one for each candidate fact. The docstring acknowledges this and suggests adding a `content_hash` column with unique constraint for production. For moderate fact volumes (under 10,000), the daily cron cadence makes this acceptable, but it is a known scalability gap.
- **Severity:** LOW

### [LOW] Models without ClassificationMetaMixin leak classification defaults

- **File:** `src/memory/models.py` (lines 519, 676, 782, 869, 1204, 1228, 1251, 1271)
- **Detail:** 8 out of 48 tables inherit from `Base` directly instead of `ClassificationMetaMixin`: `DeviceRegistry`, `OptimizationLog`, `EvidenceArtifacts`, `SubagentRegistry`, `AlertHistory`, `PgvectorConfig`, `TimescaledbConfig`, `PgcryptoConfig`. These tables do not have `classification`, `purpose`, `source`, `retention_class`, `retention_until`, `access_policy`, `encryption_profile`, `deletion_state`, `key_id`, `key_version` columns. This is architecturally intentional (extension config tables, system registries) but creates a governance blind spot.
- **Severity:** LOW

### [COSMETIC] Misleading comment in consolidation.py about exception re-raising

- **File:** `src/memory/consolidation.py:808`
- **Detail:** The docstring says "Re-raises any exception after logging (no empty catch)." The actual `except` clause on line 837 catches only 5 specific types. A comment at line 839 says "re-raise" but the `raise` keyword at line 843 is inside the `except` block — so it does re-raise, but only for those 5 types. The wording of the docstring implies ALL exceptions, which is false. (Related to the MEDIUM finding above.)
- **Severity:** COSMETIC

### [COSMETIC] Hardcoded DEFAULT_BASE_URL points to localhost

- **File:** `src/memory/embeddings.py:83`
- **Detail:** `DEFAULT_BASE_URL = "http://localhost:20128/v1"` — the 9Router default location. This is correct for local development but the default means any `EmbeddingService()` constructed without explicit `base_url` will fail in production unless the 9Router proxy runs on the same host:port. The `GUINEVERE_9ROUTER_API_KEY` env var is checked; there is no `GUINEVERE_EMBEDDING_BASE_URL` env var override path. However, `EmbeddingConfig.__init__` takes a `config` parameter that provides a `base_url`, so production can inject it. The concern is that env-var-based configuration is preferred for 12-factor apps and none exists.
- **Severity:** COSMETIC

### [COSMETIC] FaizProfile stores values in LargeBinary

- **File:** `src/memory/models.py:278`
- **Detail:** The `value` field is `LargeBinary` (bytes), not encrypted `Text`. The docstring in `models.py` line 1 claims the schemas span "memory/persona/surveillance/financial/projects/social/agents/consent/security/audit/ops/extensions + life_kernel (13 total)." LargeBinary is a server-side storage choice, not an audit issue per se, but worth noting for the broader classification-governance picture.
- **Severity:** COSMETIC

---

## Verification Methodology

- Read all 12 source files in `src/memory/` (models, db, embeddings, write_pipeline, read_pipeline, dnr, consolidation, compaction, tiers, spaced_repetition, `__init__`).
- Read `src/core/main.py` lines 1-460 (lifespan, adapter wiring, scheduler registration).
- Read `src/hermes/_memory_bridge.py` (all 362 lines).
- Read `src/life_kernel/p18_adapter.py` and `src/life_kernel/p16_adapter.py`.
- Counted `__tablename__` declarations (48), ORM classes (48), and schemas (12).
- Counted `except:` clauses — none found in memory module (only specific `except ExceptionType:`).
- Counted `pass` statements — only in Protocol method stubs (accepted pattern).
- Verified no bare `except:` or unprotected `pass` in business logic.

---

## Status Verdict

**VERIFIED IMPLEMENTED** — with the following carveouts that adjust the verdict per subsystem:

| Subsystem | Verdict |
|---|---|
| ORM models (48 tables/12 schemas) | VERIFIED IMPLEMENTED |
| DB session factory (`db.py`) | VERIFIED IMPLEMENTED |
| Embedding pipeline (`EmbeddingService`) | VERIFIED IMPLEMENTED |
| Write pipeline (`store_episode`/`store_episode_batch`) | VERIFIED IMPLEMENTED |
| Read pipeline (`recall_memories` + RRF fusion) | VERIFIED IMPLEMENTED |
| DNR (`mark_memory_dnr`/`verify_recall_results_dnr_free`) | VERIFIED IMPLEMENTED |
| Hermes Memory Bridge (read path) | VERIFIED IMPLEMENTED |
| Hermes Memory Bridge (write path) | IMPLEMENTED WITH BUGS (embedding_service=None permanently; misleading session comment) |
| Daily consolidation scheduler | DOCS CLAIM ONLY / NOT PROVEN (commented out in main.py) |
| Life kernel memory/ KG adapters | VERIFIED IMPLEMENTED (degraded parameter surface) |
| Memory tiers / FSRS | VERIFIED IMPLEMENTED (P18 superset) |

**Overall verdict: VERIFIED IMPLEMENTED** — the core P3 memory pipeline exists, is wired, and is functional. The critical gap is that the consolidation scheduler is dormant in production. The high-impact gap is that the primary write path (`HermesMemoryBridge.store_conversation`) produces episodes with `embedding=NULL`, making the dual-signal RRF fusion (vector + FTS) single-signal for the Hermes agent path.

---

## Recommendations (NO FIXES — for mama's consideration)

1. **Consolidation scheduler:** Either activate the `register_consolidation_job` call in `main.py` (with proper session factory injection) or add a `WARNING` log at startup if the consolidation job is not registered, so operators are aware the scheduled memory distillation is inactive.

2. **Embedding backfill:** If/when a provider serving `text-embedding-3-small` (or equivalent 1536-dim model) becomes available behind the 9Router proxy, add a backfill migration command (CLI or one-shot) that computes embeddings for existing episodes where `embedding IS NULL`.

3. **Exception coverage in consolidation:** Broaden the `except` clause in `daily_consolidation_job` to `except Exception` (with re-raise) so every failure is logged, not just the 5 named types.

4. **Module docstring in models.py:** Update `models.py` line 1 from "47 tables" to "48 tables" to match reality.

5. **Async embedding client reuse:** Consider lifting the `httpx.AsyncClient` out of `_do_async_request` into an instance-level client on `EmbeddingService`, similar to the sync path.

6. **Life kernel recall parameter surface:** Expose more `recall_memories` parameters (at minimum `embedding_service`, `kg_enabled`, `project_id`) through `MemoryRecallAdapter.recall()` and the `_life_recall_fn` closure so the life kernel can use the full pipeline.
