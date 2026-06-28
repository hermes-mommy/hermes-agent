# P22 DEPLOY PROMPT — Enterprise-Grade Full-Spectrum Deployment

> **Paste this entire file into a fresh Claude Code session.**
> This prompt is self-contained. It assumes ZERO prior context.

---

## PROJECT CONTEXT

You are operating on **Project Guinevere** — an autonomous AI companion and engineering system running on a single Ubuntu 24.04 VPS. The project is at `C:\Users\faizz\guinevere` on Windows (local dev) and deployed to `guinevere-vps` (SSH alias) at `/home/guinevere/code/guinevere`.

**Read `AGENTS.md` FIRST.** It is the operating contract. Follow its workflow exactly:
- §1: Super-Autopilot Flow (research → plan → delegate → verify → auditor)
- §2: Execution mandates (research wave, planner gate, collision scan, implementation, parent verify, auditor gate)
- §2.5: Per-step verification scaffold (mandatory)
- §10: Full Autonomous Task Template

**VPS details:**
- SSH alias: `guinevere-vps` (Tailscale: `guinevere.internal`)
- VPS user: `guinevere`
- VPS path: `/home/guinevere/code/guinevere`
- Service: `guinevere-core` (systemd)
- Database: PostgreSQL 16 via Docker
- Redis: via Docker
- Python: pyenv-managed
- Secrets: SOPS + age encryption

---

## WHAT HAPPENED (BACKGROUND)

A **brutal audit** of P22 (Life Integration Hub) found **32 findings** (5 CRITICAL, 10 HIGH, 17 MEDIUM). All 32 were fixed locally and independently audited PASS (32/32). **972 tests pass** (was 897, +75 new, 0 regressions). However, **all fixes are local/uncommitted** — the VPS runs pre-fix code.

### The 32 Findings (all fixed locally)

**CRITICAL (5):**
- **F01**: Discord slash commands NOT REGISTERED in bot tree → Fixed: `cmd_integrations` imported in `_entrypoint.py:210`, COMMAND_SPECS now 41
- **F02**: Only 3/13 adapters ACTIVE (discord, vps, filesystem); 10 CONFIG_MISSING → Fixed: logs now name the missing env var per adapter (honest CONFIG_MISSING, not a bug)
- **F03**: ConsentGate fail-open when `hard_stop_checker=None` → Fixed: `consent.py:124` now `if hard_stop_checker is None and tier >= L2_WRITE:` (fail-closed)
- **F04**: Unknown actions default to L1_READ (bypass consent) → Fixed: `permissions.py:230` default `L2_WRITE` with integration_id lookup
- **F05**: AuditWriter `target=None` in production → Fixed: `main.py` wires AuditLogger with real DB target

**HIGH (10):**
- **F06**: Phantom adapters (weather/search/obscura) → Fixed: docs corrected to real 13 (browser, calendar, discord, drive, filesystem, finance, github, gmail, memory, notion, telegram, vps, whatsapp)
- **F07**: No rate limiting on FastAPI → Fixed: new `src/core/api/rate_limit.py` middleware
- **F08**: GitHub client silently returns []/{} on non-200 → Fixed: raises `ProviderError` on non-200
- **F09**: Calendar/Drive no 429 retry → Fixed: retry with exponential backoff
- **F10**: X Poster leaks token[:8] → Fixed: removed partial token logging
- **F11**: dry_run classification inconsistency → Fixed: both use `integration_id`
- **F12**: 3 HARD STOP fail-open windows → Fixed: `_shims.py` fail-closed
- **F13**: TRUNCATE not in WORM contract → Fixed: new migration `p22_002_revoke_truncate_audit.py` REVOKE TRUNCATE
- **F14**: Implementation R1 fix log distorts verdicts → Fixed: honest fix log
- **F15**: Round-2 summary-adjudication aggressively reclassifies → Fixed: honest adjudication

**MEDIUM (17):** F16-F32 (README contradiction, PROGRESS.md, C10 missing, test count, browser status drift, silent audit failures, seed_last_hash, registry race, ChainVerificationError unused, no UUID v7, consent_callback collision, bare except, _rpw leak, chain_version hardcoded, dead code in secrets.py, P20 soak 37min, no external signature) — all fixed or documented as decision.

### Files Changed (34 modified + 10 new = 44 total)

**Modified (tracked by git, 34 files):**
```
PROGRESS.md
docs/setup-evidence/P20/evidence/discord-visible-autonomy/soak-monitoring.md
docs/setup-evidence/P22/production-activation/audits/round-2/round-2-summary-adjudication.md
docs/setup-evidence/P22/production-activation/runtime/p22-p19-p20-regression-proof.md
src/core/api/routes.py
src/core/main.py
src/discord/_command_registry.py
src/discord/_entrypoint.py
src/life_integrations/_shims.py
src/life_integrations/adapters/__init__.py
src/life_integrations/adapters/_clients/memory_pipeline_shim.py
src/life_integrations/adapters/browser_adapter.py
src/life_integrations/adapters/calendar_adapter.py
src/life_integrations/adapters/discord_adapter.py
src/life_integrations/adapters/drive_adapter.py
src/life_integrations/adapters/finance_adapter.py
src/life_integrations/adapters/github_adapter.py
src/life_integrations/adapters/gmail_adapter.py
src/life_integrations/adapters/memory_adapter.py
src/life_integrations/adapters/notion_adapter.py
src/life_integrations/adapters/telegram_adapter.py
src/life_integrations/adapters/vps_adapter.py
src/life_integrations/adapters/whatsapp_adapter.py
src/life_integrations/audit.py
src/life_integrations/base.py
src/life_integrations/consent.py
src/life_integrations/permissions.py
src/life_integrations/registry.py
src/life_integrations/router.py
src/life_integrations/runtime.py
src/life_integrations/secrets.py
src/life_integrations/types.py
src/life_integrations/wiring.py
tests/p22/test_shims.py
```

**New (untracked, must `git add`):**
```
src/core/api/rate_limit.py                                    (F07 rate limiting)
alembic/versions/p22_002_revoke_truncate_audit.py             (F13 WORM TRUNCATE)
tests/p22/test_audit_writer_production.py                     (F05 audit writer)
tests/p22/test_calendar_429_retry.py                          (F09 calendar retry)
tests/p22/test_consent_shims_fail_closed.py                   (F12 hard stop fail-closed)
tests/p22/test_drive_429_retry.py                             (F09 drive retry)
tests/p22/test_dry_run.py                                     (F11 dry_run classification)
tests/p22/test_github_client_errors.py                        (F08 github errors)
tests/p22/test_permissions.py                                 (F04 permissions)
tests/p22/test_registry.py                                    (F16 registry race)
src/discord/cmd_integrations.py                               (F01 Discord commands — may be untracked)
```

**Evidence/audit reports (untracked, should be committed):**
```
docs/setup-evidence/P22/audits/brutal-2026-06-28/brutal-audit-report.md
docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-prompt.md
docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/summary.md
docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/F01.md through F32.md
docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/B1-impl.md through B10-impl.md
```

---

## YOUR MISSION

Deploy all 32 P22 fixes to the production VPS. Cycle auditor + bugfixer until **truly deployed and verified live**. No shortcuts. No skipping. Full AGENTS.md workflow.

**Success criteria:**
1. All P22 fixes committed to git and pushed
2. VPS running post-fix code
3. `guinevere-core` service: active, NRestarts=0
4. All 7 FastAPI endpoints respond correctly
5. 6 Discord slash commands visible/registered
6. 972 tests pass locally (pre-deploy gate)
7. All 32 fixes verified LIVE on VPS (not just local)
8. P20 regression: no regressions introduced
9. Evidence written, PROGRESS.md updated
10. Auditor gate: PASS on all deployment steps

---

## MANDATORY WORKFLOW

Follow AGENTS.md §1 Super-Autopilot Flow and §10 Full Autonomous Task Template. Use **unlimited todo items** and **unlimited sub-agents**. Never skip a gate.

### PHASE 0: Context & State Assessment

1. Read `AGENTS.md` in full.
2. Read this prompt in full.
3. Read `docs/setup-evidence/P22/audits/brutal-2026-06-28/brutal-audit-report.md` (the 32 findings).
4. Read `docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/summary.md` (the fix verification).
5. Check `git status`, `git diff --stat`, `git log --oneline -5`.
6. Check current VPS state: `ssh guinevere-vps "systemctl status guinevere-core --no-pager -l"` and `ssh guinevere-vps "journalctl -u guinevere-core --since '5 min ago' --no-pager -l 20"`.
7. Create master todo list with ALL deployment steps (unlimited items).

### PHASE 1: Research Wave (Mandatory — AGENTS.md §2.2)

Fire **unlimited parallel sub-agents** (`run_in_background=true`) to research:

1. **explore agent**: Verify all 34 modified files have the expected fixes. Grep for each fix pattern. Confirm no forbidden patterns (`as any`, `# type: ignore`, `except Exception` in cmd_integrations.py, `target=None` in src/, `x_access_token[:` in x_poster).
2. **explore agent**: Check VPS SSH connectivity, current service state, current code version on VPS (`git log --oneline -3` on VPS).
3. **explore agent**: Identify all untracked files that need `git add` for P22 deploy. Separate P22-related from non-P22 (do NOT commit .claude/, .codex/, .env files, .playwright-mcp/, etc.).
4. **librarian agent**: Research systemd deploy best practices — graceful restart vs hard restart, `systemctl reload` vs `systemctl restart`, health check timeout, journal verification.
5. **librarian agent**: Research Alembic migration deployment — `alembic upgrade head` on VPS, rollback strategy, what happens if migration fails.
6. **explore agent**: Check if `src/discord/cmd_integrations.py` is tracked or untracked. If untracked, it MUST be `git add`-ed.
7. **explore agent**: Check if `src/life_integrations/audit_db_writer.py` was modified or if it's untracked.
8. **explore agent**: Read `alembic/versions/p22_002_revoke_truncate_audit.py` — verify migration is safe, idempotent, has proper `down_revision`.

All research outputs must use explicit `output_path` and write complete files to `docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-research/`. Parent reads all reports before proceeding.

### PHASE 2: Planner Gate (Mandatory — AGENTS.md §2.3)

Run planner agent. Planner writes file to `docs/setup-evidence/P22/audits/brutal-2026-28/deploy-plan.md`. Plan must include:

- Master todo (atomic steps)
- Dependency map (what must happen before what)
- Collision scan (shared files, shared config)
- Per-step verification scaffold (AGENTS.md §2.5):
  - Expected Files
  - Forbidden Patterns (regex/grep)
  - Required Commands (with expected exit codes)
  - Evidence Requirements
  - Hard Rejection Criteria
- Rollback plan (if deploy fails, how to revert)
- Auditor matrix (which auditor checks which step)
- Execution order (parallel vs sequential)

**Parent reads plan, verifies scaffold compliance, syncs todos.**

### PHASE 3: Pre-Deploy Verification (Local)

**Step 3.1: Run full test suite**
```bash
cd C:\Users\faizz\guinevere
python -m pytest tests/p22/ -q --no-header -p no:warnings
```
Expected: 972 passed, 0 failed. If any fail → STOP, fix before deploy.

**Step 3.2: Verify forbidden patterns clean**
```bash
# All must return 0 matches:
grep -r "as any" src/life_integrations/ src/discord/ src/core/ --include="*.py"
grep -r "# type: ignore" src/life_integrations/ src/discord/ src/core/ --include="*.py"
grep -r "@ts-ignore" src/ --include="*.py"
grep -r "target=None\|target = None" src/ --include="*.py"
grep -r "except Exception" src/discord/cmd_integrations.py
grep -r "x_access_token\[" src/x_poster/
grep -r "_rpw" src/life_integrations/runtime.py
```

**Step 3.3: Verify critical fixes in code**
```bash
# F01: Discord commands registered
grep "cmd_integrations" src/discord/_entrypoint.py
# F03: ConsentGate fail-closed
grep "hard_stop_checker is None" src/life_integrations/consent.py
# F04: Default L2_WRITE
grep "L2_WRITE" src/life_integrations/permissions.py | head -5
# F05: No target=None
grep "target=None\|target = None" src/ --include="*.py"
# F07: Rate limiting exists
test -f src/core/api/rate_limit.py && echo "EXISTS"
# F13: Migration exists
test -f alembic/versions/p22_002_revoke_truncate_audit.py && echo "EXISTS"
```

**Step 3.4: Import check (all changed modules)**
```bash
python -c "
import src.life_integrations.consent
import src.life_integrations.permissions
import src.life_integrations.router
import src.life_integrations._shims
import src.life_integrations.runtime
import src.life_integrations.audit
import src.life_integrations.registry
import src.life_integrations.secrets
import src.life_integrations.wiring
import src.core.api.routes
import src.core.main
import src.discord._entrypoint
import src.discord._command_registry
print('ALL IMPORTS OK')
"
```

### PHASE 4: Git Commit & Push

**Step 4.1: Stage P22-related files ONLY**

```bash
# Modified files (already tracked)
git add PROGRESS.md
git add docs/setup-evidence/P20/evidence/discord-visible-autonomy/soak-monitoring.md
git add docs/setup-evidence/P22/production-activation/audits/round-2/round-2-summary-adjudication.md
git add docs/setup-evidence/P22/production-activation/runtime/p22-p19-p20-regression-proof.md
git add src/core/api/routes.py
git add src/core/main.py
git add src/discord/_command_registry.py
git add src/discord/_entrypoint.py
git add src/life_integrations/
git add tests/p22/test_shims.py

# New files (untracked)
git add src/core/api/rate_limit.py
git add alembic/versions/p22_002_revoke_truncate_audit.py
git add tests/p22/test_audit_writer_production.py
git add tests/p22/test_calendar_429_retry.py
git add tests/p22/test_consent_shims_fail_closed.py
git add tests/p22/test_drive_429_retry.py
git add tests/p22/test_dry_run.py
git add tests/p22/test_github_client_errors.py
git add tests/p22/test_permissions.py
git add tests/p22/test_registry.py

# cmd_integrations.py — check if tracked or untracked
git add src/discord/cmd_integrations.py  # may need -f if .gitignored

# Evidence files
git add docs/setup-evidence/P22/audits/brutal-2026-06-28/
```

**Step 4.2: Verify staging**
```bash
git diff --cached --stat
```
Verify: ~44 files staged, ~2600+ insertions. NO .env files, NO .claude/, NO .codex/, NO secrets.

**Step 4.3: Commit**
```bash
git commit -m "fix(p22): brutal-audit remediation — 32/32 findings fixed + audited PASS

5 CRITICAL (F01-F05): Discord commands registered, consent fail-closed,
L2 default for unknown actions, audit writer wired to DB, adapter logs
10 HIGH (F06-F15): rate limiting, GitHub errors, 429 retry, token leak,
dry_run consistency, HARD STOP fail-closed, TRUNCATE WORM, honest fix logs
17 MEDIUM (F16-F32): README, PROGRESS.md, registry race, bare except, etc

972 tests pass (+75 new, 0 regressions). 32 independent auditor reports PASS.
Evidence: docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/"
```

**Step 4.4: Push**
```bash
git push origin main
```

### PHASE 5: VPS Deployment

**Step 5.1: SSH to VPS and pull**
```bash
ssh guinevere-vps "cd /home/guinevere/code/guinevere && git pull origin main"
```

**Step 5.2: Install new dependencies (if any)**
```bash
ssh guinevere-vps "cd /home/guinevere/code/guinevere && pip install -r requirements.txt 2>&1 | tail -5"
```
Check if `slowapi` or any new dependency was added for rate limiting. If so, install it.

**Step 5.3: Run Alembic migration**
```bash
ssh guinevere-vps "cd /home/guinevere/code/guinevere && alembic upgrade head"
```
Expected: `p22_002_revoke_truncate_audit` migration runs. If it fails → STOP, check migration script.

**Step 5.4: Restart guinevere-core**
```bash
ssh guinevere-vps "sudo systemctl restart guinevere-core"
```

**Step 5.5: Wait for service to stabilize**
```bash
sleep 10
ssh guinevere-vps "systemctl is-active guinevere-core"
```
Expected: `active`. If `failed` → STOP, check journal.

**Step 5.6: Verify NRestarts**
```bash
ssh guinevere-vps "systemctl show guinevere-core -p NRestarts"
```
Expected: `NRestarts=0` (counter resets on restart, so this should be 0 after the restart above).

### PHASE 6: Post-Deploy Verification (LIVE on VPS)

**Step 6.1: API endpoints respond**
```bash
# Status endpoint (no auth needed)
ssh guinevere-vps "curl -s http://127.0.0.1:8000/api/v1/integrations/status | python3 -m json.tool"

# Capabilities endpoint
ssh guinevere-vps "curl -s http://127.0.0.1:8000/api/v1/integrations/capabilities | python3 -m json.tool"

# Missing endpoint
ssh guinevere-vps "curl -s http://127.0.0.1:8000/api/v1/integrations/missing | python3 -m json.tool"
```

**Step 6.2: Auth on mutations**
```bash
# Should return 401 without API key
ssh guinevere-vps "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/v1/integrations/test -X POST -H 'Content-Type: application/json' -d '{}'"
# Expected: 401
```

**Step 6.3: Rate limiting active**
```bash
# Hit an endpoint rapidly, check for 429
ssh guinevere-vps "for i in \$(seq 1 50); do curl -s -o /dev/null -w '%{http_code} ' http://127.0.0.1:8000/api/v1/integrations/status; done; echo"
# Should see 200s then 429s (if rate limit configured)
```

**Step 6.4: Discord commands registered**
```bash
# Check journal for command sync
ssh guinevere-vps "journalctl -u guinevere-core --since '2 min ago' --no-pager | grep -i 'command\|sync\|tree'"
```

**Step 6.5: Audit trail writing to DB**
```bash
ssh guinevere-vps "python3 -c \"
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'].replace('+asyncpg',''))
cur = conn.cursor()
cur.execute('SELECT count(*) FROM audit.integration_api_log')
print(f'audit rows: {cur.fetchone()[0]}')
cur.execute('SELECT count(*) FROM audit.integration_api_log WHERE occurred_at > now() - interval \\'5 min\\'')
print(f'recent rows: {cur.fetchone()[0]}')
conn.close()
\""
```

**Step 6.6: Consent gate fail-closed (F03)**
```bash
ssh guinevere-vps "grep 'hard_stop_checker is None' /home/guinevere/code/guinevere/src/life_integrations/consent.py"
# Expected: line with "if self._hard_stop_checker is None and tier >= PermissionTier.L2_WRITE:"
```

**Step 6.7: L2 default for unknown actions (F04)**
```bash
ssh guinevere-vps "grep 'L2_WRITE' /home/guinevere/code/guinevere/src/life_integrations/permissions.py | tail -5"
# Expected: default L2_WRITE for unknown actions
```

**Step 6.8: WORM TRUNCATE revoked (F13)**
```bash
ssh guinevere-vps "psql -c \\\"SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_name='integration_api_log' AND table_schema='audit' ORDER BY grantee, privilege_type;\\\""
# Expected: guinevere_core has INSERT, SELECT only. NO UPDATE, NO DELETE, NO TRUNCATE.
```

**Step 6.9: P20 regression check**
```bash
ssh guinevere-vps "systemctl show guinevere-core -p NRestarts -p MemoryCurrent -p ActiveState"
ssh guinevere-vps "journalctl -u guinevere-core --since '5 min ago' --no-pager -l 30 | grep -iE 'error|fail|traceback|exception'"
# Expected: NRestarts=0, no errors in journal
```

**Step 6.10: Full VPS test suite (if tests exist on VPS)**
```bash
ssh guinevere-vps "cd /home/guinevere/code/guinevere && python -m pytest tests/p22/ -q --no-header -p no:warnings 2>&1 | tail -5"
```

### PHASE 7: Auditor Wave (Mandatory — AGENTS.md §2.10)

Spawn **unlimited parallel auditor sub-agents** for each verification surface:

1. **Auditor: F01-F05 (CRITICAL fixes live on VPS)** — verify each critical fix is actually running on VPS, not just in code. Check git log on VPS matches local. Check service is running post-fix code.
2. **Auditor: F07 rate limiting live** — verify rate limiting middleware is active on VPS FastAPI app. Hit endpoints rapidly, confirm 429 returned.
3. **Auditor: F13 WORM TRUNCATE live** — verify database grants on VPS. Confirm TRUNCATE is revoked from `guinevere_core` role.
4. **Auditor: P20 regression** — verify no P20 services broke. Check NRestarts=0, memory stable, no journal errors, Discord embed exists.
5. **Auditor: Migration safety** — verify `p22_002_revoke_truncate_audit` ran cleanly. Check alembic version on VPS. Verify rollback path exists.
6. **Auditor: Git hygiene** — verify commit is clean, no secrets committed, no .env files, no .claude/ artifacts. Check `git log --oneline -3` on VPS matches local.
7. **Auditor: Test suite** — verify 972 tests pass. If any fail on VPS due to environment differences, document and assess.
8. **Auditor: Evidence completeness** — verify all evidence files exist, deploy evidence written, PROGRESS.md updated.

All auditors write reports to `docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-audits/`. Parent reads all reports.

**Fix cycle:** If any auditor returns NEEDS_REVIEW or FAIL:
1. Fix the issue (locally or on VPS)
2. Re-deploy if needed
3. Re-run auditor via `task_id` continuation
4. Cycle until PASS

### PHASE 8: Evidence & Report

**Step 8.1: Write deploy evidence**
Write to `docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-evidence.md`:
- What was deployed
- Files changed on VPS
- Migration applied
- Service restart details
- Post-deploy verification results (all steps from Phase 6)
- Auditor gate results
- Any issues found and fixed
- Rollback safety assessment

**Step 8.2: Update PROGRESS.md**
Update P22 line to: `🟢 DEPLOYED — AUDIT REMEDIATED + AUDITOR PASS (32/32) — POST-DEPLOY VERIFIED`

**Step 8.3: Commit evidence**
```bash
git add docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-evidence.md
git add docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-audits/
git add docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-research/
git add docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-plan.md
git add PROGRESS.md
git commit -m "docs(p22): deploy evidence + auditor reports — DEPLOYED + VERIFIED"
git push origin main
```

**Step 8.4: Final report**
Output:
- Deploy status: ✅ DEPLOYED or ❌ FAILED
- Commit hash
- VPS git log (matches local)
- Service status (active, NRestarts=0)
- Test results (972 pass)
- All 32 fixes verified live
- Auditor gate (all PASS)
- Evidence path
- Any remaining caveats

---

## COLLISION MAP

| Resource | Owner | Conflict Risk |
|---|---|---|
| `src/core/main.py` | Deploy step only | P20 also touches this file — verify P20 code still intact |
| `src/discord/_entrypoint.py` | Deploy step only | Discord bot restart needed after deploy |
| `alembic/versions/` | Deploy step only | Migration must run in sequence |
| `PROGRESS.md` | Deploy step only | No other task should touch |
| `guinevere-core` service | Deploy step only | Brief downtime during restart |
| PostgreSQL | Deploy step only | Migration acquires brief lock |
| VPS git repo | Deploy step only | `git pull` during deploy |

---

## ROLLBACK PLAN

If deployment fails at any point:

1. **Migration rollback:** `alembic downgrade p22_001_integration_schema` (reverts p22_002)
2. **Code rollback:** On VPS: `git checkout <previous-commit-hash>` (before P22 fixes)
3. **Service rollback:** `sudo systemctl restart guinevere-core`
4. **Verify rollback:** `systemctl is-active guinevere-core` + `curl http://127.0.0.1:8000/health`
5. **Document failure:** Write incident report to `docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-incident.md`
6. **Notify operator:** Report to Faiz what failed, what was rolled back, what needs fixing

---

## FORBIDDEN ACTIONS (AGENTS.md BLOCKING RULES)

- NEVER commit secrets (.env files, tokens, passwords, SOPS keys)
- NEVER force push (`git push --force`)
- NEVER skip test suite before deploy
- NEVER skip migration on VPS
- NEVER skip auditor gate
- NEVER auto-deploy without verifying each step
- NEVER leave service in failed state — always rollback if deploy fails
- NEVER use `as any`, `# type: ignore`, `@ts-ignore`, `@ts-expect-error`
- NEVER use empty catch blocks
- NEVER delete failing tests to pass
- NEVER bypass consent/safety boundaries
- NEVER expose Faiz's personal data in artifacts/logs/external tools

---

## EXECUTION CHECKLIST

- [ ] Read AGENTS.md
- [ ] Read brutal-audit-report.md
- [ ] Read fix-verification/summary.md
- [ ] Create master todo (unlimited items)
- [ ] Fire research wave (8+ parallel agents)
- [ ] Read all research reports
- [ ] Run planner gate → write deploy-plan.md
- [ ] Verify scaffold compliance
- [ ] Sync todos to plan
- [ ] Run collision scan
- [ ] Pre-deploy: 972 tests pass
- [ ] Pre-deploy: forbidden patterns clean
- [ ] Pre-deploy: critical fixes verified in code
- [ ] Pre-deploy: import check passes
- [ ] Git: stage P22 files only (no secrets, no .claude/)
- [ ] Git: commit with detailed message
- [ ] Git: push to origin/main
- [ ] VPS: git pull
- [ ] VPS: install dependencies (if new)
- [ ] VPS: alembic upgrade head
- [ ] VPS: restart guinevere-core
- [ ] VPS: verify service active
- [ ] VPS: verify NRestarts=0
- [ ] VPS: verify API endpoints respond
- [ ] VPS: verify auth on mutations
- [ ] VPS: verify rate limiting active
- [ ] VPS: verify Discord commands registered
- [ ] VPS: verify audit trail writing to DB
- [ ] VPS: verify consent gate fail-closed (F03)
- [ ] VPS: verify L2 default (F04)
- [ ] VPS: verify WORM TRUNCATE revoked (F13)
- [ ] VPS: verify P20 no regression
- [ ] VPS: run test suite (if available)
- [ ] Spawn auditor wave (8+ parallel auditors)
- [ ] Read all auditor reports
- [ ] Fix any NEEDS_REVIEW/FAIL findings
- [ ] Re-audit until PASS
- [ ] Write deploy evidence
- [ ] Update PROGRESS.md
- [ ] Commit evidence
- [ ] Push evidence
- [ ] Final report

---

## START

Begin now. Read AGENTS.md, then this prompt, then execute the full workflow. Use unlimited todo items and unlimited sub-agents. Cycle auditor + bugfixer until truly deployed and verified. Do not stop until the execution checklist is complete and all auditors PASS.
