# STEP-2 Verification — Router CostTracker Wiring

## 1. What Was Done

Parent verified the delegated router implementation after the diagnostic-fix continuation. `src/core/services/llm_router.py` now routes Phase 6 primary calls through `ds/deepseek-v4-flash` on `http://localhost:20128/v1`, initializes `CostTracker`, records cost after each successful parsed response, and raises `RuntimeError("LLM cost tracking failed")` if cost tracking fails.

## 2. Files Changed

- `src/core/services/llm_router.py`
- `tests/hermes/test_llm_router_cost.py`
- `docs/setup-evidence/phase-6/STEP-2/implementation-report.md`

## 3. Validation Results

- `python -m pytest tests/hermes/test_llm_router_cost.py -v` → PASS, 20/20 tests passed, exit 0.
- `lsp_diagnostics src/core/services/llm_router.py` → no errors; warnings are strict typing warnings for third-party `structlog` and `json.loads` surfaces.
- `lsp_diagnostics tests/hermes/test_llm_router_cost.py` → one `pytest` missing-import diagnostic. Cross-check on `tests/hermes/test_budget_hook.py` shows the same missing pytest import diagnostic, so this is an existing LSP environment resolution issue; runtime pytest passes.
- Forbidden-pattern scan over `src/core/services/*.py` → no matches for type suppressions, empty catches, or direct provider URLs.

## 4. Evidence Artifacts

- Parent-read router source: `src/core/services/llm_router.py`
- Parent-read router tests: `tests/hermes/test_llm_router_cost.py`
- Subagent implementation report: `docs/setup-evidence/phase-6/STEP-2/implementation-report.md`
- This verification file: `docs/setup-evidence/phase-6/STEP-2/verification.md`

## 5. Doc-Sync Impact

No governance or ADR document was changed. The planner already records the deliberate ADR-035 deviation: DeepSeek primary is a current-user override because GPT-5.5 credentials are degraded.

## 6. Boundary Compliance

- All LLM base URLs remain `http://localhost:20128/v1`.
- No direct provider URLs (`api.openai.com`, `openrouter.ai`, `api.anthropic.com`) were introduced.
- No secrets were added.
- No type-safety suppressions were introduced.

## 7. Rollback / Re-run Safety

Rollback: `git checkout -- src/core/services/llm_router.py tests/hermes/test_llm_router_cost.py` before commit. Tests are deterministic and mocked; rerun command is `python -m pytest tests/hermes/test_llm_router_cost.py -v`.

## 8. Design Decisions / Caveats

- `cx/gpt-5.5` pricing is retained in `PRICING` for Phase 6 reference, but active `CORE_REASONING` is DeepSeek.
- Cost tracking is intentionally outside the provider fallback `try` block so Redis/cost failures cannot be retried as a model fallback and silently spend untracked.
- The test file uses `pytest`; LSP cannot resolve it in the current language-server environment, but the repository test runtime imports pytest successfully.

## 9. Auditor Gate

Pending. Step 12 will run independent routing, cost, and ADR auditors after deterministic runtime verification.

## 10. Security Scan

Forbidden-pattern scan over `src/core/services` found no type suppressions, no empty catches, and no direct provider URLs. Test-directory scan matches only unrelated security-audit tests that assert `# type: ignore` is absent; the new test file has no forbidden matches.

## 11. Acceptance Criteria Mapping

- CostTracker wired after every successful LLM response: PASS.
- Cost tracking failure fail-closed with exact `RuntimeError("LLM cost tracking failed")`: PASS.
- Pricing constants updated: PASS.
- Primary model DeepSeek through 9Router localhost: PASS.
- Robust SSE `[DONE]` strip for spaced and unspaced variants: PASS.

## 12. Footer

Generated 2026-06-06 for Phase 6 LLM Routing evidence. Parent verified subagent output directly before accepting this step.
