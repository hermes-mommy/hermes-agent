# Conversational Handler Memory Fix — Batch Plan

> **Date**: 2026-06-03
> **Scope**: Wire memory recall into conversational_handler.py, remove TODO(P9)
> **Status**: APPROVED FOR IMPLEMENTATION

---

## 1. Problem Statement

`conversational_handler.py` (459 lines) currently calls `get_system_prompt_with_context(memories=None, mood=...)` — no memory recall occurs. The `TODO(P9)` comment at line 359 acknowledges this gap. Production code must not contain unresolved TODOs.

## 2. Solution Design

### 2.1 Replace step 9 with `assemble_system_prompt_with_memory()`

**Current (broken):**
```python
from src.core.services.prompt_loader import get_system_prompt_with_context
system_prompt = get_system_prompt_with_context(memories=None, mood=current_mood)
```

**Target (fixed):**
```python
from src.core.services.prompt_loader import assemble_system_prompt_with_memory
from src.memory.embeddings import EmbeddingService

# Get session factory from bot
session_factory_fn = getattr(bot, "get_session_factory", None)
if session_factory_fn is not None:
    session_factory = session_factory_fn()
    if session_factory is not None:
        embedding_svc = _get_embedding_service()
        async with session_factory() as session:
            system_prompt = await assemble_system_prompt_with_memory(
                session=session,
                query_text=content,
                mood=current_mood,
                safe_mode=safe_mode_activated,
                principal="guinevere_core",
                limit=3,
                token_budget=400,
                embedding_service=embedding_svc,
            )
    else:
        # DB not configured — graceful degradation
        system_prompt = get_system_prompt_with_context(memories=None, mood=current_mood)
else:
    system_prompt = get_system_prompt_with_context(memories=None, mood=current_mood)
```

### 2.2 EmbeddingService singleton

Add `_embedding_service` module-level singleton with `_get_embedding_service()` lazy getter (matches existing `_get_router()`, `_get_cost_tracker()` pattern).

### 2.3 Session factory via bot dependency injection

`bot.get_session_factory()` already exists (bot.py:275-306). Returns `async_sessionmaker` or `None`. Pattern matches `cmd_memory_search.py` (lines 375-407).

### 2.4 Error handling

Wrap recall in try/except. On failure: log metadata, fallback to `get_system_prompt_with_context(memories=None, mood=...)`. Never crash.

## 3. Step Scaffolds

### Step 1: Modify conversational_handler.py

| Field | Value |
|---|---|
| **Expected Files** | `src/discord/conversational_handler.py` (modified) |
| **Forbidden Patterns** | `TODO`, `as any`, `@ts-ignore`, `# type: ignore`, empty `except:` |
| **Required Commands** | `grep -n "TODO" src/discord/conversational_handler.py` → 0 results |
| **Evidence** | `docs/setup-evidence/conversational-handler/memory-fix-verification.md` |
| **Hard Rejection** | Any TODO remaining; recall_memories not called; safe_mode not propagated; exclude_dnr not True |

### Step 2: Create tests

| Field | Value |
|---|---|
| **Expected Files** | `tests/discord/test_conversational_handler.py` (new) |
| **Forbidden Patterns** | `as any`, `# type: ignore`, empty catch |
| **Required Commands** | `python -m pytest tests/discord/test_conversational_handler.py -v` → exit 0 |
| **Evidence** | Same verification.md |
| **Hard Rejection** | Any test failure; missing coverage for memory recall, safe_mode, DNR, fallback |

### Step 3: Verify + audit

| Field | Value |
|---|---|
| **Expected Files** | `docs/setup-evidence/conversational-handler/memory-fix-verification.md` |
| **Required Commands** | `lsp_diagnostics` → 0 new errors |
| **Auditor Checks** | Memory integration correct, safe_mode propagated, DNR exclude_dnr=True, no TODO, no Any where proper type exists, no empty catch |

## 4. Dependency Map

```
Step 1 (code fix) → Step 2 (tests) → Step 3 (verify + audit)
```

All sequential. No parallelism possible (single file change).

## 5. Collision Scan

| File | Owner | Notes |
|---|---|---|
| `src/discord/conversational_handler.py` | This task | Only writer |
| `tests/discord/test_conversational_handler.py` | This task | New file |
| `src/discord/bot.py` | NOT MODIFIED | No changes needed — `bot` param already passed |

No collisions.

## 6. Rollback Plan

Revert conversational_handler.py to current state (459 lines, TODO(P9) version). Zero data loss.

## 7. Key Integration Points

- `assemble_system_prompt_with_memory()` at `src/core/services/prompt_loader.py:119-182`
  - Takes: `session: RecallSession`, `query_text: str`, `mood: str`, `safe_mode: bool`, `hard_stop_handler: object | None`, `principal: str`, `limit: int`, `token_budget: int`, `embedding_service: EmbeddingClient | None`
  - Returns: `str` (assembled prompt)
  - Internally calls `recall_memories()` then `get_system_prompt_with_context()`

- `bot.get_session_factory()` at `src/discord/bot.py:275-306`
  - Returns `async_sessionmaker` or `None`
  - Lazy-creates from `DATABASE_URL` env var
  - `async with session_factory() as session:` yields `AsyncSession`

- `EmbeddingService()` at `src/memory/embeddings.py:402-671`
  - Constructor: no required args
  - Has `aembed()` async method matching `EmbeddingClient` protocol

- `cmd_memory_search.py` pattern (lines 375-416) — canonical session factory + recall usage

## 8. Safety Constraints

- `safe_mode_activated` from step 7 (DistressDetector) MUST propagate to `assemble_system_prompt_with_memory(safe_mode=...)`
- `exclude_dnr=True` is hardcoded in `assemble_system_prompt_with_memory()` (line 165)
- `principal="guinevere_core"` — may read up to Critical classification
- `limit=3` memories — bounded for conversational latency
- `token_budget=400` — ~1600 chars of memory context, leaves room for system prompt + response
- Graceful degradation: if DB unavailable or recall fails, fall back to base prompt (no crash)
