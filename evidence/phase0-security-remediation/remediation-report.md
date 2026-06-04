# Phase 0 Security Remediation — Evidence Report

| Field | Value |
|---|---|
| Date | 2026-06-04 |
| Executor | Guinevere (autonomous agent) + Faiz (operator) |
| VPS | faiz-prod-01 (100.94.104.22, Ubuntu, Python 3.12.3) |
| Hermes Version | 0.15.2 (2026.5.29.2) |
| Hermes Security | 0 active advisories (CLEAN) |

## 1. What Was Done

### 1.1 guinevere-mcp Service Fix (CRITICAL — RESOLVED)

**Problem**: Service in crash-loop (exit-code 1, auto-restart infinite loop).

**Root Causes Found & Fixed**:

| # | Root Cause | Fix | Status |
|---|---|---|---|
| 1 | Missing `markdownify` package → `ModuleNotFoundError` | `pip3 install 'markdownify>=0.14'` → installed 1.2.2 | FIXED |
| 2 | Missing `playwright` package → `ModuleNotFoundError` in `obscura_cdp.py` | `pip3 install playwright` → installed 1.60.0 | FIXED |
| 3 | `InvalidSignature: Parameter _config of fs_read cannot start with '_'` | Removed `_config` param from `fs_read`, `fs_write`, `fs_delete`, `fs_list` signatures in `src/mcp/tools/filesystem.py`; functions now reference `_DEFAULT_CONFIG` module-level variable | FIXED |
| 4 | `Restart=always` with stdio transport → infinite restart loop | Changed to `Restart=on-failure` in both `/etc/systemd/system/` and `systemd/` source | FIXED |

**Verification**: MCP starts cleanly, registers 16 tools (brave_search, context7, docker×11, filesystem×4, git, grep_app, obscura_cdp, redis, sequential_thinking, shell, websearch), auth matrix verified, exits cleanly (code 0). No restart loop.

**Files Modified**:
- `/home/guinevere/code/guinevere/src/mcp/tools/filesystem.py` — removed `_config` param from 4 functions
- `/etc/systemd/system/guinevere-mcp.service` — `Restart=on-failure`, `EnvironmentFile`
- `/etc/systemd/system/guinevere-surveillance.service` — `EnvironmentFile`
- `/home/guinevere/code/guinevere/systemd/guinevere-mcp.service` — source file updated
- `/home/guinevere/code/guinevere/systemd/guinevere-surveillance.service` — source file updated

### 1.2 guinevere-surveillance Redis Auth (RESOLVED — Faiz approved 2026-06-04)

**Problem**: Service active but all Redis operations fail with `WRONGPASS invalid username-password pair`.

**Diagnosis**:
- Docker container `guinevere-redis` (Redis 7.4.9, running since 2026-05-31)
- Container started with `--requirepass 01b00faabad3164982d0dca68cedfbdc25b28d63f3604dd5ae1bf0586ce9739b`
- Both known passwords fail `redis-cli -p 6380 -a <password> ping`
- Root cause: password changed in-memory (likely `CONFIG SET requirepass`) post-start, never persisted
- SOPS-encrypted `redis-password.yaml` source file MISSING from `/home/guinevere/secrets/`

**Resolution Executed** (Faiz explicit approval received):
1. `docker restart guinevere-redis` — resets to Docker-configured password ✅
2. Updated all 5 service .env files: `.env.discord`, `.env.loops`, `.env.mcp`, `.env.scheduler`, `.env.surveillance` — changed `REDIS_PASSWORD` from `a5ed3a810ce586be8653ed5dcb5f8fc5` to `01b00faabad3164982d0dca68cedfbdc25b28d63f3604dd5ae1bf0586ce9739b` ✅
3. Restarted all Redis-dependent services: `guinevere-surveillance`, `guinevere-discord`, `guinevere-loops`, `guinevere-scheduler` ✅
4. Data preserved via AOF (`appendfsync everysec`) — no data loss ✅
5. Downtime: ~3 seconds ✅

**Verification**:
- `redis-cli -a '01b00faa...' PING` → `PONG` ✅
- `journalctl -u guinevere-surveillance` post-restart: clean logs, `consumer_started batch_size=10 poll_interval=5.0`, zero WRONGPASS errors ✅
- All 7 active services confirmed `active` via `systemctl is-active` ✅

**Status**: RESOLVED.

### 1.3 Package Upgrades

| Package | Before | After | Notes |
|---|---|---|---|
| pip | 24.0 | 26.1.2 | Upgraded |
| PyJWT | 2.12.1 | 2.12.1 | No change — hermes-agent 0.15.2 pins `PyJWT[crypto]==2.12.1` |
| markdownify | (not installed) | 1.2.2 | New dependency for MCP filesystem tools |
| playwright | (not installed) | 1.60.0 | New dependency for MCP obscura_cdp browser tool |
| hermes-agent | 0.15.2 | 0.15.2 | No change — already latest |

## 2. Service Health Matrix

| Service | Status | Notes |
|---|---|---|
| guinevere-core | active running | Health endpoint: `{"status":"healthy","version":"0.1.0"}` |
| guinevere-9router | active running | Port 20128, returns 307 redirect (normal) |
| guinevere-discord | active running | Bot operational, rituals executing |
| guinevere-loops | active running | RuntimeWarning (non-blocking) |
| guinevere-scheduler | active running | RuntimeWarning (non-blocking) |
| guinevere-monitoring | active running | Prometheus, Grafana, Loki stack |
| guinevere-mcp | inactive (dead) | Clean exit after registering 16 tools — by design (stdio transport) |
| guinevere-surveillance | active running | HEALTHY — Redis auth fixed, consumer running clean (see 1.2) |

## 3. Hermes Doctor Results

| Category | Status |
|---|---|
| Security Advisories | 0 active (CLEAN) |
| Python Environment | Python 3.12.3, venv active |
| Required Packages | All present (OpenAI SDK, Rich, python-dotenv, PyYAML, HTTPX, Croniter) |
| Directory Structure | All directories present |
| State DB | Exists (0 sessions) |
| Tools Available | 12/12 core tools operational |
| xAI Retirement | No retired models |

**Expected Warnings** (non-blocking):
- `~/.hermes/.env` not found — Guinevere uses separate config architecture
- Optional auth providers not configured (OpenRouter, Gemini, MiniMax, xAI) — uses 9Router as primary
- Optional tools missing API keys (web search, image gen, etc.) — configured per-service .env files
- `ripgrep` not installed — grep fallback used
- Venv entry point warning — hermes installed as dependency, not project

## 4. Files Changed Summary

| File | Change Type | Description |
|---|---|---|
| `src/mcp/tools/filesystem.py` | Modified | Removed `_config` parameter from 4 function signatures |
| `systemd/guinevere-mcp.service` | Modified | `Restart=on-failure`, `EnvironmentFile` directive |
| `systemd/guinevere-surveillance.service` | Modified | `EnvironmentFile` directive |
| `/etc/systemd/system/guinevere-mcp.service` | Deployed | Synced from source |
| `/etc/systemd/system/guinevere-surveillance.service` | Deployed | Synced from source |
| `.env.discord` | Modified | Updated `REDIS_PASSWORD` to correct value |
| `.env.loops` | Modified | Updated `REDIS_PASSWORD` to correct value |
| `.env.mcp` | Modified | Updated `REDIS_PASSWORD` to correct value |
| `.env.scheduler` | Modified | Updated `REDIS_PASSWORD` to correct value |
| `.env.surveillance` | Modified | Updated `REDIS_PASSWORD` to correct value |

## 5. Boundary Compliance

- No persona drift
- No consent violation
- No surveillance overreach
- No Y6 behavior
- No HARD STOP bypass
- No secrets committed to repo
- No destructive operations without approval
- No type-safety suppression (`as any`, `@ts-ignore`)
- No empty catch/except blocks introduced

## 6. Rollback Plan

### MCP Fixes
- `filesystem.py`: `git checkout src/mcp/tools/filesystem.py` to revert signature changes
- Service files: source files in `systemd/` are version-controlled; re-deploy with `systemctl daemon-reload`

### Package Upgrades
- pip: `pip install pip==24.0` to downgrade (not recommended — 24.0 has known vulnerabilities)
- markdownify/playwright: `pip uninstall markdownify playwright` if MCP tools should fail gracefully

### Redis Password Fix (EXECUTED)
- Docker restart completed successfully; AOF data preserved, no data loss
- All .env files updated with correct password
- Rollback: if needed, re-apply old password to .env files and restart services (old value was incorrect anyway)
- Container recreate: `docker-compose` or manual `docker run` with correct `--requirepass`

## 7. Open Items

| # | Item | Priority | Status |
|---|---|---|---|
| 1 | ~~Redis password reset for surveillance service~~ | ~~HIGH~~ | RESOLVED |
| 2 | Missing SOPS secrets (`redis-password.yaml`, `db-passwords.yaml`) | MEDIUM | Needs re-creation from known values |
| 3 | `setup-service-envs.sh` regeneration after Redis fix | MEDIUM | Should be updated with correct password |
| 4 | `setup_redis_exporter_acl.py` ACL user creation | LOW | Unblocked now that Redis auth works |
| 5 | RuntimeWarning in loops/scheduler (module import order) | LOW | Non-blocking, cosmetic |

## 8. Audit Trail

All changes applied via SSH to VPS (Tailscale tunnel). No changes pushed to git. Local Windows repo remains divergent from VPS state. Git sync recommended after all Phase 0 items resolved.

---

*Generated 2026-06-04 by Guinevere autonomous agent. Operator: Faiz. Last updated: 2026-06-04 — Redis auth fix completed.*
