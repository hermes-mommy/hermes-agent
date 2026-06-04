# Current Memory Flow Analysis — Hermes Phase 2 Research

> **Date**: 2026-06-04
> **Scope**: Discord conversational message → memory recall → system prompt injection → response → auto-store
> **Files Analyzed**: conversational_handler.py, read_pipeline.py, prompt_loader.py, embeddings.py, session_adapter.py, write_pipeline.py

---

## 1. Complete Flow Trace

### 1.1 Entry Point: Discord Message Received

**File**: `src/discord/conversational_handler.py`
**Function**: `handle_conversation(bot, message) -> bool`

```
handle_conversation(bot, message)
  │
  ├── Step 1: Channel check (must be #guinevere-chat, ID 1510914600777023659)
  ├── Step 2: Bot check (reject bot authors)
  ├── Step 3: Slash command check (reject /-prefixed)
  ├── Step 4: Faiz check (guild owner only)
  ├── Step 5: Rate limiting (Redis INCR, 10 msg/min/user, DB0 port 6380)
  ├── Step 6: Typing indicator
  └── _process_and_respond(bot, author, channel, content, start_time)
```

**Error handling**: Each guard returns `False` (pass-through) or `True` (silently absorbed for rate limit). Redis failures in `_is_rate_limited()` default to `False` (allow through).

---

### 1.2 Core Flow: `_process_and_respond()`

**Function signature**:
```python
async def _process_and_respond(
    bot: Any,           # GuinevereBot instance
    author: Any,        # discord.Member
    channel: Any,       # discord.TextChannel
    content: str,       # cleaned message text
    start_time: float,  # time.time() for latency
) -> bool
```

#### Step 7: Distress Detection
```python
from src.persona.safe_mode import DistressDetector, SafeModeController
detector = DistressDetector()
controller = SafeModeController()
signal = detector.detect(content)
safe_mode_activated = controller.evaluate(signal)
```
- **On failure**: Creates neutral `DistressSignal` (D0_NORMAL), `safe_mode_activated = False`
- **Bottleneck**: Fresh `DistressDetector()` and `SafeModeController()` instantiated per message (no singleton)

#### Step 8: Mood Evaluation
```python
from src.persona.mood_engine import Mood
current_mood: str = Mood.CONTENT.value  # Always "Content" — hardcoded
```
- **Gap**: Mood is always hardcoded to `Content`. No dynamic mood evaluation occurs.

---

### 1.3 Step 9: Memory Recall — THE CRITICAL PATH

**File**: `src/discord/conversational_handler.py:400-455`
**Calls into**: `src/core/services/prompt_loader.py:assemble_system_prompt_with_memory()`
**Which calls**: `src/memory/read_pipeline.py:recall_memories()`

#### 1.3.1 Session Factory Resolution
```python
session_factory_fn = getattr(bot, "get_session_factory", None)
session_factory = session_factory_fn() if session_factory_fn else None
```
- **Pattern**: Duck-typed — `bot` must have `get_session_factory()` method
- **On None**: Falls back to `get_system_prompt_with_context(memories=None, mood=...)` — base prompt only, NO memories
- **Gap**: If `bot.get_session_factory` is not defined, memory is silently skipped with only a log warning

#### 1.3.2 EmbeddingService Initialization
```python
embedding_svc = _get_embedding_service()  # Lazy singleton
```
- **Singleton**: Module-level `_embedding_service`, created once via `EmbeddingService()`
- **Config**: Uses `EmbeddingConfig()` defaults:
  - `base_url = "http://localhost:20128/v1"` (9Router)
  - `model = "openai/text-embedding-3-small"`
  - `expected_dimension = 1536`
  - API key from env: `GUINEVERE_9ROUTER_API_KEY` or `OPENROUTER_API_KEY`
- **CRITICAL GAP**: 9Router does NOT serve embedding models (HTTP 400). The embedding call WILL fail.

#### 1.3.3 Assembly Call
```python
async with session_factory() as session:
    system_prompt = await assemble_system_prompt_with_memory(
        session=session,
        query_text=content,       # raw user message
        mood=current_mood,        # always "Content"
        safe_mode=safe_mode_activated,
        principal="guinevere_core",
        limit=3,                  # max 3 memories
        token_budget=400,         # 400 tokens for memory context
        embedding_service=embedding_svc,
    )
```

#### 1.3.4 Inside `assemble_system_prompt_with_memory()`
**File**: `src/core/services/prompt_loader.py:119-182`

```python
async def assemble_system_prompt_with_memory(
    session: RecallSession,
    query_text: str,
    *,
    mood: str = "Content",
    safe_mode: bool = False,
    hard_stop_handler: object | None = None,  # NOT passed by handler
    principal: str = "guinevere_core",
    limit: int = 3,
    token_budget: int = DEFAULT_TOKEN_BUDGET,  # overridden to 400 by handler
    embedding_service: EmbeddingClient | None = None,
) -> str:
```

**Flow**:
1. Resolve `safe_mode` — `hard_stop_handler` is authoritative if provided (but handler does NOT pass it)
2. Call `recall_memories()` with all params
3. On `ReadPipelineSafetyError`: return base prompt + mood (no memories)
4. Call `get_system_prompt_with_context(memories=results, mood=mood, token_budget=400)`

**Gap**: `hard_stop_handler` is never passed by `conversational_handler.py`. The handler computes `safe_mode_activated` from `DistressDetector`/`SafeModeController` but passes it directly as `safe_mode` parameter. The `hard_stop_handler` override mechanism in `assemble_system_prompt_with_memory()` is unused.

#### 1.3.5 Inside `recall_memories()`
**File**: `src/memory/read_pipeline.py:727-917`

```python
async def recall_memories(
    session: RecallSession,
    query_text: str,
    limit: int = 20,
    *,
    exclude_dnr: bool = True,
    safe_mode: bool = False,
    principal: str = "guinevere_core",
    embedding_service: EmbeddingClient | None = None,
    token_budget: int = DEFAULT_TOKEN_BUDGET,  # 4000 default, 400 from handler
) -> RecallResults:
```

**Execution sequence**:

1. **Input validation**: `query_text` must be non-empty (raises `ReadPipelineQueryError`)

2. **Query embedding** (optional):
   ```python
   if embedding_service is not None:
       try:
           query_vector = await embedding_service.aembed(query_text_stripped)
       except Exception:
           # Graceful fallback: keyword-only search
           query_vector = None
   ```
   - **EMBEDDING FAILURE**: Silently falls back to FTS-only + recency. No error propagation.
   - **9Router reality**: This will ALWAYS fail (HTTP 400 for embedding models), so vector search NEVER works in production.

3. **Classification ceiling resolution**:
   ```python
   ceiling_label = _resolve_ceiling(principal, safe_mode)
   # Normal: guinevere_core → Critical (level 4)
   # Safe mode: guinevere_core → Internal (level 1)
   ```

4. **Three parallel signal queries** (sequential, not actually parallel):
   - **Vector query** (if `query_vector` available): `pgvector <=>` cosine distance, `expanded_limit` rows
   - **FTS query**: `plainto_tsquery('english', query_text)` + `ts_rank()`, `expanded_limit` rows
   - **Recency query**: `ORDER BY started_at DESC`, `expanded_limit` rows
   - `expanded_limit = min(limit * 3, 200)` → with `limit=3`, this is `min(9, 200) = 9`

5. **RRF Fusion** (`build_result_episode_map`):
   - Deduplicates episodes across all three signals
   - Records vector_rank and fts_rank per episode

6. **Score computation** (`compute_scored_results`):
   ```
   combined_score = RRF_score * recency_boost * importance_boost
   where:
     RRF_score = vector_weight/(k+vector_rank) + fts_weight/(k+fts_rank)
                 * both_signal_bonus (1.25x if found by both)
     recency_boost = 1.0 + 0.10 * exp(-days * ln(2) / 90)
     importance_boost = 0.5 + 0.5 * (importance/10)
   ```

7. **Classification ceiling filter**: Remove episodes above ceiling level

8. **Limit**: Take top `limit` (3) results

9. **Safe content building** (`build_safe_content`):
   - Normal mode: prefer summary if 20%+ shorter than raw
   - Safe mode: Critical→placeholder, Restricted/Confidential→summary only, Public/Internal→check blocked tags

10. **Token budget enforcement** (`apply_token_budget`):
    - Budget = 400 tokens (passed by handler)
    - Estimate: `len(text) // 4` chars per token
    - Trim from bottom (lowest-scored first)
    - With 400 tokens, that's ~1600 characters total across all 3 memories

#### 1.3.6 System Prompt Assembly (`get_system_prompt_with_context`)
**File**: `src/core/services/prompt_loader.py:41-116`

```python
def get_system_prompt_with_context(
    memories: list[dict] | list[str] | None = None,
    mood: str = "Content",
    *,
    token_budget: int = DEFAULT_TOKEN_BUDGET,  # 4000 default, 400 from handler
) -> str:
```

**Assembly**:
1. Load base prompt from `/home/guinevere/config/hermes/system-prompt.md`
2. Safety validation: must contain "HARD STOP", "safe word"/"safeword", "Y5"/"Y6", "distress"
3. If no memories: `base_prompt + "\n\n## Current Mood: {mood}"`
4. If memories: `base_prompt + "\n\n## Recalled Memories\n1. {content}\n2. {content}\n3. {content}\n\n## Current Mood: {mood}"`
5. **Second token budget pass**: Memories are trimmed again against `token_budget` (400)

**DOUBLE BUDGET ISSUE**: Memories are budget-trimmed in `recall_memories()` (400 tokens) AND again in `get_system_prompt_with_context()` (400 tokens). The second pass is redundant but harmless.

---

### 1.4 Step 10: Hermes Call

**File**: `src/discord/conversational_handler.py:457-478`
**Calls into**: `src/hermes/session_adapter.py:send_message()`

```python
hermes = _get_hermes()  # Shared singleton via src.hermes.get_adapter()
response_text = await hermes.send_message(
    user_id=str(author.id),
    content=content,
    system_prompt=system_prompt,  # assembled prompt with memories
)
```

#### Inside `HermesSessionAdapter.send_message()`

```python
async def send_message(
    self,
    user_id: str,
    content: str,
    system_prompt: str,
) -> str:
```

**Flow**:
1. Get or create `AIAgent` for user (in-memory cache `self._agents`)
2. Load history from Redis DB4: key `hermes:session:{user_id}`
3. Call `agent.run_conversation()` offloaded to thread:
   ```python
   result = await asyncio.to_thread(
       agent.run_conversation,
       user_message=content,
       system_message=system_prompt,    # system prompt injected HERE
       conversation_history=history,
   )
   ```
4. Extract `final_response` from result dict
5. Store metadata (tokens, model, cost) in `self._last_metadata[user_id]`
6. Append user+assistant turn to history
7. Prune history to `MAX_HISTORY_TURNS` (20 turns = 40 messages)
8. Persist to Redis with TTL 7200s (2 hours)

**AIAgent configuration**:
```python
AIAgent(
    base_url=llm_config["base_url"],     # 9Router
    model=llm_config["model"],           # GPT-5.5 or DeepSeek
    provider=llm_config["provider"],
    api_key=llm_config.get("api_key", ""),
    skip_memory=True,                     # Hermes native memory DISABLED
    skip_context_files=True,
    quiet_mode=True,
    max_iterations=1,
    enabled_toolsets=[],
    disabled_toolsets=["*"],              # ALL tools disabled
)
```

**KEY INSIGHT**: Hermes is used as a **stateless LLM wrapper**. Native memory disabled, all tools disabled, max 1 iteration. The only "memory" is the Redis-managed conversation history (20 turns max) and the Guinevere-managed memory recall injected into the system prompt.

**Error handling**: Any exception in `run_conversation()` returns `FALLBACK_MESSAGE`. Redis load/save failures are logged but non-fatal.

---

### 1.5 Step 11-12: Response Delivery + Cost Tracking

```python
# Split and send
chunks = _split_response(response_text)  # max 3 chunks, 2000 chars each
for chunk in chunks:
    await channel.send(chunk)

# Cost tracking
tracker = _get_cost_tracker()
await asyncio.to_thread(
    tracker.record_cost,
    model=model_used,
    input_tokens=prompt_tokens,
    output_tokens=completion_tokens,
    cost_per_1k_input=...,
    cost_per_1k_output=...,
)
```

---

### 1.6 Step 12b: Auto-Store Conversation

**File**: `src/discord/conversational_handler.py:525-562`
**Calls into**: `src/memory/write_pipeline.py:store_episode()`

```python
from src.memory.write_pipeline import RESTRICTED, store_episode

conversation_content = f"Faiz: {content}\nGuinevere: {response_text}"
conversation_summary = content[:200]  # First 200 chars of user message

async with session_factory() as session:
    await store_episode(
        session=session,
        content=conversation_content,
        source="discord_conversation",
        classification=RESTRICTED,           # Always Restricted
        importance=3,                        # Always 3 (low-medium)
        summary=conversation_summary,
        episode_type="conversation",
        tags=["discord", "chat", "auto-store"],
        embedding_service=embedding_svc,
    )
```

#### Inside `store_episode()`
**File**: `src/memory/write_pipeline.py:111-227`

1. **Critical guard**: N/A (classification is Restricted)
2. **Embedding computation**:
   ```python
   vector = await service.aembed(
       content,                              # full conversation text
       classification="Restricted",          # auto-redaction applied
       sanitized_summary=None,
   )
   ```
   - Restricted classification triggers `_redact_sensitive()` before sending to 9Router
   - **Will fail** with 9Router (HTTP 400), so `embedding = None`
3. **ORM object creation**: `Episodes(raw_content=..., embedding=None, ...)`
4. **Persist**: `session.add(episode); await session.flush()`
5. **Return**: `uuid.UUID` of new episode

**Auto-store error handling**: Entire block wrapped in `try/except Exception` — never crashes the conversation. Failure is logged as `memory_auto_store_error`.

---

## 2. Database Connection Pattern

| Component | Connection | DB | Port | Usage |
|-----------|-----------|-----|------|-------|
| Memory recall | `bot.get_session_factory()` → `AsyncSession` | PostgreSQL `guinevere` | 5433 | Read episodes |
| Memory store | `bot.get_session_factory()` → `AsyncSession` | PostgreSQL `guinevere` | 5433 | Write episodes |
| Rate limiting | `redis.asyncio.Redis` | Redis DB0 | 6380 | INCR/EXPIRE |
| Session history | `redis.asyncio.Redis` | Redis DB4 | 6380 | JSON GET/SETEX |
| Cost tracking | `CostTracker` (sync, threaded) | Redis DB5 | 6380 | (inferred) |

**Pattern**: PostgreSQL sessions are created per-operation via `async with session_factory() as session`. Two separate sessions are opened per message — one for recall (Step 9), one for store (Step 12b).

**Bottleneck**: Two DB connections opened and closed per message. No connection pooling visible at this layer (relies on SQLAlchemy engine pool underneath).

---

## 3. Embedding Dependency Analysis

### What breaks when embeddings fail (current reality with 9Router):

| Step | Impact | Severity |
|------|--------|----------|
| **Recall (Step 9)** | Vector similarity search skipped. Only FTS + recency signals work. RRF fusion has 2/3 signals. | Medium — FTS is still functional |
| **Auto-store (Step 12b)** | Episodes stored with `embedding=None`. Future vector recall has NO vectors to search. | Critical — vector index degrades over time |
| **Retry behavior** | `_acall_with_retry` retries 6x with exponential backoff (1s, 2s, 4s, 8s, 16s, 30s = 61s total) | High — adds ~61s latency per embedding call |

### Current failure chain:
```
User message → recall_memories()
  → embedding_service.aembed(query) FAILS (HTTP 400 from 9Router)
  → retry 6x over ~61 seconds
  → finally raises EmbeddingAPIError
  → caught by broad `except Exception` in recall_memories()
  → query_vector = None (keyword-only fallback)
  → FTS + recency only, no vector signal
  → memories returned (if FTS matches exist)
  
→ store_episode()
  → _compute_embedding() called
  → embedding_service.aembed(content) FAILS
  → retry 6x over ~61 seconds  
  → raises EmbeddingAPIError
  → propagates to handler's try/except
  → auto-store silently fails
  → conversation episode NOT stored
```

**CRITICAL**: The retry loop means a single failed embedding call adds ~61 seconds of latency. With two embedding calls per message (recall + store), worst case is ~122 seconds of wasted wait time.

**ACTUAL BEHAVIOR NOTE**: The recall path catches embedding failure broadly (`except Exception` at line 803), but the store path lets `_compute_embedding()` failure propagate, which means the entire auto-store fails if embeddings are unavailable.

---

## 4. Identified Gaps and Bottlenecks

### 4.1 Critical Gaps

| # | Gap | Impact | Location |
|---|-----|--------|----------|
| G1 | **Embeddings always fail** on 9Router (HTTP 400) | Vector recall never works; auto-store silently fails | `embeddings.py:83`, 9Router config |
| G2 | **61s retry latency** on every failed embedding call | User waits 1-2 minutes for response when embeddings fail | `embeddings.py:382-394` |
| G3 | **Auto-store failure = no episode saved** | When embedding fails, the ENTIRE store_episode() fails, not just the embedding portion | `write_pipeline.py:181-187` |
| G4 | **No bridge abstraction** between handler and memory system | Handler directly orchestrates session_factory, embedding_service, recall, and store — tightly coupled | `conversational_handler.py:400-562` |
| G5 | **Double session creation** per message | Two separate `async with session_factory()` — one for recall, one for store | `conversational_handler.py:413,537` |

### 4.2 Design Gaps

| # | Gap | Impact |
|---|-----|--------|
| G6 | **Mood hardcoded to Content** | No dynamic mood evaluation; persona behavior is static |
| G7 | **hard_stop_handler not wired** | `assemble_system_prompt_with_memory` supports it but handler never passes it |
| G8 | **Importance always 3** | Auto-stored conversations always get importance=3 regardless of content significance |
| G9 | **Classification always Restricted** | All auto-stored conversations are Restricted; no dynamic classification |
| G10 | **Summary is naive truncation** | `content[:200]` — first 200 chars of user message, not an actual summary |
| G11 | **No deduplication** | Every message creates a new episode; no check for duplicate/similar content |
| G12 | **Token budget double-pass** | Memories budgeted at 400 tokens in recall, then again at 400 in prompt assembly (redundant) |

### 4.3 Safety Gaps

| # | Gap | Impact |
|---|-----|--------|
| G13 | **No consent check on auto-store** | Conversations auto-stored without explicit per-message consent verification |
| G14 | **No content classification analysis** | Classification is hardcoded Restricted; sensitive content not dynamically detected |
| G15 | **Recalled memories not audited** | No verification that recalled memories are appropriate for current context |
| G16 | **System prompt not size-bounded** | Base prompt loaded from file with no total size check; could overflow context window with large prompt + memories |

### 4.4 Code Duplication / Bridge Needs

| Area | Current Code | Bridge Would Provide |
|------|-------------|---------------------|
| Session factory access | `getattr(bot, "get_session_factory", None)` duplicated in Steps 9 and 12b | Single `bridge.get_session()` |
| Embedding service | `_get_embedding_service()` singleton in handler | `bridge.get_embedding_service()` with health check |
| Error fallback | Two separate try/except blocks with similar fallback logic | `bridge.recall()` and `bridge.store()` with unified error handling |
| Conversation formatting | Inline `f"Faiz: {content}\nGuinevere: {response_text}"` | `bridge.format_conversation(user_msg, assistant_msg)` |
| Summary generation | `content[:200]` | `bridge.generate_summary()` (LLM-based) |
| Classification | Hardcoded `RESTRICTED` | `bridge.classify_content()` (dynamic) |
| Importance | Hardcoded `3` | `bridge.assess_importance()` (dynamic) |
| Tag generation | Hardcoded `["discord", "chat", "auto-store"]` | `bridge.generate_tags()` (content-aware) |

---

## 5. Token Budget Analysis

| Component | Budget | Actual Usage |
|-----------|--------|-------------|
| Memory recall (read_pipeline) | 400 tokens | Up to 400 tokens of safe_content |
| System prompt assembly (prompt_loader) | 400 tokens (second pass) | Redundant with above |
| Base system prompt | Unbounded | Loaded from file, no size check |
| Conversation history (Redis) | 20 turns × ~2000 chars | Up to ~20,000 tokens |
| Total context sent to Hermes | Unbounded | base_prompt + memories + history + user_message |

**Gap**: No total context window management. If base prompt is large (Persona Document can be 5000+ chars) + 20 turns of history + 3 memories, total could approach or exceed model limits.

---

## 6. Data Flow Diagram

```
Discord Message (Faiz in #guinevere-chat)
    │
    ▼
handle_conversation()
    │ Guard checks (channel, bot, slash, Faiz, rate limit)
    ▼
_process_and_respond()
    │
    ├── DistressDetector.detect(content) → safe_mode_activated
    ├── Mood = "Content" (hardcoded)
    │
    ├── ┌─ Memory Recall ──────────────────────────────────┐
    │   │ bot.get_session_factory() → AsyncSession          │
    │   │ EmbeddingService.aembed(query) → FAILS (9Router)  │
    │   │ FTS query → Episodes matching query text          │
    │   │ Recency query → Recent Episodes                   │
    │   │ RRF fusion → scored + filtered (3 results)        │
    │   │ Safe content building (classification-aware)      │
    │   │ Token budget trim (400 tokens)                    │
    │   └──────────────────────────────────────────────────┘
    │
    ├── ┌─ System Prompt Assembly ─────────────────────────┐
    │   │ load_system_prompt() from /home/guinevere/config/ │
    │   │ + "## Recalled Memories\n1. ...\n2. ...\n3. ..."  │
    │   │ + "## Current Mood: Content"                      │
    │   └──────────────────────────────────────────────────┘
    │
    ├── ┌─ Hermes Call ────────────────────────────────────┐
    │   │ Redis DB4: load session history (20 turns max)    │
    │   │ AIAgent.run_conversation(                         │
    │   │   user_message=content,                           │
    │   │   system_message=assembled_prompt,                 │
    │   │   conversation_history=history,                   │
    │   │ )                                                 │
    │   │ skip_memory=True, tools disabled, 1 iteration     │
    │   │ Redis DB4: save updated history (TTL 2h)          │
    │   └──────────────────────────────────────────────────┘
    │
    ├── ┌─ Response Delivery ──────────────────────────────┐
    │   │ _split_response() → max 3 chunks × 2000 chars    │
    │   │ channel.send(chunk) for each                      │
    │   └──────────────────────────────────────────────────┘
    │
    ├── ┌─ Cost Tracking ──────────────────────────────────┐
    │   │ CostTracker.record_cost() via asyncio.to_thread   │
    │   └──────────────────────────────────────────────────┘
    │
    └── ┌─ Auto-Store ─────────────────────────────────────┐
        │ bot.get_session_factory() → NEW AsyncSession      │
        │ EmbeddingService.aembed(content) → FAILS (9Router)│
        │ store_episode() FAILS (embedding error propagates)│
        │ Episode NOT stored (silent failure)               │
        └──────────────────────────────────────────────────┘
```

---

## 7. Summary of Failure Points

| # | Failure Point | Current Behavior | User Impact |
|---|--------------|------------------|-------------|
| F1 | 9Router embedding HTTP 400 | 6x retry → 61s wait → fail | 1-2 min latency per message |
| F2 | Auto-store embedding failure | Entire store_episode fails | Conversations never saved to memory |
| F3 | No session factory on bot | Silent skip, no memories | No memory context ever |
| F4 | System prompt file missing | Fallback message sent | "I'm having trouble thinking" |
| F5 | Hermes run_conversation exception | Fallback message sent | "Maaf, aku sedang kesulitan..." |
| F6 | Redis session load failure | Fresh history (0 turns) | Lost conversation context |
| F7 | Redis session save failure | Logged, non-fatal | Next message starts fresh |
| F8 | All memories filtered by classification ceiling | ReadPipelineSafetyError → base prompt | No memory context |
| F9 | Token budget too small (400) | All memories trimmed | Minimal memory context |
| F10 | DistressDetector failure | Safe mode OFF, neutral signal | Potential safety gap |

---

## 8. Recommendations for Bridge Design

A `HermesMemoryBridge` should address:

1. **Embedding failure isolation**: Store episode even when embedding fails (store with `embedding=None`, backfill later)
2. **Latency budget**: Short-circuit embedding calls when 9Router is known to lack embedding support (configurable `embedding_enabled` flag)
3. **Single session lifecycle**: One session per message, not two
4. **Dynamic metadata**: Classify content, assess importance, generate tags, produce real summaries
5. **Consent verification**: Check surveillance/consent policy before auto-store
6. **Total context budgeting**: Track base_prompt + history + memories against model context window
7. **Health check caching**: Cache embedding service availability to avoid 61s retry on every message
8. **hard_stop_handler wiring**: Pass through to `assemble_system_prompt_with_memory()`
