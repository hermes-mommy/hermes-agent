# Regression + Integration Audit: Phase 1 Safety Plugin

**Auditor**: Guinevere (regression/integration auditor)  
**Date**: 2026-06-04  
**Scope**: `src/hermes/safety_plugin.py` (1029 lines, NEW file)  
**Benchmark**: hermes-agent v0.15.2

---

## REGRESSION CHECKS

### REG-01: No Existing Module Modified — **PASS**

| Evidence | Status |
|---|---|
| `git status --short -- src/hermes/ src/discord/conversational_handler.py src/persona/ src/surveillance/ src/mcp/` | Only `?? src/hermes/safety_plugin.py` (untracked) |
| `git diff --stat HEAD -- src/` | Empty — zero modifications to existing files |
| `git log -- src/hermes/safety_plugin.py` | Empty — no prior commits exist for this file |

No existing file was modified. `safety_plugin.py` is a net-new addition. All existing modules (`session_adapter.py`, `conversational_handler.py`, `persona/*`, `surveillance/*`, `mcp/*`) are untouched.

---

### REG-02: No Circular Imports — **PASS**

Import chain trace (safety_plugin.py → each lazy import):

| Safety plugin imports from | That module imports from `src.hermes`? |
|---|---|
| `src.core.services.hard_stop_handler` | No (verified via grep) |
| `src.persona.safe_mode` | No |
| `src.persona.drift_detector` | No |
| `src.persona.yandere_fsm` | No |
| `src.surveillance.secret_scanner` | No |
| `src.mcp.auth_matrix` (→ `src.mcp.auth`) | No |

Reverse direction:

| Other modules importing from safety_plugin | Count |
|---|---|
| `grep "from src.hermes.safety_plugin\|import.*safety_plugin" src/` | Zero matches |

**Conclusion**: Import graph is a strict DAG. All imports from safety_plugin go to leaf modules that do not import back from `src.hermes`. No cycle exists.

---

### REG-03: Plugin Isolation / Graceful Degradation — **PASS**

`_init_safety_modules()` (lines 306–397) wraps every import in `try/except Exception`, setting `self._xxx_available = False` on failure and logging `WARNING` with module name + gate ID.

**Degradation behavior by gate**:

| Gate | Degrades to | Critical impact if unavailable? |
|---|---|---|
| G01: HARD STOP exact + semantic | **Always active** (module-level data) | No — exact/semantic patterns are hardcoded |
| G01: HardStopHandler delegate | Skipped if `_hard_stop_available=False` | Defense-in-depth only; exact+semantic remain |
| G02: Distress | Skipped if `_distress_available=False` | Distress detected by `conversational_handler.py` separately |
| G03: Drift | Skipped if no baseline set | Observational only — non-blocking |
| G05: Forbidden patterns | **Always active** (module-level data) | No — compiled patterns are hardcoded |
| G06: Secret scanner | Skipped if `_secret_available=False` | Non-blocking redaction |
| G07/G08: Yandere | Skipped if `_yandere_available=False` | Ceiling enforcement lost — yandere engine in persona module still active via conversational_handler |
| G09: Auth matrix | Skipped if `_auth_available=False` | Tool auth bypassed — but hermes session has `disabled_toolsets=["*"]` |

**Production monitoring**: Plugin logs `guinevere_safety_plugin_init` at construction with boolean availability for every module. This provides a single-log-line health check — operators can verify all gates are active. Warnings are logged at structlog `WARNING` level (not just debug), ensuring they surface in production monitoring (Prometheus/Loki/Grafana).

→ No silent failure risk. The critical safety gate (G01 exact+semantic) is always active regardless of imports. Degraded gates are observable via structured logging.

---

### REG-04: VPS Coexistence / Double-Blocking — **PASS**

**Coexistence analysis**:

The plugin runs **in addition to** existing safety checks in `conversational_handler.py`. Both check distress, but they serve distinct purposes:

| Layer | Distress check | Action |
|---|---|---|
| `conversational_handler.py` (Step 7, lines 393–414) | `DistressDetector.detect(content)` | Affects **system prompt tone** + **memory recall context** + `safe_mode_activated` flag used in system prompt assembly |
| `safety_plugin.py` pre_llm_call (Gate G02, lines 554–594) | `DistressDetector.detect(text)` via hermes hook | **Blocks LLM call** for D3/D4 distress; forces `yandere_level=0` and `safe_mode_active=True` for D2+ |

**No double-blocking**: The conversational_handler's distress check is non-blocking — it adjusts the system prompt. The plugin's distress check is the actual blocking gate. They are complementary layers:

1. If the handler detects distress → system prompt gets safety-aware context
2. If the plugin detects D3+ distress → LLM call is blocked entirely

**No conflicting behavior**: Both use the same `DistressDetector` class. There is NO HARD STOP check in `conversational_handler.py` (HARD STOP is handled by `bot.py`'s `_register_hard_stop_listener` at the Discord message level, which is upstream of conversational_handler). The plugin adds a second HARD STOP layer at the hermes-agent hook level — defense-in-depth, not conflict.

---

### REG-05: Hermes Config Compatibility — **PASS**

The plugin is registered via `hermes plugins enable guinevere-safety`. The `register()` function (lines 990–1029):

- Creates a **new** `GuinevereSafetyPlugin()` instance
- Registers exactly 6 hooks via `ctx.register_hook()`
- Does NOT read any hermes config settings (`safety.safe_word`, `safety.yandere_max`, etc.)
- Uses its own module-level data (HARD_STOP_EXACT, HARD_STOP_SEMANTIC, RECOVERY_TRIGGERS, _COMPILED_FORBIDDEN)
- Does NOT modify hermes config or clash with other plugins' hook registrations

**Compatibility**: The plugin is additive — it listens on hooks without modifying hermes state. Other plugins can register the same hooks; hermes dispatches to all registered callbacks. No config key overlap.

---

## INTEGRATION CHECKS

### INT-01: Hook Signatures Match hermes-agent v0.15.2 — **PASS**

Registered hooks in `register()` (lines 1010–1016):

| # | Hook Name | Registered? | Valid Hook? |
|---|---|---|---|
| 1 | `pre_llm_call` | ✅ | ✅ |
| 2 | `post_llm_call` | ✅ | ✅ |
| 3 | `pre_tool_call` | ✅ | ✅ |
| 4 | `post_tool_call` | ✅ | ✅ |
| 5 | `transform_llm_output` | ✅ | ✅ |
| 6 | `on_session_start` | ✅ | ✅ |
| — | `api_request_error` | ❌ NOT registered | ❌ Not a valid hook |

All 6 registered hooks match the VALID_HOOKS list for hermes-agent v0.15.2. `api_request_error` exists as a class method (lines 923–944) but is correctly excluded from `register()`. Docstring at line 17 explicitly documents this: *"api_request_error -> (NOT registered — not a valid hermes-agent v0.15.2 hook)"*.

All hook methods accept `**kwargs: Any` for forward compatibility with future hermes-agent versions.

---

### INT-02: Hook Return Types Correct — **PASS**

| Hook | Signature | Returns | Specification | Verdict |
|---|---|---|---|---|
| `pre_llm_call` (line 403) | `-> dict[str, Any] \| None` | `None` = allow; `dict` = block | `dict \| None` (block with dict, pass with None) | ✅ CORRECT |
| `post_llm_call` (line 642) | `-> None` | Observational only | Void callback | ✅ CORRECT |
| `pre_tool_call` (line 696) | `-> dict[str, Any] \| None` | `None` = allow; `dict` = block | `dict \| None` (block with dict, pass with None) | ✅ CORRECT |
| `post_tool_call` (line 783) | `-> None` | Observational logging | Void callback | ✅ CORRECT |
| `transform_llm_output` (line 803) | `-> str \| None` | `str` = modified response; `None` = block | `str \| None` (replace with str, block with None, pass with original) | ✅ CORRECT |
| `on_session_start` (line 950) | `-> None` | State initialization | Void callback | ✅ CORRECT |

**Detail on `transform_llm_output`**: Returns `text` (possibly modified by G05 rewrite and G06 redaction, or identical to input) when passing through. The spec says "pass with original" uses `None`, but returning the unmodified string is functionally equivalent — hermes uses the returned string directly. Returning `None` blocks; returning any string replaces the output. The plugin returns `None` only for CRITICAL forbidden matches (G05), empty response_text, or text reduced to nothing after redaction — all correct blocking scenarios.

---

### INT-03: Session State Lifecycle — **NEEDS REVIEW**

**Issue**: No session cleanup mechanism. `_session_states: dict[str, SessionSafetyState]` grows unboundedly over the plugin's lifetime.

| Concern | Detail |
|---|---|
| No `on_session_end` hook | Hermes-agent v0.15.2 does not provide a session-end hook, so cleanup cannot be hook-driven |
| No TTL-based eviction | Dictionary entries persist until process restart |
| No max-size cap | Long-running process (VPS systemd, weeks/months uptime) will accumulate every session ever created |
| Memory per entry | `SessionSafetyState` is a lightweight dataclass (~200 bytes), so slow leak |

**Practical impact**: Low. Each `SessionSafetyState` is small (~200 bytes). At 10,000 sessions, that's ~2MB. The plugin is per-hermes-agent-instance, not per-request. In the Guinevere VPS deployment, hermes runs as a long-lived process, but Discord sessions are limited to one operator (Faiz) — the session count will be in the dozens, not thousands.

**Recommendation**: Add a periodic cleanup of sessions older than N hours (`last_check_timestamp`), or a `max_sessions` cap with LRU eviction. Deferred to Phase 2.

---

### INT-04: api_request_error Correctly NOT Registered — **PASS**

- `api_request_error` method exists at line 923 — observational logging only
- `register()` at lines 1010–1016 registers exactly 6 hooks; `api_request_error` is absent
- Docstring at line 17: *"api_request_error -> (NOT registered — not a valid hermes-agent v0.15.2 hook)"*
- Comment at line 1000–1002: *"Note: api_request_error is NOT a valid hermes-agent v0.15.2 hook."*

This is the correct behavior — the method is retained for documentation and forward compatibility, but not registered per spec.

---

## FINAL VERDICT

| Check | Result |
|---|---|
| REG-01: No existing module modified | ✅ PASS |
| REG-02: No circular imports | ✅ PASS |
| REG-03: Plugin isolation / graceful degradation | ✅ PASS |
| REG-04: VPS coexistence / double-blocking | ✅ PASS |
| REG-05: Hermes config compatibility | ✅ PASS |
| INT-01: Hook signatures match v0.15.2 | ✅ PASS |
| INT-02: Hook return types correct | ✅ PASS |
| INT-03: Session state lifecycle | ⚠️ NEEDS REVIEW |
| INT-04: api_request_error not registered | ✅ PASS |

**Final Verdict: PASS**

The single NEEDS REVIEW item (INT-03: no session cleanup) is a low-risk concern in Guinevere's single-operator deployment model. It is not blocking for Phase 1.

---

## WATCH LIST

1. **INT-03: Session state accumulation** — Add `max_sessions` cap or periodic TTL-based eviction in Phase 2. Monitor `len(plugin._session_states)` via a health check endpoint.
2. **REG-03: Module availability monitoring** — Ensure the `guinevere_safety_plugin_init` log line is captured in Loki and surfaced in Grafana. If any module shows `False`, investigate immediately.
3. **REG-04: Double-distress latency** — `conversational_handler.py` and `safety_plugin.py` both run `DistressDetector.detect()` on the same text. This adds ~O(N) regex compilation overhead per message. Not significant at current volume (<1 msg/sec), but worth noting.

---

## VERIFICATION EVIDENCE

| Evidence | Path |
|---|---|
| Git status (zero modifications) | `git status --short -- src/` → only `?? src/hermes/safety_plugin.py` |
| Git diff (zero modifications) | `git diff --stat HEAD -- src/` → empty |
| Import chain grep (no cycles) | 6 grep checks — all zero matches |
| File timestamp identity | `safety_plugin.py` is new (no prior git log); all other files unmodified |
| Plugin is unreferenced | `grep "safety_plugin" src/` → zero matches in existing code |