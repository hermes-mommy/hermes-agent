# P22 Production Activation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate P22 Life Integration Hub on the production VPS — apply migration, deploy code, wire 8 real adapters to ACTIVE, prove P19/P20 not regressed, leave 5 adapters honestly CONFIG_MISSING, and earn an audit-round-2 production PASS.

**Architecture:** Two-phase deploy. **Phase A (library+migration):** ship `src/life_integrations/` + migration files to VPS, apply `p22_001` (idempotent), restart `guinevere-core` as importability no-op smoke. **Phase B (wiring+activation):** add additive `runtime.py` + `_shims.py` + ~50 LOC lifespan injection in `src/core/main.py` so `build_default_registry()` receives real clients at startup; 8 adapters go ACTIVE, 5 stay CONFIG_MISSING. P20 closed files are NEVER semantically modified — only additive methods/shims.

**Tech Stack:** Python 3.12, FastAPI/uvicorn, asyncpg, Alembic, PostgreSQL 16 (Docker `guinevere-postgres`), Redis, systemd, structlog, httpx, neonize.

## Global Constraints

- **AGENTS.md 100%** — consent-safety, HARD STOP absolute, no secret exposure, no fake PASS.
- **Never restart** any service except `guinevere-core`. 9Router/P26/discord/mcp/whatsapp/monitoring/obscura/x-poster/cloudflared/docker/tailscaled/ufw are DO-NOT-TOUCH.
- **Never print** secret/token/DB-password/PAT/OAuth values. Names/refs only.
- **Never hardcode** credentials. All secrets via `SecretProvider` (EnvSecretProvider / ProjectVaultSecretProvider).
- **Never fake PASS.** CONFIG_MISSING honest (UNKNOWN + `ConfigurationMissingError`); CONFIG_INVALID honest (ERROR + typed error); CLIENT_MISSING honest (ImportError surfaced).
- **P20 CLOSED** — do not reopen unless runtime incident (crash/recursion/fallback-storm/OOM/dashboard-fail/privacy-leak). Restart of guinevere-core resets soak clock (authorized, not incident).
- **WORM audit table** — never downgrade `audit.integration_api_log` once it has rows. Code-only rollback if needed.
- **Migration apply** = explicit `alembic upgrade p22_001_integration_schema`, NEVER `head` (multi-head state).
- Forbidden patterns in new code: `# type: ignore`, `as any`, bare `except:`, `except Exception:` without re-raise/log, empty catch, `__import__('datetime')`.

## Parent-Resolved Ground Truth (from 7 research reports, all parent-read)

### Confirmed blockers (must resolve in plan)
- **B-A:** `src/life_integrations/`, `p19_003_audit_chain_version.py`, `p22_001_integration_schema.py` are UNTRACKED locally and ABSENT on VPS. VPS `alembic heads` = `p19_002` only. Naive `upgrade head` skips p22_001.
- **B-B:** `.env.core` `DATABASE_URL` password is STALE for alembic (`InvalidPasswordError`), but guinevere-core service is healthy (uses a different auth path). Resolve before migration.
- **B-C:** `.env.core` line 13 `9ROUTER_API_KEY` (starts with digit) is an invalid env-var name → breaks `source .env.core`. Filter with `grep -E '^[A-Z_][A-Z0-9_]*='`.
- **B-D:** VPS working tree is DIRTY (10+ files unrelated to P22: `alembic/env.py`, `src/core/main.py`, `src/discord/_*.py`, etc.). `git pull` needs Path A (commit+push) or Path B (stash+filter).
- **B-E:** `ops.alembic_version` is multi-head (4 rows: p19_001, p19_002, p19_003, p20_001). Use explicit revision target.
- **B-F:** Venv = symlink to system Python 3.12. PyGithub/telethon/notion-client missing — but 8 ACTIVE adapters don't need them. PEP 668 blocks new pip installs; out of scope for this phase.
- **B-G:** `life_kernel:dashboard_message_id` unset in Redis though dashboard edits canonical 1519135545501028549. Verify storage location; not a blocker.
- **B-H:** WORM audit rollback — code-only rollback if audit table has rows.

### Interface mismatches (parent-verified, shim-required, safety-critical)
- `HardStopHandler.is_safe()` (hard_stop_handler.py:63) vs P22 `HardStopCheckerProtocol.is_hard_stop_active()` (consent.py:44,106). If wired bare, HARD STOP gate is silent no-op → BYPASS. **Shim mandatory.**
- Gmail `ConsentCheckResult` return (gmail/service.py:802) vs P22 `ConsentCheckerProtocol.check_consent() -> bool` (consent.py:24). **Shim mandatory.**
- P19 `ProjectRegistry.get_by_slug` vs P22 `ProjectRegistryProtocol.resolve(slug)` (project_context.py:26). **Shim mandatory.**
- `DiscordRestClient` lacks `health()`/`get_messages`/`delete_message` — additive methods only (not P20 closed-file semantic change; verify wiring.py only calls `IntegrationRegistry.register()`).
- `FinanceMind` lacks `replay()`/`summarize()` — not needed for L1 health; skip.

### Activation matrix (parent-resolved)
| Adapter | Now | After Phase B | Build param | In-tree client |
|---|---|---|---|---|
| discord | CONFIG_MISSING | **ACTIVE** | discord_rest_client | `DiscordRestClient` |
| github | CONFIG_MISSING | **ACTIVE** | github_client | `src.mcp.tools.github.GitHubClient` (httpx) |
| vps | CONFIG_MISSING | **ACTIVE** | vps_docker_client, vps_shell_client | `DockerTool`, `ShellTool` |
| finance | CONFIG_MISSING | **ACTIVE** | finance_mind | `FinanceMind` |
| browser | CONFIG_MISSING | **ACTIVE** | browser_search, browser_fetch, browser_cdp | `BraveSearchTool`, `FetchTool`, `ObscuraCDPTool` |
| memory | CONFIG_MISSING | **ACTIVE** | memory_write_pipeline, memory_read_pipeline, kg_engine | shim around `store_episode`/`recall_memories` + `KGQueryEngine` |
| filesystem | CONFIG_MISSING | **ACTIVE** | workspace_root | self-contained |
| whatsapp | CONFIG_MISSING | **ACTIVE** (after re-verify `.env.whatsapp`) | whatsapp_adapter | `WhatsAppIngressEgressAdapter` |
| gmail | CONFIG_MISSING | **CONFIG_MISSING** | — | google libs local-missing; VPS-only; OAuth operator-gated |
| calendar | CONFIG_MISSING | **CONFIG_MISSING** | — | no client, no OAuth |
| drive | CONFIG_MISSING | **CONFIG_MISSING** | — | no client, no OAuth |
| notion | CONFIG_MISSING | **CONFIG_MISSING** | — | no client lib, no token |
| telegram | CONFIG_MISSING | **CONFIG_MISSING** | — | no client lib, no token |

## File Structure

### Files to CREATE (additive only — no P20 closed-file semantic changes)
- `src/life_integrations/runtime.py` — production factory: reads secrets via `SecretProvider`, constructs 8 real clients, calls `build_default_registry()` with real kwargs, returns `(registry, router)`. ~250 LOC.
- `src/life_integrations/_shims.py` — safety-critical adapters that bridge existing services to P22 protocols: `ConsentGateShim` (ConsentCheckResult→bool), `HardStopShim` (is_safe→is_hard_stop_active), `ProjectRegistryShim` (get_by_slug→resolve). ~120 LOC.
- `src/life_integrations/adapters/_clients/memory_pipeline_shim.py` — thin shim exposing `.store_episode()`/`.recall_memories()` forwarding to `src.memory.write_pipeline`/`read_pipeline` module functions. ~60 LOC.
- Evidence files (see Evidence Paths below).

### Files to MODIFY
- `src/core/main.py` — add ~50 LOC in `lifespan()` (after LoopManager init, ~line 60-606 block): import `build_runtime_registry` from `src.life_integrations.runtime`, await it, attach `registry`+`router` to `app.state`. MUST be wrapped in try/except that logs `p22.activation_failed` and CONTINUES startup (P22 failure must NOT take down guinevere-core — fail-open for the app, fail-closed for P22 only).
- `src/life_kernel/discord_rest_client.py` — ADD additive methods `health()`, `get_messages(channel_id, limit)`, `delete_message(channel_id, message_id)` if absent. Verify first; only add missing. NOT a P20 closed file per research (P18-era), but treat as sensitive — additive only.

### Files NOT to modify (collision scan)
- P20 closed source: `src/life_kernel/heartbeat*`, `cognition.py`, `hermes_brain.py`, `dashboard_writer.py`, `sensors.py`, `graph*.py`, `state/models.py` — NONE.
- Any `adr/`, `docs/20-security/`, `PersonaSafetyPolicy` — NONE.
- 9Router config, P26 files, `.env.*` value contents (may add NEW key NAMES only if a client needs one; never edit existing secret values).

## Dependency Map + Parallelism

```
Phase A (library+migration) — sequential, single owner:
  T1 commit P22 to git ──┐
  T2 backup VPS DB+code ─┤ (T1||T2 parallel; both before T3)
  T3 deploy code to VPS ─┤ (needs T1)
  T4 resolve alembic auth (B-B/B-C) ─┤ (parallel with T3)
  T5 apply migration p22_001 ──── needs T2(backup) + T3(code) + T4(auth)
  T6 restart guinevere-core + importability smoke ── needs T5

Phase B (wiring+activation) — T7..T10 parallel-able, T11 sequential:
  T7 write _shims.py (safety-critical) ──┐
  T8 write memory_pipeline_shim.py ──────┤
  T9 write runtime.py factory ───────────┤ needs T7+T8 (parallel dev, sequential integrate)
  T10 modify main.py lifespan injection ── needs T9
  T11 local verification (tests+smoke+scan) ── needs T10
  T12 deploy Phase B to VPS (rsync src/life_integrations/ + main.py) ── needs T11
  T13 restart + runtime smoke 8 ACTIVE adapters ── needs T12
  T14 P19/P20 regression proof ── needs T13
```

## Exact Migration Commands (Phase A, T5)
```bash
# Pre-flight (read-only)
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && ls alembic/versions/p19_003_audit_chain_version.py alembic/versions/p22_001_integration_schema.py'
# Source env filtering the invalid 9ROUTER_API_KEY line
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && export $(grep -E "^[A-Z_][A-Z0-9_]*=" .env.core | xargs) && .venv/bin/alembic current 2>&1 | tail -3'
# Dry-run SQL
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && export $(grep -E "^[A-Z_][A-Z0-9_]*=" .env.core | xargs) && .venv/bin/alembic upgrade p22_001_integration_schema --sql 2>&1 | head -50'
# Apply (explicit revision, NEVER head)
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && export $(grep -E "^[A-Z_][A-Z0-9_]*=" .env.core | xargs) && .venv/bin/alembic upgrade p22_001_integration_schema 2>&1 | tee /home/guinevere/logs/migration-p22-$(date -u +%Y%m%dT%H%M%SZ).log'
# Verify
ssh guinevere-vps 'export $(grep -E "^[A-Z_][A-Z0-9_]*=" /home/guinevere/code/guinevere/.env.core | xargs) && PGPASSWORD="$(...)" psql -h localhost -p 5433 -U guinevere_core -d guinevere -c "SELECT version_num FROM ops.alembic_version ORDER BY version_num" -c "\dn p22" -c "\dt p22.*" -c "SELECT count(*) FROM p22.integration_registry"'
# Expect: 5 alembic rows (incl p22_001), schema p22 exists, 2 tables, 12 registry rows
```
> NOTE: `PGPASSWORD` extraction must come from the auth path the running service uses (B-B resolve). NEVER echo it. If trust-auth, omit password.

## Backup Strategy (Phase A, T2 — BEFORE any migration)
```bash
ssh guinevere-vps 'TS=$(date -u +%Y%m%dT%H%M%SZ) && mkdir -p /home/guinevere/data/backups && docker exec guinevere-postgres pg_dumpall -U guinevere --no-role-passwords 2>/tmp/p22-predeploy-${TS}.pgerr | gzip -9 > /home/guinevere/data/backups/guinevere-p22-predeploy-${TS}.sql.gz && sha256sum /home/guinevere/data/backups/guinevere-p22-predeploy-${TS}.sql.gz > /home/guinevere/data/backups/guinevere-p22-predeploy-${TS}.sql.gz.sha256 && stat -c%s /home/guinevere/data/backups/guinevere-p22-predeploy-${TS}.sql.gz'
# Expect: size > 1 GB. Code snapshot (no .env, no .venv):
ssh guinevere-vps 'TS=$(date -u +%Y%m%dT%H%M%SZ) && cp -a /home/guinevere/code/guinevere /home/guinevere/data/backups/guinevere-code-bak-${TS} && find /home/guinevere/data/backups/guinevere-code-bak-${TS} -name ".env*" -delete && rm -rf /home/guinevere/data/backups/guinevere-code-bak-${TS}/.venv && echo "code snapshot: ${TS}"'
```

## Deploy Strategy
- Phase A code: `git pull` (Path A: local commit+push first) OR `rsync` only the 3 new artifact sets (`src/life_integrations/`, `alembic/versions/p19_003*.py`, `alembic/versions/p22_001*.py`). Prefer rsync to avoid touching the dirty tree.
- Phase B code: `rsync src/life_integrations/` (updated) + `src/core/main.py` (modified).
- Restart: `sudo systemctl restart guinevere-core` ONLY. Verify 9Router/discord/etc still active.

## Runtime Smoke Matrix (Phase B, T13 — per adapter)
| Adapter | health_check | safe read | safe write (policy-gated) | delete (dry-run/tombstone) | audit event | project_id |
|---|---|---|---|---|---|---|
| discord | OK | list_messages (L1) | skip (L2 needs consent) | skip (L3) | yes | yes |
| github | OK | list_repos (L1) | skip | skip | yes | yes |
| vps | OK | health_metrics (L1) | skip (L2 restart gated) | skip (L3) | yes | yes |
| finance | OK | list_transactions (L1) | skip (L2 gated, pay-blocked) | skip | yes | yes |
| browser | OK | search (L1) | skip | n/a | yes | yes |
| memory | OK | recall_memories (L1) | skip (L2) | mark_dnr dry-run (L3) | yes | yes |
| filesystem | OK | list_files (L1) | write to /tmp/p22-smoke (L2 gated) | tombstone dry-run (L3) | yes | yes |
| whatsapp | OK | skip (no read API) | skip | skip | yes | yes |
| gmail..telegram (5) | UNKNOWN | CONFIG_MISSING honest | n/a | n/a | yes (status=missing) | yes |
Plus: P20 heartbeat alive, P19 registry query OK, HARD STOP blocks L2+ (test set+unset), consent revoke blocks, dashboard 1 canonical msg, no secret in logs.

## CONFIG_MISSING Criteria
- `CONFIG_MISSING`: secret genuinely absent (SOPS/env has no key) OR client not injected at startup. Adapter returns `IntegrationHealth.UNKNOWN`, raises `ConfigurationMissingError`. **Honest.**
- `CONFIG_INVALID`: secret present but fails validation (revoked/expired/wrong scope). Returns `ERROR` + typed error. (gmail/calendar/drive/notion/telegram if creds appear later but invalid.)
- `CLIENT_MISSING`: client library not installed. Surfaces as ImportError at construction.
- `ACTIVE`: secret present + client constructed+injected + health_check() == OK.
- **HARD RULE:** no adapter may report OK in the first three states. Fake PASS = HARD REJECTION.

## Hard Rejection Criteria
1. Secrets printed/committed → FAIL.
2. Migration not applied but final says production pass → FAIL.
3. Real clients not wired but final says production pass → FAIL.
4. CONFIG_MISSING adapter claimed OK → FAIL.
5. HARD STOP does not block L2+ (incl. bare ConsentGate without shim → silent no-op) → FAIL.
6. Consent revoke does not block relevant adapter → FAIL.
7. project_id/project_scope missing from action audit → FAIL.
8. P19/P20 regression not checked → FAIL.
9. Deploy without backup → FAIL.
10. Audit round 2 missing → FAIL.
11. Sub-agent output inline-only → FAIL.
12. Any service other than guinevere-core restarted → FAIL.

## Evidence Paths
```
docs/setup-evidence/P22/production-activation/
  research/            (7 files — DONE)
  plan/                (this file + scaffold)
  implementation/p22-real-client-wiring.md
  implementation/p22-migration-application.md
  deploy/p22-backup-evidence.md
  deploy/p22-deploy-evidence.md
  deploy/p22-rollback-plan.md
  runtime/p22-configured-adapter-smoke.md
  runtime/p22-p19-p20-regression-proof.md
  audits/round-1/*.md
  fixes/round-1-fix-log.md
  audits/round-2/*.md
  final/p22-production-activation-final-report.md
```

## Auditor Matrix
Round 1 (8): runtime-activation, db-migration, secrets-security, consent-hardstop, adapter-correctness, p19-namespace, p20-regression, evidence-docs.
Round 2 (7): runtime, db, adapters, secrets, consent, p19-p20-regression, evidence.

## Rollback Plan
- Code: restore snapshot (`cp -a .../guinevere-code-bak-<TS> .../guinevere`) OR `git checkout` prev.
- Migration: **DO NOT downgrade** `audit.integration_api_log` if rows exist (WORM). Leave schema, rollback code only, restart, smoke. Only consider `alembic downgrade` if audit table empty + registry empty + verifier agrees.
- P22 activation failure in lifespan: MUST be try/except → log `p22.activation_failed`, app continues. P22 isolated, guinevere-core never down from P22.

## Caveats
- B-B (alembic auth) is the single highest-risk step; if unresolvable, Phase A stops at DEPLOY HOLD.
- whatsapp `.env.whatsapp` perm-denied in research; re-verify before flipping ACTIVE or leave CONFIG_MISSING honest.
- memory needs shim (module functions → instance protocol); verify `store_episode`/`recall_memories` signatures at impl time.
- `recall_degraded` 24h=79 is monitor-only; if P22 amplifies it → runtime incident → escalate.

## Execution Checklist
- [ ] T1 commit P22 to git
- [ ] T2 backup VPS DB + code
- [ ] T3 deploy code (rsync preferred)
- [ ] T4 resolve alembic auth (B-B/B-C)
- [ ] T5 apply migration p22_001
- [ ] T6 restart + importability smoke (Phase A done)
- [ ] T7 write _shims.py (safety-critical)
- [ ] T8 write memory_pipeline_shim.py
- [ ] T9 write runtime.py factory
- [ ] T10 modify main.py lifespan injection
- [ ] T11 local verification (tests+smoke+scan)
- [ ] T12 deploy Phase B to VPS
- [ ] T13 runtime smoke 8 ACTIVE adapters
- [ ] T14 P19/P20 regression proof
- [ ] T15 audit round 1 (8 auditors)
- [ ] T16 fix all valid findings
- [ ] T17 audit round 2 (7 auditors) — final gate
- [ ] T18 finalization + docs
