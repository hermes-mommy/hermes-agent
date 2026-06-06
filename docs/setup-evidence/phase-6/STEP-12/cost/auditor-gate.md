# Step 12 Cost Auditor Gate

**VERDICT: PASS**

## Scope

Parent-run independent audit of Phase 6 cost tracking, Redis DB5 accounting, and fail-closed budget enforcement after sub-agent auditor infrastructure failed and Faiz explicitly instructed direct audit.

## Files / Evidence Reviewed

- `src/core/services/llm_router.py`
- `src/core/services/cost_tracker.py`
- `hermes-config/hooks/budget_check.py`
- `hermes-config/hooks/_hook_utils.py`
- `tests/hermes/test_llm_router_cost.py`
- `tests/hermes/test_budget_hook.py`
- `docs/setup-evidence/phase-6/STEP-2/verification.md`
- `docs/setup-evidence/phase-6/STEP-3/verification.md`
- `docs/setup-evidence/phase-6/STEP-4/verification.md`
- `docs/setup-evidence/phase-6/STEP-5/verification.md`
- `docs/setup-evidence/phase-6/STEP-9/verification.md`
- `docs/setup-evidence/phase-6/STEP-10/implementation-report.md`

## Checks Performed

| Check | Evidence | Result |
|---|---|---|
| Pricing constants match required values | `PRICING`: GPT 0.005/0.03, DeepSeek 0.00014/0.00028, guinevere 0.00014/0.00028 | PASS |
| `CostTracker` initialized in router | `LLMRouter.__init__` creates/injects `CostTracker` | PASS |
| `record_cost()` called after successful LLM response | Router lines 221-228 call `self.cost_tracker.record_cost(...)` after JSON parse and usage extraction | PASS |
| Cost tracking failure is fail-closed | Router raises exact `RuntimeError("LLM cost tracking failed")` outside provider fallback loop | PASS |
| Redis DB5 keys updated by real traffic | STEP-9 Redis delta: +$0.00127708 to `cost:current_month`, day/month/model keys | PASS |
| Step 9 cost math is plausible | 1,350 input and 3,886 output tokens at DeepSeek pricing gives about `$0.00127708` | PASS |
| Production CostTracker can authenticate | STEP-9 production verifier: Redis PING True, current/month cap/status readable | PASS |
| Budget hook registered fail-closed | STEP-5/8 config: budget hook priority 100, timeout 500, `on_failure: block` | PASS |
| Hook Redis auth path fixed | `_hook_utils.py` builds DB5 URL from `REDIS_PASSWORD` and `guinevere_core` when no `GUINEVERE_REDIS_URL` | PASS |
| Redis/check failure blocks with marker | STEP-10: `Budget check unavailable (Redis down) — budget_check_failed`, exit 1 | PASS |
| Forced budget/check path blocks and restores state | STEP-10: over-budget/check path exit 1; cap/current_month restored; services active | PASS |
| Empty catch / type suppression in hook surfaces | Targeted scan of `hermes-config/hooks` clean for empty catches and type suppressions | PASS |

## Findings

1. Cost accounting is wired in `llm_router.py` after successful response parsing and before returning the result.
2. Cost tracking errors cannot be swallowed by the provider fallback loop because the call to `record_cost()` is outside the provider try/except.
3. Unit tests cover successful cost recording, default token behavior, exact fail-closed RuntimeError, pricing constants, and SSE stripping.
4. Real 100-prompt traffic updated Redis DB5 cost keys by the expected amount.
5. Production Redis credentialing initially had a gap (`.env.core` missing `REDIS_PASSWORD`); it was fixed, verified, and documented in STEP-9 evidence.
6. Budget hook runtime Redis authentication initially had a gap in `_hook_utils.py`; Step 10 fixed it by deriving the authenticated Redis URL from `REDIS_PASSWORD` without exposing the value.
7. Step 10 proves fail-closed behavior and state restoration.

## Caveats

- The hook's hard cap currently uses Python constant `MONTHLY_CAP = 30.0` rather than Redis key `budget:monthly_cap`. Step 10 therefore temporarily set `cost:current_month` to the cap boundary to prove the deployed hard-cap path, then restored it exactly.
- The forced hard-cap run blocked through `Budget check error — budget_check_failed` rather than a clean `Budget blocked: MONTHLY_BLOCKED` response. This is still fail-closed and satisfies the non-negotiable user requirement, but improving the clean monthly-block path should be tracked as a follow-up.
- Step 10 did not mutate or delete any cost keys permanently; cap and current spend were restored.

## Verdict

**VERDICT: PASS** — Cost tracking and budget enforcement meet Phase 6 acceptance, with documented follow-up caveat for cleaner monthly-block reporting.
