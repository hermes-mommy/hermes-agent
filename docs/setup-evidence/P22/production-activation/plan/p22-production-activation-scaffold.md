# P22 Production Activation — Per-Step Verification Scaffold

> Machine-checkable contract for every atomic step (AGENTS.md §2.5). Parent must re-run every Required Command after sub-agent claims done; self-report is not evidence. Any violation recorded in `fixes/round-1-fix-log.md` even if later fixed.

## Step T1: Commit P22 to git
- **Expected Files:** git tracks `src/life_integrations/` (28 .py), `alembic/versions/p19_003_audit_chain_version.py`, `alembic/versions/p22_001_integration_schema.py`, `tests/p22/`, `scripts/p22_smoke_test.py`, `adr/ADR-053*.md`, `docs/setup-evidence/P22/`.
- **Forbidden Patterns:** `git log --oneline -- src/life_integrations/` must return ≥1 commit (not empty). `git diff --cached --name-only | grep -iE 'ghp_|sk-|ya29|xox|BEGIN PRIVATE KEY'` → 0.
- **Required Commands:**
  - `git add src/life_integrations alembic/versions/p19_003_audit_chain_version.py alembic/versions/p22_001_integration_schema.py tests/p22 scripts/p22_smoke_test.py adr/ADR-053* docs/setup-evidence/P22` → exit 0
  - `git commit -m "feat(p22): life integration hub core + migration (production activation staging)"` → exit 0
- **Evidence Requirements:** `implementation/p22-migration-application.md` (commit SHA section).
- **Hard Rejection:** P22 still untracked after step; secret staged in commit.

## Step T2: Backup VPS DB + code
- **Expected Files:** `/home/guinevere/data/backups/guinevere-p22-predeploy-<TS>.sql.gz` + `.sha256`; `/home/guinevere/data/backups/guinevere-code-bak-<TS>/` (no .env, no .venv).
- **Forbidden Patterns:** backup dir contains NO `.env*` files (`find .../guinevere-code-bak-<TS> -name '.env*'` → 0). `.env.core` value NEVER echoed.
- **Required Commands (via ssh guinevere-vps):**
  - `docker exec guinevere-postgres pg_dumpall -U guinevere --no-role-passwords | gzip -9 > .../guinevere-p22-predeploy-<TS>.sql.gz` → exit 0
  - `stat -c%s .../guinevere-p22-predeploy-<TS>.sql.gz` → > 1000000000 (1 GB)
  - `cp -a /home/guinevere/code/guinevere .../guinevere-code-bak-<TS> && find .../guinevere-code-bak-<TS> -name '.env*' -delete && rm -rf .../guinevere-code-bak-<TS>/.venv` → exit 0
- **Evidence Requirements:** `deploy/p22-backup-evidence.md` (sizes, sha256, timestamps).
- **Hard Rejection:** backup < 1 GB; .env file present in code backup; no sha256.

## Step T3: Deploy code to VPS (Phase A)
- **Expected Files on VPS:** `/home/guinevere/code/guinevere/src/life_integrations/__init__.py` + 14 modules + `adapters/`; `alembic/versions/p19_003_audit_chain_version.py`; `alembic/versions/p22_001_integration_schema.py`.
- **Forbidden Patterns:** `.env.core` modified; any P20 closed file modified.
- **Required Commands:**
  - `rsync -avz --exclude='__pycache__' C:/Users/faizz/guinevere/src/life_integrations/ guinevere-vps:/home/guinevere/code/guinevere/src/life_integrations/` → exit 0
  - `rsync -avz C:/Users/faizz/guinevere/alembic/versions/p19_003_audit_chain_version.py C:/Users/faizz/guinevere/alembic/versions/p22_001_integration_schema.py guinevere-vps:/home/guinevere/code/guinevere/alembic/versions/` → exit 0
  - `ssh guinevere-vps 'ls /home/guinevere/code/guinevere/src/life_integrations/*.py | wc -l'` → ≥13
  - `ssh guinevere-vps 'ls /home/guinevere/code/guinevere/alembic/versions/p22_001_integration_schema.py /home/guinevere/code/guinevere/alembic/versions/p19_003_audit_chain_version.py'` → both exist
- **Evidence Requirements:** `deploy/p22-deploy-evidence.md`.
- **Hard Rejection:** file count < 13; migration file missing; `.env.core` touched.

## Step T4: Resolve alembic auth (B-B/B-C)
- **Expected Files:** none modified (read-only diagnosis + choose auth path). If password fix needed, operator-only.
- **Forbidden Patterns:** NEVER print DB password. NEVER `cat .env.core` to evidence.
- **Required Commands:**
  - `ssh guinevere-vps 'cd /home/guinevere/code/guinevere && export $(grep -E "^[A-Z_][A-Z0-9_]*=" .env.core | xargs) && .venv/bin/alembic current 2>&1 | tail -5'` → must show a revision WITHOUT `InvalidPasswordError` (or document trust-auth path)
- **Evidence Requirements:** `implementation/p22-migration-application.md` (auth resolution: trust-auth vs corrected password, no value).
- **Hard Rejection:** `alembic current` still throws `InvalidPasswordError` at T5 start.

## Step T5: Apply migration p22_001
- **Expected DB state:** `ops.alembic_version` has 5 rows (incl p22_001); schema `p22` exists; `audit.integration_api_log`, `p22.integration_registry`, `p22.secret_ref_metadata` exist; `p22.integration_registry` has 12 rows; `guinevere_core` has INSERT/SELECT but NOT UPDATE/DELETE on `audit.integration_api_log`.
- **Forbidden Patterns:** `alembic upgrade head` (multi-head ambiguity) → must use `alembic upgrade p22_001_integration_schema`. Any destructive op.
- **Required Commands:**
  - `ssh guinevere-vps 'cd /home/guinevere/code/guinevere && export $(grep -E "^[A-Z_][A-Z0-9_]*=" .env.core | xargs) && .venv/bin/alembic upgrade p22_001_integration_schema --sql 2>&1 | head -50'` → dry-run SQL, no error
  - `ssh guinevere-vps 'cd /home/guinevere/code/guinevere && export $(grep -E "^[A-Z_][A-Z0-9_]*=" .env.core | xargs) && .venv/bin/alembic upgrade p22_001_integration_schema 2>&1 | tee /home/guinevere/logs/migration-p22-<TS>.log'` → exit 0, "Running upgrade" line
  - `ssh guinevere-vps 'psql ... -c "SELECT count(*) FROM ops.alembic_version"'` → 5
  - `ssh guinevere-vps 'psql ... -c "\dn p22" -c "\dt p22.*" -c "SELECT count(*) FROM p22.integration_registry"'` → schema p22, 2 tables, 12 rows
  - `ssh guinevere-vps 'psql ... -c "SELECT has_table_privilege('"'"'guinevere_core'"'"','"'"'audit.integration_api_log'"'"','"'"'UPDATE'"'"')"'` → false (WORM enforced)
- **Evidence Requirements:** `implementation/p22-migration-application.md`.
- **Hard Rejection:** migration not applied; < 12 registry rows; UPDATE/DELETE granted on audit table.

## Step T6: Restart + importability smoke (Phase A gate)
- **Expected:** `guinevere-core` active; all 13 P22 modules importable; other services still active.
- **Forbidden Patterns:** any service other than guinevere-core restarted.
- **Required Commands:**
  - `ssh guinevere-vps 'sudo systemctl restart guinevere-core && sleep 15 && systemctl is-active guinevere-core'` → active
  - `ssh guinevere-vps 'for s in guinevere-9router 9router-proxy guinevere-discord guinevere-mcp guinevere-whatsapp guinevere-monitoring guinevere-obscura guinevere-x-poster cloudflared docker; do echo "$s: $(systemctl is-active $s)"; done'` → all active
  - `ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -c "import importlib; [importlib.import_module(m) for m in [\"src.life_integrations\",\"src.life_integrations.router\",\"src.life_integrations.consent\",\"src.life_integrations.audit\",\"src.life_integrations.registry\",\"src.life_integrations.wiring\"]]; print(\"OK\")"'` → OK
  - `ssh guinevere-vps 'curl -fsS http://127.0.0.1:8000/health/detailed | head -c 600'` → 200, components ok
- **Evidence Requirements:** `deploy/p22-deploy-evidence.md`, `runtime/p22-configured-adapter-smoke.md` (Phase A importability section).
- **Hard Rejection:** guinevere-core not active; any other service down; P22 import error; 2-min traceback storm.

## Step T7: Write _shims.py (safety-critical)
- **Expected Files:** `src/life_integrations/_shims.py` with `ConsentGateShim`, `HardStopShim`, `ProjectRegistryShim`.
- **Forbidden Patterns:** `# type: ignore`, `as any`, bare `except:`. Shim that silently no-ops HARD STOP.
- **Required Commands:**
  - `python -m pytest tests/p22/ -k "shim or consent or hard_stop" -v` → PASS (add 3 shim tests first per TDD)
  - `grep -rE "# type: ignore|except:|except Exception:" src/life_integrations/_shims.py` → 0
- **Evidence Requirements:** `implementation/p22-real-client-wiring.md` (shim section + test output).
- **Hard Rejection:** HARD STOP shim returns is_safe→always-False-bypass; consent shim swallows ConsentCheckResult.allowed=False.

## Step T8: Write memory_pipeline_shim.py
- **Expected Files:** `src/life_integrations/adapters/_clients/memory_pipeline_shim.py`.
- **Required Commands:** `python -m pytest tests/p22/ -k "memory" -v` → PASS.
- **Hard Rejection:** shim drops project_id in store/recall.

## Step T9: Write runtime.py factory
- **Expected Files:** `src/life_integrations/runtime.py` — `async build_runtime_registry(app_state_or_settings) -> (registry, router)`.
- **Forbidden Patterns:** hardcoded secrets; bare `EnvSecretProvider()` without mapping where needed; fake ACTIVE.
- **Required Commands:**
  - `python -m pytest tests/p22/ -v` → 76+ PASS (≥76, plus new shim/factory tests)
  - `python scripts/p22_smoke_test.py` → exit 0 (12/12)
  - `grep -rEi "ghp_|sk-|ya29\.|xox|AIza|BEGIN PRIVATE KEY" src/life_integrations/runtime.py src/life_integrations/_shims.py` → 0
- **Evidence Requirements:** `implementation/p22-real-client-wiring.md`.
- **Hard Rejection:** factory returns ACTIVE for adapter with no secret/client; secret value in code.

## Step T10: Modify main.py lifespan injection
- **Expected Files:** `src/core/main.py` modified in `lifespan()` — adds `await build_runtime_registry(...)` + `app.state.p22_registry`/`app.state.p22_router`, wrapped in try/except that logs `p22.activation_failed` and continues.
- **Forbidden Patterns:** unguarded P22 init that can crash guinevere-core on P22 failure; modify P20 closed files.
- **Required Commands:**
  - `python -m pytest tests/p22/ tests/p19/ tests/p20/ -v --no-header 2>&1 | tail -20` → 0 fail
  - `python -c "from src.core.main import app; print('main imports OK')"` → OK
  - `grep -n "life_integrations\|build_runtime_registry" src/core/main.py` → ≥1 match in lifespan
- **Evidence Requirements:** `implementation/p22-real-client-wiring.md` (lifespan diff).
- **Hard Rejection:** P22 init unguarded (can take down core); P20 closed file edited.

## Step T11: Local verification
- **Required Commands:**
  - `python -m pytest tests/p22/ -v` → 0 fail
  - `python -m pytest tests/p19/ tests/p20/ -v -x 2>&1 | tail -5` → 0 fail (regression)
  - `python scripts/p22_smoke_test.py` → exit 0
  - `grep -rE "# type: ignore|except:|except Exception:|as any|@ts-ignore" src/life_integrations/ src/core/main.py` → 0 (or documented pre-existing)
  - `grep -rEi "ghp_|sk-|ya29\.|xox|AIza[0-9A-Za-z]{30}|BEGIN PRIVATE KEY" src/life_integrations/ src/core/main.py` → 0
- **Evidence Requirements:** `runtime/p22-configured-adapter-smoke.md` (local section).
- **Hard Rejection:** any test fail; forbidden pattern; secret in code.

## Step T12: Deploy Phase B to VPS
- **Required Commands:**
  - `rsync -avz --exclude='__pycache__' C:/Users/faizz/guinevere/src/life_integrations/ guinevere-vps:/home/guinevere/code/guinevere/src/life_integrations/` → exit 0
  - `rsync -avz C:/Users/faizz/guinevere/src/core/main.py guinevere-vps:/home/guinevere/code/guinevere/src/core/main.py` → exit 0
  - `ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -c "from src.life_integrations.runtime import build_runtime_registry; from src.core.main import app; print(\"Phase B import OK\")"'` → OK
- **Evidence Requirements:** `deploy/p22-deploy-evidence.md` (Phase B).
- **Hard Rejection:** rsync fails; import error on VPS.

## Step T13: Runtime smoke 8 ACTIVE adapters (production)
- **Required Commands (via ssh, run a smoke script on VPS):**
  - health_check_all → 8 OK, 5 UNKNOWN (CONFIG_MISSING honest)
  - L1 read on discord/github/vps/finance/browser/memory/filesystem → success
  - HARD STOP set (redis SET life_kernel:hard_stop 1) → L2 write blocked → unset after
  - consent revoke test → blocked
  - audit row has project_id (query `audit.integration_api_log` newest row)
  - `journalctl -u guinevere-core --since "2 min ago" | grep -iE "traceback|secret|password|token"` → 0 secret leaks
- **Evidence Requirements:** `runtime/p22-configured-adapter-smoke.md`, `runtime/p22-p19-p20-regression-proof.md`.
- **Hard Rejection:** CONFIG_MISSING adapter reports OK; HARD STOP doesn't block L2+; secret in logs; no project_id in audit.

## Step T14: P19/P20 regression proof
- **Required Commands:**
  - P19: `redis-cli GET feature:projects:enabled` → true; `/project` command works
  - P20: `systemctl is-active guinevere-core`; `redis-cli GET life_kernel:hard_stop` → empty; journal `hermes_brain_think_complete > 0` last 5 min; `dashboard_edited > 0`; 0 GraphRecursionError/traceback storm
  - dashboard canonical 1519135545501028549 still 1 msg editing
- **Evidence Requirements:** `runtime/p22-p19-p20-regression-proof.md` (18-check matrix R-01..R-18).
- **Hard Rejection:** P19 flag off; P20 dashboard broken; NRestarts > 0 without authorized reason; recursion/fallback/OOM.

## Step T15: Audit round 1 (8 auditors, parallel)
- **Auditors:** runtime-activation, db-migration, secrets-security, consent-hardstop, adapter-correctness, p19-namespace, p20-regression, evidence-docs. Each writes `audits/round-1/audit-<name>.md`.
- **Hard Rejection:** any FAIL-severity finding unfixed before round 2.

## Step T16: Fix all valid findings
- **Evidence:** `fixes/round-1-fix-log.md` (every finding + fix + re-verify).

## Step T17: Audit round 2 (7 auditors) — final gate
- **Auditors:** runtime, db, adapters, secrets, consent, p19-p20-regression, evidence. Each writes `audits/round-2/audit-<name>.md`.
- **Hard Rejection:** any FAIL; round 2 missing → no production PASS.

## Step T18: Finalization + docs
- **Expected Files:** `final/p22-production-activation-final-report.md`; update P22 README/status, PROGRESS/CHECKLIST, evidence index, ADR addendum if deploy decision changed, P23/P24 dependency docs.
- **Hard Rejection:** final report lacks migration status/deploy proof/runtime proof/audit r1+r2/P19-P20 regression/accepted risks/next action.

## Allowed Final Statuses
1. `P22 PRODUCTION PASS — LIFE INTEGRATION HUB RUNTIME ACTIVE` (all 8 ACTIVE, 0 invalid)
2. `P22 PRODUCTION PASS WITH CONFIG_MISSING ADAPTERS — configured adapters live, missing creds documented honestly` (8 ACTIVE, 5 CONFIG_MISSING)
3. `P22 DEPLOY HOLD — <exact blocker> + next executable step`
4. `P22 FIXES REQUIRED — valid findings remain`
