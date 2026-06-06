# STEP-3 Verification — Router Unit Tests

## 1. What Was Done

Parent verified the new mocked router unit tests that cover Phase 6 CostTracker wiring, fail-closed behavior, pricing constants, SSE `[DONE]` stripping, primary 9Router routing, and provider fallback preservation.

## 2. Files Changed

- `tests/hermes/test_llm_router_cost.py`
- `src/core/services/llm_router.py`

## 3. Validation Results

Command: `python -m pytest tests/hermes/test_llm_router_cost.py -v`

Result: PASS. Pytest collected 20 tests and all 20 passed. Runtime warnings are pytest-asyncio deprecation warnings from the installed plugin/runtime and do not indicate Phase 6 test failure.

Additional checks:

- New test file contains no `skip`, `xfail`, or `assert False` markers.
- Router scaffold grep found `CostTracker`, `record_cost`, exact fail-closed RuntimeError string, SSE regex, DeepSeek model ID, localhost 9Router URL, and required pricing constants.
- LSP test-file diagnostic has `pytest` missing-import resolution only; the same diagnostic exists on pre-existing `tests/hermes/test_budget_hook.py`, while runtime pytest succeeds.

## 4. Evidence Artifacts

- Test file: `tests/hermes/test_llm_router_cost.py`
- Router file under test: `src/core/services/llm_router.py`
- Subagent report: `docs/setup-evidence/phase-6/STEP-2/implementation-report.md`
- This verification file: `docs/setup-evidence/phase-6/STEP-3/verification.md`

## 5. Doc-Sync Impact

No docs beyond evidence files were changed for this step.

## 6. Boundary Compliance

Tests are fully mocked and do not perform live LLM, Redis, or 9Router calls. No secrets, no provider credentials, and no direct provider endpoints are used.

## 7. Rollback / Re-run Safety

The test file is deterministic. Rerun with `python -m pytest tests/hermes/test_llm_router_cost.py -v`. Rollback before commit via `git checkout -- tests/hermes/test_llm_router_cost.py src/core/services/llm_router.py`.

## 8. Design Decisions / Caveats

The suite validates cost-failure non-fallback by asserting exactly one HTTP call when `record_cost()` raises. This specifically protects the user constraint that untracked spend must not be hidden by fallback.

## 9. Auditor Gate

Pending. Step 12 auditors must review this file and the router implementation.

## 10. Security Scan

No forbidden test-control patterns (`skip`, `xfail`, `assert False`) exist in `tests/hermes/test_llm_router_cost.py`. No direct-provider URLs or secrets were introduced.

## 11. Acceptance Criteria Mapping

- Cost recording test coverage: PASS.
- Fail-closed test coverage: PASS.
- Pricing test coverage: PASS.
- SSE strip test coverage: PASS.
- Primary model and localhost 9Router test coverage: PASS.
- Provider fallback test coverage: PASS.

## 12. Footer

Generated 2026-06-06 for Phase 6 router test evidence. Parent reran tests and diagnostics after subagent diagnostic-fix continuation.
