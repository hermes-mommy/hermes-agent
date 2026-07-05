# Adversarial DNR Bypass Hunt — Wave 2

**Date:** 2026-06-25
**Agent:** Wave-2 Adversarial Audit (Explore, read-only)
**Scope:** Hunt every path where do_not_recall=True content can reach LLM context or semantic facts
**Read-only affirmation:** YES. No runtime code modified. No DB accessed. No secrets printed.

---

## Executive Summary

After exhaustive adversarial analysis of all six specified files and their transitive dependencies, I identified **3 confirmed bypass vectors** (1 CRITICAL, 1 HIGH, 1 MEDIUM) and **2 defensive weaknesses** (MEDIUM). The claim from the final report that "`verify_recall_results_dnr_free` is never called at runtime, and the result dicts it would inspect lack the `do_not_recall` key anyway" is **fully confirmed**. The system's DNR protection relies entirely on SQL WHERE clause filtering and the consolidation exclusion gate; the Python-side guard function is dead code that cannot fire even if called.

---

## Finding (a): Consolidation DNR Exclusion — SAFE WITH CAVEAT

### Analysis

`consolidate_episodes_to_facts` in `src/memory/consolidation.py` has a two-layer DNR defense:

1. **SQL WHERE clause (primary)** — line 323:
   ```python
   stmt = select(Episodes).where(Episodes.do_not_recall.is_(False))
   ```
   This excludes DNR'd episodes at the database level before they ever reach Python.

2. **Python defensive double-check** — line 341:
   ```python
   if getattr(ep, "do_not_recall", False):
       skipped_dnr += 1
       continue
   ```
   Belt-and-suspenders for ORM/protocol objects where the SQL filter might not apply (e.g., test doubles).

Both the daily consolidation (line 323) and the decay sweep (line 995) filter DNR at SQL level.

### Verdict

**SAFE.** A DNR'd episode cannot be consolidated into a `semantic_fact` while it is marked DNR. The double-check at line 341 is genuinely defensive. However, see Finding (g) for the temporal gap where this protection breaks.

---

## Finding (b): `verify_recall_results_dnr_free` — DEAD CODE, NEVER WIRED

**Severity: [CRITICAL]**

### Analysis

**Definition:** `src/memory/dnr.py:385-418`

**Exports:** `src/memory/dnr.py:38` and `src/memory/__init__.py:81,237`

**Actual call sites in production code (non-test):**

| File | Line | Context |
|------|------|---------|
| `src/memory/read_pipeline.py` | (none) | NOT called anywhere in the pipeline |
| `src/core/services/prompt_loader.py` | (none) | NOT called before prompt injection |
| `src/hermes/_memory_bridge.py` | (none) | NOT called after recall_for_context |
| `src/core/main.py` | (none) | NOT called in the main application loop |
| `src/hermes_plugins/commands_memory/memory_search.py` | (none) | NOT called |
| `src/discord/cmd_memory_search.py` | (none) | NOT called |
| `src/life_kernel/p16_adapter.py` | (none) | NOT called |
| `src/life_kernel/p18_adapter.py` | (none) | NOT called |

**Test-only call sites:**
- `tests/memory/test_dnr.py:504,507,514,521,530`
- `tests/phase7/test_T4_memory_pipeline.py:58-59` (just `assert callable(...)`)
- `scripts/ab_test_recall.py:86` (import-only, no call)

**Why it cannot work even if called:**

`compute_scored_results` in `src/memory/read_pipeline.py:721-781` builds each result dict at lines 769-777 with these keys: `id`, `safe_content`, `classification`, `importance`, `created_at`, `combined_score`, `is_summarized`. The key `do_not_recall` is **never set**. Therefore, when `verify_recall_results_dnr_free` checks `entry.get("do_not_recall")` at `dnr.py:405`, it always gets `None`, which is neither `True` nor `"True"` nor `"true"`, so the check always passes silently.

### Verdict

[CRITICAL] `verify_recall_results_dnr_free` is exported, documented, and tested, but it is:
1. Never called in any production code path.
2. Structurally unable to detect violations because the result dicts lack the `do_not_recall` key.

The pre-injection safety gate this function was designed to be does not exist at runtime. If the SQL WHERE clause were bypassed (e.g., a caller passing `exclude_dnr=False`), there is **no second line of defense**.

---

## Finding (c): FTS/Vector Search — SQL WHERE Clause (NOT Post-Filter)

**Severity: [MEDIUM]**

### Analysis

All three query builders apply `do_not_recall` filtering in SQL:

- **Vector query** — `src/memory/read_pipeline.py:561-562`:
  ```python
  if exclude_dnr:
      stmt = stmt.where(Episodes.do_not_recall.is_(False))
  ```

- **FTS query** — `src/memory/read_pipeline.py:598-599`:
  ```python
  if exclude_dnr:
      stmt = stmt.where(Episodes.do_not_recall.is_(False))
  ```

- **Recency query** — `src/memory/read_pipeline.py:632-633`:
  ```python
  if exclude_dnr:
      stmt = stmt.where(Episodes.do_not_recall.is_(False))
  ```

The filter is applied **in the SQL WHERE clause**, not as Python post-filtering. This is the correct approach because:
- The database uses snapshot isolation, so there is no TOCTOU race between query execution and DNR mutation within the same transaction.
- DNR'd rows are excluded from index scans (HNSW vector, GIN FTS, B-tree recency), reducing false results.

### Risk: `exclude_dnr=False` Override

The parameter defaults to `True` in `recall_memories` (line 794), and every production caller explicitly passes `exclude_dnr=True`:
- `src/core/services/prompt_loader.py:261`
- `src/hermes/_memory_bridge.py:157`
- `src/core/main.py:280`
- `src/hermes_plugins/commands_memory/memory_search.py:112`
- `src/discord/cmd_memory_search.py:412`
- `src/life_kernel/p18_adapter.py:95`

However, the function signature **allows** `exclude_dnr=False`. A future caller or a code injection could pass this to bypass DNR filtering. There is no runtime assertion or log-warning when `exclude_dnr=False` is used.

### Verdict

[MEDIUM] The SQL-level filtering is correctly implemented and there is no race condition within a single transaction. The residual risk is that `exclude_dnr=False` is a valid, unchecked parameter that a future caller could exploit.

---

## Finding (d): `unmark_memory_dnr` Authorization — PROPERLY ENFORCED

**Severity: [LOW]**

### Analysis

`unmark_memory_dnr` in `src/memory/dnr.py:265-345`:

1. **Line 300:** `_check_authorized(principal)` is called as the **first operation** before any database mutation.
2. **`_check_authorized`** at line 116-124 checks `principal not in _AUTHORIZED_PRINCIPALS` where `_AUTHORIZED_PRINCIPALS = frozenset({"guinevere_core"})`.
3. If the principal is not authorized, `DNRAuthorizationError` is raised immediately, and no update statement is built or executed.

The authorization check is fail-closed: the frozenset is hardcoded (line 113), not configurable, and not overridable. The only authorized principal is `"guinevere_core"`.

`mark_memory_dnr` (line 179) uses the identical `_check_authorized` gate at line 214.

### Verdict

[LOW] Authorization is correctly enforced. The only residual risk is that `principal` is a string parameter; if a caller passes a spoofed `"guinevere_core"` string, the check accepts it. There is no cryptographic verification of the principal identity. This is a design limitation, not an implementation bug.

---

## Finding (e): Batch Store Path — CANNOT Override Existing DNR

**Severity: [LOW]**

### Analysis

`store_episode_batch` in `src/memory/write_pipeline.py:245-277`:

1. Iterates over episodes and calls `store_episode` for each (line 262).
2. `store_episode` always sets `do_not_recall=False` (line 203) when **creating a new row**.
3. The batch API accepts a dict `ep_data` but does NOT accept or forward a `do_not_recall` key. Even if `ep_data` contained `{"do_not_recall": True}`, it would be ignored.
4. `store_episode` does **INSERT only** (creates new `Episodes` ORM instances), never UPDATE. It cannot modify an existing DNR'd row.

To "override" an existing DNR, an attacker would need to call `unmark_memory_dnr`, which requires `principal="guinevere_core"` authorization.

### Verdict

[LOW] The batch store path cannot write `do_not_recall=False` to override an existing DNR because it only creates new episodes. The DNR write path requires explicit authorization.

---

## Finding (f): The Final Report Claim — CONFIRMED

### Claim

> "verify_recall_results_dnr_free is never called at runtime, and the result dicts it would inspect lack the do_not_recall key anyway."

### Verification

**Part 1: "never called at runtime"** — CONFIRMED.

Searching all `.py` files under `src/` for `verify_recall_results_dnr_free` yields:
- `src/memory/dnr.py:38` — `__all__` export
- `src/memory/dnr.py:377-418` — function definition
- `src/memory/__init__.py:81,237` — re-export

Zero call sites in production code. The only calls are in `tests/memory/test_dnr.py` and `tests/phase7/test_T4_memory_pipeline.py`.

**Part 2: "result dicts lack the do_not_recall key"** — CONFIRMED.

`compute_scored_results` at `src/memory/read_pipeline.py:769-777` constructs result dicts with exactly 7 keys. `do_not_recall` is not among them. No subsequent code in `recall_memories` adds this key.

### Verdict

The final report's claim is **100% accurate**. The function is a dead-letter safety guard that cannot fulfill its intended purpose.

---

## Finding (g): Consolidated Semantic Facts from DNR'd Episodes — STALE FACT BYPASS

**Severity: [CRITICAL]**

### This is the most significant finding.

### Analysis

**The Temporal Gap:**

1. An episode exists with `do_not_recall=False`.
2. The daily consolidation job runs at 03:00 ICT (line 49, `consolidation.py`), creating `SemanticFacts` from this episode. The fact's `subject` may be the episode title, `object_val` may be the episode summary, and `source_episode` is the episode's UUID.
3. Later, the episode is marked `do_not_recall=True` via `mark_memory_dnr`.
4. The semantic fact **persists unchanged** — `SemanticFacts` has **no `do_not_recall` column** (`src/memory/models.py:208-263`).

**Recall Path for Semantic Facts:**

The `SemanticFacts` table is queried in two places that matter:

- **KG ingestion batch processor** — `src/knowledge_graph/ingestion/batch_processor.py:449-456`: queries `SemanticFacts` with only `deletion_state` filter. **No DNR check on source episode.**
- **KG pipeline lookup** — `src/knowledge_graph/ingestion/pipeline.py:912-981`: queries `SemanticFacts` by subject/predicate/object/source_episode. **No DNR check.**

**The KG Consent DNR Gate:**

`src/knowledge_graph/consent/manager.py:704-747` implements `check_dnr(entity_id)` which transitively checks `entity -> edges -> semantic_facts -> episodes` for DNR. This is correct for KG entity reads.

However, this gate only applies when a caller explicitly invokes `check_dnr`. The `ConsolidationResult.facts_created` list (returned at line 491-497 of `consolidation.py`) is passed directly to `kg_pipeline.ingest_from_consolidation()` at line 480. The KG ingestion pipeline does NOT re-check DNR on the source episodes of those facts.

**Concrete Attack Scenario:**

1. Episode E1 contains sensitive content, `do_not_recall=False`.
2. Consolidation runs, creates Fact F1 from E1: `subject="Faiz mentioned X"`, `object_val="details about X"`.
3. Fact F1 is ingested into KG as Entity Ent1 with edges.
4. User marks E1 as DNR via `mark_memory_dnr`.
5. Future recall via KG path queries Ent1. If `check_dnr` is not called, Ent1's description (derived from F1, which was derived from E1) is returned.
6. Even without KG, if a future recall or batch processor directly reads `SemanticFacts`, the content from E1 is accessible because F1 has no DNR flag.

### Verdict

[CRITICAL] The `SemanticFacts` table lacks a `do_not_recall` column and has no cascade mechanism when the source episode is marked DNR. Content from episodes marked DNR **after** consolidation survives indefinitely in `semantic_facts` and in the knowledge graph. The `ConsentManager.check_dnr` transitive check partially mitigates this for KG entity reads, but it requires callers to invoke it explicitly. No such check exists for direct `SemanticFacts` queries.

---

## Additional Findings

### Finding (h): ContextCompactor Preserves DNR in Summaries — [MEDIUM]

`src/memory/compaction.py:26-32`:
```python
_PINNED_TAGS = frozenset({
    "safe_word", "hard_stop", "distress",
    "consent_revocation", "do_not_recall",
})
```

The compactor checks for `do_not_recall` as a **substring in message content** (line 203: `any(tag in content_lower for tag in _PINNED_TAGS)`). This means:
- If a recalled memory's text literally contains the string "do_not_recall", the message is pinned (protected from compaction). This is coincidental, not intentional DNR enforcement.
- The compactor does NOT check episode DNR status in the database. If a DNR'd episode's content was injected into a conversation **before** the DNR was applied, that content flows through compaction into summaries and back into the conversation.
- The LLM summarizer at `_summarize` (line 246-293) instructs the model to "Never remove mentions of: safe words, hard stops, distress signals, consent changes, or do-not-recall requests" — but this is a prompt instruction, not a programmatic guarantee. The LLM could fail to preserve DNR markers.

### Finding (i): `SemanticFacts` Has No `do_not_recall` Column — [HIGH]

`src/memory/models.py:208-263` — The `SemanticFacts` model inherits from `ClassificationMetaMixin` which provides `classification`, `deletion_state`, etc. But there is no `do_not_recall` column. This means:
- There is no database-level mechanism to mark a semantic fact as DNR.
- The only way to suppress a stale fact is to set `deletion_state='deleted'` or `deletion_state='archived'`, which requires a separate operation.
- The KG DNR check (`check_dnr`) must traverse `semantic_facts -> episodes` to determine DNR status, rather than checking a local flag.

---

## Summary Table

| ID | Hunt Item | Severity | Status |
|---|---|---|---|
| (a) | Consolidation DNR exclusion | — | SAFE |
| (b) | `verify_recall_results_dnr_free` wiring | [CRITICAL] | Dead code; never called; result dicts lack key |
| (c) | SQL WHERE vs Python post-filter | [MEDIUM] | SQL-level (correct); `exclude_dnr=False` is unchecked |
| (d) | `unmark_memory_dnr` authorization | [LOW] | Properly enforced; principal is string-only |
| (e) | Batch store DNR override | [LOW] | Cannot override; INSERT-only, no DNR key |
| (f) | Final report claim verification | — | CONFIRMED 100% accurate |
| (g) | Stale semantic fact from DNR'd episode | [CRITICAL] | Content survives in semantic_facts indefinitely |
| (h) | ContextCompactor DNR handling | [MEDIUM] | String-match only; no DB check |
| (i) | SemanticFacts lacks DNR column | [HIGH] | No per-fact DNR suppression mechanism |

---

## Status Verdict

**FAIL — conditional CRITICAL bypass paths confirmed.**

The episode-level DNR gate (SQL WHERE clause in `recall_memories` and `consolidate_episodes_to_facts`) is correctly implemented and provides the primary protection. However:

1. The `verify_recall_results_dnr_free` pre-injection gate is dead code that cannot detect violations (result dicts lack the `do_not_recall` key). If the SQL filter were bypassed, there is zero fallback.

2. The `SemanticFacts` table has no `do_not_recall` column. Content from DNR'd episodes that was consolidated before the DNR mark persists indefinitely and can be recalled through the KG path or direct fact queries. This is a confirmed temporal bypass.

3. The `ContextCompactor` has no database-level DNR enforcement; its DNR handling relies on substring matching of the literal text `"do_not_recall"` in message content.

These gaps are architectural, not implementation bugs. A complete fix requires: (1) wiring `verify_recall_results_dnr_free` into the prompt injection path, (2) adding a `do_not_recall` column to `SemanticFacts` with cascade from episode DNR, and (3) implementing a periodic DNR-sweep job that tombstones facts whose source episodes are marked DNR.