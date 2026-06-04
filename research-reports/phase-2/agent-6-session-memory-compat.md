# Phase 2: Session + Memory Bridge Compatibility Analysis

**Date**: 2026-06-04  
**Target**: Hermes Agent built-in session/memory vs. Custom Guinevere Implementation  
**Scope**: `src/hermes/session_adapter.py`, `src/hermes/memory_bridge.py`, `src/discord/conversational_handler.py`  
**Status**: Read-only research completed  

---

## 1. Session Adapter Analysis (`src/hermes/session_adapter.py`)

### Redis Key Format & Data Structure
- **Key Pattern**: `hermes:session:{user_id}` (where `user_id` is the raw Discord snowflake string).
- **Data Structure**: JSON object containing:
  - `history`: Array of `{role: "user" | "assistant", content: string}`.
  - `created_at`: ISO-8601 timestamp of session creation.
  - `last_used`: ISO-8601 timestamp of last interaction.
  - `turn_count`: Integer representing number of user+assistant pairs.

### Session Lifecycle
- **Create**: Implicitly created on first `send_message()` call if Redis key is missing.
- **Read**: Loaded via `redis.get(key)` at the start of every `send_message()` call.
- **Update**: New user/assistant turn appended, history pruned, then saved.
- **Expire**: Managed via `redis.setex(key, SESSION_TTL, ...)`. 
  - `SESSION_TTL = 7200` seconds (2 hours idle TTL).

### AIAgent Wrapper Configuration
Hermes native memory is **explicitly disabled** to prevent conflict with custom memory:
```python
AIAgent(
    base_url="http://localhost:20128/v1",
    model="ds/deepseek-v4-flash",
    provider="9router",
    api_key="sk-local",
    skip_memory=True,           # CRITICAL: Disables Hermes internal memory
    skip_context_files=True,
    quiet_mode=True,
    max_iterations=1,
    enabled_toolsets=[],
    disabled_toolsets=["*"],    # CRITICAL: Disables all Hermes tools
)
```

### Agent Cache Mechanism
- **In-Memory Cache**: `_agents: dict[str, AIAgent]` keyed by `user_id`.
- **Behavior**: Avoids re-instantiating the `AIAgent` object per message. 
- **State**: The `AIAgent` instance itself is stateless; all conversational state is delegated to Redis. 
- **Cleanup**: `_agents.pop(user_id)` is called only via explicit `clear_session()` (e.g., `/new` slash command), **not** on Redis TTL expiry.

---

## 2. Memory Bridge Analysis (`src/hermes/memory_bridge.py`)

### `recall_for_context()`
- **Return Format**: `list[dict[str, object]]`. Each dict contains: `id`, `safe_content`, `classification`, `importance`, `created_at`, `combined_score`, `is_summarized`.
- **Max Items**: Controlled by `limit` parameter (default: `5`).
- **Delegation**: Wraps `src.memory.read_pipeline.recall_memories()`.

### `store_conversation()`
- **Trigger**: Called asynchronously via `asyncio.create_task()` in `conversational_handler.py` (fire-and-forget).
- **Stored Data**: 
  - `content`: Formatted as `"Faiz: {user_message}\nGuinevere: {assistant_response}"`.
  - `classification`: Hardcoded to `RESTRICTED`.
  - `importance`: Hardcoded to `3`.
  - `tags`: `["discord", "chat", f"user:{user_id_hash}"]`.
  - `metadata`: Includes `channel`, `user_hash`, `response_length`, `safe_mode`.
- **Embedding Bypass**: Explicitly passes `embedding_service=None` to `store_episode()` to prevent crashes (9Router lacks embedding models). Relies on FTS-only recall until a backfill job runs.

### Safety Mechanisms (Delegated)
- **DNR Exclusion**: Enforced by passing `exclude_dnr=True` to `recall_memories()`.
- **Classification Ceiling**: Enforced by passing `principal="guinevere_core"` to `recall_memories()`.
- **Safe-Mode Integration**: Boolean `safe_mode` is passed to both `recall_memories()` (to substitute critical content) and stored in `store_conversation()` metadata for downstream filtering.

---

## 3. Conversational Handler Pipeline (`src/discord/conversational_handler.py`)

### Session & Memory Interaction (13-Step Pipeline)
1. **Guard Checks**: Channel, bot, slash command, Faiz (guild owner) validation.
2. **Rate Limiting**: Redis DB0, 10 msg/min/user.
3. **Distress Detection**: `DistressDetector` evaluates content.
4. **Safe Mode Evaluation**: `SafeModeController` evaluates distress signal.
5. **Mood Evaluation**: Defaults to `Content`.
6. **Memory Recall**: `HermesMemoryBridge.recall_for_context()` (awaited).
7. **Prompt Assembly**: `get_system_prompt_with_context()` + `ANTI_HALLUCINATION_GUARD` if no memories.
8. **Hermes LLM Call**: `HermesSessionAdapter.send_message()` (awaited, offloaded to thread).
9. **Response Formatting**: `_split_response()` into Discord-safe chunks (max 3 chunks, 2000 chars each).
10. **Discord Send**: Chunked delivery with typing indicator.
11. **Cost Tracking**: Extracts metadata from `_last_metadata` and records via `CostTracker`.
12. **Auto-Store Memory**: `asyncio.create_task(bridge.store_conversation(...))` (fire-and-forget).
13. **Structured Logging**: `structlog` emits metadata-only event.

### Hermes vs. Custom Logic Boundary
- **Hermes Responsibility**: *Strictly* LLM generation with injected conversation history. No tools, no native memory, no safety evaluation.
- **Custom Logic Responsibility**: All guardrails, distress detection, memory recall, memory storage, cost tracking, response chunking, and anti-hallucination prompting.

### Error Handling Between Session and Memory
- **Graceful Degradation**: Universal pattern. No exceptions bubble up to Discord.
- **Redis Load Failure**: Logs warning, proceeds with empty `history` (fresh session).
- **LLM Call Failure**: Logs error, returns `FALLBACK_MESSAGE` ("Maaf, aku sedang kesulitan berpikir jernih...").
- **Memory Recall Failure**: Logs warning, proceeds with `memories=None` and injects `ANTI_HALLUCINATION_GUARD`.
- **Memory Store Failure**: Logs warning, silently discarded (does not block user response).

---

## 4. Edge Cases & Compatibility Gaps

### ⚠️ Gap 1: Fire-and-Forget Memory Store Race Condition
- **Issue**: `store_conversation` is invoked via `asyncio.create_task()`. If the bot process shuts down, restarts, or the event loop closes before the task completes, the memory is lost silently.
- **Impact**: Data loss on graceful shutdown or unexpected crash. No retry queue exists.
- **Mitigation**: Consider switching to a persistent background job queue (e.g., Celery/Redis Streams) or awaiting the task with a timeout during shutdown hooks.

### ⚠️ Gap 2: In-Memory Agent Cache Leak
- **Issue**: `HermesSessionAdapter._agents` dict grows unbounded with unique `user_id`s. While `AIAgent` is lightweight, long-running bots with many unique users will accumulate orphaned `AIAgent` instances in memory.
- **Impact**: Memory leak over time. Redis TTL expiry (2 hours) does **not** trigger cleanup of the in-memory `_agents` dict.
- **Mitigation**: Implement an LRU cache (e.g., `functools.lru_cache` or a custom TTL dict) or periodically prune `_agents` keys that no longer exist in Redis.

### ⚠️ Gap 3: Metadata Race Condition (Low Probability)
- **Issue**: `_last_metadata` is a shared dict updated in `send_message()` and read immediately after in `conversational_handler.py`. If the same user sends two messages in rapid succession (bypassing rate limits), the second call could overwrite `_last_metadata[user_id]` before the first call reads it.
- **Impact**: Incorrect cost tracking attribution.
- **Mitigation**: Return metadata directly from `send_message()` as part of the response tuple, rather than relying on a shared state dict.

### ⚠️ Gap 4: FTS-Only Memory Storage (Phase 2 Constraint)
- **Issue**: `store_conversation` explicitly passes `embedding_service=None` to avoid 9Router embedding crashes. 
- **Impact**: All newly stored conversations lack vector embeddings. Recall relies entirely on PostgreSQL Full-Text Search (FTS). Semantic similarity search will fail for these new episodes until a dedicated backfill job runs.
- **Mitigation**: Document this as a known Phase 2 limitation. Ensure Phase 3 includes an embedding backfill cron job.

### ⚠️ Gap 5: Stale Session Context Reset
- **Issue**: Redis `SESSION_TTL` is 2 hours. If Faiz returns after 2 hours of inactivity, Redis returns `None`, and a fresh session is created.
- **Impact**: Loss of conversational context after 2 hours of idle time.
- **Mitigation**: This is likely by design to prevent unbounded context growth, but should be explicitly documented in the PRD. If long-term context is desired, consider implementing a "session resume" feature that loads the last N turns from episodic memory instead of Redis.

---

## 5. Summary & Recommendations

The current implementation successfully isolates Hermes Agent's native capabilities, delegating all safety, memory, and session management to Guinevere's custom pipelines. This aligns with the Phase 2 architecture.

**Critical Actions Before Phase 2 Deployment**:
1. **Fix Metadata Return**: Refactor `send_message()` to return `(response_text, metadata_dict)` to eliminate the `_last_metadata` race condition.
2. **Prune Agent Cache**: Implement an LRU or TTL-based eviction policy for the in-memory `_agents` dict to prevent memory leaks.
3. **Shutdown Hook**: Add an `await` for pending `store_conversation` tasks in the bot's graceful shutdown sequence (`src/discord/bot.py`).
4. **Document FTS Limitation**: Explicitly note in Phase 2 release notes that new memories are FTS-only until the Phase 3 embedding backfill is deployed.

---
*Generated by Guinevere Research Agent | Read-only analysis*
