# Phase 1 Research Synthesis — Safety Migration Architecture

| Field | Value |
|---|---|
| Date | 2026-06-04 |
| Agents | 7 (2 librarian, 5 explore) |
| Phase | Phase 1 Safety Migration (ADR-035) |
| Status | ALL 7 COMPLETE |

## CRITICAL FINDING: ADR-035 Hook Spec ≠ Reality

ADR-035 describes a **subprocess-based JSON stdin/stdout** hook system with exit codes 0/1/2.
Reality: hermes-agent v0.15.2 uses **in-process Python callbacks** with different hook names.

### ADR-035 → Real Hermes Hook Mapping (DECISION: use real API)

| ADR-035 Hook | Real Hermes Hook | Return Contract |
|---|---|---|
| `pre_prompt` | `pre_llm_call` | `dict \| None` — `{"context": "..."}` to inject, None to pass |
| `post_prompt` | `post_llm_call` | `None` — observational only |
| `pre_tool_call` | `pre_tool_call` | `dict \| None` — `{"action": "block", "message": "..."}` to veto |
| `post_tool_call` | `post_tool_call` | `None` — observational |
| `pre_response` / `post_response` | `transform_llm_output` | `str \| None` — return string to replace, None to pass |
| `on_error` | `api_request_error` | `None` — observational |

### Real Hook Signatures (all accept `**_` for forward compat)

```python
pre_llm_call(*, task_id, session_id, platform, model, provider, base_url,
             api_mode, api_call_count, messages, turn_type,
             conversation_history, user_message, **_) -> dict | None

pre_tool_call(*, tool_name, args, task_id, session_id, tool_call_id, **_) -> dict | None

transform_llm_output(*, response_text, session_id, model, platform, **_) -> str | None

post_llm_call(*, task_id, session_id, provider, model, api_call_count,
              assistant_message, response, api_duration, finish_reason, usage, **_) -> None
```

## Plugin Registration Pattern

- **NO base class** to subclass
- **Directory-based**: `plugin.yaml` manifest + `__init__.py` with `register(ctx: PluginContext)` function
- Hooks registered via `ctx.register_hook(hook_name, callback)`
- Config: `plugins.enabled` list in `config.yaml`
- Entry point group: `hermes_agent.plugins`
- Dispatcher wraps each callback in try/except — misbehaving plugins can't break agent loop
- Supports both sync and async callbacks (inspects `isawaitable`)

## VALID_HOOKS (from `hermes_cli/plugins.py`)

```
pre_tool_call, post_tool_call, transform_terminal_output, transform_tool_result,
transform_llm_output, pre_llm_call, post_llm_call, pre_api_request, post_api_request,
api_request_error, on_session_start, on_session_end, on_session_finalize, on_session_reset,
subagent_start, subagent_stop, pre_gateway_dispatch, pre_approval_request, post_approval_response
```

## Module Import Paths

- Package: `hermes-agent` v0.15.2
- Top-level modules: `hermes_cli`, `agent`, `plugins`, `tools`, `gateway`, `run_agent`, `cli`, `cron`, `batch_runner`
- Flat files: `hermes_bootstrap.py`, `hermes_constants.py`, `hermes_logging.py`, `hermes_state.py`, `hermes_time.py`
- **NO `hermes` or `hermes_agent` module exists**
- Plugin system import: `from hermes_cli.plugins import PluginContext, VALID_HOOKS`

## Existing Architecture Constraint

`src/hermes/__init__.py` and `session_adapter.py` state: *"All safety guards remain in conversational_handler.py — NEVER inside Hermes."*

This constraint was written PRE-migration. Phase 1 explicitly PORTS safety into Hermes hooks. The plugin COEXISTS with conversational_handler.py safety during transition; eventually conversational_handler.py safety becomes redundant.

**Decision**: Implement safety plugin using real hermes-agent API. During transition, both safety layers active (defense-in-depth). Plugin is the migration target.

## Safety Subsystem API Surface (9 modules)

| Module | Type | Key API | Notes |
|---|---|---|---|
| `hard_stop_handler.py` | Stateful singleton | `HardStopHandler.check_message(text)` → bool | `is_safe` property, EXACT_TRIGGERS + semantic |
| `safe_mode.py` | Stateful singleton | `SafeModeController` + `DistressDetector.detect(text)` | Threshold D2_MODERATE |
| `yandere_fsm.py` | Stateful singleton | `YandereEngine(is_safe)` | IntEnum Y0-Y5, Y4 baseline, Y5 ceiling |
| `punishment_engine.py` | Stateful singleton | `PunishmentEngine(safe_mode, hard_stop)` | L1-L6, L5 max |
| `drift_detector.py` | Stateful singleton | `DriftDetector.check(text)` | SHA-256, threshold 0.10 |
| `secret_scanner.py` | Stateless | `scan_text(text)` / `redact_secrets(text)` | 17 patterns, Shannon ≥4.5 |
| `classification.py` | Stateless | `classify_event(event_type)` | 12 types, fail-closed CONFIDENTIAL |
| `consent_gate.py` | **Async only** | `await check_consent(scope, redis, db)` | 4 scopes, fail-closed |
| `auth_matrix.py` | Stateless | `get_auth_level(tool_name)` | 16 tools, KeyError on miss |

## Document Contradictions (3 resolved)

| # | Contradiction | Decision |
|---|---|---|
| 1 | YandereLevel names: ADR=Y4_DOMINANT, Phase-1=Y4_BASELINE | Use ACTUAL code: Y4_BASELINE, Y5_MAX |
| 2 | SessionSafetyState fields: ADR=14, Phase-1=9 | Use Phase-1-safety (matches actual module APIs) |
| 3 | Hook mechanism: ADR=subprocess JSON, Reality=Python callbacks | Use REAL hermes-agent in-process API |

## Testing Conventions (from existing 9 test files)

- Class-based grouping: `class TestXxx:`, methods `test_<scenario>_<expected>`
- `@pytest.mark.parametrize` with `ids`
- `unittest.mock.AsyncMock` for Redis/DB
- Custom fake objects for protocol interfaces
- Source code pattern verification (no `# type: ignore`, no bare `except`)
- Frozen dataclass verification (attempt mutation → expect AttributeError)
- `@pytest.mark.asyncio` for async tests
- pytest config: `testpaths=["tests"]`, `pythonpath=["src"]`

## AC-SAFE Acceptance Criteria

| ID | Criterion | Safety Gate |
|---|---|---|
| AC-SAFE-001 | HARD STOP exact + semantic triggers block | G01 pre_prompt |
| AC-SAFE-002 | Distress D1-D4 detection | G02 pre_prompt |
| AC-SAFE-003 | Forbidden patterns F-01..F-15 block | G05 pre_response |
| AC-SAFE-004 | Yandere boundary Y4 baseline, Y5 ceiling | G07 pre_prompt + G08 pre_response |
| AC-SAFE-005 | Secret scanner blocks API keys/tokens | G06 pre_response |
| AC-SAFE-006 | Surveillance consent gate 4 scopes | G09 pre_tool_call |
| AC-SAFE-007 | Drift detector SHA-256 threshold | G03 post_prompt |
| AC-SAFE-008 | Recovery triggers clear HARD STOP | G04 pre_prompt |

---

*Synthesized 2026-06-04. All 7 research agents complete.*
