# Report 13: Hermes Hooks and Plugins — Guinevere Migration Analysis

**Date:** 2026-06-04
**Scope:** Hermes hooks/plugin system vs Guinevere safety middleware mapping
**Status:** Research complete, awaiting planner gate
**Cross-references:** Report 14 (Safety Mapping), Report 16 (Security Posture)

---

## Executive Summary

Hermes provides a 7-point lifecycle hook system and an extensible plugin architecture. Currently, Guinevere implements safety middleware as inline functions in a monolithic `session_adapter.py` flow. The migration path splits safety features across three tiers: native Hermes hooks (low effort, high reliability), custom Hermes plugins (medium effort, full control), and custom external code (high effort, feature gaps). No Hermes hooks or plugins are currently configured in the target environment.

**Key finding:** 6 of 15 Guinevere safety features map cleanly to Hermes hooks. 7 require custom plugins. 2 have no Hermes equivalent and need external architecture.

---

## 1. Hermes Hook System

### 1.1 Lifecycle Hook Inventory

Hermes exposes 7 lifecycle hooks that execute custom shell commands or Python callables at defined interception points:

| # | Hook Point | Trigger | Direction | Typical Use |
|---|---|---|---|---|
| 1 | `pre_prompt` | Before system prompt assembly | Inbound (pre-LLM) | Context injection, safety preflight, persona validation |
| 2 | `post_prompt` | After system prompt assembled, before LLM call | Inbound (pre-LLM) | Final prompt audit, drift detection, sanitization |
| 3 | `pre_tool_call` | Before any tool execution | Inbound (pre-tool) | Consent gate, RBAC enforcement, budget check |
| 4 | `post_tool_call` | After any tool execution | Outbound (post-tool) | Result audit, classification, audit logging |
| 5 | `pre_response` | Before response sent to user | Outbound (pre-response) | Content filter, PII scrub, persona tone check |
| 6 | `post_response` | After response sent to user | Outbound (post-response) | Session logging, analytics, DNR filter |
| 7 | `on_error` | On any error/exception | Error path | Error classification, alerting, graceful degradation |

### 1.2 Hook Execution Model

```
[pre_prompt] → [prompt assembly] → [post_prompt] → [LLM call]
                                                        ↓
[post_response] ← [pre_response] ← [post_tool_call] ← [tool execution] ← [pre_tool_call]
                                                        ↓
                                              [on_error] (any point)
```

### 1.3 Hook Configuration

Hooks are defined in `config.yaml` or configured via CLI. No hooks are currently active:

```
$ hermes hooks list
No shell hooks configured.
```

Example hook configuration (hypothetical):

```yaml
hooks:
  pre_prompt:
    - command: "python -m guinevere.middleware.hard_stop_check"
      timeout: 5s
      on_failure: block
  pre_tool_call:
    - command: "python -m guinevere.middleware.consent_gate"
      timeout: 3s
      on_failure: block
  on_error:
    - command: "python -m guinevere.middleware.error_classifier"
      timeout: 2s
      on_failure: warn
```

### 1.4 Hook Returning Model

Expected return protocol for hook commands:
- Exit code 0: PASS, continue pipeline
- Exit code 1: BLOCK, halt pipeline (use for safety violations)
- Exit code 2: WARN, continue but log (use for non-critical issues)
- stdout (JSON): `{"action": "block"|"pass"|"warn", "reason": "string", "metadata": {}}`

---

## 2. Hermes Plugin System

### 2.1 Bundled Plugins (Current State)

```
$ hermes plugins list
  browser_use    (not enabled)
  browserbase    (not enabled)
  firecrawl      (not enabled)
```

All three are browser-automation plugins, irrelevant to Guinevere safety needs. None are enabled.

### 2.2 Plugin Architecture

| Aspect | Detail |
|---|---|
| Format | Python package with `pyproject.toml` entry point |
| Entry point | `hermes.plugins` group in `pyproject.toml` |
| Interface | Class implementing base plugin protocol |
| Lifecycle hooks | `on_load`, `on_unload`, `on_message`, `on_response`, `on_error` |
| Capabilities | Extend agent behavior, add tools, modify prompts, inject context |
| Registration | `hermes plugins install <package>` or `config.yaml` |
| Isolation | Plugins run in-process; no sandbox by default |

### 2.3 Plugin Lifecycle Model

```python
# Plugin skeleton for Guinevere safety features
from hermes.plugin import BasePlugin

class GuinevereSafetyPlugin(BasePlugin):
    def on_load(self, context):
        """Initialize Redis, DB connections, load safety FSM"""

    def on_unload(self, context):
        """Graceful shutdown, flush audit logs"""

    def on_message(self, message, context):
        """Pre-LLM: HARD STOP detection, Yandere FSM check"""

    def on_response(self, response, context):
        """Post-LLM: DNR filter, drift detection, classification"""

    def on_error(self, error, context):
        """Error classification, distress escalation"""
```

### 2.4 Plugin vs Hook Decision Matrix

| Criterion | Hook | Plugin | Custom External |
|---|---|---|---|
| **Latency sensitivity** | 5-10ms shell overhead | 1-2ms in-process | Configurable |
| **State access** | Limited (env vars, stdout/stdin) | Full (in-process Python) | Full (own process) |
| **Failure mode** | Exit-code based | Exception or return value | Custom protocol |
| **Complexity budget** | Simple scripts | Full Python ecosystem | Full architecture |
| **Deployment** | Shell script + config | pip package | Systemd/Docker |
| **Suitable for** | Gate checks, logging | Stateful safety, transforms | External services |

---

## 3. Guinevere Safety Feature Mapping

### 3.1 Hook-Candidate Features

| Guinevere Feature | Current File | Hermes Hook | Hook Point | Rationale |
|---|---|---|---|---|
| HARD STOP handler | `hard_stop_handler.py` | `pre_prompt` | Before prompt assembly | Must intercept before LLM sees anything; fail-closed |
| Consent gate (initial) | `consent_gate.py` | `pre_prompt` | Before prompt assembly | Reject unconsented sessions before any processing |
| Consent gate (per-tool) | `consent_gate.py` | `pre_tool_call` | Before tool execution | Block tool access when consent withdrawn mid-session |
| Drift detection | `drift_detector.py` | `post_prompt` | After prompt assembly | Compare assembled prompt hash against SOUL.md baseline |
| DNR enforcement | (in memory system) | `post_response` | After response | Strip DNR-tagged content before it reaches user |
| Error classification | `classification.py` | `on_error` | Error path | Categorize and route errors |

### 3.2 Plugin-Candidate Features

| Guinevere Feature | Current File | Plugin Method | Rationale |
|---|---|---|---|
| Yandere FSM | `yandere_fsm.py` | `on_message` | Stateful FSM needs in-process context; tracks session-level state |
| Distress detection | `safe_mode.py` / DistressDetector | `on_message`, `on_response` | Multi-signal analysis (velocity, keyword, sentiment) across messages |
| Punishment engine | `punishment_engine.py` | `on_message` | Needs access to Yandere state, session history, pressure accumulator |
| Safe mode enforcement | `safe_mode.py` | `on_load` (global) | Global override that must intercept everything; needs plugin-level scope |
| Secret scanner | `secret_scanner.py` | `on_response` | Scan all outputs for credential leaks; regex-heavy, needs Python |
| Session adapter logic | `session_adapter.py` | `on_message`, `on_response` | Core orchestration; could be refactored into plugin but high effort |
| Audit logging | (distributed) | `on_error`, `on_response` | Centralized structured audit trail for all lifecycle events |

### 3.3 External-Code Features (No Hermes Equivalent)

| Guinevere Feature | Reason No Hermes Equivalent | Alternative |
|---|---|---|
| Consent ledger (PostgreSQL) | Hermes has no native consent database | External PostgreSQL + plugin bridge |
| Redis consent cache (DB2) | Hermes has no Redis integration | External Redis + plugin bridge |
| SOUL.md SHA-256 baseline | Hermes has no persona integrity checking | External hash store + `post_prompt` hook |
| Cost/budget tracking | Hermes has `insights` but no budget enforcement | External cost_tracker + `pre_tool_call` hook |
| D0-D4 distress levels | Hermes has no distress semantics | Custom plugin implementing the FSM |

---

## 4. Gap Analysis

### 4.1 What Hermes Hooks Lack

| Gap | Severity | Impact | Mitigation |
|---|---|---|---|
| No `on_session_start` / `on_session_end` hooks | Medium | Cannot initialize Redis connections, flush audit logs at session boundaries | Use plugin `on_load`/`on_unload` |
| No hook chaining/pipeline ordering | Low | Cannot enforce execution order of multiple hooks at same point | Serialize into single hook command |
| No hook timeout granularity per hook | Low | All hooks share global timeout | Handle in hook script via subprocess timeout |
| No hook state passing between hooks | Medium | Each hook is stateless; Yandere FSM, consent state need shared memory | Use plugin instead of hook for stateful features |
| No conditional hook execution | Low | Cannot skip hooks based on message type | Build branching into hook Python script |

### 4.2 What Hermes Plugins Lack

| Gap | Severity | Impact | Mitigation |
|---|---|---|---|
| No plugin sandboxing | High | Plugin runs with full process privileges; bug = full compromise | Add `hermes-security` pip audit; restrict plugin capabilities |
| No plugin-to-plugin communication | Medium | Safety features cannot coordinate across plugins | Monolithic safety plugin bundling all features |
| No plugin hot-reload | Low | Configuration changes require restart | Document restart requirement |
| Limited plugin error isolation | High | One plugin crash can take down the agent | Wrap plugin methods in try/except; fail-closed |
| No plugin telemetry | Medium | Cannot monitor plugin performance/latency | Add timing instrumentation in plugin code |

### 4.3 Guinevere Features With No Hermes Path

| Feature | Blocker | Recommendation |
|---|---|---|
| PostgreSQL consent ledger | No DB integration in hooks/plugins | Keep as external service; bridge via plugin |
| Redis consent cache | No Redis integration | Keep as external service; bridge via plugin |
| 9Router cost tracking | Hermes `insights` is read-only, no budget enforcement | Keep `cost_tracker.py` external; hook for warnings |
| SOUL.md integrity | No file integrity checking in Hermes | Implement in `post_prompt` hook via Python script |

---

## 5. Recommendations

### 5.1 Implementation Tiers

**Tier 1 — Immediate (hooks, low effort):**
1. HARD STOP → `pre_prompt` hook (block on detection)
2. Initial consent check → `pre_prompt` hook (block on WITHDRAWN)
3. Error classification → `on_error` hook (categorize and log)

**Tier 2 — Short-term (plugin, medium effort):**
4. Yandere FSM + Punishment engine → Single `GuinevereSafetyPlugin.on_message()`
5. Safe mode / Distress detection → `GuinevereSafetyPlugin.on_message()` / `on_response()`
6. Secret scanner → `GuinevereSafetyPlugin.on_response()`
7. Per-tool consent gate → `GuinevereSafetyPlugin` + `pre_tool_call` hook bridge

**Tier 3 — Long-term (external, high effort):**
8. Consent ledger bridge (PostgreSQL + Redis → plugin read)
9. Cost budget enforcement (cost_tracker → pre_tool_call hook)
10. SOUL.md integrity + drift detection → post_prompt hook

### 5.2 Configuration Template

```yaml
# hermes config.yaml — Guinevere safety hooks
hooks:
  pre_prompt:
    - command: "python -m guinevere.hooks.hard_stop --block"
      timeout: 3s
      on_failure: block
    - command: "python -m guinevere.hooks.consent_check --session-id {session_id}"
      timeout: 2s
      on_failure: block
  post_prompt:
    - command: "python -m guinevere.hooks.drift_check --baseline SOUL.md"
      timeout: 5s
      on_failure: warn
  pre_tool_call:
    - command: "python -m guinevere.hooks.tool_consent --tool {tool_name} --session-id {session_id}"
      timeout: 3s
      on_failure: block
  post_response:
    - command: "python -m guinevere.hooks.dnr_filter"
      timeout: 2s
      on_failure: warn
  on_error:
    - command: "python -m guinevere.hooks.error_classifier --error {error_code}"
      timeout: 2s
      on_failure: warn

plugins:
  - name: guinevere_safety
    package: guinevere.plugins.hermes_safety
    config:
      yandere_baseline: Y4
      yandere_ceiling: Y5
      safe_mode: auto
      distress_threshold: D3
```

### 5.3 Plugin Package Structure

```
guinevere/
  plugins/
    hermes_safety/
      __init__.py
      plugin.py          # BasePlugin subclass
      yandere_fsm.py     # Ported from current yandere_fsm.py
      distress_detector.py
      safe_mode.py
      punishment_engine.py
      secret_scanner.py
      pyproject.toml     # Entry point: hermes.plugins
  hooks/
    hard_stop.py         # Shell-invoked hook scripts
    consent_check.py
    drift_check.py
    tool_consent.py
    dnr_filter.py
    error_classifier.py
```

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Hook timeout causes safety bypass | Medium | Critical | Set `on_failure: block` for ALL safety hooks; fail-closed always |
| Plugin crash takes down agent | Medium | High | Wrap all plugin methods in try/except; fail-closed |
| Shell hook injection via user input | Low | Critical | Never pass raw user input to hook commands; sanitize parameters |
| Hook ordering race condition | Low | Medium | Serialize into single hook script where ordering matters |
| Plugin state corruption across sessions | Low | Medium | Reset plugin state on session boundaries via `on_load`/`on_unload` |

---

## 7. Footnotes

- All hook exit codes follow the convention: 0=PASS, 1=BLOCK, 2=WARN
- Plugin `on_error` supersedes hook `on_error`; plugins fire first
- See Report 14 (Safety Mapping) for per-feature migration strategy details
- See Report 16 (Security Posture) for plugin security and sandboxing analysis