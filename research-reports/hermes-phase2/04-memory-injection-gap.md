# Memory Injection Gap Analysis — Hermes Phase 2 Research Agent 4

> **Date**: 2026-06-04
> **Role**: Research Agent 4 — Memory to System Prompt Injection Flow
> **Files Analyzed**: prompt_loader.py, read_pipeline.py, conversational_handler.py, session_adapter.py, bot.py, embeddings.py
> **System Prompt Template**: /home/guinevere/config/hermes/system-prompt.md (fetched from VPS)
> **Depends On**: 01-current-memory-flow.md (complete flow trace already documented)

---

## 1. Exact Memory Injection Flow

### 1.1 assemble_system_prompt_with_memory() — Signature and Behavior

**File**: `src/core/services/prompt_loader.py:119-182`

```python
async def assemble_system_prompt_with_memory(
    session: RecallSession,
    query_text: str,
    *,
    mood: str = "Content",
    safe_mode: bool = False,
    hard_stop_handler: object | None = None,
    principal: str = "guinevere_core",
    limit: int = 3,
    token_budget: int = DEFAULT_TOKEN_BUDGET,  # 4000
    embedding_service: EmbeddingClient | None = None,
) -> str:
```

**Returns**: Fully assembled system prompt string (base prompt + memory section + mood line).

**Internal flow**:
1. Resolve `safe_mode` — if `hard_stop_handler` is provided, `hard_stop_handler.is_safe` overrides the `safe_mode` parameter (line 157-158).
2. Call `recall_memories(session, query_text, ...)` with all parameters passed through.
3. On `ReadPipelineSafetyError`: log and return base prompt + mood only (no memories).
4. On success: call `get_system_prompt_with_context(memories=results, mood=mood, token_budget=token_budget)`.

### 1.2 How recall_memories() Is Called

**Session source**: `conversational_handler.py:408-413` obtains the session from `bot.get_session_factory()`, which lazily creates a SQLAlchemy `async_sessionmaker` from the `DATABASE_URL` env var (`bot.py:480-499`). A new `AsyncSession` is opened per message via `async with session_factory() as session`.

**Embedding service source**: `conversational_handler.py:114-125` — module-level lazy singleton `_get_embedding_service()`. Created once as `EmbeddingService()` with default config:
- base_url: http://localhost:20128/v1 (9Router local proxy)
- model: openai/text-embedding-3-small
- expected_dimension: 1536
- API key from env GUINEVERE_9ROUTER_API_KEY or OPENROUTER_API_KEY

**Parameters passed by conversational_handler**:

| Parameter | Value | Source |
|-----------|-------|--------|
| session | Fresh AsyncSession | bot.get_session_factory() |
| query_text | Raw user message | message.content |
| mood | "Content" | Hardcoded Mood.CONTENT.value |
| safe_mode | DistressDetector result | controller.evaluate(signal) |
| principal | "guinevere_core" | Hardcoded |
| limit | 3 | Hardcoded |
| token_budget | 400 | Hardcoded |
| embedding_service | Singleton EmbeddingService | _get_embedding_service() |

**NOT passed**: `hard_stop_handler` — the parameter exists in assemble_system_prompt_with_memory() but the handler never passes it. The handler computes safe_mode_activated independently and passes it directly as safe_mode.

### 1.3 How Recalled Memories Are Formatted in the System Prompt

**File**: `src/core/services/prompt_loader.py:79-102`

When memories exist, the format injected into the system prompt is:

```
{base_system_prompt}

## Recalled Memories
1. {safe_content of memory 1}
2. {safe_content of memory 2}
3. {safe_content of memory 3}

## Current Mood: {mood}
```

Each memory is a numbered line with ONLY the safe_content field. No metadata (classification, importance, timestamp, score) is included. No section headers, tags, or context hints.

When memories are empty or None:

```
{base_system_prompt}


## Current Mood: {mood}
```

### 1.4 Token Budget — How It Is Enforced

**Two-pass enforcement**:

1. **Pass 1** (read_pipeline.py:464-494, apply_token_budget()): After recall, results are trimmed from the bottom (lowest-scored first) until total estimated tokens fit within budget (400 tokens as passed by handler). Estimation: len(text) // 4 chars per token.

2. **Pass 2** (prompt_loader.py:82-101, get_system_prompt_with_context()): Memories are iterated again and trimmed with the same estimation against the same token_budget (400). This second pass is **redundant** — memories were already trimmed in pass 1.

**Budget math**: 400 tokens x 4 chars/token = **1600 characters total** across all 3 memories. Average ~533 chars per memory.

**No total context budget**: The base system prompt has no size limit. Combined with 20 turns of conversation history (up to ~20,000 tokens from Redis), there is no mechanism to ensure the total context sent to the LLM stays within the model context window.

### 1.5 What Happens When Recall Returns Empty

Three scenarios:

| Scenario | Trigger | Behavior |
|----------|---------|----------|
| No results from DB | FTS + recency + vector all return 0 rows | recall_memories() returns [] (line 837-842) |
| All filtered by classification | Ceiling filter removes all candidates | ReadPipelineSafetyError raised (line 860-865) |
| Token budget trims all | All memories exceed 400 tokens | apply_token_budget() returns [] (line 473-494) |

In all cases, assemble_system_prompt_with_memory() handles it gracefully — returns base prompt + mood only. No error shown to the user.

---

## 2. Gap Analysis

### 2.1 DB Session — Same or Different?

**Finding**: Memory recall uses a **different session instance** but the **same session factory**.

- conversational_handler.py:408-413: Opens session for recall.
- conversational_handler.py:537: Opens a **second** session for auto-store.
- Both from same bot.get_session_factory() -> same async_sessionmaker -> same connection pool.

**Impact**: Two separate DB connections checked out per message. Not a correctness issue, but resource-inefficient. A bridge should use one session per message lifecycle.

**Severity**: **Important** — wastes connection pool slots, but not a data consistency problem.

### 2.2 EmbeddingService — Singleton or Per-Call?

**Finding**: **Lazy singleton** at module level in conversational_handler.py:83,114-125. Created once, reused across all messages. Holds a sync httpx.Client.

**Gap**: Singleton defined in conversational_handler.py, not in a shared module. Other handlers (slash commands, agent loop) would create their own singletons. No centralized embedding service registry.

**Severity**: **Important** — potential for multiple EmbeddingService instances with separate httpx clients and retry state.

### 2.3 DB Connection Failure During Recall

**Finding**: Entire recall block wrapped in broad try/except Exception (conversational_handler.py:406-455). Falls back to base prompt without memories.

**Sub-scenarios**:
- Connection refused: Exception caught, fallback to base prompt.
- Query timeout: Same — caught and fallback.
- Session factory returns None: Handled separately (line 429-435) — base prompt with log memory_recall_skipped.
- System prompt file missing: Inner try/except (line 443-455) sends FALLBACK_MESSAGE.

**Gap**: No retry logic for transient DB failures.

**Severity**: **Nice-to-have** — graceful degradation works, but a single retry would improve reliability.

### 2.4 Token Budget — Is 400 Tokens Appropriate?

**Current**: limit=3, token_budget=400 (hardcoded in conversational_handler.py:420-421).

**Analysis**:
- 400 tokens = ~1600 characters across 3 memories = ~533 chars per memory.
- For auto-stored conversations: summary = content[:200] (~50 tokens). Three 50-token memories = 150 tokens, well within 400.
- For richer memories (surveillance data, engineering notes), 400 tokens is restrictive.

**Bridge spec proposal**: limit=5, token_budget=800.

**Impact of increasing**:
- 800 tokens = ~3200 chars across 5 memories = ~640 chars per memory.
- More memories recalled = better LLM context.
- With GPT-5.5 1M context window, 800 tokens is negligible (0.08%).
- Slightly higher per-message cost but materially better recall quality.

**Severity**: **Important** — current budget is too conservative for the value memory recall provides.

### 2.5 Memory Format Efficiency

**Current format**:
```
## Recalled Memories
1. {safe_content}
2. {safe_content}
3. {safe_content}
```

**Issues**:
- No temporal context — LLM does not know when the memory was created.
- No importance signal — LLM cannot weight memories by significance.
- No source/type context — LLM does not know if memory is a conversation, surveillance data, or engineering note.
- No deduplication — if the same fact appears in multiple episodes, all copies are injected.

**Proposed [RECENT MEMORIES] format** (bridge spec):
```
[RECENT MEMORIES]
- [2h ago, importance:8] Faiz mentioned deadline for project X is Friday
- [1d ago, importance:5] Discussion about PostgreSQL migration strategy
- [3d ago, importance:3] Casual chat about weekend plans
```

**Advantages**: Temporal context, importance signal, compact single-line format, more information per token.

**Severity**: **Important** — current format wastes tokens and loses critical context.

### 2.6 Deduplication

**Finding**: RRF fusion in read_pipeline.py:603-651 deduplicates episodes **across signals** (vector, FTS, recency). If the same episode is found by multiple signals, it appears once in the merged map.

**BUT**: There is NO deduplication across **different episodes with similar content**. If Faiz discussed the same topic in 3 separate conversations, all 3 episodes will be recalled and injected.

**Severity**: **Important** — wastes token budget on redundant information.

### 2.7 Safe Mode in Recall Chain

**Finding**: safe_mode is properly respected in the recall chain:

1. conversational_handler computes safe_mode_activated from DistressDetector/SafeModeController.
2. Passed to assemble_system_prompt_with_memory() as safe_mode parameter.
3. Passed through to recall_memories().
4. recall_memories() applies classification ceiling downgrade (guinevere_core: Critical -> Internal in safe mode).
5. build_safe_content() redacts/blocks content per classification level.

**Gap**: hard_stop_handler is NOT wired. The assemble_system_prompt_with_memory() function supports hard_stop_handler.is_safe as authoritative override, but conversational_handler never passes it. This means if a HARD STOP is active, the handler relies on DistressDetector catching it rather than using the hard_stop_handler directly.

**Severity**: **Critical** — the HARD STOP protocol should be wired through hard_stop_handler, not rely on DistressDetector pattern matching.

---

## 3. Complete Flow Diagram

```
Discord Message (Faiz in #guinevere-chat)
    |
    v
handle_conversation() -- guards (channel, bot, slash, Faiz, rate limit)
    |
    v
_process_and_respond()
    |
    +-- DistressDetector.detect(content) --> safe_mode_activated
    +-- Mood = "Content" (HARDCODED -- GAP)
    |
    +--[MEMORY RECALL]-------------------------------------------+
    |   bot.get_session_factory() --> session_factory             |
    |   async with session_factory() as session:                  |
    |     assemble_system_prompt_with_memory(                     |
    |       session, content, mood="Content",                     |
    |       safe_mode=X, principal="guinevere_core",              |
    |       limit=3, token_budget=400,                            |
    |       embedding_service=singleton,                          |
    |       hard_stop_handler=NOT_PASSED  <-- GAP                 |
    |     )                                                       |
    |     |                                                       |
    |     +-- recall_memories()                                   |
    |     |   +-- embedding.aembed(query) --> FAILS (9Router)     |
    |     |   +-- FTS query (expanded_limit=9 rows)               |
    |     |   +-- Recency query (expanded_limit=9 rows)           |
    |     |   +-- RRF fusion (dedup across signals)               |
    |     |   +-- Score: RRF * recency_boost * importance_boost   |
    |     |   +-- Classification ceiling filter                   |
    |     |   +-- Take top 3                                      |
    |     |   +-- build_safe_content() per episode                |
    |     |   +-- apply_token_budget(400) -- PASS 1               |
    |     |                                                       |
    |     +-- get_system_prompt_with_context()                    |
    |         +-- load_system_prompt() from VPS file              |
    |         +-- Safety validation (HARD STOP, Y5/Y6, distress)  |
    |         +-- Format: "## Recalled Memories\n1. ...\n2. ..."  |
    |         +-- Token budget check -- PASS 2 (redundant)        |
    |         +-- Append "## Current Mood: Content"               |
    |         +-- Return assembled string                          |
    +--------------------------------------------------------------+
    |
    +--[HERMES CALL]----------------------------------------------+
    |   hermes.send_message(                                      |
    |     user_id, content, system_prompt=assembled_prompt        |
    |   )                                                         |
    |   +-- Load history from Redis DB4 (20 turns max)            |
    |   +-- AIAgent.run_conversation(                             |
    |         user_message, system_message, conversation_history   |
    |       )  [skip_memory=True, tools disabled, 1 iteration]    |
    |   +-- Save updated history to Redis (TTL 2h)                |
    +--------------------------------------------------------------+
    |
    +--[AUTO-STORE]-----------------------------------------------+
    |   async with session_factory() as NEW session:              |
    |     store_episode(                                          |
    |       content="Faiz: ...\nGuinevere: ...",                  |
    |       classification=RESTRICTED (hardcoded),                |
    |       importance=3 (hardcoded),                             |
    |       summary=content[:200] (naive truncation),             |
    |       tags=["discord","chat","auto-store"] (hardcoded)      |
    |     )                                                       |
    |   +-- embedding.aembed(content) --> FAILS (9Router)         |
    |   +-- store_episode FAILS entirely (embedding error)        |
    |   +-- Episode NOT stored (silent failure)                   |
    +--------------------------------------------------------------+
```

---

## 4. System Prompt Template Analysis

Fetched from VPS: /home/guinevere/config/hermes/system-prompt.md

The system prompt is SystemPromptMaster v1.1, approximately 5000 tokens. It contains:
- Section A: Core Identity Block (Guinevere de Baroque persona)
- Section B: Dominant Behavior Instructions (punishment L1-L5, rewards T1-T5)
- Safety elements verified by prompt_loader.py: HARD STOP, safe word, Y5/Y6, distress

The memory injection appends AFTER the base prompt as:
```
{~5000 token base prompt}

## Recalled Memories
1. {memory}
2. {memory}
3. {memory}

## Current Mood: Content
```

There is NO designated placeholder section in the system prompt template for memories. The injection is purely append-based with markdown headers.

---

## 5. Token Budget Analysis

### 5.1 Current Budget Breakdown

| Component | Tokens (estimated) | Notes |
|-----------|-------------------|-------|
| Base system prompt | ~5000 | From SystemPromptMaster v1.1 |
| Memory context | Up to 400 | limit=3, token_budget=400 |
| Conversation history (Redis) | Up to ~20,000 | 20 turns x ~1000 tokens avg |
| User message | Variable | Typically 50-200 tokens |
| **Total context to LLM** | **~25,600** | With GPT-5.5 1M window: 2.56% |

### 5.2 Proposed Budget (Bridge Spec)

| Component | Tokens (estimated) | Change |
|-----------|-------------------|--------|
| Base system prompt | ~5000 | No change |
| Memory context | Up to 800 | +400 (+100%) |
| Conversation history | Up to ~20,000 | No change |
| User message | Variable | No change |
| **Total context to LLM** | **~26,000** | +400 tokens (2.6% of 1M) |

### 5.3 Cost Impact

With 400 additional tokens per message:
- Input cost increase: negligible at GPT-5.5 pricing
- Context window utilization: 2.56% -> 2.60% of 1M window
- Value gain: 67% more memories, richer context per turn

**Verdict**: The increase from 400 to 800 tokens is strongly justified. The cost is negligible relative to the context window and per-message cost.

---

## 6. Format Comparison — Current vs Proposed

### 6.1 Current Format

```
## Recalled Memories
1. Faiz: Hey can you remind me about the project deadline?
Guinevere: Of course darling, the project X deadline is Friday...
2. Faiz: What's the status of the PostgreSQL migration?
Guinevere: The migration is at 70% completion, sayang...
3. Database migration discussion from last week about schema changes.
```

**Problems**:
- No temporal markers (when was this?)
- No importance signal (which matters most?)
- Raw conversation format is verbose
- No source/type classification
- LLM must infer relevance from raw text

### 6.2 Proposed [RECENT MEMORIES] Format

```
[RECENT MEMORIES]
- [2h ago | importance:8 | conversation] Faiz asked about project X deadline (Friday); Guinevere confirmed
- [1d ago | importance:5 | conversation] PostgreSQL migration status: 70% complete, targeting Wednesday
- [5d ago | importance:3 | conversation] Schema changes discussion for memory episodes table
```

**Advantages**:
- Temporal context: LLM knows recency
- Importance signal: LLM can prioritize
- Source type: LLM knows context origin
- Compressed: More information per token
- Structured: Consistent parseable format

### 6.3 Token Efficiency Comparison

Using the same 3 memories:
- Current format: ~250 tokens (verbose conversation snippets)
- Proposed format: ~120 tokens (structured one-liners)
- **Savings**: ~52% fewer tokens for MORE information

This means with 800 token budget and proposed format, the bridge could fit ~6-7 rich memories instead of 3 sparse ones.

---

## 7. Mood and Context Handling

### 7.1 Current State

- Mood is **always hardcoded to "Content"** (conversational_handler.py:398).
- No dynamic mood evaluation occurs.
- The Mood enum is imported from src.persona.mood_engine but only CONTENT.value is used.
- The mood line is appended to the system prompt: "## Current Mood: Content"

### 7.2 What the Bridge Needs

- Dynamic mood evaluation based on conversation context, distress signals, and punishment state.
- Mood should reflect the persona state, not just default to Content.
- If punishment is active (L1-L5), mood should reflect that (e.g., "Cold Shoulder", "Silent Treatment").
- If distress was detected, mood should shift appropriately.

**Severity**: **Important** — static mood means the persona never shifts based on context, reducing the richness of the companion experience.

---

## 8. Consolidated Gap Register

| ID | Gap | Severity | Location | Bridge Fix |
|----|-----|----------|----------|------------|
| G1 | hard_stop_handler NOT wired | **Critical** | conversational_handler.py:414 | Bridge passes hard_stop_handler to assemble |
| G2 | Embeddings always fail on 9Router | **Critical** | embeddings.py / 9Router config | Bridge adds embedding_enabled flag, skips retry |
| G3 | Auto-store fails entirely on embedding error | **Critical** | write_pipeline.py / conversational_handler.py:525-562 | Bridge stores episode even without embedding |
| G4 | Mood hardcoded to Content | **Important** | conversational_handler.py:398 | Bridge integrates dynamic mood evaluation |
| G5 | Token budget too low (400) | **Important** | conversational_handler.py:421 | Bridge increases to 800 |
| G6 | Memory format lacks metadata | **Important** | prompt_loader.py:80-102 | Bridge uses [RECENT MEMORIES] format |
| G7 | No cross-episode deduplication | **Important** | read_pipeline.py | Bridge adds content similarity dedup |
| G8 | Two DB sessions per message | **Important** | conversational_handler.py:413,537 | Bridge uses single session per lifecycle |
| G9 | EmbeddingService singleton not centralized | **Important** | conversational_handler.py:114-125 | Bridge provides shared registry |
| G10 | Classification always Restricted | **Important** | conversational_handler.py:531 | Bridge adds dynamic classification |
| G11 | Importance always 3 | **Important** | conversational_handler.py:542 | Bridge adds dynamic importance assessment |
| G12 | Summary is naive truncation | **Important** | conversational_handler.py:535 | Bridge uses LLM-based summarization |
| G13 | No total context window management | **Important** | session_adapter.py | Bridge tracks total token budget |
| G14 | Double token budget pass (redundant) | **Nice-to-have** | read_pipeline.py + prompt_loader.py | Bridge consolidates to single pass |
| G15 | No retry on transient DB failure | **Nice-to-have** | conversational_handler.py:406-455 | Bridge adds single-retry logic |
| G16 | Tags hardcoded | **Nice-to-have** | conversational_handler.py:546 | Bridge generates content-aware tags |

---

## 9. Recommendations for Phase 2 Bridge Implementation

### 9.1 Priority 1 — Critical (Must Fix)

1. **Wire hard_stop_handler**: The bridge must accept and pass hard_stop_handler to assemble_system_prompt_with_memory(). This ensures HARD STOP protocol is authoritative, not dependent on DistressDetector pattern matching.

2. **Embedding failure isolation**: Store episodes even when embedding fails (embedding=None). Add an embedding_enabled config flag to skip the 61-second retry loop when 9Router is known to lack embedding support. Add a backfill mechanism for episodes stored without embeddings.

3. **Auto-store resilience**: Decouple embedding computation from episode persistence. The store path should never fail entirely due to embedding unavailability.

### 9.2 Priority 2 — Important (Should Fix)

4. **Increase token budget to 800**: Change limit=5, token_budget=800 in the bridge. Negligible cost increase, significant context improvement.

5. **Adopt [RECENT MEMORIES] format**: Replace the current numbered-list format with structured one-liners including temporal, importance, and source metadata. This improves token efficiency by ~52%.

6. **Dynamic mood evaluation**: Integrate mood engine with punishment state, distress signals, and conversation context. Stop hardcoding "Content".

7. **Single session lifecycle**: Use one DB session per message for both recall and store operations.

8. **Cross-episode deduplication**: Add content similarity check before injecting memories to avoid redundant information consuming token budget.

9. **Centralized EmbeddingService**: Move singleton to a shared module (e.g., src/memory/service_registry.py) accessible by all handlers.

### 9.3 Priority 3 — Nice-to-Have

10. **Single retry on transient DB failures**: Add one retry attempt before falling back to memory-less prompt.

11. **Consolidate double token budget pass**: Remove the redundant pass in get_system_prompt_with_context() since recall_memories() already enforces the budget.

12. **Dynamic metadata generation**: LLM-based summarization, classification, importance assessment, and tag generation for auto-stored episodes.

13. **Total context window tracking**: Track base_prompt + history + memories against model context window limit, prune history if needed.

---

## 10. Footer

| Field | Value |
|-------|-------|
| Report | 04-memory-injection-gap.md |
| Phase | Hermes Phase 2 — Memory Bridge Research |
| Agent | Research Agent 4 |
| Date | 2026-06-04 |
| Status | Complete |
| Verdict | 16 gaps identified (3 critical, 10 important, 3 nice-to-have). Bridge must prioritize hard_stop_handler wiring, embedding failure isolation, and auto-store resilience. Token budget increase to 800 and [RECENT MEMORIES] format are strongly recommended. |
