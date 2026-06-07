# Phase 6 Regression Audit

## Verdict
**FAIL** — The regression suite is not green. One required module (`tests/safety/`) failed during collection because `pytest_asyncio` was missing, and several other required modules still contain substantial test failures when executed via `uv run pytest`.

## Execution Summary
- Dependency install: `uv sync --extra test` ✅
- Test runner: `uv run pytest <module> -v --tb=short` ✅
- Forbidden flag check: no `--timeout` used ✅

## Module Results

| Module | Passed | Failed | Skipped | XFailed | Notes |
|---|---:|---:|---:|---:|---|
| `tests/phase7/` | 139 | 0 | 0 | 0 | Clean pass |
| `tests/safety/` | 0 | 0 | 0 | 0 | Collection stopped by `ModuleNotFoundError: pytest_asyncio` |
| `tests/hermes/` | 709 | 28 | 0 | 0 | Async tests in `test_llm_metrics.py`, `test_llm_router_cost.py`, `test_memory_bridge.py` failed with async plugin support errors |
| `tests/memory/` | 235 | 104 | 3 | 0 | Broad failures across `test_time_tools.py`, `test_tool_selector.py`, `test_websearch.py`, plus related async-marked tests |
| `tests/mcp/` | 807 | 241 | 0 | 0 | Broad async-related failures across `test_auth_matrix.py`, `test_budget.py`, `test_time_tools.py`, `test_tool_selector.py`, `test_websearch.py` |
| `tests/persona/` | 347 | 148 | 10 | 0 | Large failures across drift, mood persistence, ritual, scheduler, streak tracker suites |
| `tests/surveillance/` | 347 | 148 | 10 | 0 | Large failures across consent gate, consumer, discord commands, redis buffer, replay, timescale suites |

## Failure Details

### 1) `tests/safety/` collection failure
The module did not execute because pytest could not import `pytest_asyncio`:

- `tests/safety/test_hard_stop_model.py:15`
- Error: `ModuleNotFoundError: No module named 'pytest_asyncio'`

This indicates the test dependency is still not available in the current environment for that module, despite running `uv sync --extra test`.

### 2) Hermes regression failures
The Hermes suite mostly passed, but 28 tests failed. The dominant pattern was async test collection/execution failure:

- `tests/hermes/test_llm_metrics.py`
- `tests/hermes/test_llm_router_cost.py`
- `tests/hermes/test_memory_bridge.py`

Representative failure text:
- `async def functions are not natively supported.`
- `PytestUnknownMarkWarning: Unknown pytest.mark.asyncio`

This strongly suggests the async test plugin is not active in the test environment for these modules.

### 3) Memory regression failures
The memory suite had 104 failures and 3 skips. Main failure clusters were in:

- `tests/memory/test_time_tools.py`
- `tests/memory/test_read_pipeline_hybrid.py`
- `tests/memory/test_safe_mode_memory.py`

### 4) MCP regression failures
The MCP suite had 241 failures. Major areas:

- `tests/mcp/test_auth_matrix.py`
- `tests/mcp/test_budget.py`
- `tests/mcp/test_time_tools.py`
- `tests/mcp/test_tool_selector.py`
- `tests/mcp/test_websearch.py`

Observed failure mode was consistently the async plugin error:
- `async def functions are not natively supported.`
- `PytestUnknownMarkWarning: Unknown pytest.mark.asyncio`

### 5) Persona regression failures
The persona suite had 148 failures and 10 skips. Failures were concentrated in:

- `tests/persona/test_drift_corrector.py`
- `tests/persona/test_mood_persistence.py`
- `tests/persona/test_persona_e2e.py`
- `tests/persona/test_ritual_afternoon.py`
- `tests/persona/test_ritual_evening.py`
- `tests/persona/test_ritual_midday.py`
- `tests/persona/test_ritual_midnight.py`
- `tests/persona/test_ritual_morning.py`
- `tests/persona/test_ritual_scheduler.py`
- `tests/persona/test_streak_tracker.py`

### 6) Surveillance regression failures
The surveillance suite also had 148 failures and 10 skips. Main failing areas:

- `tests/surveillance/test_consent_gate.py`
- `tests/surveillance/test_consumer.py`
- `tests/surveillance/test_discord_commands.py`
- `tests/surveillance/test_redis_buffer.py`
- `tests/surveillance/test_replay.py`
- `tests/surveillance/test_timescale.py`

## Overall Justification
The audit cannot be accepted as passing because:
1. A required test dependency (`pytest_asyncio`) is still missing for at least one module during collection.
2. Multiple critical suites fail in bulk, not as isolated edge cases.
3. The failing patterns are systemic across async-heavy modules, suggesting an environment/configuration issue and/or incomplete dependency wiring.
4. The regression target is therefore not stable enough to claim Phase 6 completion.

## Notes
- `uv sync --extra test` was executed first as required.
- All test commands were run with `uv run pytest ... -v --tb=short` and **without** `--timeout`.
- Source files were not edited.