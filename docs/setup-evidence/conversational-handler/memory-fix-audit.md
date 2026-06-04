# Audit Report: conversational_handler.py Memory Recall Integration

| Field | Value |
|---|---|
| **Date** | 2026-06-03 |
| **Auditor** | Guinevere (automated read-only audit) |
| **File** | `src/discord/conversational_handler.py` (517 lines) |
| **Supporting Files** | `src/core/services/prompt_loader.py` (lines 119-182), `src/memory/read_pipeline.py` (lines 727-737) |
| **Overall Verdict** | **PASS** |

---

## Check A: Memory Integration — PASS

| Criterion | Status | Evidence |
|---|---|---|
| `assemble_system_prompt_with_memory` is called | PASS | Line 389: `system_prompt = await assemble_system_prompt_with_memory(...)` |
| Session obtained via `bot.get_session_factory()` | PASS | Lines 383-384: `getattr(bot, "get_session_factory", None)` → `session_factory_fn()` |
| `EmbeddingService()` passed as `embedding_service` | PASS | Line 387: `embedding_svc = _get_embedding_service()` → Line 397: `embedding_service=embedding_svc` |
| `limit=3` and `token_budget=400` bounded for latency | PASS | Lines 395-396: `limit=3, token_budget=400` |
| `principal="guinevere_core"` is set | PASS | Line 394: `principal="guinevere_core"` |
| Graceful fallback when session factory unavailable | PASS | Lines 404-410: falls back to `get_system_prompt_with_context(memories=None, mood=current_mood)` with `logger.info("memory_recall_skipped", reason="no_session_factory")` |

---

## Check B: Safety Propagation — PASS

| Criterion | Status | Evidence |
|---|---|---|
| `safe_mode_activated` passed to `assemble_system_prompt_with_memory(safe_mode=...)` | PASS | Line 393: `safe_mode=safe_mode_activated` |
| `exclude_dnr=True` hardcoded in `assemble_system_prompt_with_memory` | PASS | `prompt_loader.py` line 165: `exclude_dnr=True` (inside `recall_memories()` call) |
| Distress detection error does not crash handler | PASS | Lines 350-367: `except Exception` creates neutral `DistressSignal(D0_NORMAL)`, sets `safe_mode_activated = False`, logs warning |

---

## Check C: Code Quality — PASS

| Criterion | Status | Evidence |
|---|---|---|
| `grep "TODO"` → 0 results | PASS | No matches found |
| No `as any`, `@ts-ignore`, `# type: ignore`, `@ts-expect-error` | PASS | No matches found |
| No empty `except:` blocks | PASS | `grep "except\s*:"` returned 0 matches; all except clauses specify explicit exception types |
| No raw content logging | PASS | All 12 `logger.*()` calls verified — only metadata logged (hash, length, latency, error types, model name, token counts). `query_length=len(content)` at line 401 logs length, not content. |
| `_embedding_service` singleton follows lazy pattern | PASS | Lines 108-119: identical lazy-init pattern to `_get_router()` (lines 80-91) and `_get_cost_tracker()` (lines 94-105) — global check, lazy import, assign, return |

---

## Check D: Error Handling — PASS

| Criterion | Status | Evidence |
|---|---|---|
| Session factory None → graceful fallback | PASS | Lines 386-410: `if session_factory is not None` branch; else falls back to `get_system_prompt_with_context(memories=None, ...)` |
| `recall_memories` exception → fallback to base prompt | PASS | Lines 411-430: outer `except Exception` at line 411 catches any recall failure, inner try at line 418 falls back to `get_system_prompt_with_context`. Additionally `prompt_loader.py` lines 171-176 catches `ReadPipelineSafetyError` and returns base prompt. |
| LLM failure → `FALLBACK_MESSAGE` sent | PASS | Lines 447-454: `except Exception` → `logger.error("llm_call_failed", ...)` → `await channel.send(FALLBACK_MESSAGE)` |
| Redis failure → rate limit returns False | PASS | Lines 168-183: `(ConnectionError, OSError)` handler returns `False`; generic `Exception` handler returns `False`. Both log warnings with hashed user ID. |
| System prompt assembly failure → `FALLBACK_MESSAGE` sent | PASS | Lines 423-430: inner `except (FileNotFoundError, ValueError)` → `logger.error("system_prompt_assembly_error", ...)` → `await channel.send(FALLBACK_MESSAGE)` |

---

## Check E: Data Protection — PASS

| Criterion | Status | Evidence |
|---|---|---|
| No raw message content logged | PASS | All 12 logger calls verified — none log `content` variable directly. Closest is `query_length=len(content)` (line 401) which logs only the integer length. |
| No raw memory content logged | PASS | No memory recall results or memory text appears in any logger call. |
| User ID hashed (SHA-256) before logging | PASS | Lines 171, 179: `hashlib.sha256(str(user_id).encode()).hexdigest()[:8]` in rate limit handlers. Lines 499-501: same pattern for response logging. |
| Query text length logged, not content | PASS | Line 401: `query_length=len(content)` — integer length only, no raw text |

---

## Findings and Recommendations

### Findings

1. **All five audit checks PASS.** The memory recall integration is correctly implemented with proper safety propagation, error handling, and data protection.

2. **Dual-layer fallback chain is robust.** The implementation has three fallback layers: (1) full memory recall → (2) base prompt without memories → (3) `FALLBACK_MESSAGE`. This ensures the handler never crashes.

3. **Session factory access pattern is safe.** Using `getattr(bot, "get_session_factory", None)` with a `None` check gracefully handles the case where the bot doesn't expose a session factory (e.g., during testing or partial initialization).

### Recommendations (Non-Blocking)

1. **Consider structured typing for `_embedding_service`.** The `Any` type annotation on the singleton variables (lines 67-77) is functional but could be improved with `EmbeddingService | None` for better IDE support. Not blocking since the lazy import pattern requires deferred type resolution.

2. **`async with session_factory()` context manager.** Line 388 correctly uses `async with session_factory() as session:` ensuring proper session cleanup. This follows the `cmd_memory_search.py` reference pattern.

---

## Summary

| Check | Verdict |
|---|---|
| A. Memory Integration | **PASS** |
| B. Safety Propagation | **PASS** |
| C. Code Quality | **PASS** |
| D. Error Handling | **PASS** |
| E. Data Protection | **PASS** |
| **Overall** | **PASS** |

The memory recall integration in `conversational_handler.py` correctly replaces the previous `get_system_prompt_with_context(memories=None)` call with `assemble_system_prompt_with_memory(session, query_text, ...)` which internally invokes `recall_memories()`. All safety parameters are properly propagated, error handling is comprehensive with multi-layer fallbacks, and no raw user content or memory data is exposed in logs.
