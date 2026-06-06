# Phase 6 Final Evidence Index — LLM Routing & Budget Enforcement

| Field | Value |
|---|---|
| Phase | ADR-035 Phase 6 — LLM Routing & Budget Enforcement |
| Date | 2026-06-06 |
| Status | PASS — implemented, deployed, runtime-verified, audited |
| Evidence Root | `docs/setup-evidence/phase-6/` |
| Primary Runtime | 9Router `http://localhost:20128/v1` |
| Primary Model | `ds/deepseek-v4-flash` |
| Fallbacks | `cx/gpt-5.5`, `guinevere` |
| Budget Cap | `$30/month`, fail-closed |
| Auditor Verdicts | Routing PASS, Cost PASS, ADR PASS |

## What Was Done

Phase 6 routed Guinevere LLM traffic through 9Router at `localhost:20128`, retained DeepSeek V4 Flash as the current primary model, configured two fallback entries through 9Router, wired `CostTracker.record_cost()` into `LLMRouter` after successful LLM responses, updated pricing constants, hardened SSE `[DONE]` stripping, registered the fail-closed budget hook, added Redis-authenticated hook utilities, exposed Prometheus LLM metrics on `localhost:9191`, deployed source/config/hook changes to the VPS runtime, restarted `hermes-gateway` and `guinevere-core`, ran a 100-prompt VPS integration test, verified Redis DB5 cost keys, proved budget fail-closed behavior, and completed three auditor gates.

## Files Changed

| Area | Files |
|---|---|
| LLM routing | `src/core/services/llm_router.py`, `tests/hermes/test_llm_router_cost.py` |
| Metrics | `src/core/services/llm_metrics.py`, `src/core/main.py`, `tests/hermes/test_llm_metrics.py`, `monitoring/prometheus/prometheus.yml` |
| Budget hook | `hermes-config/hooks/budget_check.py`, `hermes-config/hooks/_hook_utils.py`, `tests/hermes/test_budget_hook.py` |
| Hermes config | `hermes-config/config.yaml` |
| Reports | `research-reports/phase-6-execution/`, `docs/setup-evidence/phase-6/` |
| Tracker | `PROGRESS.md` |

## Validation Results

| Gate | Result | Evidence |
|---|---|---|
| Planner gate | PASS | `plan.md` |
| Secret redaction | PASS | `STEP-0/verification.md` |
| Router CostTracker wiring | PASS | `STEP-2/verification.md`, `STEP-3/verification.md` |
| Budget hook marker/tests | PASS | `STEP-4/verification.md` |
| Hook/config deploy | PASS | `STEP-5/verification.md` |
| Fallback config | PASS | `STEP-6/verification.md` |
| Prometheus metrics | PASS | `STEP-7/verification.md` |
| VPS deploy/restart | PASS | `STEP-8/verification.md` |
| 100-prompt integration | PASS | `STEP-9/verification.md` |
| Budget fail-closed proof | PASS | `STEP-10/implementation-report.md` |
| Auditor gates | PASS | `STEP-12/routing/auditor-gate.md`, `STEP-12/cost/auditor-gate.md`, `STEP-12/adr/auditor-gate.md` |

## Evidence Artifacts

- `docs/setup-evidence/phase-6/plan.md`
- `docs/setup-evidence/phase-6/STEP-0/verification.md`
- `docs/setup-evidence/phase-6/STEP-1/verification.md`
- `docs/setup-evidence/phase-6/STEP-2/verification.md`
- `docs/setup-evidence/phase-6/STEP-3/verification.md`
- `docs/setup-evidence/phase-6/STEP-4/verification.md`
- `docs/setup-evidence/phase-6/STEP-5/verification.md`
- `docs/setup-evidence/phase-6/STEP-6/verification.md`
- `docs/setup-evidence/phase-6/STEP-7/verification.md`
- `docs/setup-evidence/phase-6/STEP-8/verification.md`
- `docs/setup-evidence/phase-6/STEP-9/verification.md`
- `docs/setup-evidence/phase-6/STEP-10/implementation-report.md`
- `docs/setup-evidence/phase-6/STEP-12/routing/auditor-gate.md`
- `docs/setup-evidence/phase-6/STEP-12/cost/auditor-gate.md`
- `docs/setup-evidence/phase-6/STEP-12/adr/auditor-gate.md`

## Boundary Compliance

- No direct provider calls were introduced; Phase 6 runtime uses 9Router `http://localhost:20128/v1`.
- Secrets discovered in research/evidence scripts were redacted before commit preparation.
- Redis credentials are read from VPS environment sources and are not written into local evidence.
- Budget enforcement is fail-closed; Redis/check failures block with `budget_check_failed`.
- No type-safety suppressions or empty catches were introduced in changed Phase 6 runtime/hook surfaces.
- Consent/DNR hooks were preserved and budget hook runs before consent gate at priority 100.

## Caveats / Follow-Ups

1. `cx/gpt-5.5` remains a known-degraded fallback until Codex credentials are refreshed.
2. The budget hook hard-cap verification currently blocks through `budget_check_failed` rather than a clean `MONTHLY_BLOCKED` response. Fail-closed behavior is correct; improve clean monthly-block reporting in a follow-up.
3. The 100-prompt test did not activate fallback because all requests succeeded on the primary model. Fallback configuration and model inventory were verified.
4. Prometheus scrape target intentionally remains `localhost:9191` per user requirement; container-network adaptation, if needed, is an operations follow-up.

## Auditor Gate

| Auditor | Verdict | Path |
|---|---|---|
| Routing correctness | PASS | `STEP-12/routing/auditor-gate.md` |
| Cost accuracy | PASS | `STEP-12/cost/auditor-gate.md` |
| ADR-035 compliance | PASS | `STEP-12/adr/auditor-gate.md` |

## Acceptance Criteria Mapping

| Requirement | Status |
|---|---|
| 9Router HTTP 200 / localhost:20128 | PASS |
| DeepSeek primary | PASS |
| Two fallbacks configured | PASS |
| Budget hook active and fail-closed | PASS |
| CostTracker wired after successful LLM response | PASS |
| Redis DB5 cost keys updated | PASS |
| No direct provider calls | PASS |
| `hermes-gateway` active | PASS |
| 100-prompt test through 9Router | PASS |
| Prometheus scrape configured | PASS |
| No empty catch in budget hook | PASS |
| Three auditor gates PASS | PASS |

## Phase 7 Readiness

**YES** — Phase 6 is ready for Phase 7 with documented follow-ups for GPT/Codex credential refresh and clean monthly-block reason reporting.

## Footer

Generated for Phase 6 closure before git commit/tag/push.
