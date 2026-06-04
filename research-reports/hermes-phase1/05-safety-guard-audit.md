# Hermes Phase 1 — Safety Guard Audit Report

**Date:** 2026-06-03
**Target:** `src/discord/conversational_handler.py` + `src/discord/bot.py`
**Goal:** Trace exact safety guard order, confirm all guards execute BEFORE the LLM call, identify precise insertion point for `HermesSessionAdapter.send_message()`.

---

## Executive Summary

All 13 safety steps execute **BEFORE** the LLM call. Additionally, two pre-LLM guards fire in `bot.py` before `conversational_handler.py` is even entered (HARD STOP listener + `on_message` safe-mode check). The LLM call is at **lines 441–463** of `conversational_handler.py`. The recommended insertion point is **after line 440, before line 441** — replacing lines 441–478 with `HermesSessionAdapter.send_message()`.

---

## 1. Complete Safety Pipeline — Execution Order

### Phase 0: `bot.py` — Pre-Handler Guards (fires BEFORE `on_message`)

| # | Guard | Line(s) | File | Action |
|---|---|---|---|---|
| A | Listener registration | 121 | `bot.py` | `self.listen("on_message")` registers `_on_message_listener` — Discord guarantees listeners fire BEFORE the main `on_message` handler. |
| B | HARD STOP — bot self-check | 131–136 | `bot.py` | `if author is None or author.bot: return` — skips bot messages to prevent self-trigger loops. |
| C | HARD STOP detection | 140–143 | `bot.py` | `handle_safeword_message_async(message)` — calls `HardStopHandler.check(content)` which checks exact triggers (`"hard stop"`, `"safe word"`, `"hentikan"`, etc.) + semantic regex patterns. If consumed, `return` blocks ALL downstream processing. |

### Phase 1: `bot.py` — Main `on_message` Handler (fires AFTER listener)

| # | Guard | Line(s) | File | Action |
|---|---|---|---|---|
| D | Bot self-check | 501–502 | `bot.py` | `if message.author.bot: return` — double-check, redundant with Step B. |
| E | HARD STOP safe-mode check | 504–510 | `bot.py` | `handler.is_safe` — if safe mode active: `handler.check_recovery(message.content)` permits ONLY recovery triggers; all other messages are blocked via `return`. |
| F | Conversational handler dispatch | 513–517 | `bot.py` | `handle_conversation(self, message)` — delegates to the 13-step pipeline. Only reached if NOT in safe mode (Step E passes). |

### Phase 2: `conversational_handler.py` — The 13-Step Pipeline

All steps inside `handle_conversation()`:

| Step | Function | Line(s) | Guard | Action |
|---|---|---|---|---|
| **1** | `handle_conversation` | 284–287 | **Channel check** | `channel.id != GUINEVERE_CHAT_CHANNEL_ID` (ID: 1510914600777023659) → `return False`. Only #guinevere-chat passes. |
| **2** | `handle_conversation` | 290–292 | **Bot user check** | `author is None or author.bot` → `return False`. |
| **3** | `handle_conversation` | 295–297 | **Slash command check** | `not content or content.startswith("/")` → `return False`. |
| **4** | `handle_conversation` | 300–302 | **Faiz-only check** | `guild.owner_id != author.id` → `return False`. Only guild owner passes. |
| **5** | `handle_conversation` | 305–307 | **Rate limiting** | `_is_rate_limited(user_id)` — Redis INCR + EXPIRE, 10 msg/min/user. If limited → `return True` (silently absorbed). |
| **6** | `handle_conversation` | 309–318 | **Typing indicator** | `channel.typing()` context manager wraps `_process_and_respond()`. Visual only, no blocking. |
| **7** | `_process_and_respond` | 344–376 | **Distress detection** | `DistressDetector.detect(content)` + `SafeModeController.evaluate(signal)`. Graceful degradation on error. |
| **8** | `_process_and_respond` | 378–382 | **Mood evaluation** | Defaults to `Mood.CONTENT.value`. Simple assignment, no blocking. |
| **9** | `_process_and_respond` | 384–439 | **System prompt assembly with memory recall** | `assemble_system_prompt_with_memory()` via bot session factory + `EmbeddingService`. Falls back to `get_system_prompt_with_context()` without memories if DB unavailable. Falls further to `FALLBACK_MESSAGE` if system prompt assembly fails entirely. |
| **10** | `_process_and_respond` | **441–463** | **LLM call** | `router.chat(messages_list, ...)` — **THE LLM CALL**. |
| **11** | `_process_and_respond` | 480–483 | **Response formatting** | `_split_response()` + chunked `channel.send()`. |
| **12** | `_process_and_respond` | 485–505 | **Cost tracking** | `CostTracker.record_cost()` with token counts and model config. |
| **13** | `_process_and_respond` | 507–524 | **Structured logging** | structlog with metadata (no content). |

### Key Observation: All Guards Execute BEFORE Step 10

Steps 1–9 are entirely pre-LLM. Step 10 (the LLM call) is the **first** non-guard operation. Steps 11–13 are post-LLM (response delivery, cost, logging).

---

## 2. Current LLM Call — Exact Code Block (Lines 441–478)

```python
441:     # ── Step 10: LLM call ──────────────────────────────────────────────────
442:     from src.core.services.llm_router import TaskType
443:
444:     router = _get_router()
445:     messages_list: list[dict[str, str]] = [
446:         {"role": "system", "content": system_prompt},
447:         {"role": "user", "content": content},
448:     ]
449:
450:     try:
451:         result: dict[str, Any] = await router.chat(
452:             messages_list,
453:             task_type=TaskType.CORE_REASONING,
454:             max_tokens=LLM_MAX_TOKENS,
455:         )
456:     except Exception as exc:
457:         logger.error(
458:             "llm_call_failed",
459:             error=str(exc),
460:             error_type=type(exc).__name__,
461:         )
462:         await channel.send(FALLBACK_MESSAGE)
463:         return True
464:
465:     # Extract response components
466:     choices: list[dict[str, Any]] = result.get("choices", [])
467:     first_choice: dict[str, Any] = choices[0] if choices else {}
468:     message_data: dict[str, Any] = first_choice.get("message", {})
469:     response_text: str = str(message_data.get("content", ""))
470:     usage: dict[str, Any] = result.get("usage", {})
471:     prompt_tokens: int = int(usage.get("prompt_tokens", 0))
472:     completion_tokens: int = int(usage.get("completion_tokens", 0))
473:     model_used: str = str(result.get("model", "unknown"))
474:
475:     if not response_text:
476:         logger.warning("llm_empty_response", model_used=model_used)
477:         await channel.send(FALLBACK_MESSAGE)
478:         return True
```

### What the Current Code Does

1. **Line 442**: Imports `TaskType` (for model config lookup)
2. **Line 444**: Gets the `LLMRouter` singleton
3. **Lines 445–448**: Builds a **stateless** `messages_list` with exactly **2 items**:
   - `{"role": "system", "content": system_prompt}` (assembled in Step 9)
   - `{"role": "user", "content": content}` (raw user message)
4. **Lines 450–455**: Calls `router.chat()` which sends a POST to 9Router with fallback chain (`CX/GPT-5.5` → `DS/DeepSeek-V4-Flash` → `Guinevere` combo)
5. **Lines 456–463**: Catches `Exception`, sends `FALLBACK_MESSAGE` to channel, returns `True`
6. **Lines 466–473**: Extracts `response_text`, `usage` (prompt_tokens, completion_tokens), and `model_used` from the OpenAI-compatible response dict
7. **Lines 475–478**: Empty response guard — sends fallback if response is empty string

### Downstream Dependencies on These Variables

| Variable | Where Used | Line(s) |
|---|---|---|
| `response_text` | Step 11 — `_split_response()` and `channel.send()` | 481–483 |
| `prompt_tokens` | Step 12 — `CostTracker.record_cost()` | 491–497 |
| `completion_tokens` | Step 12 — `CostTracker.record_cost()` | 491–497 |
| `model_used` | Step 12 — `CostTracker.record_cost()` + Step 13 — logging | 491–497, 518 |

---

## 3. HermesSessionAdapter.send_message() Interface

From `src/hermes/session_adapter.py` (lines 170–275):

```python
async def send_message(
    self,
    user_id: str,       # Discord user snowflake (string)
    content: str,        # User message text
    system_prompt: str,  # Assembled system prompt from Step 9
) -> str:               # Response text (or FALLBACK_MESSAGE)
```

### What It Does Internally

1. Gets or creates `AIAgent` instance for `user_id`
2. Loads conversation history from Redis DB4 (`hermes:session:{user_id}`)
3. Calls `agent.run_conversation()` with user message + system prompt + history
4. Appends user + assistant turn to history
5. Prunes history if > `MAX_HISTORY_TURNS` (20 turns = 40 messages)
6. Persists session to Redis with 2-hour TTL
7. Returns `final_response` string (or built-in `FALLBACK_MESSAGE` on failure)

### Key Difference from Current Pattern

| Concern | Current (LLMRouter.chat) | HermesSessionAdapter.send_message |
|---|---|---|
| **Response** | Full OpenAI-compatible `dict` with `choices`, `usage`, `model` | Plain `str` (response text only) |
| **History** | **Stateless** — exactly system+user, no prior context | **Stateful** — loads/prunes/persists conversation history in Redis DB4 |
| **Error handling** | Catches `Exception`, sends `FALLBACK_MESSAGE`, returns `True` | Returns `FALLBACK_MESSAGE` string internally; caller still handles |
| **Fallback chain** | Built into `LLMRouter.chat()` (3-model chain) | Delegates to `AIAgent.run_conversation()` — Hermes handles fallback internally |
| **Token usage** | Extracted from response dict | Not returned — adapter must be modified or alternative tracking used |
| **Model name** | Extracted from response dict | Not returned — adapter must be modified or alternative tracking used |

---

## 4. Recommended Insertion Point

### Exact Location

**Replace lines 441–478** (`# ── Step 10: LLM call` through the empty-response check) with `HermesSessionAdapter.send_message()`.

### Boundary Conditions

| Condition | Value |
|---|---|
| **Before insertion point** | Line 440 (end of Step 9 — `return True` for system prompt failure) |
| **After insertion point** | Line 480 (Step 11 — `_split_response(response_text)` and chunked send) |
| **Variables available** | `content` (user message), `system_prompt` (from Step 9), `author.id` (for `user_id`) |
| **Variables needed downstream** | `response_text`, `prompt_tokens`, `completion_tokens`, `model_used` |

### Required Code Changes

The LLM call block (lines 441–478) must be replaced with:

```python
    # ── Step 10: LLM call via Hermes Session Adapter ──────────────────
    from src.hermes import HermesSessionAdapter

    adapter = _get_hermes_adapter()  # or injected via bot
    try:
        response_text: str = await adapter.send_message(
            user_id=str(author.id),
            content=content,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        logger.error(
            "hermes_llm_call_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        await channel.send(FALLBACK_MESSAGE)
        return True

    if not response_text:
        logger.warning("hermes_empty_response")
        await channel.send(FALLBACK_MESSAGE)
        return True
```

### Critical: Cost Tracking and Token Usage

`HermesSessionAdapter.send_message()` does **not** return token usage or model name. Since Step 12 (CostTracker.record_cost()) and Step 13 (logging) depend on `prompt_tokens`, `completion_tokens`, and `model_used`, one of these approaches is needed:

1. **Modify `HermesSessionAdapter.send_message()`** to return a tuple or dataclass with `(response_text, prompt_tokens, completion_tokens, model_used)` — requires accessing `agent.run_conversation()` internals.
2. **Separate cost estimation** — use a rough cost estimator based on response length (less accurate but simpler).
3. **Track via intermediate** — parse usage from `AIAgent`'s last API call metadata if exposed.

**Recommendation:** Option 1 (modify the adapter to return usage metadata). The adapter's `run_conversation()` call returns a dict; the adapter already has access to the raw response data internally.

---

## 5. Safety Pipeline Integrity Verification

### Confirmed: All 13 guard steps execute BEFORE the LLM call

```
bot.py Phase 0:  Listener (A) -> Bot self-check (B) -> HARD STOP detection (C)
     |
     v
bot.py Phase 1:  Bot self-check (D) -> Safe-mode check (E) -> Dispatch (F)
     |
     v
conversational_handler.py Phase 2:
     Step 1:  Channel check              (line 284-287)
     Step 2:  Bot check                  (line 290-292)
     Step 3:  Slash command check        (line 295-297)
     Step 4:  Faiz-only check            (line 300-302)
     Step 5:  Rate limiting              (line 305-307)
     Step 6:  Typing indicator           (line 309-318)
          |
          v
     _process_and_respond():
     Step 7:  Distress detection         (line 344-376)
     Step 8:  Mood evaluation            (line 378-382)
     Step 9:  System prompt assembly     (line 384-439)
          |
          v  <-- INSERTION POINT (after line 440, before line 441)
     Step 10: LLM call                   (line 441-463)  <-- REPLACE THIS
          |
          v
     Step 11: Response formatting/send   (line 480-483)
     Step 12: Cost tracking              (line 485-505)
     Step 13: Structured logging         (line 507-524)
```

### No safety guard is bypassed by replacing the LLM call

- Steps 1–9 are **upstream** of the insertion point and unaffected
- Step 11 (response send) is **downstream** and receives `response_text` — same contract
- Steps 12–13 depend on token counts — adapter must return these or alternative tracking used

### Safety boundaries NOT disturbed by Hermes integration

| Concern | Status |
|---|---|
| Channel restriction (#guinevere-chat) | Step 1 — unchanged |
| Bot user filtering | Steps 2, D — unchanged |
| Slash command passthrough | Step 3 — unchanged |
| Faiz-only enforcement | Step 4 — unchanged |
| Rate limiting | Step 5 — unchanged |
| Distress detection | Step 7 — unchanged |
| Mood evaluation | Step 8 — unchanged |
| System prompt assembly | Step 9 — unchanged |
| HARD STOP listener | Steps B-C — unchanged (fires before conversational flow) |
| Safe-mode blocking | Step E — unchanged (fires before `handle_conversation`) |
| Response delivery | Step 11 — unchanged |
| Cost tracking | Step 12 — needs minor refactor (Hermes adapter doesn't return token counts) |
| Structured logging | Step 13 — needs minor refactor (model_used not returned by adapter) |

---

## 6. Stateless vs Stateful Pattern Summary

| Aspect | Current (LLMRouter) | Hermes Adapter |
|---|---|---|
| `messages_list` | Exactly `[system, user]` (2 items) | History loaded from Redis + prepended |
| Session persistence | None | Redis DB4 with 2-hour TTL |
| History pruning | N/A | Keeps last 20 turns (40 messages) |
| User identification | None | `user_id` (Discord snowflake) |
| Model | `cx/gpt-5.5` (CORE_REASONING) | Configured at adapter init time |

---

## 7. Final Verification Checklist

| Item | Status |
|---|---|
| All pre-LLM guards confirmed (Steps 1-9) | ✅ |
| HARD STOP guard fires BEFORE all other processing | ✅ |
| Insertion point identified (line 440/441 boundary) | ✅ |
| Replacement block identified (lines 441-478) | ✅ |
| Downstream variable dependencies mapped | ✅ |
| Cost tracking impact identified | ⚠️ (needs adapter change or estimator) |
| Logging impact identified | ⚠️ (model_used not available) |
| `HermesSessionAdapter` import path confirmed (`src.hermes`) | ✅ |
| `HermesSessionAdapter.send_message()` signature confirmed | ✅ |

---

## 8. Key Files Referenced

| File | Lines | Relevance |
|---|---|---|
| `src/discord/bot.py` | 115-143, 485-519 | HARD STOP listener + `on_message` safe-mode check |
| `src/discord/conversational_handler.py` | 265-526 | All 13 safety steps + LLM call |
| `src/core/services/llm_router.py` | 58-104 | Current `LLMRouter.chat()` implementation |
| `src/hermes/session_adapter.py` | 74-275 | `HermesSessionAdapter.send_message()` implementation |
| `src/hermes/__init__.py` | 1-9 | Package exports |
| `src/discord/cmd_safeword.py` | 643-711, 276-288 | `handle_safeword_message_async` + `_get_handler` |
| `src/core/services/hard_stop_handler.py` | 34-149 | `HardStopHandler` state machine |

---

## 9. Raw Line Reference — LLM Call Replacement Zone

```python
# conversational_handler.py, _process_and_respond(), lines 440-480

440:                                 # <- END of Step 9 (system prompt assembly)
441:     # -- Step 10: LLM call --
442:     from src.core.services.llm_router import TaskType
443:
444:     router = _get_router()
445:     messages_list: list[dict[str, str]] = [
446:         {"role": "system", "content": system_prompt},
447:         {"role": "user", "content": content},
448:     ]
449:
450:     try:
451:         result: dict[str, Any] = await router.chat(
452:             messages_list,
453:             task_type=TaskType.CORE_REASONING,
454:             max_tokens=LLM_MAX_TOKENS,
455:         )
456:     except Exception as exc:
457:         logger.error(
458:             "llm_call_failed",
459:             error=str(exc),
460:             error_type=type(exc).__name__,
461:         )
462:         await channel.send(FALLBACK_MESSAGE)
463:         return True
464:
465:     # Extract response components
466:     choices: list[dict[str, Any]] = result.get("choices", [])
467:     first_choice: dict[str, Any] = choices[0] if choices else {}
468:     message_data: dict[str, Any] = first_choice.get("message", {})
469:     response_text: str = str(message_data.get("content", ""))
470:     usage: dict[str, Any] = result.get("usage", {})
471:     prompt_tokens: int = int(usage.get("prompt_tokens", 0))
472:     completion_tokens: int = int(usage.get("completion_tokens", 0))
473:     model_used: str = str(result.get("model", "unknown"))
474:
475:     if not response_text:
476:         logger.warning("llm_empty_response", model_used=model_used)
477:         await channel.send(FALLBACK_MESSAGE)
478:         return True
479:
480:     # -- Step 11: Format and send response --
```

**Entire block to replace:** Lines 441–478 (38 lines).
**Boundary variable:** `system_prompt` (set at line 398, available at line 440).
**Boundary variable:** `content` (parameter, available throughout).
**Boundary variable:** `author.id` (set at line 305 as `user_id`, available as `author.id`).
