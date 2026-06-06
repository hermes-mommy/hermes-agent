# B8-M Verification — Process-Correct Metrics

**Step:** B8-M — Add local process-correct metrics definitions and safety plugin wiring  
**Plan:** `phase-7c-b3-b8-safe-subset-plan.md` §7  
**Date:** 2026-06-06  
**Status:** IMPLEMENTED

---

## 1. Metric Names and Ownership Rationale

| Metric | Type | Labels | Owner | Rationale |
|---|---|---|---|---|
| `hermes_safety_blocks_total` | Counter | `gate`, `reason` | Safety plugin | Block events originate from plugin hooks; low-cardinality labels only. |
| `hermes_session_count` | Gauge | (none) | Safety plugin | Session count tracked by plugin's `on_session_start`. |
| `hermes_message_count_total` | Counter | `direction` | Safety plugin | Message direction observed from hook activity; safe directions: `incoming`, `assistant`, `tool_call`, `tool_result`, `outgoing`. |

### Blocked Metric

| Metric | Reason |
|---|---|
| `hermes_gateway_up` | NOT emitted. Ownership belongs to the real Hermes Agent gateway process, not the core/FastAPI metrics server on port 9191. Defining it here would falsely represent gateway process health. |

---

## 2. Files Changed

| File | Change | Status |
|---|---|---|
| `src/core/services/llm_metrics.py` | Added `SAFETY_BLOCKS_TOTAL` Counter, `SESSION_COUNT` Gauge, `MESSAGE_COUNT_TOTAL` Counter metric families; added `observe_safety_block()`, `set_session_count()`, `observe_message()` observer helpers; docstring note blocking `hermes_gateway_up`. | ✅ Verified |
| `src/hermes/safety_plugin.py` | Imported B8 observers from `llm_metrics`; wired `observe_safety_block()` at 8 block points (G01 exact/semantic/handler, G02 D3+, G07 yandere, G09 auth forbidden/unknown, G05 forbidden critical); wired `observe_message("incoming")` in `pre_llm_call`, `"assistant"` in `post_llm_call`, `"tool_call"` in `pre_tool_call`, `"tool_result"` in `post_tool_call`, `"outgoing"` in `transform_llm_output`; wired `set_session_count()` in `on_session_start`. | ✅ Verified |
| `tests/hermes/test_llm_metrics.py` | Added 3 metric definition tests, 3 observer output tests, 3 value increment tests for B8 metrics. | ✅ 38 passed |
| `tests/hermes/test_safety_plugin.py` | Added 13 tests in `TestB8MetricsObservers` class proving observer calls at all block points. | ✅ 110 passed |

---

## 3. Observer Wiring Map

### Safety Block Points (calling `observe_safety_block`)

| Gate | Point in Code | Label Values |
|---|---|---|
| G01 HARD STOP exact | `pre_llm_call` — exact trigger match | `gate="G01"`, `reason="exact:<trigger>"` |
| G01 HARD STOP semantic | `pre_llm_call` — semantic pattern match | `gate="G01"`, `reason="semantic:<index>"` |
| G01 HARD STOP handler | `pre_llm_call` — HardStopHandler delegation | `gate="G01"`, `reason="hard_stop_handler"` |
| G02 Distress D3+ | `pre_llm_call` — D3/D4 block | `gate="G02"`, `reason="DISTRESS_<level>"` |
| G07 Yandere safety | `pre_llm_call` — Y6 ceiling breach | `gate="G07"`, `reason="YANDERE_SAFETY_VIOLATION"` |
| G09 Auth forbidden/destructive | `pre_tool_call` — auth block | `gate="G09"`, `reason="AUTH_<level>:<tool>:<op>"` |
| G09 Auth unknown tool | `pre_tool_call` — KeyError block | `gate="G09"`, `reason="AUTH_UNKNOWN_TOOL:<tool>"` |
| G05 Forbidden critical | `transform_llm_output` — CRITICAL block | `gate="G05"`, `reason="<pattern_id>:<description>"` |

### Message Count Points (calling `observe_message`)

| Hook | Direction | Condition |
|---|---|---|
| `pre_llm_call` | `"incoming"` | User message text is present |
| `post_llm_call` | `"assistant"` | Assistant message or response is present |
| `pre_tool_call` | `"tool_call"` | Every tool call |
| `post_tool_call` | `"tool_result"` | Every tool result |
| `transform_llm_output` | `"outgoing"` | Response text is present |

### Session Count Point (calling `set_session_count`)

| Hook | Call |
|---|---|
| `on_session_start` | `set_session_count(len(self._session_states))` after state creation |

---

## 4. Command Outputs

### 4.1 `test_llm_metrics.py` — 38 passed, exit 0

```
> python -m pytest tests/hermes/test_llm_metrics.py -q --tb=short
38 passed in 3.38s
```

### 4.2 `test_safety_plugin.py` — 110 passed, exit 0

```
> python -m pytest tests/hermes/test_safety_plugin.py -q --tb=short
110 passed in 10.35s
```

### 4.3 `tests/phase7/` — 139 passed, exit 0

```
> python -m pytest tests/phase7/ -q --tb=short
139 passed in 3.74s
```

### 4.4 Forbidden patterns — no new violations

Checked: `# type: ignore`, `bare except:`, `hermes_gateway_up` definition in source code (not docstrings/tests).

Result: Zero new forbidden pattern matches in modified code.
- `# type: ignore` found only in test file string literals (pre-existing `test_no_type_ignore_in_source`)
- `hermes_gateway_up` found only in docstring (explicit blocked note) and test (explicit `not in output` assertion)

### 4.5 `hermes_gateway_up` — correctly blocked

- `src/core/services/llm_metrics.py`: Only in docstring as blocked note (line 14)
- `tests/hermes/test_llm_metrics.py`: Only in `test_no_gateway_up_defined` test assertion (line 383)
- No metric definition exists in any source file

### 4.6 LSP diagnostics — zero errors

```
> lsp_diagnostics on src/core/services/llm_metrics.py
No diagnostics found

> lsp_diagnostics on src/hermes/safety_plugin.py
No errors found. Only pre-existing warnings (reportAny, reportExplicitAny)
```

---

## 5. Hard Rejection Criteria Check

| Criterion | Status |
|---|---|---|
| `hermes_gateway_up` emitted from wrong process | ✅ BLOCKED — not defined; present only in docstring note |
| High-cardinality labels (raw session id, etc.) | ✅ Not used — only `gate`, `reason`, `direction` |
| Safety plugin tests fail | ✅ 110 passed (all pass) |
| New type-safety suppression or empty catch | ✅ Not introduced |
| All three metric families defined | ✅ `hermes_safety_blocks_total`, `hermes_session_count`, `hermes_message_count_total` |
| Observer helpers wired at all block points | ✅ 8 safety block points + 5 message count points + 1 session count point |

---

## 6. Boundary Compliance

- ✅ No persona drift — metrics are observational, not behavioral.
- ✅ No consent violation — metrics track safety events, not user data.
- ✅ No surveillance overreach — metric labels are low-cardinality event descriptors.
- ✅ No Y6 — no persona intensity added.
- ✅ No HARD STOP bypass — HARD STOP events are counted, not suppressed.
- ✅ No secret/intimate data exposure — metric labels contain gate IDs, pattern IDs, and tool names only.

---

## 7. Caveats

- `hermes_gateway_up` remains blocked until the real Hermes Agent gateway exposes a metrics endpoint. Dashboard panels currently referencing `up{job="hermes"}` reflect Prometheus scrape target liveness, not gateway process health.
- Message count observations are approximate — they fire once per hook invocation. Multiple hooks may fire for the same logical message (e.g., `pre_llm_call` + `transform_llm_output` both count directions).
- Session count gauge is scoped to sessions tracked by the safety plugin's `_session_states` dict. Sessions created outside the plugin are not counted.

---

## 8. Footer

**Verification Method:** Local tests + grep + LSP diagnostics. No VPS deploy/restart performed.
**Next Step:** B8-D (dashboard/alert update) or VERIFY/AUDIT/REPORT per plan.
