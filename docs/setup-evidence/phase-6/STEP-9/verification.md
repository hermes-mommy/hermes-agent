# Step 9 Verification — 100-Prompt VPS Integration Test

## 1. What Was Done

Executed and parent-verified a 100-prompt LLM integration test on the VPS through the deployed `LLMRouter` at `/home/guinevere/code/guinevere/src/core/services/llm_router.py`, routing all calls through 9Router at `http://localhost:20128/v1`. Captured Redis DB5 before/after cost keys, sampled metrics, discovered and fixed a production `REDIS_PASSWORD` environment gap, and sanitized local evidence scripts.

## 2. Files Changed

- `docs/setup-evidence/phase-6/STEP-9/implementation-report.md`
- `docs/setup-evidence/phase-6/STEP-9/verification.md`
- `docs/setup-evidence/phase-6/STEP-9/redis-env-fix-report.md`
- `docs/setup-evidence/phase-6/STEP-9/vps_100_prompt_test.py`
- `docs/setup-evidence/phase-6/STEP-9/run_100_fixed.sh`
- `docs/setup-evidence/phase-6/STEP-9/run_test.sh`
- `docs/setup-evidence/phase-6/STEP-9/capture_redis_state.py`
- `docs/setup-evidence/phase-6/STEP-9/verify_redis_keys.py`
- `docs/setup-evidence/phase-6/STEP-9/verify_prod_costtracker.py`
- `docs/setup-evidence/phase-6/STEP-9/list_redis_env_keys.sh`
- `docs/setup-evidence/phase-6/STEP-9/container_env_keys.sh`
- `docs/setup-evidence/phase-6/STEP-9/systemd_env_keys.py`
- `docs/setup-evidence/phase-6/STEP-9/inspect_redis_url_shape.py`

VPS runtime env changed by follow-up fix:

- `/home/guinevere/code/guinevere/.env.core` — appended `REDIS_PASSWORD` from existing VPS credential source.
- `/home/guinevere/code/guinevere/.env.core.bak.2026-06-06` — backup created before edit.

## 3. Validation Results

### 3.1 100-Prompt Test

| Metric | Result |
|---|---|
| Total prompts | 100 |
| Successes | 100 |
| Failures | 0 |
| Success rate | 100% |
| SSE artifacts | 0 |
| Total tokens | 5,236 (1,350 in / 3,886 out) |
| Avg latency | 2.037s |
| Model used | deepseek-v4-flash (100%) |
| Direct provider calls | 0 |

### 3.2 Redis DB5 Cost Keys

| Key | Before | After | Delta |
|---|---|---|---|
| `cost:current_month` | 0.42542750 | 0.42670458 | +$0.00127708 |
| `cost:current_day` | 0.42542750 | 0.42670458 | +$0.00127708 |
| `cost:monthly:2026-06` | 0.42542750 | 0.42670458 | +$0.00127708 |
| `cost:daily:2026-06-06` | absent | 0.00127708 | NEW |
| `cost:by_model:ds/deepseek-v4-flash` | 0.31190000 | 0.31317708 | +$0.00127708 |
| `budget:monthly_cap` | 30.00 | 30.00 | Unchanged |

### 3.3 Metrics

All four metric families registered at `:9191/metrics`:

- `hermes_llm_calls_total` — present (HELP/TYPE)
- `hermes_llm_latency_seconds` — present (HELP/TYPE)
- `hermes_llm_cost_usd_total` — present (HELP/TYPE)
- `hermes_fallback_activations_total` — present (HELP/TYPE)

Counters remain zero in the deployed endpoint because the 100-prompt test harness ran in a separate Python process from `guinevere-core`; the metric families are present and production traffic through the service process can populate them.

### 3.4 Direct Provider Check

Grep across the test harness and deployed router returned zero matches for direct provider URLs. All calls used `LLMRouter` and 9Router localhost.

### 3.5 Evidence Secret Sanitation

A parent review found plaintext Redis password material in archived Step 9 scripts. This was treated as a blocking evidence violation and fixed immediately.

Actions taken:

- Replaced plaintext Redis password in archived local evidence scripts with `[REDACTED_REDIS_PASSWORD]`.
- Removed temporary Phase 6 scripts from VPS `/tmp`:
  - `/tmp/phase6_100_prompt_test.py`
  - `/tmp/run_100_fixed.sh`
  - `/tmp/run_test.sh`
  - `/tmp/capture_redis_state.py`
- Re-scanned `docs/setup-evidence/phase-6/STEP-9/` for long hex secrets, `sk-` tokens, plaintext Redis password assignments, and credential hash disclosures.

Final scan result: no matches for secret patterns.

### 3.6 Production CostTracker Environment Fix

Step 9 initially proved CostTracker with a test-process `REDIS_PASSWORD`, but parent review identified that `guinevere-core.service` itself needed production environment proof.

Follow-up report: `docs/setup-evidence/phase-6/STEP-9/redis-env-fix-report.md`.

Fix summary:

- `.env.core` lacked `REDIS_PASSWORD`.
- Existing VPS credential source `.env.loops` had the same Redis password as other env files.
- Backed up `.env.core` to `.env.core.bak.2026-06-06`.
- Appended `REDIS_PASSWORD` to `.env.core` on the VPS without writing the value locally or to evidence.
- Restarted `guinevere-core.service` only.
- Verified production venv `CostTracker()` can read Redis DB5.

Parent production-context verification output:

```text
redis_password_present True
redis_ping True
current_month 0.42670458
monthly_cap 30.0
status NORMAL
by_model_keys ['cost:by_model:deepseek-v4-flash', 'cost:by_model:ds/deepseek-v4-flash']
TMP_PROD_VERIFY_REMOVED
```

## 4. Evidence Artifacts

- `docs/setup-evidence/phase-6/STEP-9/implementation-report.md` — 100-prompt integration report.
- `docs/setup-evidence/phase-6/STEP-9/redis-env-fix-report.md` — production Redis env fix report.
- `docs/setup-evidence/phase-6/STEP-9/vps_100_prompt_test.py` — sanitized archived harness.
- `docs/setup-evidence/phase-6/STEP-9/run_100_fixed.sh` — sanitized archived runner.
- `docs/setup-evidence/phase-6/STEP-9/verify_prod_costtracker.py` — sanitized production CostTracker verifier.

## 5. Doc-Sync Impact

No docs outside Phase 6 evidence root changed.

## 6. Boundary Compliance

- All routing through localhost:20128 (9Router).
- No direct provider endpoints.
- No secrets remain in Step 9 evidence.
- Budget cap unchanged at $30.
- Redis cost keys updated only through normal CostTracker increments from LLM calls.
- No Redis `FLUSHDB` or destructive operations.
- No git operations used.
- VPS temp scripts removed.

## 7. Rollback / Re-run Safety

- The 100-prompt test is idempotent but increments Redis cost keys each run.
- `.env.core` rollback: restore `/home/guinevere/code/guinevere/.env.core.bak.2026-06-06` to `.env.core`, then restart `guinevere-core.service`.
- Sanitized local evidence helpers do not contain secrets and are safe to retain.

## 8. Design Decisions / Caveats

1. Redis ACL user `guinevere_core` had to be created during the delegated 100-prompt test. This was a pre-existing deployment gap.
2. Production `REDIS_PASSWORD` was missing from `.env.core`; fixed and validated in `redis-env-fix-report.md`.
3. Metrics are process-bound; the separate harness did not populate the service process counters.
4. No fallback activation occurred because all 100 prompts succeeded on primary DeepSeek.
5. Evidence scripts are archived in sanitized form and are not intended to be re-run without restoring runtime-only credentials via environment variables.

## 9. Auditor Gate

Pending Step 12 independent auditors.

## 10. Security Scan

Final Step 9 evidence secret scan found no matches for:

- long 64-character hex secret-like values
- `sk-` token patterns
- plaintext `REDIS_PASSWORD="..."` or `REDIS_PASSWORD='...'` assignments
- credential hash disclosure markers (`hash:`, `MD5`)

## 11. Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| Success rate >= 95/100 | PASS (100/100) |
| No SSE artifacts | PASS |
| No direct provider URLs | PASS |
| Redis DB5 cost keys updated | PASS |
| `budget:monthly_cap` unchanged | PASS |
| Metrics families exist | PASS (process-bound counters caveat) |
| CostTracker called per success | PASS (verified via Redis delta) |
| Production `CostTracker()` can read Redis DB5 | PASS |
| Evidence secrets sanitized | PASS |

## 12. Footer

Step 9 parent verification completed 2026-06-06 after correcting evidence secret handling and production Redis environment. Next: Step 10 — budget fail-closed block test and cap restoration.
