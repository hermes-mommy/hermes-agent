# D07 — Test Coverage & Quality Audit: Agent Loop (P5)

**Date:** 2026-06-02  
**Auditor:** Independent Testing Auditor  
**Scope:** `src/loops/`, `src/core/api/`, `src/discord/cmd_loop_*.py`  
**Test Files Audited:** 1 file (`tests/test_e2e_loop.py`)  
**Total Source Modules:** 24 (with logic)  
**Total Test Files:** 1

---

## 1. What `test_e2e_loop.py` Actually Tests

The file contains exactly **one test function**: `async def test_full_loop_cycle()` — 194 lines. It is NOT a pytest test; it uses a custom runner (`asyncio.run()`) invoked via `if __name__ == "__main__"` with boolean-tuple assertions and manual `_print_results()` formatting.

### Assertion Inventory (15 total)

| # | Assertion | Type | Meaningful? |
|---|---|---|---|
| 1 | `start_loop returns loop_id` | `isinstance(str) and len > 0` | ✅ Basic but OK |
| 2 | `Loop reached terminal status within 30s` | `final_status is not None` | ✅ Timeout check |
| 3 | `Final status is 'complete'` | String equality | ✅ |
| 4 | `Reached COMPLETE phase (value=8)` | Integer equality | ✅ |
| 5 | `Final phase name is 'Complete'` | String equality | ✅ |
| 6 | `Artifact exists: research.md` | File existence | ⚠️ Binary check |
| 7 | `Artifact exists: plan-delegate.md` | File existence | ⚠️ Binary check |
| 8 | `Artifact exists: delegate.md` | File existence | ⚠️ Binary check |
| 9 | `Artifact exists: execute.md` | File existence | ⚠️ Binary check |
| 10 | `Artifact exists: validate-audit.md` | File existence | ⚠️ Binary check |
| 11 | `Artifact exists: update-documents.md` | File existence | ⚠️ Binary check |
| 12 | `Artifact exists: setup-evidence.md` | File existence | ⚠️ Binary check |
| 13 | `Final evidence report (evidence-final.md)` | File existence | ⚠️ Binary check |
| 14 | `error_count is 0` | Integer equality | ✅ |
| 15 | `Status artifacts dict has 7 entries` | Dict length check | ✅ |
| 16 | `Task preserved in status` | String equality | ✅ |
| 17 | `Goal preserved in status` | String equality | ✅ |

**Verdict:** 17 checks, all happy-path. Zero error-path coverage. Zero edge-case coverage. Artifact checks only verify file existence, NOT content validity. No structural assertion framework (no `unittest`/`assert` statements — just boolean tuple accumulation).

---

## 2. Modules With NO Test Coverage

11 modules have **zero** test coverage — no test file imports or exercises them:

| # | Module | Lines | Key Untested Entities |
|---|---|---|---|
| 1 | `src/loops/enforcer.py` | 132 | `TodoEnforcer` (6 methods: `track_agent`, `untrack_agent`, `record_activity`, `check_idle`, `enforce`) |
| 2 | `src/loops/hash_anchor.py` | 121 | `compute_line_hash`, `validate_edit_content`, `validate_edit`, `HashAnchorError` |
| 3 | `src/loops/sub_agent.py` | 128 | `SubAgentSpawner` (4 methods: `spawn`, `get_spawned`, `mark_complete`, `mark_failed`) |
| 4 | `src/loops/contract.py` | 130 | `TaskContract`, `build_contract`, `contract_to_prompt`, `_as_list` |
| 5 | `src/loops/verify.py` | 183 | `OutputVerifier` (6 methods: `verify_file_exists`, `verify_markdown`, `verify_no_forbidden`, `verify_command`, `record`, `summary`) |
| 6 | `src/loops/cost.py` | 194 | `LoopCostTracker` (3 methods: `record_loop_cost`, `get_loop_cost`, `get_all_loop_costs`) + Redis dependency |
| 7 | `src/loops/scheduler.py` | 175 | `LoopScheduler` (5 methods: `add_daily_ritual`, `remove_job`, `list_jobs`, `start`, `stop`) + APScheduler dependency |
| 8 | `src/core/api/routes.py` | 90 | 4 HTTP endpoints: `GET /loops`, `POST /loops`, `GET /loops/{id}`, `POST /loops/{id}/cancel` |
| 9 | `src/core/api/auth.py` | 62 | `verify_api_key`, `get_api_key` (API key auth + HMAC comparison) |
| 10 | `src/discord/cmd_loop_start.py` | 453 | `build_loop_start_embed_data`, `to_discord_embed`, `loop_start_callback`, `_format_wib_timestamp`, `_get_option_value`, `_send_denied`, `_defer_ephemeral`, `_followup_send` |
| 11 | `src/discord/cmd_loop_stop.py` | 522 | `build_loop_stop_embed_data`, `to_discord_embed`, `loop_stop_callback`, `_cancel_loop`, `_list_active_loops`, `_format_wib_timestamp`, `_get_option_value`, `_send_denied`, `_defer_ephemeral`, `_followup_send` |

---

## 3. Untested Functions/Methods in Partially-Covered Modules

13 modules have **partial** (indirect, E2E happy-path only) coverage:

| Module | Covered | NOT Covered |
|---|---|---|
| `manager.py` | `__init__`, `start_loop`, `get_loop_status`, `_run_loop` | **`stop_loop()`**, **`list_loops()`**, **`main()`** |
| `state_machine.py` | `__init__`, `advance`, `set_status`, `is_terminal` (indirect), `record_artifact`, `to_dict` | **`pause()`**, **`resume()`**, **`fail()`**, **`cancel()`**, **`is_complete()`**, **`get_artifact()`** |
| `guardian.py` | `__init__`, `register_loop`, `unregister_loop`, `heartbeat`, `record_phase_advance` | **`monitor()`**, **`kill_loop()`**, **`stop()`** |

---

## 4. Test Infrastructure Assessment

| Property | Status | Notes |
|---|---|---|
| **Test framework** | ❌ None | Not pytest, not unittest. Custom `async def` with `asyncio.run()` |
| **pytest** | ❌ Not used | File is manually runnable via `python tests/test_e2e_loop.py` |
| **Fixtures** | ❌ None | No setup/teardown, manual `shutil.rmtree` cleanup in `finally` |
| **Mocking** | ❌ None | Zero mocks. Test requires real filesystem at `/home/guinevere/evidence/loops/` |
| **Parametrization** | ❌ None | Single hardcoded task/goal: "Create README for memory module" |
| **Assertion library** | ❌ Custom | Boolean tuples + manual print formatting, not `assert`/`unittest` |
| **Coverage tooling** | ❌ None | No `coverage.py`, no `pytest-cov` |
| **CI/CD hooks** | ❌ Unknown | No `.github/workflows`, no `tox.ini`, no `Makefile` target for this test |
| **conftest.py** | ❌ None | No `tests/conftest.py` for loop tests |

**⚠️ CRITICAL:** The test directly depends on filesystem path `/home/guinevere/evidence/loops/` which will fail on Windows or non-standard environments.

---

## 5. Assertion Quality Analysis

| Quality Dimension | Score | Evidence |
|---|---|---|
| **Meaningfulness** | 4/10 | Happy-path checks are reasonable but surface-level. No content validation. |
| **Precision** | 3/10 | Artifact assertions only check file existence — not a single line of content. 200+ characters of phase output are produced but never validated. |
| **Error differentiation** | 0/10 | Three `except` blocks (`ImportError`, `OSError`, `Exception`) catch ALL errors and record them as assertion tuples. Useful for diagnostics but NOT for test isolation. |
| **Independence** | 0/10 | All 17 assertions are sequential and co-dependent. Phase 1 failure cascades to all subsequent checks. |
| **Boundary testing** | 0/10 | No edge cases: `start_loop` with empty task, special characters, long strings, None goal, invalid priority. |
| **Regression safety** | 2/10 | Only catches catastrophic breakage (loop doesn't complete). Silent failures (wrong artifact content, skipped phase, partial output) pass undetected. |

**Overall:** Assertions are barely above smoke-test quality. They confirm "the car starts and moves" but never check "it steers, brakes, or has airbags."

---

## 6. Error Path Coverage

**ZERO error paths are tested. Period.**

| Error Scenario | Tested? | Impact |
|---|---|---|
| Loop fails mid-execution (`state.fail()`) | ❌ | `fail()` never called in test |
| Loop cancelled (`state.cancel()`) | ❌ | `stop_loop()` never tested |
| Phase handler raises exception | ❌ | All handlers are synchronous templates — no realistic failure path |
| Guardian kills a loop (`kill_loop()`) | ❌ | Monitor never runs in test |
| Enforcer idle/kill thresholds | ❌ | `TodoEnforcer` never instantiated |
| Hash anchor mismatch | ❌ | `HashAnchorError` never raised |
| Invalid sub-agent category (`ValueError`) | ❌ | `SubAgentSpawner.spawn()` never called |
| Redis connection failure | ❌ | `LoopCostTracker` never instantiated |
| API auth failure (missing/invalid key) | ❌ | No HTTP client test |
| Discord command denied (non-Faiz) | ❌ | No Discord interaction test |
| APScheduler trigger failure | ❌ | `LoopScheduler` never instantiated |

**Verdict:** The test suite has **zero error-path coverage** across all 24 modules.

---

## 7. State Machine Transition Testing

| Transition | Tested? | Notes |
|---|---|---|
| `INIT → RUNNING` (via `set_status`) | ✅ Indirect | Manager sets this in `start_loop` |
| `RESEARCH → PLAN_AND_DELEGATE` (via `advance`) | ✅ Indirect | Through 7-phase loop |
| `PLAN_AND_DELEGATE → DELEGATE` | ✅ Indirect | Through 7-phase loop |
| `DELEGATE → EXECUTE` | ✅ Indirect | Through 7-phase loop |
| `EXECUTE → VALIDATE_AND_AUDIT` | ✅ Indirect | Through 7-phase loop |
| `VALIDATE_AND_AUDIT → UPDATE_DOCUMENTS` | ✅ Indirect | Through 7-phase loop |
| `UPDATE_DOCUMENTS → SETUP_EVIDENCE` | ✅ Indirect | Through 7-phase loop |
| `SETUP_EVIDENCE → COMPLETE` | ✅ Indirect | Through 7-phase loop |
| `RUNNING → PAUSED` (via `pause()`) | ❌ | `pause()` never called |
| `PAUSED → RUNNING` (via `resume()`) | ❌ | `resume()` never called |
| `BLOCKED → RUNNING` (via `resume()`) | ❌ | `resume()` never called |
| `* → FAILED` (via `fail()`) | ⚠️ Indirect | Only via manager exception handler, not directly tested |
| `* → CANCELLED` (via `cancel()`) | ❌ | `cancel()` called only in `stop_loop()` which is untested |
| `advance()` on already-COMPLETE (`ValueError`) | ❌ | Edge case not tested |
| `pause()` on terminal status (`ValueError`) | ❌ | Edge case not tested |
| `resume()` on non-PAUSED/BLOCKED (`ValueError`) | ❌ | Edge case not tested |

**Verdict:** Only the linear happy-path 7-step advance is exercised. No branching, no error transitions, no guard-rail violations.

---

## 8. Guardian Timeout Testing

| Guardian Feature | Tested? | Notes |
|---|---|---|
| `HEARTBEAT_INTERVAL` (30s) | ❌ | Guard class constant, never evaluated as threshold |
| `PROGRESS_TIMEOUT` (300s) | ❌ | 5-minute stall detection — never tested |
| `RESOURCE_CHECK` (60s) | ❌ | Periodic resource checks — never tested |
| `monitor()` loop | ❌ | Guardian runs as separate `asyncio.Task` in `main()` but the E2E test never starts it |
| `kill_loop()` on heartbeat loss | ❌ | Never triggered |
| `kill_loop()` on progress stall | ❌ | Never triggered |

**Verdict:** Guardian monitoring is **completely untested**. The E2E test creates a `LoopGuardian` instance but never runs `monitor()`. Heartbeat recording is exercised indirectly (via phase advance path) but the watchdog that READS and ACTS on those heartbeats is never tested.

---

## 9. Enforcer Idle/Kill Testing

| Enforcer Feature | Tested? | Notes |
|---|---|---|
| `track_agent()` | ❌ | Never called |
| `untrack_agent()` | ❌ | Never called |
| `record_activity()` | ❌ | Never called |
| `check_idle()` at `IDLE_THRESHOLD` (30s) | ❌ | Never called |
| `enforce()` yank logic | ❌ | Never called |
| `enforce()` kill_respawn logic at `KILL_THRESHOLD` (60s) | ❌ | Never called |
| `yanked` flag prevents double-yank | ❌ | Never called |

**Pct:** 0.0% coverage on `src/loops/enforcer.py`. 132 lines, no tests.

---

## 10. Hash Anchor Validation Testing

| Hash Anchor Feature | Tested? | Notes |
|---|---|---|
| `compute_line_hash()` | ❌ | Never called |
| `compute_line_hash()` — `IndexError` on out-of-range | ❌ | Never tested |
| `validate_edit_content()` — match | ❌ | Never called |
| `validate_edit_content()` — mismatch | ❌ | Never called |
| `validate_edit_content()` — `IndexError` fallback | ❌ | Never tested |
| `validate_edit()` — file read | ❌ | Never called |
| `validate_edit()` — `FileNotFoundError` | ❌ | Never tested |
| `validate_edit()` — `OSError` on read | ❌ | Never tested |
| `HashAnchorError` exception | ❌ | Never raised/caught |

**Pct:** 0.0% coverage on `src/loops/hash_anchor.py`. 121 lines, no tests.

---

## 11. Sub-Agent Spawning Testing

| SubAgentSpawner Feature | Tested? | Notes |
|---|---|---|
| `spawn()` — valid category | ❌ | Never called |
| `spawn()` — invalid category (`ValueError`) | ❌ | Never tested |
| `get_spawned()` | ❌ | Never called |
| `mark_complete()` — found | ❌ | Never called |
| `mark_complete()` — not found (`ValueError`) | ❌ | Never tested |
| `mark_failed()` — found | ❌ | Never called |
| `mark_failed()` — not found (`ValueError`) | ❌ | Never tested |

**Pct:** 0.0% coverage on `src/loops/sub_agent.py`. 128 lines, no tests.

---

## 12. Cost Tracking (Redis) Testing

| LoopCostTracker Feature | Tested? | Notes |
|---|---|---|
| `record_loop_cost()` | ❌ | Requires Redis on localhost:6380 |
| `get_loop_cost()` | ❌ | Requires Redis |
| `get_all_loop_costs()` | ❌ | Requires Redis |
| Global `CostTracker` integration | ❌ | Requires Redis |

**Pct:** 0.0% coverage on `src/loops/cost.py`. 194 lines, no tests. Module imports and initializes `redis.Redis` in `__init__`, making it impossible to unit-test without mocking or a real Redis instance.

---

## 13. API Route Testing (HTTP Client)

| Endpoint | Tested? | Notes |
|---|---|---|
| `GET /api/v1/loops` (`list_loops`) | ❌ | Returns hardcoded stub: `{"loops": [], "active": 0, "completed": 0}` |
| `POST /api/v1/loops` (`create_loop`) | ❌ | API-key auth required, returns stub response |
| `GET /api/v1/loops/{id}` (`get_loop`) | ❌ | Returns hardcoded stub with "unknown" status |
| `POST /api/v1/loops/{id}/cancel` (`cancel_loop`) | ❌ | API-key auth required, returns stub |
| `verify_api_key()` | ❌ | HMAC comparison never tested |
| `get_api_key()` — missing header | ❌ | 401 path never tested |
| `get_api_key()` — invalid key | ❌ | 401 path never tested |
| `get_api_key()` — valid key | ❌ | Success path never tested |
| `get_api_key()` — env var fallback | ❌ | Dev default key path never tested |

**Pct:** 0.0% coverage on `routes.py` + `auth.py`. 152 combined lines, no HTTP tests.

**⚠️ NOTE:** The comment at the top of `test_e2e_loop.py` (line 9-14) shows a `curl` command for server-based testing but the actual test bypasses HTTP entirely and instantiates `LoopManager` directly in-process.

---

## 14. Discord Command Testing

| Feature | `cmd_loop_start.py` | `cmd_loop_stop.py` |
|---|---|---|
| `build_*_embed_data()` | ❌ | ❌ |
| `to_discord_embed()` | ❌ | ❌ |
| `*_callback()` (main handler) | ❌ | ❌ |
| `_format_wib_timestamp()` | ❌ | ❌ |
| `_get_option_value()` | ❌ | ❌ |
| `_send_denied()` | ❌ | ❌ |
| `_defer_ephemeral()` | ❌ | ❌ |
| `_followup_send()` | ❌ | ❌ |
| `_cancel_loop()` (API call) | N/A | ❌ |
| `_list_active_loops()` (API call) | N/A | ❌ |
| Faiz-only access enforcement | ❌ | ❌ |
| httpx error handling (`HTTPStatusError`, `RequestError`) | ❌ | ❌ |
| Empty goal rejection ("Goal tidak boleh kosong") | ❌ | N/A |
| No-active-loops message | N/A | ❌ |
| Multiple loop cancellation | N/A | ❌ |

**Pct:** 0.0% coverage on both Discord modules. 975 combined lines, no tests. Both modules have `Protocol`-based Discord type stubs that would allow mocking, but none exists.

---

## 15. Phase Handler Testing (Individual)

All 7 phase handlers (`research.py`, `plan_delegate.py`, `delegate.py`, `execute.py`, `validate_audit.py`, `update_docs.py`, `setup_evidence.py`) produce **template/mock artifacts** — every one returns placeholder markdown with `*pending*` entries. None perform real LLM calls.

| Phase | Individual Test? | What's Actually Produced |
|---|---|---|
| Research | ❌ | Placeholder template with `*No findings recorded yet*` |
| Plan & Delegate | ❌ | Placeholder template with `*pending*` entries |
| Delegate | ❌ | Placeholder template with `*pending*` sub-agents |
| Execute | ❌ | Placeholder template with `*No errors recorded yet*` |
| Validate & Audit | ❌ | Placeholder template with `*pending*` checks |
| Update Documents | ❌ | Placeholder template with `*pending*` docs |
| Setup Evidence | ❌ | Placeholder template with `*pending*` criteria |

Each handler follows the same pattern: construct an f-string template, return it. Testing one in isolation would take ~5 lines. Zero isolation tests exist.

---

## 16. LQS Calculation Testing

The Loop Quality Score (LQS) is calculated in `EvidencePipeline.generate_final_report()`:

```python
completed_phases = sum(1 for v in artifacts.values() if v is not None)
total_phases = len(_EXECUTION_PHASES)
lqs_score = (completed_phases / total_phases * 100.0) if total_phases > 0 else 0.0
```

| LQS Scenario | Tested? |
|---|---|
| All 7 phases complete (100.0) | ⚠️ Indirect (happy path produces this) |
| Partial completion (e.g., 3/7 = 42.9) | ❌ |
| Zero phases (0.0) | ❌ |
| Empty `_EXECUTION_PHASES` guard | ❌ |
| Weights all 1.0 (placeholder) | ❌ |

The E2E test verifies the final report EXISTS but never reads its content — the LQS value inside is never validated.

---

## 17. Migration Rollback Testing

**Not applicable.** The agent loop has no database migrations. All state is in-memory (`dict[str, LoopStateMachine]`) or filesystem (`/home/guinevere/evidence/loops/`). No migration rollback tests exist because no migrations exist.

---

## 18. Coverage Statistics

### Module-Level Coverage

| Category | Count | Modules |
|---|---|---|
| **Total testable modules** | 24 | All modules with non-trivial logic |
| **Modules with any coverage** | 13 | `manager`, `state_machine`, `guardian`, `evidence`, `artifacts`, `phases/__init__`, 7 phase handlers |
| **Modules with zero coverage** | 11 | `enforcer`, `hash_anchor`, `sub_agent`, `contract`, `verify`, `cost`, `scheduler`, `routes`, `auth`, `cmd_loop_start`, `cmd_loop_stop` |

**Module Coverage: 13/24 = 54.2%**

### Function-Level Coverage

| Category | Count |
|---|---|
| **Total functions/methods** | ~83 |
| **Functions with any test exercise** | ~34 |
| **Functions with zero test exercise** | ~49 |
| **Functions tested in isolation** | 0 |

**Function Coverage: ~34/83 ≈ 41.0%**

### Line-Level Coverage (estimated)

Based on source analysis:

| Module | Lines | Covered Lines (est.) | Coverage |
|---|---|---|---|
| `manager.py` | 272 | ~140 | ~51% |
| `state_machine.py` | 226 | ~90 | ~40% |
| `guardian.py` | 157 | ~70 | ~45% |
| `evidence.py` | 194 | ~110 | ~57% |
| `artifacts.py` | 110 | ~80 | ~73% |
| `phases/__init__.py` | 48 | ~20 | ~42% |
| Phase handlers (7×~80) | ~560 | ~560 (indirect) | ~100% |
| All zero-coverage (11×~190) | ~2,090 | 0 | 0% |
| **TOTAL** | **~3,657** | **~1,070** | **~29.3%** |

**Estimated line coverage: ≈29%**

### Coverage Quality Weighting

| Tier | Modules | Weight |
|---|---|---|
| **Direct unit test** | 0 | 1.0 |
| **E2E indirect (happy path)** | 13 | 0.3 |
| **Zero coverage** | 11 | 0.0 |

**Weighted coverage: (13 × 0.3) / 24 = 16.3%**

---

## 19. Summary of Critical Gaps

| # | Gap | Severity |
|---|---|---|
| 1 | **No unit tests exist.** Zero isolated component tests for any module. | 🔴 CRITICAL |
| 2 | **11 of 24 modules (46%) have zero test coverage.** Including enforcer, hash_anchor, sub_agent, contract, verify, cost, scheduler, API routes, auth, and both Discord commands. | 🔴 CRITICAL |
| 3 | **Zero error-path testing.** No failure, timeout, exception, or edge-case scenarios are tested anywhere. | 🔴 CRITICAL |
| 4 | **No mocking infrastructure.** Cost tracker requires Redis. Scheduler requires APScheduler. Discord commands require httpx+discord.py. None are mocked. | 🔴 CRITICAL |
| 5 | **Assertions are existence-only.** Artifact content (200+ chars of markdown per phase) is never validated. A file with one byte would pass. | 🟠 HIGH |
| 6 | **Guardian watchdog loop never tested.** `monitor()` kills loops after 5-min stall — untested. | 🟠 HIGH |
| 7 | **State machine error transitions untested.** `pause`, `resume`, `fail`, `cancel`, advance-on-complete guard — all untested. | 🟠 HIGH |
| 8 | **No parametrized tests.** Single hardcoded task/goal. No variation in input. | 🟡 MEDIUM |
| 9 | **Not pytest-compatible.** Custom runner with manual boolean assertions. Cannot integrate with CI/CD coverage tools. | 🟡 MEDIUM |
| 10 | **Filesystem dependency.** Hardcoded `/home/guinevere/evidence/loops/` path breaks on Windows/non-standard environments. | 🟡 MEDIUM |

---

## 20. Final Verdict

| Metric | Value | Threshold |
|---|---|---|
| Module coverage (binary) | **54.2%** | 40-80% = NEEDS REVIEW |
| Function coverage | **41.0%** | <40% = FAIL |
| Estimated line coverage | **29.3%** | <40% = FAIL |
| Weighted quality coverage | **16.3%** | <40% = FAIL |
| Error path coverage | **0.0%** | <40% = FAIL |
| Unit test isolation | **0 of 24 modules** | <40% = FAIL |

### VERDICT: **NEEDS REVIEW** → effectively **FAIL**

The binary module count (54.2%) technically falls in the NEEDS REVIEW band, but the quality-weighted effective coverage is 16.3% — well below the 40% FAIL threshold. The single E2E test exercises the happy path through 13 modules but only as a black-box integration test. Component-level behavior, error handling, edge cases, security boundaries (auth), and infrastructure dependencies (Redis, APScheduler, Discord, httpx) are completely untested.

**Recommendation:** Do not accept this test suite as adequate. At minimum, add pytest-based unit tests for the 11 zero-coverage modules before the next release cycle.

---

*Report generated by Independent Testing Auditor for P5 Agent Loop Audit — D07*