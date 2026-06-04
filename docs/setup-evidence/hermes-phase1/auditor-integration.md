# Hermes Phase 1 — Integration Audit Report

**Audit date:** 2026-06-04  
**Scope:** `src/hermes/`, `src/discord/conversational_handler.py`, `src/discord/cmd_new_session.py`, `src/discord/cmd_history.py`, `src/discord/bot.py`  
**Verdict:** NEEDS REVIEW (1 finding requires fix before shipping)

---

## Verdict Summary

| Criterion | Result |
|---|---|
| AIAgent: skip_memory=True, skip_context_files=True, quiet_mode=True, max_iterations=1, no tools | ✅ PASS |
| run_conversation() params: user_message, system_message, conversation_history | ✅ PASS |
| Redis DB4 (not DB0/2/3/5) for session storage | ✅ PASS |
| TTL 7200s on session keys | ✅ PASS |
| History capped at 20 turns (40 messages) | ✅ PASS |
| No bare except / empty catch | ✅ PASS |
| No type safety suppression in Hermes integration | ✅ PASS |
| Error handling: typed exceptions, graceful fallback | ✅ PASS |
| Cost tracking uses Hermes metadata (get_last_metadata) | ✅ PASS |
| Auto-store uses store_episode with classification=RESTRICTED | ✅ PASS |
| /new and /history have Faiz-only guards | ✅ PASS |
| Safety guard order: HARD STOP → rate limit → distress → mood → prompt → Hermes | ✅ PASS |
| **Singleton consistency: one `HermesSessionAdapter` instance used project-wide** | ❌ NEEDS REVIEW |

---

## Finding 1: Duplicate `HermesSessionAdapter` Instances (NEEDS REVIEW)

**Severity:** Medium — not a correctness bug today, but a correctness risk tomorrow.

### What's happening

Two separate `HermesSessionAdapter` singletons exist in separate modules:

| Module | Caller | How created |
|---|---|---|
| `src/hermes/__init__.py` | `get_adapter()` — used by `/new`, `/history` | `HermesSessionAdapter(redis_client=None, llm_config={...})` |
| `src/discord/conversational_handler.py:148` | `_get_hermes()` — used by conversational handler | `HermesSessionAdapter(redis_client=None, llm_config={...})` |

Both pass `redis_client=None`, which triggers the adapter's `__init__` to create a **new async Redis connection to DB4**. That means **two separate Redis connections, two separate `_agents` caches, and two separate `_last_metadata` stores**.

### Why it mostly works today

- Both Redis connections point to the same DB4, so `DELETE` (from `/new`), `SETEX`, and `GET` operations target the same keys.
- `send_message()` sets `_last_metadata[user_id]` and `get_last_metadata()` reads it — both on the conversational handler's instance, within the same call flow. No cross-instance metadata access happens.
- `AIAgent` is stateless (history lives in Redis), so separate `_agents` caches are harmless.
- `/new` deletes the Redis key via its adapter; the conversational handler's adapter loads empty `history` from Redis on the next `send_message` call.

### What's wrong

1. **Two idle Redis connections to DB4** when one would suffice — wasteful but not breaking.
2. **Bifurcated config**: the `llm_config` is duplicated in `__init__.py:27-33` and `conversational_handler.py:160-166`. If someone updates one and not the other, the system silently runs with two different configs depending on code path.
3. **Future risk**: if any module ever calls `get_last_metadata()` on the wrong adapter instance, it gets an empty dict and cost tracking silently reports zero tokens.
4. **Violates the stated intent**: `hermes/__init__.py` docstring says "shared singleton" and `get_adapter()` is the documented API. The conversational handler bypasses it entirely.

### How to fix

Edit `conversational_handler.py` to use `get_adapter()` instead of creating its own instance:

```python
# conversational_handler.py, _get_hermes() — current (L148-166)
def _get_hermes() -> Any:
    global _hermes
    if _hermes is None:
        from src.hermes import HermesSessionAdapter
        _hermes = HermesSessionAdapter(
            redis_client=None,
            llm_config={...},
        )
    return _hermes

# Replace with:
def _get_hermes() -> Any:
    from src.hermes import get_adapter
    return get_adapter()
```

Then remove the module-level `_hermes` variable and the duplicated `llm_config` dict. The existing `get_adapter()` already creates the same `llm_config`.

**Effort:** Quick (<1h)

---

## Audit Criterion Walkthrough

### 1. AIAgent configuration (`session_adapter.py:112-123`)

```python
AIAgent(
    base_url=llm_config["base_url"],
    model=llm_config["model"],
    provider=llm_config["provider"],
    api_key=llm_config.get("api_key", ""),
    skip_memory=True,
    skip_context_files=True,
    quiet_mode=True,
    max_iterations=1,
    enabled_toolsets=[],
    disabled_toolsets=["*"],
)
```

✅ All flags match spec. `enabled_toolsets=[]` + `disabled_toolsets=["*"]` ensures zero tool access.

### 2. run_conversation() call (`session_adapter.py:166-171`)

```python
result: dict[str, Any] = await asyncio.to_thread(
    agent.run_conversation,
    user_message=content,
    system_message=system_prompt,
    conversation_history=history,
)
```

✅ Correct keyword arguments. `asyncio.to_thread` offloads the sync `run_conversation` from the event loop.

### 3. Redis DB4 (`session_adapter.py:26, 83-89`)

```python
REDIS_DB: int = 4

self._redis = aioredis.Redis(..., db=REDIS_DB, ...)
```

✅ DB4. Rate limiter uses DB0, cost tracker uses DB5 — no collision.

### 4. TTL 7200s (`session_adapter.py:30, 212`)

```python
SESSION_TTL: int = 7200

await self._redis.setex(key, SESSION_TTL, json.dumps(session_data, ...))
```

✅ 2-hour idle TTL applied on every `send_message`.

### 5. History pruning (`session_adapter.py:33, 126-135`)

```python
MAX_HISTORY_TURNS: int = 20

max_messages = MAX_HISTORY_TURNS * 2  # = 40
if len(history) > max_messages:
    excess = len(history) - max_messages
    return history[excess:]
```

✅ 20 turns = 40 messages. Oldest truncated, newest retained.

### 6. No bare except / empty catch

- `session_adapter.py`: All except blocks either specify typed exceptions (`json.JSONDecodeError`, `ConnectionError`, `OSError`) or use `except Exception as exc:` with structured `logger.warning`/`logger.error` calls.
- `conversational_handler.py`: Same pattern — typed where possible, `except Exception as exc:` with logging + graceful degradation for external calls.
- `cmd_new_session.py`, `cmd_history.py`: Use `except Exception:` (no `as exc`) but call `logger.exception(...)` which captures full traceback. Not bare/empty.

✅ No suppression, no swallowed errors.

### 7. No type safety suppression

- `src/hermes/`: zero matches for `type: ignore`, `as any`, `@ts-ignore`, `@ts-expect-error`.
- `src/discord/bot.py:33` has a pre-existing `# type: ignore[assignment]` for dynamic `discord.ext.commands` import — unrelated to Hermes.

✅ Clean.

### 8. Error handling + graceful fallback

- `send_message()` wraps `run_conversation` in `except Exception` → returns `FALLBACK_MESSAGE`.
- Redis load errors are caught and degrade to empty history.
- Redis save errors are caught and logged as non-fatal.
- `conversational_handler` wraps every external call (distress, memory, hermes, cost, auto-store) in try/except → never crashes the handler.
- All fallbacks have structured logging with `user_id_hash`, `error_type`, `error`.

✅ Graceful under all failure modes.

### 9. Cost tracking via get_last_metadata (`conversational_handler.py:291-294`)

```python
hermes_metadata: dict[str, Any] = hermes.get_last_metadata(str(author.id))
prompt_tokens: int = int(hermes_metadata.get("input_tokens", 0))
completion_tokens: int = int(hermes_metadata.get("output_tokens", 0))
model_used: str = str(hermes_metadata.get("model", "unknown"))
```

✅ Called immediately after `send_message()` on the same adapter instance.

### 10. Auto-store with RESTRICTED classification (`conversational_handler.py:320-338`)

```python
from src.memory.write_pipeline import RESTRICTED, store_episode
...
await store_episode(
    session=session,
    content=conversation_content,
    source="discord_conversation",
    classification=RESTRICTED,
    importance=3,
    summary=conversation_summary,
    episode_type="conversation",
    tags=["discord", "chat", "auto-store"],
    embedding_service=embedding_svc,
)
```

✅ `classification=RESTRICTED`, `store_episode` from `write_pipeline`, wrapped in try/except.

### 11. Faiz-only guards (`cmd_new_session.py:35-37`, `cmd_history.py:57-59`)

```python
if not is_faiz_interaction(interaction):
    await send_denied(interaction)
    return
```

`is_faiz_interaction` in `commands.py:288-299` checks `guild.owner_id == user.id` — dynamic guild-owner check, no hardcoded ID.

✅ Faiz-exclusive access. `send_denied` sends ephemeral rejection.

### 12. Safety guard order

```
_on_message_listener (HARD STOP) → listener runs first, sets safe mode
    ↓
on_message() → checks handler.is_safe, returns if active
    ↓
handle_conversation()
    ├─ Step 4: Faiz check (guild owner)
    ├─ Step 5: Rate limiting
    └─ _process_and_respond()
        ├─ Step 7: Distress detection + safe mode activation
        ├─ Step 8: Mood evaluation
        ├─ Step 9: System prompt assembly
        └─ Step 10: Hermes multi-turn call
```

✅ HARD STOP listener fires before `on_message`; `on_message` blocks non-recovery messages in safe mode; conversational handler runs guards before Hermes.

---

## Minor Observations (no action required)

1. **`_is_rate_limited` has a redundant except block** (`conversational_handler.py:177-185`): the broad `except Exception` catches everything the preceding `except (ConnectionError, OSError)` also catches. The first block is dead code. Harmless — both return `False` (fail open).
2. **No `dispose()` call on bot shutdown**: `GuinevereBot.close()` doesn't close the Hermes Redis connection. The OS will clean up on process exit, but adding `await get_adapter().dispose()` in `close()` would be cleaner.
3. **`except Exception:` without `as exc` in `cmd_new_session.py:67` and `cmd_history.py:107`**: `logger.exception(...)` still captures the traceback, so logging quality is unaffected. Minor style point.

---

## Evidence

- Files read: `src/hermes/__init__.py`, `src/hermes/session_adapter.py`, `src/discord/conversational_handler.py`, `src/discord/cmd_new_session.py`, `src/discord/cmd_history.py`, `src/discord/bot.py`, `src/discord/commands.py` (L288-299)
- Grep: type suppression scan across `src/hermes/` and `src/discord/`
- No tests executed (audit is read-only code review)

---

## Acceptance Criteria Mapping

| AC | Description | Result |
|---|---|---|
| Multi-turn Hermes session replaces stateless LLMRouter.chat() | ✅ `send_message()` loads history from Redis, passes to `run_conversation()`, saves updated history |
| No safety guard bypass | ✅ HARD STOP, rate limit, distress, mood all run before Hermes |
| Faiz-only /new and /history | ✅ Guild owner check via `is_faiz_interaction` |
| Conversations auto-stored as RESTRICTED | ✅ `store_episode` with `classification=RESTRICTED` |
| Cost tracking from Hermes metadata | ✅ `get_last_metadata()` → `CostTracker.record_cost()` |
| One shared adapter instance | ❌ Two instances exist (Finding 1) |