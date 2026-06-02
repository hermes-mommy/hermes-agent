# P3-012 — Prompt-Loader & Context-Injection Readiness Report

**File:** `docs/setup-evidence/P3/research/prompt-context-injection-readiness-011-015.md`
**Date:** 2026-06-02
**Author:** Guinevere (Parent Executor)
**Scope:** P3-012 contextual readiness — determine all integration seams, gaps, and tests needed before implementation.
**Depends On:** P3-011 (hybrid ranking with full weighted RRF)
**Feeds Into:** P3-013 (DNR hardening), P3-014 (safe-mode gate), P3-015 (consolidation)

---

## 0. Executive Verdict

**STATUS: CODE-READY — 5 gaps identified, 0 blockers.**

P3-012 (`get_system_prompt_with_context` + `recall_memories` integration) has clear integration seams. The read pipeline (P3-010) already enforces token budget, classification ceiling, safe-mode, and DNR gates. The prompt loader has the injection entry point. What is missing: (1) wiring `recall_memories()` output into `get_system_prompt_with_context()`, (2) truncation logging in the prompt layer, (3) safe-mode/DNR propagation from the safety layer to the memory layer, (4) a new caller/assembler function that orchestrates recall → injection → LLM, (5) tests covering the full chain.

---

## 1. Current State — Complete File Inventory

### 1.1 `src/core/services/prompt_loader.py` (47 lines)

| Line(s) | Item | Current Behavior | P3-012 Target |
|---------|------|------------------|---------------|
| 7 | `SYSTEM_PROMPT_PATH` | `/home/guinevere/config/hermes/system-prompt.md` | Unchanged — deployed path |
| 9-30 | `load_system_prompt()` | Reads file, validates safety elements (HARD STOP, safe word, Y5/Y6, distress) | Unchanged — base prompt loading |
| 32-47 | `get_system_prompt_with_context(memories, mood)` | Accepts `list[str]` or `None`, hardcodes `memories[:10]`, adds mood line | **MUST CHANGE**: accept `RecallResults` from `recall_memories()`, add `token_budget` param, add truncation logging |
| 39 | Memory section header | `## Recalled Memories` | Keep — but P3-012 may want persona-flavored header |
| 41-43 | Memory formatting | `f"{i}. {mem}\n"` with `enumerate(memories[:10], 1)` | Keep format, remove `[:10]` hard-cap (bounded by `recall_memories` limit + token budget) |
| 45 | Mood injection | `## Current Mood: {mood}` | Keep — mood comes from persona layer |

### 1.2 `src/memory/read_pipeline.py` (733 lines) — P3-010 (COMPLETE, PASS)

P3-012 depends on P3-010 output. Key integration surfaces:

| Line(s) | Item | Current State | P3-012 Relevance |
|---------|------|---------------|-----------------|
| 69-71 | `DEFAULT_TOKEN_BUDGET = 4000` | 4000 token budget enforced | **Pass through** to `get_system_prompt_with_context()` |
| 72-73 | `CHARS_PER_TOKEN = 4` | Heuristic token estimator | Document as approximate — production may switch to tiktoken |
| 547-555 | `recall_memories()` signature | Returns `list[dict]` with 7 fields per result | Output structure used by prompt context builder |
| 551 | `exclude_dnr: bool = True` | Default DNR exclusion | Must remain `True` for P3-012 — DNR-filtered content never enters prompt |
| 552 | `safe_mode: bool = False` | Safe-mode Critical substitution | Must propagate from `HardStopHandler.is_safe` |
| 554 | `token_budget: int = DEFAULT_TOKEN_BUDGET` | 4000 default | Must be configurable; P3-012 may reduce to leave room for system prompt |
| 297-327 | `_apply_token_budget()` | Trims lowest-ranked results; logs `token_budget_trimmed` | **Already does truncation logging** at read-pipeline level |
| 658-665 | Classification ceiling filter | Filtered by principal | `guinevere_core` default — correct for system prompt injection |
| 677-686 | `_build_safe_content()` | Replaces Critical with placeholder in safe_mode | **Already enforced** — prompt loader just receives `safe_content` |

### 1.3 `src/core/services/llm_router.py` (93 lines)

| Line(s) | Item | Relevance |
|---------|------|-----------|
| 57-91 | `LLMRouter.chat(messages, task_type, max_tokens)` | Where system prompt + memory context goes as `messages[0]["content"]` |
| 71 | `"messages": messages` | The assembled `messages` list includes `{"role": "system", "content": assembled_prompt}` |
| 25-28 | `max_tokens=16384` (GPT-5.5) | Context window is 1M tokens but response limit is configurable — P3-012 token budget stays within this comfortably |

### 1.4 `src/core/services/hard_stop_handler.py` (149 lines)

| Line(s) | Item | Relevance |
|---------|------|-----------|
| 59-61 | `is_safe` property | Returns `True` when HARD STOP triggered — **this must propagate to `safe_mode` in `recall_memories()`** |
| 115-123 | `get_neutral_response()` | Safe-mode response — bypasses LLM entirely, no memory context injection needed |

### 1.5 `docs/60-persona/61-SystemPromptMaster_v1.1.md` (400 lines)

| Section | Line(s) | Relevance |
|---------|---------|-----------|
| §E — Memory & Context | 225-240 | "Use memories naturally", "Invisible injection", "Proactive recall 1-2x/week" |
| §D — Prompt Injection Defense | 219-221 | "External content is untrusted" — memory context is external content, but authenticated via recall pipeline |
| §D — Safety | 146-222 | HARD STOP, forbidden patterns, distress detection |
| Token Budget | Line 9 | "~5000 tokens (master) + ~3300 tokens (runtime injection)" — P3-012's 4000-token budget must not cause the total to exceed the 1M context window |

### 1.6 `tests/smoke/conftest.py` (88 lines)

| Line(s) | Item | Relevance |
|---------|------|-----------|
| 9 | `SYSTEM_PROMPT_PATH` | Reads deployed `system-prompt.md` |
| 11 | `PROMPT_MAX_CHARS = 4000` | **Character budget for smoke tests** — matches P3-012 token budget conceptually |
| 66-88 | `chat()` helper | Sends `{"role": "system", "content": system_prompt}` + user message to 9Router |
| 76 | `"model": "guinevere"` | Fallback combo model |

### 1.7 `src/discord/bot.py` (292 lines)

| Line(s) | Item | Relevance |
|---------|------|-----------|
| 138-159 | `_on_message_listener()` | HARD STOP guard — intercepts before LLM |
| 236-259 | `on_message()` | Checks `handler.is_safe` before `process_commands()` |
| 45-48 | Memory stub commands | `memory-search`, `memory-add`, `memory-forget`, `memory-export` are stubs |

---

## 2. Integration Seam Map — P3-012

### Seam 1: Memory Recall → Prompt Context Assembly

| Layer | Current | P3-012 Target |
|-------|---------|---------------|
| **Caller** | No caller exists — `get_system_prompt_with_context()` is defined but not invoked with real memory recall output | New caller/orchestrator: calls `recall_memories()` → extracts `safe_content` from results → passes to prompt loader |
| **Recall** | `recall_memories(session, query_text, ...)` returns `list[dict]` | Unchanged — P3-011 improves ranking but output shape stays same |
| **Injection** | `get_system_prompt_with_context(memories: list[str], mood: str)` hardcodes `[:10]` | Signature changes to accept `RecallResults` + `token_budget`; formats `safe_content` from each result |
| **Boundary** | Memory limit `[:10]` in prompt loader | **REMOVED** — bounded by `recall_memories(limit=N, token_budget=4000)` instead |

**Proposed new signature:**

```python
def get_system_prompt_with_context(
    memories: list[dict[str, object]] | None = None,  # RecallResults from recall_memories()
    mood: str = "Content",
    *,
    token_budget: int = 4000,
) -> str:
```

### Seam 2: Token Budget Flow

| Component | Current | P3-012 Target |
|-----------|---------|---------------|
| Read pipeline | `_apply_token_budget()` trims at 4000, logs `token_budget_trimmed` | Keep — enforces budget at recall level |
| Prompt loader | No token awareness; no truncation logging | **MUST ADD**: `token_budget` param; second-layer trimming if needed; structlog `prompt_budget_trimmed` event |
| Total budget | 4000 (read) + ~5000 (system prompt) = ~9000 tokens | Well within 1M context window — no danger of overflow |

**Token budget logging** (must add to `get_system_prompt_with_context`):

```python
logger.info("prompt_context_assembled",
    token_estimate=estimated,
    budget=token_budget,
    memory_count=len(memories) if memories else 0,
    truncated=estimated > token_budget,
)
```

### Seam 3: Safe-Mode / DNR Filter Propagation

| Signal | Source | Destination | Current Status |
|--------|--------|-------------|----------------|
| `safe_mode` | `HardStopHandler.is_safe` | `recall_memories(safe_mode=True)` | **GAP** — no propagation wire exists |
| `exclude_dnr` | Default `True` in `recall_memories()` | All query builders (WHERE `do_not_recall = false`) | **OK** — already enforced at query level |
| `principal` | `"guinevere_core"` default | Classification ceiling filter | **OK** — allows up to Critical |

**Safe-mode propagation path:**

```
HardStopHandler.is_safe == True
  → caller sets safe_mode=True
  → recall_memories(safe_mode=True)
  → Critical content replaced with SAFE_MODE_PLACEHOLDER
  → prompt loader receives safe_content (already redacted)
  → system prompt context contains "[Content redacted per safe-mode policy]"
  → No raw Critical memory enters LLM
```

### Seam 4: P3-011 → P3-012 Output Contract

P3-011 (hybrid ranking with full weighted RRF) returns the SAME output shape as P3-010:

```python
list[dict[str, object]] = [
    {
        "id": str,              # UUID
        "safe_content": str,    # Content safe for injection
        "classification": str,  # Data classification
        "importance": int,      # 1-10
        "created_at": datetime, # Timestamp
        "combined_score": float, # Hybrid ranking score
        "is_summarized": bool,  # True if summary preferred
    }
]
```

P3-012 does not need to change when P3-011 ships — the output schema is **identical**.

### Seam 5: System Prompt Template Section for Memory

Current system prompt (§E, line 225-240) includes: "Use memories naturally", "Invisible injection: memories enter context without mention unless needed."

P3-012 injects into the runtime-injected section (NOT the master system prompt file). The master system prompt is loaded as-is; memory context appends after it:

```
[SystemPromptMaster §A-§J — 5000 tokens]
[P3-012 memory context — up to 4000 tokens]
  ## Recalled Memories
  1. [safe_content from top-ranked result]
  2. [safe_content from 2nd-ranked]
  ...
  N. [safe_content from Nth-ranked]

  ## Current Mood: Content
```

### Seam 6: LLM Router Assembly Point

Currently no unified "prompt assembler" exists. The smoke test `conftest.py` shows the pattern:

```python
messages = [
    {"role": "system", "content": system_prompt},  # ← P3-012 injects memory here
    {"role": "user", "content": user_message},
]
```

P3-012 must either:
- **(Option A)** Create a new `assemble_prompt()` function in `prompt_loader.py` that calls both `load_system_prompt()` and `recall_memories()`, then assembles; OR
- **(Option B)** Keep `get_system_prompt_with_context()` as the assembly point and have the caller pass `recall_memories()` output

**Recommendation: Option A** — a single `assemble_context(sql_session, query_text, mood, safe_mode, token_budget)` function that:
1. Calls `recall_memories(session, query_text, ..., safe_mode=safe_mode, token_budget=token_budget)`
2. Calls `get_system_prompt_with_context(memories=results, mood=mood, token_budget=token_budget)`
3. Returns the fully assembled system prompt string

---

## 3. Gap Analysis

### GAP-1: No Caller/Orchestrator Function (BLOCKED until P3-011)

| Aspect | Detail |
|--------|--------|
| **Description** | No function exists that calls `recall_memories()` and feeds output to `get_system_prompt_with_context()` |
| **Location** | Must be created in `src/core/services/prompt_loader.py` (or new `src/core/services/context_assembler.py`) |
| **Impact** | Without this, memory context never enters the system prompt |
| **Prerequisite** | P3-011 (ranking) must be complete so top-k results are ranked correctly |
| **Resolution** | Create `assemble_system_prompt_with_memory()` or extend `get_system_prompt_with_context()` |

### GAP-2: No Token Budget Awareness in Prompt Loader

| Aspect | Detail |
|--------|--------|
| **Description** | `get_system_prompt_with_context()` has no `token_budget` parameter, no estimation, no truncation logging |
| **Location** | `src/core/services/prompt_loader.py` lines 32-47 |
| **Current behavior** | Hardcodes `memories[:10]` — could still exceed budget with 10 long memories |
| **Resolution** | Add `token_budget` param to `get_system_prompt_with_context()`; estimate tokens using `len(text) // 4`; truncate and log if exceeded |

### GAP-3: No Safe-Mode Propagation Wire

| Aspect | Detail |
|--------|--------|
| **Description** | `HardStopHandler.is_safe` → `recall_memories(safe_mode=True)` propagation does not exist |
| **Location** | The caller/orchestrator that bridges safety → memory → prompt |
| **Impact** | In safe mode, Critical content could still enter context if `safe_mode` is not set |
| **Mitigation** | `_build_safe_content()` in read_pipeline is fail-safe — if `safe_mode=False`, Critical is NOT substituted. The bug is that we never pass `safe_mode=True`, not that the gate doesn't work. |
| **Resolution** | In the new assembler function, check `HardStopHandler.is_safe` and pass `safe_mode=True` to `recall_memories()` |

### GAP-4: No `get_system_prompt_with_context` Signature Update

| Aspect | Detail |
|--------|--------|
| **Description** | Current signature `(memories: list[str] | None, mood: str = "Content")` is incompatible with `recall_memories()` output |
| **Location** | `src/core/services/prompt_loader.py` line 32 |
| **Resolution** | Change to accept `list[dict[str, object]]` (RecallResults) or a typed dataclass |
| **Rich context** | Each result dict has `safe_content`, `classification`, `importance`, `is_summarized` — prompt loader could format differently per classification (e.g., skip Restricted context for sub-agents) |

### GAP-5: Missing Structlog Truncation Events at Prompt Level

| Aspect | Detail |
|--------|--------|
| **Description** | Read pipeline logs `token_budget_trimmed` at recall level; prompt loader has NO truncation logging |
| **Location** | `src/core/services/prompt_loader.py` |
| **Resolution** | Add `logger.info("prompt_context_truncated", ...)` when token budget forces trimming at prompt assembly level |
| **Double-layer trimming**: Read pipeline trims at recall → prompt loader does second pass if system prompt + headers consume budget |

---

## 4. P3-012 Implementation Design

### 4.1 Updated `get_system_prompt_with_context()` Signature

```python
from typing import Optional
from src.memory.read_pipeline import RecallResults, DEFAULT_TOKEN_BUDGET

def get_system_prompt_with_context(
    memories: RecallResults | None = None,
    mood: str = "Content",
    *,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> str:
    """Build system prompt with recalled memory context, mood, and budget enforcement.

    Args:
        memories: Ranked results from ``recall_memories()`` (P3-010/P3-011).
                  Each dict must have ``safe_content`` key.
        mood: Current persona mood state for ``## Current Mood`` line.
        token_budget: Max tokens for memory context section.

    Returns:
        Assembled system prompt string: base prompt + memory context + mood.

    Raises:
        ValueError: If system prompt fails safety validation.
        FileNotFoundError: If system prompt file is missing.
    """
    base_prompt = load_system_prompt()
    logger.info("system_prompt_loaded", chars=len(base_prompt))

    if not memories:
        context_parts = [base_prompt, f"\n\n## Current Mood: {mood}"]
        return "\n".join(context_parts)

    context_parts = [base_prompt]
    memory_section = "\n\n## Recalled Memories\n"

    total_tokens = 0
    included = 0
    for r in memories:
        safe_content = str(r.get("safe_content", ""))
        if not safe_content:
            continue
        estimated = len(safe_content) // 4  # ~4 chars per token
        if total_tokens + estimated > token_budget:
            logger.info(
                "prompt_context_truncated",
                extra={
                    "budget": token_budget,
                    "total_memories": len(memories),
                    "included": included,
                    "discarded": len(memories) - included,
                    "tokens_used": total_tokens,
                    "tokens_remain": token_budget - total_tokens,
                },
            )
            break
        total_tokens += estimated
        included += 1
        memory_section += f"{included}. {safe_content}\n"

    context_parts.append(memory_section)
    context_parts.append(f"\n## Current Mood: {mood}")

    return "\n".join(context_parts)
```

### 4.2 New Assembler Function (Option A)

```python
async def assemble_system_prompt_with_memory(
    session,          # RecallSession (AsyncSession)
    query_text: str,
    *,
    mood: str = "Content",
    safe_mode: bool = False,
    principal: str = "guinevere_core",
    limit: int = 20,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> str:
    """Assemble the full system prompt with memory recall context.

    Orchestrates: recall → format → inject → return.
    """
    from src.memory.read_pipeline import recall_memories

    results = await recall_memories(
        session,
        query_text,
        limit=limit,
        exclude_dnr=True,        # DNR gate
        safe_mode=safe_mode,      # Safe-mode gate
        principal=principal,
        token_budget=token_budget,
    )

    return get_system_prompt_with_context(
        memories=results if results else None,
        mood=mood,
        token_budget=token_budget,
    )
```

### 4.3 Call Sequence with Safe-Mode Propagation

```python
# In Discord message handler or agent loop
from src.core.services.hard_stop_handler import _get_handler  # or pass handler

handler = _get_handler()
is_safe = handler.is_safe

system_prompt = await assemble_system_prompt_with_memory(
    session=db_session,
    query_text=user_message,
    mood="Content",
    safe_mode=is_safe,          # ← Propagate safe-mode
    token_budget=4000,
)

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message},
]
response = await llm_router.chat(messages)
```

---

## 5. Current File Readiness

### 5.1 Files That Need Changes (P3-012)

| File | Change | Risk |
|------|--------|------|
| `src/core/services/prompt_loader.py` | Update `get_system_prompt_with_context()` signature + add token budget + truncation logging + new assembler function | Low — 47-line file, well-understood |
| `src/core/services/__init__.py` | Add exports for new assembler function | Low — 1-line stub |
| `src/memory/read_pipeline.py` | **No changes** — output contract already satisfies P3-012 | None |

### 5.2 Files That Must NOT Change

| File | Reason |
|------|--------|
| `docs/60-persona/61-SystemPromptMaster_v1.1.md` | Master template — P3-012 injects at runtime, does not edit |
| `src/core/services/hard_stop_handler.py` | Safety handler — unchanged; `is_safe` is read-only |
| `src/memory/read_pipeline.py` | Stable P3-010 output — P3-012 consumes, does not modify |
| `src/memory/models.py` | Schema — no changes needed |

### 5.3 Files That Are Candidates for Future Changes (P3-013+)

| File | P3-013 | P3-014 | P3-015 |
|------|--------|--------|--------|
| `prompt_loader.py` | DNR assertion tests | Safe-mode assertion tests | Consolidation-aware context |
| `read_pipeline.py` | DNR hardening | Safe-mode hardening | Consolidation scoring |

---

## 6. Required Test Suite — P3-012

### 6.1 Unit Tests (New File: `tests/memory/test_prompt_context_injection.py`)

| Test ID | Description | Assertions |
|---------|-------------|------------|
| TC-012-01 | `get_system_prompt_with_context(None, mood)` returns base + mood | No memory section present; mood line included |
| TC-012-02 | Empty `memories=[]` returns base + mood | Same as TC-012-01 |
| TC-012-03 | 5 memories with `safe_content` formatted correctly | `## Recalled Memories` header + 5 numbered entries |
| TC-012-04 | Token budget enforced — memories trimmed when exceeding 4000 | Structlog event `prompt_context_truncated` emitted; only top-ranked included |
| TC-012-05 | Token budget 0 — no memories included | All memories discarded; log event shows 0 included |
| TC-012-06 | Token budget very large — all memories included | No truncation; all entries present |
| TC-012-07 | Memories with empty `safe_content` skipped | Empty entries do not consume budget or appear |
| TC-012-08 | `is_summarized` flagged memories still included | Summary used instead of raw content |
| TC-012-09 | Classification-aware formatting (optional future) | (if implemented) Restricted vs Critical formatting differs |
| TC-012-10 | `load_system_prompt()` called and validated | Returns non-empty string with safety elements |
| TC-012-11 | `assemble_system_prompt_with_memory()` integration | Full chain: recall → inject → return |

### 6.2 Integration Tests (New File: `tests/integration/test_p3_012_end_to_end.py`)

| Test ID | Description | Assertions |
|---------|-------------|------------|
| TC-012-I01 | Safe-mode propagation: `safe_mode=True` → Critical content redacted | `SAFE_MODE_PLACEHOLDER` in context, not raw content |
| TC-012-I02 | DNR exclusion: `do_not_recall=True` episodes absent | No DNR-flagged content in prompt context |
| TC-012-I03 | Classification ceiling: sub-agent principal capped at Confidential | `ReadPipelineSafetyError` if Critical-only results |
| TC-012-I04 | Full chain with fake session: recall → assembly → token count | Total prompt tokens ≤ base_prompt_tokens + budget |
| TC-012-I05 | Token budget trimming preserves highest-ranked results | Verifies `combined_score` of trimmed vs kept |

### 6.3 Existing Test Compatibility

| Test File | Compatibility | Action |
|-----------|--------------|--------|
| `tests/smoke/conftest.py` | `system_prompt` fixture reads deployed file directly — bypasses prompt loader | OK — smoke tests test the LLM, not the loader |
| `tests/smoke/test_persona_basic.py` | Uses `conftest.py` chat helper | OK |
| `tests/smoke/test_safe_word.py` | Tests HARD STOP via 9Router | OK |
| `tests/safety/test_hard_stop_handler.py` | Unit tests for `HardStopHandler` | No changes needed |
| `tests/discord/test_bot.py` | Discord bot integration | No changes needed — memory context is transparent to bot message handling |

---

## 7. Token Budget Model — P3-012 vs System Prompt Master

| Component | Tokens | Source |
|-----------|--------|--------|
| SystemPromptMaster §A-§J | ~5000 | `61-SystemPromptMaster_v1.1.md` line 9 |
| P3-012 memory context budget | 4000 | `DEFAULT_TOKEN_BUDGET` in `read_pipeline.py` line 69 |
| Mood line | ~10 | Static |
| **Total system prompt** | **~9010** | Well within 1M context window |
| Runtime injection (other) | ~3300 | Line 9 of SPM |
| User message | Variable | — |
| **Grand total ceiling** | **~12,310 + user** | Comfortable margin |

---

## 8. Safety Boundary Verification

### 8.1 DNR Gate — Existing and Sufficient

| Gate | Enforced At | Evidence |
|------|------------|----------|
| DNR exclusion | `recall_memories(exclude_dnr=True)` → WHERE `do_not_recall = false` | `read_pipeline.py` lines 361, 387, 410 |
| DNR in model | `Episodes.do_not_recall` Boolean column | `models.py` line 137-139 |
| Default behavior | `exclude_dnr=True` in recall signature | `read_pipeline.py` line 551 |

**P3-012 Action:** No changes needed — DNR is enforced at query level. Memories flagged `do_not_recall=True` never reach the prompt loader.

### 8.2 Safe-Mode Gate — Wire Missing

| Gate | Current | P3-012 Target |
|------|---------|---------------|
| Safe-mode placeholder | `"[Content redacted per safe-mode policy]"` | Keep |
| `safe_mode` propagation | Not wired | **Must wire** from `HardStopHandler.is_safe` to `recall_memories(safe_mode=True)` |
| Prompt loader awareness | Not aware of safe-mode | Already handled — prompt loader receives `safe_content` which is already substituted |

**P3-012 Action:** Add `safe_mode` boolean parameter to the new assembler function; propagate from caller's safety handler.

### 8.3 Classification Ceiling — Existing and Sufficient

| Gate | Enforced At | Evidence |
|------|------------|----------|
| `guinevere_core` → Critical | `_CLASSIFICATION_CEILING` map | `read_pipeline.py` lines 79-83 |
| `guinevere_subagent` → Confidential | Same map | `read_pipeline.py` line 81 |
| Default → Restricted | Same map | `read_pipeline.py` line 82 |
| Ceiling filter | `filtered_scored` loop | `read_pipeline.py` lines 656-665 |

**P3-012 Action:** Always use `principal="guinevere_core"` for system prompt context (core agent only).

### 8.4 Audit Trail

| Event | Logged By | Event Name |
|-------|-----------|------------|
| Token budget triggered | `read_pipeline.py` | `token_budget_trimmed` |
| Recall complete | `read_pipeline.py` | `recall_complete` |
| Prompt context truncated | `prompt_loader.py` (NEW) | `prompt_context_truncated` |
| System prompt loaded | `prompt_loader.py` | `system_prompt_loaded` |
| HARD STOP triggered | `hard_stop_handler.py` | `hard_stop_triggered` |
| LLM request | `llm_router.py` | `llm_request` |

---

## 9. P3-011 Dependency Impact

### 9.1 What P3-011 Changes

P3-011 improves ranking: full weighted RRF with all 4 signals (vector + FTS + recency + importance) as rank inputs, not multiplicative factors.

### 9.2 P3-012 Impact

| Aspect | Stable | Reason |
|--------|--------|--------|
| Output schema | ✅ | P3-011 returns same `list[dict[str, object]]` with 7 fields |
| Token budget | ✅ | Budget enforcement unchanged |
| DNR gate | ✅ | Unchanged |
| Safe-mode gate | ✅ | Unchanged |
| Classification ceiling | ✅ | Unchanged |
| Combined score range | ⚠️ May change | RRF score values differ when all 4 signals are rank inputs |
| Ranking order | ⚠️ Changes | Better ranking — P3-012 just takes top-k in order |

**Conclusion:** P3-012 can be designed and partially implemented before P3-011 completes (using the P3-010 output shape), but integration testing requires P3-011 PASS.

---

## 10. File Change Inventory — P3-012

| File | Operation | Lines | Owner |
|------|-----------|-------|-------|
| `src/core/services/prompt_loader.py` | **Modify** — update `get_system_prompt_with_context()` + add `assemble_system_prompt_with_memory()` | ~47 → ~120 | One sub-agent |
| `src/core/services/__init__.py` | **Modify** — add exports | ~1 → ~4 | Same sub-agent |
| `tests/memory/test_prompt_context_injection.py` | **Create** — unit tests (TC-012-01 to TC-012-11) | ~200 | Same sub-agent |
| `tests/integration/test_p3_012_end_to_end.py` | **Create** — integration tests (TC-012-I01 to TC-012-I05) | ~150 | Same or separate sub-agent |
| `docs/setup-evidence/P3/STEP-P3-012/verification.md` | **Create** — evidence | ~200 | Parent |

---

## 11. Implementation Pre-Flight Checklist

Before P3-012 implementation begins:

- [ ] P3-011 auditor gate = PASS (ranking complete)
- [ ] `src/memory/read_pipeline.py` `recall_memories()` output shape confirmed (7 fields)
- [ ] P3-010 auditor gate = PASS (read pipeline stable)
- [ ] `src/memory/__init__.py` exports `recall_memories`, `DEFAULT_TOKEN_BUDGET`, `ReadPipelineError`, `RecallResults` accessible
- [ ] `src/core/services/prompt_loader.py` `load_system_prompt()` loads from deployed path
- [ ] `HardStopHandler` singleton accessible from context assembler (or passed as parameter)
- [ ] `structlog` logger available in `prompt_loader.py` (already imported at line 2)
- [ ] `CHARS_PER_TOKEN = 4` constant documented or imported from `read_pipeline.py`
- [ ] SQLAlchemy `AsyncSession` protocol compatible with `assembler` function signature
- [ ] Aizanta health verified (`pg_isready -p 5432`) — standard pre-step gate

---

## 12. Footer

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Author** | Guinevere (Parent Executor) |
| **Scope** | P3-012 prompt-loader & context-injection readiness |
| **Files Inspected** | 14 source files, 3 research reports, 2 batch plans, 3 evidence files |
| **Integration Seams Identified** | 6 seams (recall→prompt, token budget, safe-mode, P3-011 contract, template, LLM assembly) |
| **Gaps Found** | 5 gaps (no caller function, no budget in prompt loader, no safe-mode wire, signature mismatch, missing truncation logs) |
| **Blockers** | 0 — P3-011 must complete before P3-012 but all seams are defined |
| **Tests Required** | 11 unit + 5 integration = 16 test cases |
| **Files to Change** | 2 existing (`prompt_loader.py`, `__init__.py`) + 2 new test files |
| **Safety Boundary** | ✅ DNR enforced at query level, ✅ classification ceiling, ⚠️ safe-mode wire must be added |

---

*End of research report. Ready for P3-012 planner gate after P3-011 completes.*