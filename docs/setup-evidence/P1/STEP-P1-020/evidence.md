# P1-020 Cost Tracking Baseline Evidence

## What Was Done

Deployed cost tracking baseline in Redis DB5 per ADR-030. Initialized budget thresholds, per-model cost counters, and deployed the `CostTracker` Python module with ACL-aware Redis authentication.

## Files Changed

- `src/core/services/cost_tracker.py` — deployed to VPS `/home/guinevere/code/guinevere/src/core/services/cost_tracker.py`
  - `CostTracker` class with `record_cost()`, `check_budget()`, `_get_status()` methods
  - ACL-aware Redis connection: username `guinevere_core`, password from `REDIS_PASSWORD` env var
  - Budget status levels: NORMAL, NORMAL_ALERT, WARNING, CRITICAL, HARD_STOP
- Redis DB5 keys initialized:
  - budget thresholds: monthly_cap=30.00, daily_alert=1.00, warning=15.00, critical=25.00, hard_stop=30.00
  - cost counters: current_month=0.00, current_day=0.00
  - cost:by_model hash: gpt-5.5=0.00, deepseek-v4-flash=0.00, graceful_degradation=0.00
  - cost:by_phase hash: P1=0.00

## Validation Results

- ✅ Redis DB5 PING via `guinevere_core` ACL user: PONG
- ✅ 11 cost tracking keys set with correct initial values
- ✅ Module import succeeds: `from src.core.services.cost_tracker import CostTracker`
- ✅ `check_budget()` returns NORMAL with 0% used, $30.00 remaining
- ✅ `record_cost()` writes to Redis pipeline, structlog output confirmed
- ✅ Test costs recorded and then reset to zero

## Evidence Artifacts

- Cost tracker source: `docs/setup-evidence/P1/STEP-P1-020/cost_tracker.py`
- Redis DB5 keys: `docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt`
- Verification script: `tmp/verify-p1-020.sh`
- Init script: `tmp/init-cost-tracking-keys.sh`

## Doc-Sync Impact

- PROGRESS.md: P1-020 marked complete
- CHECKLIST.md: P1-020 marked done
- StepPrompts.md: P1-020 Redis auth bug fixed (redis-password.yaml → redis-acl-passwords.yaml, added SOPS_AGE_KEY_FILE, absolute path, --user guinevere_core)

## Boundary Compliance

- No secrets exposed in evidence files
- No API keys, JWTs, or credentials recorded
- Redis ACL user `guinevere_core` used with env var, not hardcoded password
- No Aizanta resources touched
- No persona safety boundary affected

## Rollback / Re-run Safety

Rollback: `docker exec guinevere-redis redis-cli --user guinevere_core -a <pass> -n 5 FLUSHDB` clears all cost keys. Remove `src/core/services/cost_tracker.py` from VPS.

Safe to re-run: all keys overwritten with zero values, idempotent.

## Design Decisions / Caveats

- ACL user `guinevere_core` has `+@all -@dangerous` permissions — sufficient for SET/GET/INCR but not KEYS/ACL/INFO
- Password read from `REDIS_PASSWORD` env var at runtime (not hardcoded)
- SOPS secrets live at `/home/guinevere/secrets/` (not inside code directory)
- Age key requires `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt`
- Old `redis-password.yaml` with `redis_master_password` is stale — default user disabled

## Auditor Gate

Pending. Auditor report path target:

`audit-reports/P1/STEP-P1-020/step-p1-020-auditor-report.md`

## Footer

- Source task: StepPrompts P1-020
- Date: 2026-06-01
- Implementer: Guinevere
- Validation method: SSH verify script, Python import test, Redis key inspection