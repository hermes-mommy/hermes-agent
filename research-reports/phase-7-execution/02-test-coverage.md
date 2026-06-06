# Phase 7 — Local Test Coverage & ADR-029 Test Inventory Report

**Generated:** 2026-06-06
**Collect command:** python -m pytest --collect-only -q
**Scope:** All 	ests/ subtree — 3878 tests collected in 22.01s

---

## 1. Test File Inventory

### 1.1 Count by Directory

| Directory | .py Files | Test Functions | Notes |
|---|---|---|---|
| tests/mcp/ | 22 | 807 | Largest area — shell, docker, git, redis, auth, budgets, search tools |
| tests/hermes/ | 12 | 695 | Auth overlay, hybrid guards, security audit, integration e2e |
| tests/persona/ | 19 | ~520 | Mood, yandere FSM, rituals, drift/correction, rewards, punishment |
| tests/surveillance/ | 16 | ~520 | Consent gate, HMAC, secret scanner, replay, timescale, router |
| tests/memory/ | 7 | 235 | Read pipeline, consolidation, DNR, safe-mode memory, prompt injection |
| tests/discord/ | 8 | 152 | Bot instantiation, mood embed, conversational handler, notifications |
| tests/safety/ | 8 | ~430 | Hard stop (handler + model + comprehensive), distress e2e, yandere cap |
| tests/smoke/ | 5 | 9 | Persona basic, safe word, yandere boundary (live 9Router smoke tests) |
| tests/ (root) | 2 | 1 | 	est_e2e_loop.py (1 test), __init__.py (empty) |
| tests/ab_testing/ | 1 | 0 | Only empty __init__.py — no actual tests |
| **Total** | **100** | **3878** | |

> Note: Directory-level test function counts are approximate totals from --collect-only output; function-level breakdowns are exact per file from grep.

### 1.2 Top 10 Heaviest Test Files

| File | Tests | Focus |
|---|---|---|
| tests/hermes/test_hybrid_guards.py | 201 | Hermes hybrid guard injection & enforcement |
| tests/safety/test_distress_protocol_e2e.py | 126 | D0-D4 distress escalation, false positives, yandere interaction |
| tests/persona/test_distress_detection.py | 113 | Distress detection signals, confidence, batch, history |
| tests/hermes/test_security_audit.py | 108 | Security audit checks, fail-closed stance |
| tests/persona/test_punishment_engine.py | 96 | Punishment tiers escalation logic |
| tests/persona/test_safe_mode.py | 95 | Safe mode entry/exit, suppression rules |
| tests/hermes/test_auth_overlay.py | 94 | Auth matrix, pre-tool-call enforcement |
| tests/mcp/test_auth_matrix.py | 94 | MCP-level auth matrix (same surface, different layer) |
| tests/hermes/test_safety_plugin.py | 90 | Safety plugin integration points |
| tests/safety/test_hard_stop_comprehensive.py | 86 | Hard stop semantics, patterns, recovery |

---

## 2. Collection State

### 2.1 Summary

3878 tests collected in 22.01s

### 2.2 Collection Errors

**None.** Zero collection errors or import failures.

### 2.3 Warnings

| Severity | Source | Message |
|---|---|---|
| DeprecationWarning | src/hermes/__init__.py:12 | memory_bridge is deprecated; use plugins/memory/guinevere_memory |
| StarletteDeprecationWarning | fastapi/testclient.py | Using httpx with starlette.testclient is deprecated; install httpx2 |
| PytestDeprecationWarning | pytest_asyncio plugin | asyncio_default_fixture_loop_scope is unset |

### 2.4 Async Fixture Warning Detail

The pytest_asyncio plugin warns that asyncio_default_fixture_loop_scope is unset. Future versions will default to function scope. Should be set explicitly in pyproject.toml.

---

## 3. E2E / Integration Test Presence

### 3.1 Dedicated E2E Test Files

| File | Tests | Scope Summary |
|---|---|---|
| tests/test_e2e_loop.py | 1 | Single test_full_loop_cycle — full agent loop cycle |
| tests/hermes/test_integration_e2e.py | 59 | Config parsing, auth matrix, shell injection blocking, docker/git/filesystem security, budget Lua scripts, fail-closed, port blocking, no-type-ignore, test count scaffold validation |
| tests/surveillance/test_e2e.py | 10 | HMAC signed requests, invalid HMAC rejection, expiry, duplicate nonce, event classification, consent gate, secret scanner redaction |
| tests/persona/test_persona_e2e.py | 58 | Full happy-path lifecycle, punishment/stresk/reset, distress/safe/recovery, drift detection+correction, rituals, D4 full safety chain, yandere ceiling, hard stop recovery |
| tests/safety/test_distress_protocol_e2e.py | 126 | D0-D4 full escalation chain, false-negative zero requirement, false-positive threshold, yandere interaction, punishment suspension, explicit deactivation, Indonesian distress signals |
| tests/memory/test_memory_e2e.py | 28 | Memory read pipeline, consolidation, recall |

### 3.2 E2E-Capable Test Files (partial E2E coverage)

| File | Relevant Tests |
|---|---|
| tests/hermes/test_auth_overlay.py | Auth enforcement via pre-tool-call |
| tests/persona/test_drift_detector.py | Rollback for severe drift |
| tests/persona/test_drift_corrector.py | Auto-rollback triggers, commit failures |
| tests/safety/test_hard_stop_model.py | Hard stop model validation |

---

## 4. Phase 7 T-Suite Presence (ADR-029)

### 4.1 T1-T10 Named Tests

| Test ID | File | Status |
|---|---|---|
| T1 (full loop cycle) | tests/test_e2e_loop.py::test_full_loop_cycle | **Present** — 1 test |
| T2-T10 named | *None found* | **ABSENT** — No files or test functions use T1/T2/...T10 naming convention |

### 4.2 Tests Relevant to Phase 7 Scope

| Phase 7 Concern | Relevant Test Files | Tests |
|---|---|---|
| Full loop cycle | tests/test_e2e_loop.py | 1 |
| Auth enforcement | tests/hermes/test_auth_overlay.py, tests/mcp/test_auth_matrix.py | 188 |
| Safety plugin | tests/hermes/test_safety_plugin.py | 90 |
| Hybrid guards | tests/hermes/test_hybrid_guards.py | 201 |
| Security audit | tests/hermes/test_security_audit.py | 108 |
| Budget fail-closed | tests/hermes/test_budget_hook.py | 47 |
| Shell/docker/git security | tests/mcp/test_shell_tool.py, tests/mcp/test_docker_tool.py, tests/mcp/test_git_tool.py | 192 |
| FastMCP bridge | tests/hermes/test_fastmcp_bridge.py | 18 |
| MCP manager | tests/mcp/test_manager.py | 20 |

### 4.3 Key Gap: No T-Suite Naming

No test files or functions carry T1 through T10 identifiers. Phase 7 requirements call for a dedicated T-suite. Existing tests cover the scope but are not organized under the T-suite naming convention.

---

## 5. Coverage Configuration

### 5.1 .coveragerc

**STATUS: ABSENT** — No .coveragerc file exists anywhere in the project root.

### 5.2 Coverage in pyproject.toml

**Not configured.** pyproject.toml has [tool.pytest.ini_options] but zero coverage-related sections.

### 5.3 Gap

Coverage measurement is **not configured at all**. Phase 7 requires full pytest tests/ -q --tb=short + coverage PASS. Without .coveragerc or coverage tool config, coverage cannot be enforced.

---

## 6. .guinevere/safety-critical-paths.yml

**STATUS: ABSENT** — No .guinevere/ directory exists at the project root.

---

## 7. Pytest Configuration

### 7.1 Config Sources

| Source | Exists | Content |
|---|---|---|
| pytest.ini | **No** | Not present |
| pyproject.toml [tool.pytest.ini_options] | **Yes** | testpaths = ["tests"], pythonpath = ["src"] |
| Root conftest.py | **No** | Not present |
| Directory-level conftest.py | **3 files** | See below |

### 7.2 Directory-Level conftest Files

| File | Purpose |
|---|---|
| tests/smoke/conftest.py | System prompt reader from 9Router config path + httpx.AsyncClient fixture + chat helper for smoke tests |
| tests/surveillance/conftest.py | Pre-caches real discord library before src/discord/ shadows it |
| tests/discord/conftest.py | Pre-caches real discord.ext.commands before src/discord/ shadows it (same pattern) |

### 7.3 Missing Configuration

| Item | Status | Blocker? |
|---|---|---|
| asyncio_default_fixture_loop_scope | Not set | Medium |
| --strict-markers | Not set | Low |
| --strict-config | Not set | Low |
| filterwarnings | Not set | Low |

---

## 8. Deprecated / Archivable Test Imports

### 8.1 tests/hermes/test_memory_bridge.py

- **17 tests** — imports from src.hermes.memory_bridge import HermesMemoryBridge
- src/hermes/__init__.py:12 triggers DeprecationWarning at collection time:
  memory_bridge is deprecated; use plugins/memory/guinevere_memory
- **Target for archive in Phase 7** — entire file is deprecated.

### 8.2 tests/discord/* (8 files, 152 tests)

All files import from src.discord.*:

| File | Tests | Deprecated Import |
|---|---|---|
| tests/discord/test_bot.py | 30 | from src.discord.bot |
| tests/discord/test_cmd_mood.py | 44 | from src.discord.cmd_mood |
| tests/discord/test_conversational_handler.py | 21 | from src.discord.conversational_handler |
| tests/discord/test_startup.py | 22 | from src.discord.startup |
| tests/discord/test_notifications.py | 13 | from src.discord.notifications |
| tests/discord/test_gotify_fallback.py | 12 | from src.discord.gotify_fallback |
| tests/discord/test_gotify_client.py | 10 | from src.discord.gotify_client |
| tests/surveillance/test_discord_commands.py | 37 | from src.discord.cmd_surveillance_status |

**Total: 189 tests** across 8 files importing from src.discord.* — all at risk if src/discord/ is archived.

### 8.3 tests/surveillance/conftest.py

Also uses the _cache_real_discord() workaround to shadow src/discord/. Must be updated if discord source is archived.

### 8.4 tests/memory/test_consolidation.py

Contains archive test functions (test_archive_default_is_non_destructive, etc.) — these test a retention/mode=archive feature, not archiving of test files themselves. These are safe.

---

## 9. Rollback Tests

### 9.1 Rollback Test Files

| File | Rollback Tests | Coverage |
|---|---|---|
| tests/persona/test_drift_corrector.py | 20+ | Auto-rollback on severe drift, safe-mode deferral, commit failure, double failure, hash restoration, drift log creation |
| tests/persona/test_drift_detector.py | 1 | test_rollback_for_severe_drift |
| tests/persona/test_persona_e2e.py | 2 | Corrector triggers rollback, corrector defers in safe mode |
| tests/surveillance/test_consumer.py | 1 | test_store_rollback_on_failure |

### 9.2 Gap

No **dedicated standalone rollback test suite**. Rollback coverage exists inside test_drift_corrector.py but is combined with drift correction tests.

---

## 10. Key Gaps and Blockers

| # | Gap | Severity | Impact |
|---|---|---|---|
| 1 | **No .coveragerc** | RED BLOCKER | Cannot measure or enforce coverage thresholds. Phase 7 requires coverage PASS. |
| 2 | **No .guinevere/safety-critical-paths.yml** | RED BLOCKER | Safety-critical paths not defined. Phase 7 requires this file. |
| 3 | **No T1-T10 named test suite** | YELLOW High | Phase 7 requires organized T-suite. Existing tests cover the scope but lack T-suite structure. |
| 4 | **189 tests import from src.discord.*** | YELLOW High | If src/discord/ is archived, these tests break without migration. |
| 5 | **tests/hermes/test_memory_bridge.py (17 tests)** | YELLOW High | Deprecated memory_bridge — will break when module is removed. |
| 6 | **No asyncio_default_fixture_loop_scope** | YELLOW Medium | Future pytest-asyncio behavioral change; may cause test failures. |
| 7 | **No dedicated rollback test file** | YELLOW Medium | Rollback tests embedded in drift corrector — not independently runnable as a suite. |
| 8 | **tests/ab_testing/ empty** | GREEN Low | Placeholder directory with no tests. |
| 9 | **Smoke tests require live 9Router** | GREEN Low | tests/smoke/conftest.py requires http://localhost:20128 — cannot run offline. |

---

## 11. Risk Summary for Planner Scaffold

### Green (Ready — no action needed)
- 3878 tests collect cleanly with zero errors
- All existing tests pass collection (no import failures)
- E2E coverage across hermes, surveillance, persona, memory, safety
- Rollback coverage exists (though embedded)
- Hermes integration E2E (59 tests) covers many Phase 7 surfaces

### Yellow (Needs attention before Phase 7 implementation)
- T-suite naming/organization needs to be created (not refactored — new)
- Rollback test standalone suite may be needed
- Async loop scope config needs to be set

### Red (Blockers — must create before Phase 7 verification gate)
- .coveragerc must be created
- .guinevere/safety-critical-paths.yml must be created
- Coverage tool (pytest-cov or coverage) must be added to dependencies

---

## 12. Collection Command Details

### Command
python -m pytest --collect-only -q

### Warnings (Exact)
src/hermes/__init__.py:12: DeprecationWarning: memory_bridge is deprecated; use plugins/memory/guinevere_memory
(REDACTED - no secrets) fastapi/testclient.py:1: StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated
pytest_asyncio/plugin.py:207: PytestDeprecationWarning: asyncio_default_fixture_loop_scope is unset

### Result
3878 tests collected in 22.01s

---

## Appendix A: Complete Test File List

tests/__init__.py
tests/ab_testing/__init__.py
tests/discord/conftest.py
tests/discord/test_bot.py
tests/discord/test_cmd_mood.py
tests/discord/test_conversational_handler.py
tests/discord/test_gotify_client.py
tests/discord/test_gotify_fallback.py
tests/discord/test_notifications.py
tests/discord/test_startup.py
tests/hermes/__init__.py
tests/hermes/test_auth_overlay.py
tests/hermes/test_budget_hook.py
tests/hermes/test_fastmcp_bridge.py
tests/hermes/test_hybrid_guards.py
tests/hermes/test_integration_e2e.py
tests/hermes/test_llm_metrics.py
tests/hermes/test_llm_router_cost.py
tests/hermes/test_mcp_config.py
tests/hermes/test_memory_bridge.py         /* DEPRECATED */
tests/hermes/test_security_audit.py
tests/hermes/test_safety_plugin.py
tests/mcp/__init__.py
tests/mcp/test_auth_matrix.py
tests/mcp/test_budget.py
tests/mcp/test_brave_search.py
tests/mcp/test_context7.py
tests/mcp/test_cost.py
tests/mcp/test_docker_tool.py
tests/mcp/test_exa_search.py
tests/mcp/test_fetch.py
tests/mcp/test_filesystem.py
tests/mcp/test_git_tool.py
tests/mcp/test_github.py
tests/mcp/test_grep_app.py
tests/mcp/test_manager.py
tests/mcp/test_obscura_cdp.py
tests/mcp/test_postgres_tool.py
tests/mcp/test_redis_tool.py
tests/mcp/test_sequential_thinking.py
tests/mcp/test_shell_tool.py
tests/mcp/test_time_tools.py
tests/mcp/test_tool_selector.py
tests/mcp/test_websearch.py
tests/memory/__init__.py
tests/memory/test_consolidation.py
tests/memory/test_dnr.py
tests/memory/test_memory_e2e.py
tests/memory/test_prompt_context_injection.py
tests/memory/test_read_pipeline_hybrid.py
tests/memory/test_safe_mode_memory.py
tests/persona/__init__.py
tests/persona/test_distress_detection.py
tests/persona/test_drift_corrector.py
tests/persona/test_drift_detector.py
tests/persona/test_mood_engine.py
tests/persona/test_mood_persistence.py
tests/persona/test_persona_e2e.py
tests/persona/test_punishment_engine.py
tests/persona/test_reward_engine.py
tests/persona/test_ritual_afternoon.py
tests/persona/test_ritual_evening.py
tests/persona/test_ritual_midday.py
tests/persona/test_ritual_midnight.py
tests/persona/test_ritual_morning.py
tests/persona/test_ritual_scheduler.py
tests/persona/test_safe_mode.py
tests/persona/test_streak_tracker.py
tests/persona/test_transition_rules.py
tests/persona/test_yandere_fsm.py
tests/safety/__init__.py
tests/safety/test_consent_revocation.py
tests/safety/test_distress_protocol_e2e.py
tests/safety/test_hard_stop_comprehensive.py
tests/safety/test_hard_stop_handler.py
tests/safety/test_hard_stop_model.py
tests/safety/test_punishment_overflow.py
tests/safety/test_yandere_cap.py
tests/smoke/__init__.py
tests/smoke/conftest.py
tests/smoke/test_persona_basic.py
tests/smoke/test_safe_word.py
tests/smoke/test_yandere_boundary.py
tests/surveillance/__init__.py
tests/surveillance/conftest.py
tests/surveillance/test_auth.py
tests/surveillance/test_classification.py
tests/surveillance/test_consent_gate.py
tests/surveillance/test_consumer.py
tests/surveillance/test_discord_commands.py  /* imports from src.discord */
tests/surveillance/test_e2e.py
tests/surveillance/test_redis_buffer.py
tests/surveillance/test_replay.py
tests/surveillance/test_retention.py
tests/surveillance/test_router.py
tests/surveillance/test_safe_mode.py
tests/surveillance/test_secret_scanner.py
tests/surveillance/test_secrets.py
tests/surveillance/test_timescale.py
tests/test_e2e_loop.py

---

## Appendix B: Deprecated File Details

### tests/hermes/test_memory_bridge.py
- **17 tests** — direct import of deprecated HermesMemoryBridge
- Module source src/hermes/memory_bridge.py emits DeprecationWarning
- Mitigation: Entire file is candidate for archive

### tests/discord/* (8 files)
- **152 tests** importing from src.discord.*
- Mitigation: These require migration if src/discord/ is removed or restructured

### tests/surveillance/test_discord_commands.py
- **37 tests** importing from src.discord.cmd_surveillance_status
- Double risk: surveillance import + discord dependency

---

*End of report*
