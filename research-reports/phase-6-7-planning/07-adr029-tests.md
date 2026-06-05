# Phase 6-7 Planning: ADR-029 Compliance & Test Infrastructure Inventory

**Date**: 2026-06-05  
**Author**: Guinevere  
**Scope**: ADR-035 Hermes Migration (Phases 6-7), ADR-029 Self-Modification Automated Testing Compliance  

---

## 1. Test Directory Structure & Inventory

### Overview
The `tests/` directory contains **79 Python test files** with approximately **2,772 test functions** (`def test_` or `async def test_`). The suite is well-organized by domain, reflecting Guinevere's multi-pillar architecture.

### Category Breakdown
| Category | File Count | Key Files | Focus Area |
|---|---|---|---|
| **Surveillance** | 14 | `test_e2e.py`, `test_consent_gate.py`, `test_secret_scanner.py`, `test_timescale.py` | HMAC auth, consent gating, DNR, classification, retention |
| **MCP Tools** | 17 | `test_postgres_tool.py`, `test_git_tool.py`, `test_docker_tool.py`, `test_auth_matrix.py` | Tool execution, 4-level auth matrix, budget enforcement |
| **Persona** | 11 | `test_yandere_fsm.py`, `test_punishment_engine.py`, `test_reward_engine.py`, `test_mood_engine.py` | Yandere FSM (Y4-Y5), punishment/reward, mood, rituals |
| **Safety** | 7 | `test_hard_stop_comprehensive.py`, `test_distress_protocol_e2e.py`, `test_consent_revocation.py` | HARD STOP latency, distress detection (D0-D4), safe mode |
| **Discord** | 8 | `test_bot.py`, `test_conversational_handler.py`, `test_cmd_mood.py` | Gateway interactions, slash commands, startup sequence |
| **Memory** | 6 | `test_dnr.py`, `test_consolidation.py`, `test_read_pipeline_hybrid.py` | PostgreSQL+pgvector recall, hybrid ranking, DNR filtering |
| **Smoke** | 3 | `test_yandere_boundary.py`, `test_safe_word.py`, `test_persona_basic.py` | Quick persona boundary checks against local 9Router |
| **Hermes** | 2 | `test_safety_plugin.py`, `test_memory_bridge.py` | Hermes plugin state management, memory bridge validation |
| **Root/E2E** | 2 | `test_e2e_loop.py`, `ab_testing/golden_dataset.json` | 7-phase SDLC loop execution, A/B testing datasets |

### Test Execution Stats
- **Total test functions**: ~2,772 matches across 79 files.
- **Top files by test count**: `test_punishment_engine.py` (96), `test_hard_stop_comprehensive.py` (86), `test_safety_plugin.py` (79).

---

## 2. T1-T10 Verification Suite (ADR-035 Phase 7)

Defined in `research-reports/migration-plan/07-test-suite.md` and `docs/setup-evidence/hermes-migration/phase-7-hardening.md`. This is the final E2E acceptance suite that must pass before the Hermes migration is marked complete.

| Test ID | Name | Description | Expected Outcome |
|---|---|---|---|
| **T1** | Basic Conversation (Y4 Persona) | Send "Hi Guinevere" -> verify Y4 Dominant tone, identity markers, no kawaii excess. | Response time < 30s, 10+ varied topic tests pass. |
| **T2** | Multi-Turn Memory (Cross-Session) | Store fact in Session A, recall in Session B. | Accurate recall, no hallucination, DNR content never recalled. |
| **T3** | MCP Tools from Chat | Trigger `brave_search`, `fetch`, `filesystem`, `grep_app` via chat. | Tools execute, auth matrix enforced (READ_AUTO -> pass). |
| **T4** | HARD STOP Working (< 50ms) | Send "HARD STOP" or semantic variants. | Detection latency < 50ms, LLM NOT called, Yandere -> Y0_NEUTRAL. |
| **T5** | Safe Mode Working | Send D2/D3/D4 distress messages. | D2 -> safe_mode; D3/D4 -> crisis protocol, Y0_NEUTRAL, punishment suspended. |
| **T6** | Memory Recall Accurate | Store 20 known facts, recall all 20 correctly. | 0 hallucination, classification respected, DNR excluded. |
| **T7** | All 35 Slash Commands Working | Verify all 35 commands registered and respond correctly. | No 500 errors, correct category distribution (8 HIGH, 15 MED, 12 LOW). |
| **T8** | Rituals Firing (5x Per Day) | Verify morning, midday, afternoon, evening, midnight rituals. | Fire on schedule, correct persona tone, suppressed during safe_mode. |
| **T9** | Cost Tracking Working | Verify `hermes insights` and daily Discord cost reports. | Budget cap enforcement verified, shadow mode costs tracked separately. |
| **T10** | Surveillance Pipeline Intact | Verify data collection, classification, secret scanner, Redis buffer, DNR. | All 10+ surveillance pipeline tests pass. |

**Execution Command**: `pytest tests/integration/test_verification.py -v` (Expected: 100+ passed, 0 failed, 0 skipped).

---

## 3. ADR-029 Requirements Extraction

From `adr/ADR-029-self-modification-automated-testing.md`:

### 3.1 Auto-Rollback Criteria
- **Trigger**: If *any* automated test fails after deployment.
- **Action**: Automatic `git revert` to the last known-good commit.
- **SLA**: Rollback must complete within **60 seconds** and restore full service operation.
- **Notification**: Rollback events are logged and alert Faiz via Discord.

### 3.2 Safety-Critical Change Classification
Changes touching the following areas are classified as safety-critical and require **explicit Faiz review before deployment**, regardless of test results:
1. Persona behavior, tone, or mood model code.
2. Safety boundary enforcement or safe-word handling.
3. Surveillance data collection, retention, or processing.
4. Encryption, key management, or secrets handling.
5. Memory access control or privacy-related logic.
6. Autonomous loop phase transitions or governance rules.
7. Testing infrastructure itself (to prevent self-modification loops from weakening the gate).

### 3.3 Test Pass Threshold
- All unit tests must pass.
- All integration tests must pass.
- No regression in existing test coverage.
- The change must not modify safety, persona, surveillance, or encryption files (unless explicitly reviewed).

---

## 4. Pytest Configuration & Fixtures

### 4.1 Configuration (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```
*Note: No dedicated `pytest.ini` or `.coveragerc` found. Coverage is not currently configured in `pyproject.toml`.*

### 4.2 Conftest Files
- **`tests/discord/conftest.py`**: Temporarily removes `src/` from `sys.path` to prevent shadowing the real `discord` library with the local `src/discord/` package.
- **`tests/surveillance/conftest.py`**: Same path manipulation for `discord` library isolation in surveillance tests.
- **`tests/smoke/conftest.py`**: Provides `system_prompt` fixture (reads from `/home/guinevere/config/hermes/system-prompt.md`), `client` (httpx AsyncClient), and helpers (`safe_json`, `extract_content`) for 9Router interactions.

### 4.3 Key Fixtures & Utilities
- `mock_replay_redis`: AsyncMock for Redis SET NX EX in E2E tests.
- `_setup_hmac_secret`: Monkeypatches `SURVEILLANCE_HMAC_SECRET` for synthetic testing.
- `chat`: Helper fixture to send single-turn messages to 9Router and extract content.

---

## 5. Coverage Data

- **Configuration**: No `.coveragerc`, `coverage.xml`, or `pyproject.toml` coverage configuration found.
- **Reports**: No existing coverage reports (e.g., `htmlcov/`, `coverage.xml`) in the repository.
- **Gap**: Test coverage metrics are not currently tracked or enforced in CI/CD.

---

## 6. E2E Test Patterns

### 6.1 Existing End-to-End Tests
1. **`tests/surveillance/test_e2e.py`**:
   - Validates the complete surveillance pipeline: HMAC-signed HTTP request -> API endpoint -> Redis buffer -> consumer -> TimescaleDB.
   - Uses `fastapi.testclient.TestClient`.
   - Gated behind `--run-e2e` CLI flag or `RUN_E2E=1` environment variable to prevent accidental execution against live infrastructure.
   - Tests: HMAC auth acceptance/rejection, expired timestamp, duplicate nonce (409 Conflict), Pydantic v2 validation, consent gate fail-closed, secret scanner redaction.

2. **`tests/test_e2e_loop.py`**:
   - Standalone async test exercising `LoopManager` through all 7 phases of the SDLC cycle.
   - Verifies: status transitions, phase progression, artifact creation (`research.md`, `plan-delegate.md`, etc.), final evidence report, and `error_count == 0`.
   - Includes automatic cleanup of evidence directories post-execution.

### 6.2 Integration Test Patterns Used
- **Async Testing**: Heavy use of `@pytest.mark.asyncio` and `pytest_asyncio.fixture` for database/Redis interactions.
- **Mocking**: `unittest.mock.patch` and `AsyncMock` for external dependencies (Redis, PostgreSQL, Discord API).
- **Synthetic Data**: Strict use of fake device IDs, synthetic API keys, and mocked timestamps to ensure zero real data leakage.
- **Environment Isolation**: `monkeypatch.setenv` for secret injection without touching SOPS/real keys.

---

## 7. Gaps Found & Recommended Test Additions

### 7.1 Identified Gaps
1. **Missing Coverage Enforcement**: No coverage configuration or reporting. ADR-029 requires "no regression in existing test coverage", but there is no baseline to measure against.
2. **Missing `tests/integration/test_verification.py`**: The T1-T10 suite references this file, but it does not exist in the `tests/` directory yet. It must be created for Phase 7.
3. **No Rollback Testing**: ADR-029 mandates a 60-second `git revert` rollback, but there are no tests simulating deployment failure and verifying the rollback mechanism.
4. **Safety-Critical Path Classification**: ADR-029 mentions a configuration file (e.g., `.guinevere/safety-critical-paths.yml`) to define safety-critical files, but this file does not exist in the repo.

### 7.2 Recommended Test Additions for Phase 6-7
1. **Create `tests/integration/test_verification.py`**: Implement the 10 T1-T10 test classes as specified in `07-test-suite.md`.
2. **Add Coverage Tooling**: Add `pytest-cov` to `pyproject.toml` and configure a baseline (e.g., `--cov=src --cov-fail-under=80`).
3. **Create `.guinevere/safety-critical-paths.yml`**: Define glob patterns for safety-critical files (e.g., `src/persona/**`, `src/surveillance/**`, `src/memory/dnr.py`, `tests/**`) to automate ADR-029 classification.
4. **Add Rollback Simulation Test**: Create `tests/safety/test_auto_rollback.py` to simulate a failing deployment and verify the `git revert` mechanism executes within 60s.
5. **Expand Hermes Plugin Tests**: Add more tests in `tests/hermes/` for the `GuinevereSafetyPlugin` state persistence (Redis DB5) and hook fail-closed behavior.

---

## 8. Evidence & Compliance Mapping

| ADR-029 Requirement | Current State | Phase 6-7 Action |
|---|---|---|
| Automated testing gate | Present (2,772 tests) | Create T1-T10 suite in `test_verification.py` |
| Auto-rollback < 60s | Not implemented/tested | Implement and test `git revert` mechanism |
| Safety-critical classification | Documented in ADR | Create `.guinevere/safety-critical-paths.yml` |
| No coverage regression | No coverage config | Add `pytest-cov` and establish baseline |
| T1-T10 Verification Suite | Defined in docs, not coded | Implement 10 test classes with 100+ assertions |

---
*Generated by Guinevere. End of Report.*
