# P3-016 / P3-017: Context Injection & Privacy Audit

**Audit date:** 2026-06-25  
**Agent:** subagent (read-only)  
**Scope:** `read_pipeline.py` (safe-content builder, token budget, RRF fusion, `recall_memories`), `compaction.py` (ContextCompactor, pinned-tag isolation), `dnr.py` (verify_recall_results_dnr_free), `prompt_loader.py` (context injection into system prompt), `embeddings.py` (privacy preprocessing), `write_pipeline.py`, `consolidation.py`, all logging paths  
**Files examined:**
- `src/memory/read_pipeline.py` (lines 1-1198)
- `src/memory/compaction.py` (lines 1-297)
- `src/memory/dnr.py` (lines 1-419)
- `src/memory/embeddings.py` (lines 1-775)
- `src/memory/write_pipeline.py` (lines 1-369)
- `src/memory/consolidation.py` (lines 1-1127)
- `src/core/services/prompt_loader.py` (lines 1-294)
- `src/hermes/_memory_bridge.py` (lines 1-362)
- `src/discord/cmd_memory_search.py` (search path)
- `src/life_kernel/p18_adapter.py` (lines 1-116)
- `tests/memory/test_dnr.py` (DNR post-recall gate tests)
- `ADR-035-hermes-migration.md` (claims DNR gate is wired)

**Read-only affirmation:** True. No runtime code modified. No DB accessed.

---

## Findings

### [HIGH] `verify_recall_results_dnr_free` is exported but never called in production — no pre-injection DNR gate

`dnr.py` lines 385-418 defines `verify_recall_results_dnr_free()`, a post-recall / pre-injection safety gate that raises `DNRViolationError` if a result dict contains `do_not_recall=True`. The function is:
- Exported in `src/memory/__init__.py` line 81, documented as "Pre-injection guard"
- Mentioned in `ADR-035-hermes-migration.md` line 618 as the DNR enforcement point
- Tested in `tests/memory/test_dnr.py` lines 504-530

However, a content search across the entire `src/` tree shows **zero call sites** in production code. No caller invokes `verify_recall_results_dnr_free` after `recall_memories` returns. The pipeline's DNR protection relies solely on the SQL `WHERE do_not_recall is False` clause injected by `exclude_dnr=True` (read_pipeline.py lines 562, 599, 633).

Additionally, even if the function were called, it could not detect a violation: the result dicts constructed by `compute_scored_results()` (read_pipeline.py lines 769-777) do **not** include a `do_not_recall` key. The function checks `entry.get("do_not_recall")` but that key is absent from recall output.

**Defense:** The SQL WHERE filter is the primary defense and is correct for query-level exclusion. The missing pre-injection gate means a concurrent DNR mark (race condition between query execution and prompt assembly) would not be caught. The impact is narrow — a DNR mark must be committed between the SELECT and the injection.

**Source:** `src/memory/dnr.py:385-418` — function definition, never called in `src/`; `src/memory/read_pipeline.py:769-777` — result dicts lack `do_not_recall` key; `tests/memory/test_dnr.py:504-530` — tests verify the function works when called; `adr/ADR-035-hermes-migration.md:618` — claims DNR enforcement via this function.

### [MEDIUM] ContextCompactor may include sensitive classification content in LLM-generated summaries

`ContextCompactor._summarize()` (compaction.py lines 246-293) sends the middle portion of conversation messages to an LLM for summarization. The summary instruction (lines 261-272) asks the LLM to preserve key facts, decisions, safety tags, and DNR/hard-stop/distress references — but it does **not** instruct the LLM to avoid synthesizing or leaking Restricted/Critical/surveillance/emotional content into the summary.

The `_extract_pinned()` method (compaction.py lines 178-210) only protects messages that contain the literal safety tag substrings (e.g., "hard_stop", "do_not_recall") from being compacted away. It does not filter by classification level. If a middle-section conversation message contains Critical/emotional/surveillance content, that content is eligible for LLM summarization, and the summary could include sensitive details.

The 5-step cascade (lines 55-61) states "NEVER compact these" for pinned messages — but "pinned" is defined by substring tag matching, not by data classification.

**Source:** `src/memory/compaction.py:246-293` — _summarize sends all middle messages to LLM without classification-aware filtering; `:178-210` — _extract_pinned uses substring matching on safety tags, not classification. Summary prompt line 261-272 omits any redaction/safety instruction.

### [MEDIUM] Dual token budget enforcement with inconsistent input

The budget is enforced at two points with slightly different input:
- `read_pipeline.py` `apply_token_budget()` (line 493-523) checks `safe_content` alone, using `len(text) // 4`.
- `prompt_loader.py` `get_system_prompt_with_context()` (lines 82-105) checks the formatted line `"(Classification) safe_content"` using `len(line) // 4`.

The prompt_loader version includes more characters per entry (the classification prefix adds ~15 chars), so its budget check is slightly stricter. This could cause rare clipping where the pipeline returns N entries that fit its budget, but the prompt_loader discards the last 1-2 entries.

**Impact:** Low in practice (classification prefix is ~15 chars, budget is 4000). The most likely effect is one fewer memory in rare edge cases.

**Source:** `src/core/services/prompt_loader.py:82-105` — secondary budget check on formatted line; `src/memory/read_pipeline.py:493-523` — primary budget check on safe_content.

### [LOW] Discord memory search passes `safe_mode=False` by default

`cmd_memory_search.py` lines 113 and 119 call `recall_memories` with `safe_mode=False`. This means Critical/Restricted/Confidential content is returned raw in Discord embed fields (truncated to 100 chars, `cmd_memory_search.py:285`). The Discord search command is a manual operator tool with principal `"guinevere_core"` (which has CRITICAL clearance), so this is an intentional design choice. However, it means content classified as Critical or Restricted is rendered in Discord messages without redaction.

**Source:** `src/discord/cmd_memory_search.py:113` — `safe_mode=False`; `:119` — `bridge.recall_for_context(query, safe_mode=False, ...)`; `:285` — content truncated to 100 chars but unredacted.

### [LOW] Logging discipline is by convention, not enforcement

All memory system modules follow metadata-only logging conventions:
- `read_pipeline.py` logs query hashes (SHA-256 truncated to 16 hex chars at line 884-886), lengths, and counts
- `embeddings.py` logs model, dimension, classification, redaction_applied, char_count — never raw text (lines 537-542)
- `write_pipeline.py` logs episode_id, classification, source, has_embedding, char_count (lines 225-235)
- `consolidation.py` logs counts and job IDs
- `compaction.py` logs counts and tokens_saved
- `dnr.py` logs episode_id (UUID), principal, reason_hash only
- `_memory_bridge.py` logs query_length, results_count flags (lines 201-209)

However, there is no centralized audit, no type-checking gate, and no automated enforcement. A future developer adding a `logger.info("episode", extra={"raw_content": content})` call would not be caught by any guardrail. The convention is good but fragile — it relies on reviewer vigilance.

**Source:** All six memory modules, examined for `log`/`logger` calls with `.info`, `.warning`, `.error` — none emit raw text beyond safe identifiers.

### [LOW] `compaction._extract_pinned` uses naive substring matching for safety tag detection

`_extract_pinned()` at compaction.py line 203 checks `any(tag in content_lower for tag in _PINNED_TAGS)`. This is Python `in` substring matching, not tokenization or regex. The tags are `"safe_word"`, `"hard_stop"`, `"distress"`, `"consent_revocation"`, `"do_not_recall"` (lines 26-32).

- `"do_not_recall"` matches only when the underscored form appears (the conversational phrase "do not recall" would not match due to spaces vs underscores)
- `"hard_stop"` could match a message discussing "hard stop" in a normal context
- `"distress"` could match "distress signal" or "emotional distress"

The consequence of a false positive on any of these tags is preserving that message through compaction (including it in the output alongside first/last 3), which is a safe failure mode — the message stays, no data is lost.

**Source:** `src/memory/compaction.py:26-32` — PINNED_TAGS definition; `:203` — substring containment check.

### [PASS] Embedding privacy preprocessing is correct and fail-closed

`prepare_embedding_text()` (embeddings.py lines 206-268) enforces:
- Critical classification **requires** a `sanitized_summary` or raises `CriticalEmbeddingError`
- Restricted/Confidential text undergoes deterministic redaction of 7 sensitive patterns (API keys, bearer tokens, emails, phone numbers, credential-bearing URLs, hex hashes) via `_redact_sensitive()` (lines 176-188)
- Text is truncated to `MAX_INPUT_CHARS` (8000) before sending to external API

This is dual-enforced by `write_pipeline._compute_embedding()` (write_pipeline.py lines 298-316) which passes the summary as `sanitized_summary` for Critical episodes and the raw content for others (with redaction applied by the embedding service).

**Source:** `src/memory/embeddings.py:159-173` — redaction patterns; `:206-268` — prepare_embedding_text; `:237-247` — Critical fail-closed; `src/memory/write_pipeline.py:298-316` — _compute_embedding dual enforcement.

### [PASS] Classification ceiling + safe mode filtering is correctly layered

The read pipeline implements a 3-layer filtering cascade:
1. **SQL query filter**: `exclude_dnr=True` on all three signal queries (read_pipeline.py lines 562, 599, 633)
2. **Classification ceiling filter** (lines 1078-1096): post-scoring filter that drops episodes whose `classification_level() > ceil_level`. The ceiling is resolved per principal by `_resolve_ceiling()` (lines 177-191) — safe mode downgrades the ceiling (guinevere_core from Critical to Internal).
3. **Safe-mode content substitution** via `build_safe_content()` (lines 419-475):
   - Critical → placeholder string
   - Restricted/Confidential → summary only (never raw content)
   - Public/Internal → checks `_is_safe_mode_blocked_content()` for emotional/surveillance/escalation tags
   - Unknown classification → fail-closed placeholder

`classification_level()` (lines 361-369) returns 5 for None/unknown, which is beyond Critical (level 4), ensuring unknown labels are always filtered.

**Source:** `src/memory/read_pipeline.py:177-191` — _resolve_ceiling; `:361-369` — classification_level fail-closed; `:419-475` — build_safe_content; `:1078-1096` — ceiling filter loop.

### [PASS] DNR exclusion at SQL query level is correct

All three query builders (`build_vector_query`, `build_fts_query`, `build_recency_query`) apply `.where(Episodes.do_not_recall.is_(False))` when `exclude_dnr=True` (read_pipeline.py lines 561-562, 598-599, 632-633). The `recall_memories()` entry point defaults `exclude_dnr=True` at line 794.

Additionally, `consolidation.py` (line 323) and `decay_sweep_job` (consolidation.py line 995) also filter `do_not_recall.is_(False)`. The `store_episode()` write path creates episodes with `do_not_recall=False` by default (write_pipeline.py line 203). DNR marking (`dnr.py` lines 179-256) is authorized exclusively to `guinevere_core`.

**Source:** `src/memory/read_pipeline.py:561-562` — vector query DNR filter; `:598-599` — FTS query DNR filter; `:632-633` — recency query DNR filter; `src/memory/consolidation.py:323` — consolidation DNR filter; `src/memory/dnr.py:113-124` — authorization gate.

### [PASS] No confabulation — read pipeline returns stored content only

The read pipeline (`recall_memories`) retrieves episodes from the database via SQL queries, ranks them with deterministic RRF/Hybrid scoring (no LLM generation), and applies safety transforms (classification ceiling + safe-content placeholders). It never generates synthetic memory content.

The only LLM-based summary generation in the memory system is `ContextCompactor._summarize()` (compaction.py lines 246-293), which operates on conversation message lists, not on DB episodes. It is explicitly labeled as a summary and includes the original first 3 + last 3 messages alongside it. The summary is produced only when token budget is exceeded, which means the original messages are already too long to fit in context.

**Source:** `src/memory/read_pipeline.py:789-1151` — recall_memories returns DB-stored content; `src/memory/compaction.py:246-293` — _summarize produces LLM summary from middle messages only.

---

## Status Verdict

**PARTIALLY IMPLEMENTED**

The core safety mechanisms — DNR SQL filtering, classification ceiling, safe-mode content substitution, token budget enforcement, embedding privacy preprocessing, and metadata-only logging — are all correctly implemented. The embedding privacy path is particularly well-designed with dual enforcement (write pipeline guard + embedding service guard).

The critical gap is the **missing pre-injection DNR gate**: `verify_recall_results_dnr_free` exists, is tested, and is documented in ADR-035 as the DNR enforcement point, but is never called in production. This means there is no defense against a concurrent DNR mark being committed between recall query execution and prompt assembly. The result dicts also lack a `do_not_recall` key, so the gate would not work even if called without modification.

---

## Recommendations (NO FIXES — for mama consideration)

1. **Wire `verify_recall_results_dnr_free` as a post-recall guard** in `prompt_loader.assemble_system_prompt_with_memory()` and `hermes._memory_bridge.recall_for_context()`. Add a `do_not_recall` field to the result dicts in `compute_scored_results()` so the gate has data to check. This addresses the HIGH finding.

2. **Add classification-awareness to `ContextCompactor`.** Before summarizing middle messages, filter out or redact messages whose content matches Critical/Restricted/emotional/surveillance patterns. Update the summary prompt to instruct the LLM against leaking sensitive classification content.

3. **Add a centralized logging privacy audit** — a simple CI check or pytest that scans all `logger.*` calls in `src/memory/` and flags any that include `raw_content` or `content` as positional or extra arguments.

4. **Reconcile the dual token budget.** Since `prompt_loader.py` applies a stricter budget (including classification prefix), consider either aligning both to the same input, or documenting the difference and ensuring the pipeline budget is always slightly stricter so the prompt_loader never clips entries the pipeline allowed.
