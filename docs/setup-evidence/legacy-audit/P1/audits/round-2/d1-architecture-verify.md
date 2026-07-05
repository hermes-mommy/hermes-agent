# D1: Architecture-Implementation -- Round 2 Adversarial Verification

**Date:** 2026-06-25
**Method:** Independent re-verification of every Round 1 finding + missed-surface scan
**Scope:** Same as Round 1 + broader `src/` scan for hidden failures
**Status:** COMPLETE

---

## 1. Original Findings vs Verification

| ID | Round-1 Verdict | Round-2 Verdict | Notes |
|----|----------------|----------------|-------|
| D1-01 | PASS | **CONFIRMED** | TaskType enum has 3 values: `core`, `sub_agent`, `fallback`. CostTracker imported (line 30), instantiated (line 131), wired at lines 222-228 with fail-closed RuntimeError (line 235). Metrics observe_* calls at lines 238-240 all real. |
| D1-01b | PASS | **CONFIRMED** | 0 `# TODO.*(mock|placeholder|stub)` in `src/core/services/llm_router.py`. |
| D1-01c | PASS | **CONFIRMED** | 0 `raise NotImplementedError` in `src/core/services/llm_router.py`. |
| D1-02 | PASS | **PARTIAL** | 6 active callers + 1 docstring confirmed. But auditor MISSED two systemic bugs affecting ALL 6 callers (see New Bug N1 and N2 below). Callers count is correct; severity assessment was wrong. |
| D1-03 | PASS | **CONFIRMED** | `record_cost()` has exactly 14 Redis pipeline commands (lines 34-49). `check_budget()` returns full dict at lines 55-66. No stubs. |
| D1-04 | PASS | **CONFIRMED** | Import:63, Instantiation:101, app.state:102, Guardian wiring:103-104, monitor task:109. Full lifecycle verified. |
| D1-05 | PASS | **CONFIRMED** | `load_system_prompt` is a real function. Safety checks at lines 26-34. KG injection via `_append_kg_context()`. |
| D1-06 | PASS | **CONFIRMED** | Re-ran: 56 passed, 0 failed in 2.07s. Identical test list. Count verified. |
| D1-07 | NEEDS RUNTIME | **CONFIRMED** | conftest.py hits `http://localhost:20128/v1` with model `ds/deepseek-v4-flash`. Requires live 9Router. Cannot run locally. |
| D1-08 | PASS | **CONFIRMED** | 7 metric families in `llm_metrics.py` (145 lines). Server binds `127.0.0.1:9191` (line 88). Guard flag `_metrics_server_started`. |
| D1-09 | NEEDS REVIEW | **CONFIRMED** | Evidence dir has `health-check.txt` + `evidence.md` only. Live script at `scripts/health-check-p1.sh` (59 lines). Cannot diff. |
| D1-10 | PASS | **CONFIRMED** | 5 direct endpoints + 3 routers. `/health` at line 621 verified. |

### D1-BUG-01 through D1-BUG-07 verification

| Bug ID | Round-1 Severity | Round-2 Verdict | Notes |
|--------|-----------------|----------------|-------|
| D1-BUG-01 | Medium | **PARTIAL** | `LoopManager(llm_router=None)` is confirmed at main.py:97. Phase handlers correctly raise RuntimeError when no router (base.py:158-162). ResearchHandler falls back to static template. This is documented behavior, but the round-1 "by design" claim is unverified -- there is no comment or ADR explaining why the router is None. |
| D1-BUG-02 | Medium | **CONFIRMED** | compaction.py:80 creates own `LLMRouter()`. Second httpx AsyncClient. `close()` method exists at line 295 but is NEVER called anywhere in the codebase (grep for `compactor.(compact|close)` = 0 matches). Resource leak if ever instantiated. |
| D1-BUG-03 | Low | **CONFIRMED** | Hardcoded VPS path `/home/guinevere/config/hermes/system-prompt.md` at prompt_loader.py:16. FileNotFoundError on non-VPS. Smoke conftest has fallback (REPO_SYSTEM_PROMPT_PATH), but prompt_loader.py does not. |
| D1-BUG-04 | Low | **CONFIRMED** | health-check-p1.sh lines 36-48 require SOPS-encrypted Redis password. VPS-only. |
| D1-BUG-05 | Low | **CONFIRMED** | Evidence dir has no .sh artifact. health-check.txt is UTF-16 encoded (wide spacing in raw read). |
| D1-BUG-06 | Cosmetic | **CONFIRMED** | PRICING dict at line 77 has `cx/gpt-5.5` as dead reference. |
| D1-BUG-07 | Cosmetic | **REFUTED (partial)** | Round-1 said "port 5433 (PostgreSQL port, not Redis)" -- WRONG. Port 5433 IS the PostgreSQL port used throughout the codebase (main.py:147, 217, 246, 679). The REAL bug is the Redis default fallback URL `redis://localhost:***@localhost:5433/guinevere_core` at line 663: (a) `***` is a literal three-asterisk placeholder password, not redacted; (b) it uses 5433 which is PG port, not Redis port 6380; (c) it's inside the guardian else-block due to incorrect indentation (see New Bug N3). |

---

## 2. New Bugs Found

### N1: task_type string vs TaskType enum -- silent fallback degradation

**Severity:** Medium (currently dead code; latent bug if LLM router is injected)
**Files:**
- `src/loops/phases/base.py:143` -- `_call_llm` signature: `task_type: str = "CORE_REASONING"`
- `src/loops/review_fork.py:218` -- `task_type="CORE_REASONING"`
- `src/loops/reflection.py:85` -- `task_type="CORE_REASONING"`
- `src/loops/conversation.py:225` -- `task_type="CORE_REASONING"`
- `src/loops/phases/research.py:109` -- `task_type="CORE_REASONING"`
- `src/loops/phases/plan_delegate.py:97` -- `task_type="CORE_REASONING"`
- `src/loops/phases/update_docs.py:126` -- `task_type="CORE_REASONING"`
- `src/loops/phases/setup_evidence.py:135` -- `task_type="CORE_REASONING"`
- `src/loops/phases/validate_audit.py:125` -- `task_type="CORE_REASONING"`

**Evidence:** `LLMRouter.chat()` at llm_router.py:147 compares `task_type == TaskType.SUB_AGENT` (enum comparison). String `"CORE_REASONING"` never equals `TaskType.SUB_AGENT`, so the else branch runs: `fallback_chain = ["CORE_REASONING", TaskType.SUB_AGENT, TaskType.FALLBACK]`. Then `MODELS["CORE_REASONING"]` raises `KeyError` (MODELS keys are TaskType enum members, not strings). The KeyError is caught by `except Exception` at line 183, logged as error, and the chain falls through to `TaskType.SUB_AGENT`.

**Verified with simulation:**
```
fallback_chain: ['CORE_REASONING', <TaskType.SUB_AGENT>, <TaskType.FALLBACK>]
  [0] 'CORE_REASONING' -> KeyError (would trigger fallback)
  [1] <TaskType.SUB_AGENT> -> config.name=ds/deepseek-v4-flash
  [2] <TaskType.FALLBACK> -> config.name=guinevere
```

**Impact:** Every call from these callers silently falls back to SUB_AGENT tier. Each call generates an `observe_call(name, "error")` + `observe_fallback()` metric. The call succeeds (via fallback) but:
1. Uses wrong tier (SUB_AGENT instead of CORE_REASONING -- same model, wrong billing/pricing path)
2. Generates false error metrics on every call
3. Log spam: `llm_fallback` warning on every single LLM call

**Mitigating factor:** `LoopManager.__init__` passes `llm_router=None` (main.py:97), so `_call_llm` raises RuntimeError before reaching the fallback chain. The callers via phase handlers are dead code in current production. The ConversationLoop and ReviewFork callers are not instantiated in production main.py either. Bug is latent.

**Fix:** Change `task_type: str` to `task_type: TaskType` and use `TaskType.CORE_REASONING` enum value everywhere.

---

### N2: Response content extraction uses wrong key path

**Severity:** Medium (currently dead code; latent bug)
**Files:**
- `src/loops/conversation.py:247` -- `content: str = result.get("content", "")`
- `src/loops/phases/research.py:126` -- `raw_content = result.get("content", "")`
- `src/loops/reflection.py:89` -- `content = result.get("content", "")`
- `src/loops/review_fork.py:221` -- `content = response.get("content", "")`
- `src/loops/phases/base.py:174` -- `usage.get("input_tokens", 0)` (should be `prompt_tokens`)

**Evidence:** `LLMRouter.chat()` returns the raw OpenAI-compatible JSON at line 249. The response structure is:
```json
{
  "choices": [{"message": {"content": "actual text"}}],
  "usage": {"prompt_tokens": 10, "completion_tokens": 20},
  "model": "ds/deepseek-v4-flash"
}
```

All callers use `result.get("content", "")` which returns `""` (no top-level "content" key). Correct extraction is `result["choices"][0]["message"]["content"]`. Similarly, `usage.get("input_tokens", 0)` returns 0 because the key is `prompt_tokens`.

Only `src/memory/compaction.py:285` uses the correct pattern: `result.get("choices", [{}])[0].get("message", {}).get("content", "")`.

**Mitigating factor:** Same as N1 -- all these callers are dead code paths because LoopManager passes `llm_router=None`. If an LLM call succeeded, the callers would get empty content.

**Fix:** Extract content via `result["choices"][0]["message"]["content"]` and usage via `prompt_tokens`/`completion_tokens`.

---

### N3: health_detailed Redis check indentation bug

**Severity:** Low
**File:** `src/core/main.py:659-671`

**Evidence:** The Redis connectivity check (lines 660-671) is indented one level deeper than expected. It sits inside the `else` block of the guardian check (line 655-657):

```python
    else:
        components["guardian"] = {"status": "not_running"}
        status_code = 503

        # Redis connectivity (optional — fail-soft, don't block health)  <-- indented under else!
    try:
        ...
```

The comment at line 659 says "Redis is non-critical for health — don't set 503" but the `try` block at line 660 is at the SAME indentation as the `else` keyword, meaning it executes regardless of guardian status. However, the comment's placement INSIDE the else block is misleading. More critically: when the guardian IS healthy, the Redis check still runs (line 660 is at the function body level), and when it fails, it correctly does NOT override status_code because line 670 only sets `components["redis"]` without touching `status_code`. So the functional behavior is correct despite the misleading indentation. **The bug is cosmetic/structural, not functional.**

Actually, re-examining: lines 659-671 are all at the same indentation level (8 spaces). The `try` at line 660 is NOT inside the else block. The `else` block ends at line 657. The comment at line 659 is just poorly placed. This is a **readability issue**, not a logic bug. **Downgrading to Cosmetic.**

---

## 3. Missed-Surface Analysis

### Broader NotImplementedError scan

Round-1 scoped the forbidden pattern scan to `src/core/services/*.py`, `src/core/main.py`, `tests/smoke/*.py`, `tests/safety/*.py`. A broader scan of `src/` finds:

| File | Line | Context | Assessment |
|------|------|---------|------------|
| `src/memory/write_pipeline.py` | 91 | `EmbeddingClient.embed()` -- abstract Protocol method | Valid Protocol stub |
| `src/memory/dnr.py` | 79, 83, 87 | `DNRSession` Protocol methods | Valid Protocol stubs |

All `NotImplementedError` raises are in Protocol/interface definitions, which is correct Python pattern for abstract methods. No production code raises NotImplementedError. **No missed bugs here.**

### Broader swallowed-error scan

Round-1 did not scan for swallowed errors. Key findings:

| Pattern | Location | Assessment |
|---------|----------|------------|
| `except Exception:` (bare, no re-raise) | `src/observability/windows_metrics.py:185` | Metrics collection -- acceptable |
| `except Exception as exc:` (logged, no re-raise) | `src/gmail/bridge.py:227,305,330,416` | Gmail integration -- acceptable fail-soft |
| `return ""` on LLM failure | `src/memory/compaction.py:293` | `_summarize` returns empty string on error -- silently produces empty compaction summaries |

The compaction.py empty-string fallback is concerning: when LLM summarization fails, the compacted conversation gets an empty summary message, which could degrade conversation quality. However, compaction is only triggered at 100k tokens, so this is low-frequency.

### ContextCompactor: dead code with resource leak

`ContextCompactor` (compaction.py:52) is defined and exported (`src/memory/__init__.py:68`) but NEVER instantiated anywhere in the codebase. Grep for `ContextCompactor(` = 0 matches. It creates its own `LLMRouter()` at line 80 (confirmed by D1-BUG-02) and has a `close()` method (line 295) that is never called. If ever instantiated, it would create an unmanaged httpx AsyncClient. **This is dead code -- no runtime impact.**

---

## 4. Caller Inventory Re-verification

### `.chat()` callers in `src/` (active code)

| File | Line | task_type | Content extraction | Production-instantiated? |
|------|------|-----------|-------------------|-------------------------|
| `src/loops/conversation.py` | 223 | STRING `"CORE_REASONING"` (BUG N1) | `result.get("content", "")` (BUG N2) | NO -- not in main.py |
| `src/loops/phases/base.py` | 164 | STRING (from caller) (BUG N1) | Returns raw result (BUG N2 in callers) | NO -- llm_router=None |
| `src/loops/reflection.py` | 83 | STRING `"CORE_REASONING"` (BUG N1) | `result.get("content", "")` (BUG N2) | Not directly |
| `src/loops/review_fork.py` | 213 | STRING `"CORE_REASONING"` (BUG N1) | `response.get("content", "")` (BUG N2) | Not directly |
| `src/memory/compaction.py` | 280 | TaskType.FALLBACK (correct enum) | `choices[0].message.content` (correct) | Not instantiated |
| `src/self_improve/optimizer.py` | 213 | TaskType.CORE_REASONING (correct enum) | Not checked (uses response differently) | Not in main.py |

**Round-1 missed:** compaction.py is the ONLY caller using the correct enum AND correct extraction. All other 5 active callers have the string/enum bug (N1) and 4 of those also have the content extraction bug (N2). Round-1 classified all callers as "HERMESBRAIN-WIRED" and "PASS" without checking the argument types or response parsing.

---

## 5. Overall D1 Verdict

**Verdict: PASS (with latent bugs)**

All Round 1 PASS verdicts on core infrastructure (D1-01, D1-03, D1-04, D1-05, D1-06, D1-08, D1-10) are CONFIRMED. The core llm_router.py, cost_tracker.py, hard_stop_handler.py, prompt_loader.py, and llm_metrics.py implementations are real, complete, and contain no mocks/stubs/placeholders.

Two latent bugs (N1, N2) were found in the callers of LLMRouter.chat() that Round 1 did not detect. Both are currently dormant because LoopManager passes `llm_router=None` to phase handlers. If an LLM router is ever injected into the loop infrastructure, all callers would: (a) silently fall back to SUB_AGENT tier on every call, (b) receive empty content strings, (c) generate false error metrics.

**Caveats remain:**
- D1-07 (smoke tests) and 14 model compliance tests require VPS runtime
- D1-09 evidence artifact gap
- N1/N2 latent bugs in loop callers (dormant until router injection)

**Downstream compatibility:**
- P19: CLEAR (cognition registry is additive)
- P20: CLEAR (all .chat() callers are dormant; no autonomy bypass)
- P22/P23: CLEAR (localhost binding constraint preserved)
- P24: CLEAR (llm_router.py is canonical; callers need fixing before loop autonomy activates)

---

*End of D1 Round-2 verification. READ-ONLY -- no files modified except this output.*
