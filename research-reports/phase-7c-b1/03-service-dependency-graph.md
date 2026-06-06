# Service Dependency Graph — Guinevere Runtime

> **Report**: research-reports/phase-7c-b1/03-service-dependency-graph.md
> **Date**: 2026-06-06
> **Scope**: guinevere-mcp, hermes-gateway, and related Guinevere services
> **Method**: Read-only code search + VPS state inspection (from stability-check.md & prior evidence)
> **Verdict**: COMPLETE — see below

---

## 1. Service Topology — Dependency Map

Derived from `After=`, `Requires=`, and `Wants=` directives in all systemd unit files found in the repository.

```
                         ┌──────────────────────────┐
                         │  docker.service           │  (external)
                         │  guinevere-9router        │  (external, port 20128)
                         │  network.target            │  (external)
                         └──────┬───────┬────────────┘
                                │       │
                         ┌──────▼───────▼──────────┐
                         │  guinevere-core          │  ★ FOUNDATION ★
                         │  uvicorn :8000           │
                         │  Requires: docker +      │
                         │  9router                  │
                         └──┬─────┬─────┬─────┬─────┘
                            │     │     │     │
              ┌─────────────┼──┐  │  ┌──┼─────┼──────────┐
              │             │  │  │  │  │     │          │
         ┌────▼────┐  ┌─────▼──▼──▼──▼──▼──┐ ┌─▼──────────▼──┐
         │ discord │  │     loops          │ │    mcp        │
         │ bot.py  │  │  state_machine.py  │ │  FastMCP      │
         │ R:c     │  │  R:c               │ │  R:c          │
         └─────────┘  └─────────┬──────────┘ └───────────────┘
                                │
                         ┌──────▼──────┐
                         │  scheduler  │
                         │  R:loops    │
                         └─────────────┘

         ┌────────────────────────────┐
         │  surveillance              │
         │  consumer.py               │
         │  R:c + A:docker            │
         └────────────────────────────┘

         ┌────────────────────────────┐
         │  monitoring (Docker)       │
         │  Prometheus/Grafana/Loki   │
         │  R:docker  W:core          │
         └────────────────────────────┘

         ┌────────────────────────────┐
         │  obscura  CDP :9222        │
         │  A:network (standalone)    │
         └────────────────────────────┘

         ┌────────────────────────────┐
         │  hermes-gateway (Hermes)   │
         │  R:core  W:redis           │
         │  Metrics :9191             │
         └────────────────────────────┘
```

**Legend:** `R:x` = Requires x, `A:x` = After x, `W:x` = Wants x, `c` = guinevere-core

---

## 2. Service File Inventory

### 2.1 Systemd Unit File Locations

| Service | Repo Template | Deployed On VPS? | Notes |
|---|---|---|---|
| `guinevere-core` | `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` (evidence only) | ✅ YES — `/etc/systemd/system/guinevere-core.service` | **NOT in `systemd/` dir.** Only historical snapshot in evidence. |
| `guinevere-discord` | `systemd/guinevere-discord.service` | ✅ YES | Active but potentially replaced by hermes-gateway |
| `guinevere-loops` | `systemd/guinevere-loops.service` | ✅ YES | Always restart |
| `guinevere-scheduler` | `systemd/guinevere-scheduler.service` | ✅ YES | Depends on loops |
| `guinevere-mcp` | `systemd/guinevere-mcp.service` | ✅ YES | **Currently inactive/disabled** |
| `guinevere-surveillance` | `systemd/guinevere-surveillance.service` | ✅ YES | With rate-limited restart |
| `guinevere-monitoring` | `systemd/guinevere-monitoring.service` | ✅ YES | Docker Compose stack |
| `guinevere-obscura` | `systemd/guinevere-obscura.service` | ✅ YES | Standalone CDP |
| `guinevere-shadow-monitor` | `systemd/guinevere-shadow-monitor.service` | ✅ YES (user-level) | Oneshot timer |
| `hermes-gateway` | `systemd/hermes-gateway.service` (hardened) + `scripts/hermes-gateway.service` (simpler) | ✅ YES | **Two different templates exist** — see §4 |
| `guinevere-9router` | **NOT IN REPO** | ✅ YES (separately managed) | Node.js on :20128 |

### 2.2 Missing Service Files

| Service | Missing From | Impact |
|---|---|---|
| `guinevere-core.service` | `systemd/` | Repo template not versioned. Evidence copy is outdated (references `guinevere-9router.service` which may not exist on VPS). |
| `guinevere-9router.service` | Entire repo | Managed externally — no systemd template in the Guinevere repository. |

---

## 3. VPS Runtime Status (as of 2026-06-06 18:30 WIB)

From stability-check.md:

| Service | Status | Active Since | Uptime | NRestarts |
|---|---|---|---|---|
| `guinevere-mcp` | **inactive (dead)** | — | **0 (disabled)** | N/A |
| `hermes-gateway` | active (running) | 2026-06-06 12:35 | ~5h 46min | 0 |
| `guinevere-core` | active (running) | 2026-06-06 12:35 | ~5h 46min | 0 |
| `guinevere-loops` | active (running) | 2026-06-06 12:35 | ~5h 46min | 0 |
| `guinevere-surveillance` | active (running) | 2026-06-06 12:35 | ~5h 46min | 0 |
| `guinevere-scheduler` | active (running) | 2026-06-06 12:35 | ~5h 46min | 0 |
| `guinevere-9router` | active (running) | 2026-06-01 08:21 | **5+ days** | 0 |
| `guinevere-monitoring` | active (running) | 2026-06-03 10:26 | **3+ days** | 0 |
| `guinevere-obscura` | (not reported) | — | — | — |

### 3.1 guinevere-mcp — Blocker Status

**Status:** `inactive (dead)`, **`disabled`**
**Last known run:** 2026-06-04 14:17:04 (shut down cleanly)
**Restart policy:** `Restart=always` with `RestartSec=10` — but since unit is `disabled`, systemd will NOT attempt to start it automatically even on boot.
**No recent crash logs** — the service was cleanly shut down, not crashed.
**Root cause unknown from code inspection alone** — requires VPS journal inspection and manual `systemctl enable + start` to diagnose.

---

## 4. Template Discrepancies — hermes-gateway

There are **two different service templates** for hermes-gateway in the repo:

| Field | `systemd/hermes-gateway.service` (hardened) | `scripts/hermes-gateway.service` (simpler) |
|---|---|---|
| ExecStart | `hermes --config .../config.yaml gateway` | `hermes gateway run --accept-hooks` |
| EnvFile | `/home/guinevere/code/guinevere/.env.hermes` | `/home/guinevere/.hermes/.env` |
| Security | Full hardening (ProtectKernelTunables, ProtectControlGroups, RestrictSUIDSGID) | Basic hardening only |
| Resource limits | MemoryHigh=512M, MemoryMax=1G, CPUQuota=100% | Same |
| Restart | `on-failure` with StartLimitBurst=3 | `always` no burst limit |

**Which one is deployed?** VPS unit was likely generated from `scripts/hermes-gateway.service` based on the stability-check report which shows `Restart=always` pattern and env file at `/home/guinevere/.hermes/.env`.

---

## 5. Environment File Dependencies

| Service | Environment File | Contents (from setup-service-envs.sh) | SOPS-encrypted? |
|---|---|---|---|
| `guinevere-core` | `.env.core` | `GUINEVERE_9ROUTER_API_KEY` | ✅ SOPS |
| `guinevere-loops` | `.env.loops` | `REDIS_PASSWORD` | ✅ SOPS |
| `guinevere-mcp` | `.env.mcp` | `REDIS_PASSWORD` | ✅ SOPS |
| `guinevere-scheduler` | `.env.scheduler` | `REDIS_PASSWORD` | ✅ SOPS |
| `guinevere-surveillance` | `.env.surveillance` | `REDIS_PASSWORD`, `GUINEVERE_DB_PASSWORD`, `DATABASE_URL`, `SURVEILLANCE_HMAC_KEY` | ✅ SOPS |
| `guinevere-discord` | `.env.discord` | `DISCORD_BOT_TOKEN`, `GUINEVERE_9ROUTER_API_KEY` | ✅ SOPS |
| `hermes-gateway` | `.env.hermes` or `~/.hermes/.env` | `DISCORD_BOT_TOKEN`, `NINEROUTER_API_KEY`, `DISCORD_APPLICATION_ID`, `DISCORD_GUILD_ID`, `DISCORD_APPROVAL_WEBHOOK` etc. | ✅ SOPS |
| `guinevere-monitoring` | `monitoring/.env` | Grafana/Prometheus credentials | Partial |
| `guinevere-obscura` | None | — | N/A |

**NOTE:** `.env.mcp` currently contains **only** `REDIS_PASSWORD` (generated by `setup-service-envs.sh`). Additional env vars like `BRAVE_API_KEY`, `EXA_API_KEY`, `GITHUB_PAT`, and `DATABASE_URL` are referenced in MCP tool code and expected to be in `.env.mcp` but are not generated by the setup script.

---

## 6. Port Map and Collisions

| Port | Service | Protocol | Binding | Notes |
|---|---|---|---|---|
| 8000 | guinevere-core (uvicorn) | HTTP (FastAPI) | `127.0.0.1` | Health, memory, consent, auth APIs |
| 9191 | guinevere-core (llm_metrics) | HTTP (metrics) | `0.0.0.0`? | **COLLISION** — both uvicorn workers try to bind this in `src/core/services/llm_metrics.py` → non-fatal `Address already in use` errors |
| 9191 | hermes-gateway (Prometheus) | HTTP (metrics) | — | **POTENTIAL COLLISION** — same port as core metrics. Hermes config sets metrics port to 9191. |
| 9222 | guinevere-obscura | CDP (Chrome DevTools) | — | Standalone, no conflict |
| 20128 | guinevere-9router | HTTP (LLM routing) | `localhost` | Node.js, separately managed |
| 5433 | PostgreSQL | PostgreSQL | — | Custom port (not 5432), shared with Aizanta |
| 6380 | Redis | Redis | — | Non-standard port, shared with Aizanta |
| 3000 | Grafana | HTTP | — | Docker, monitoring stack |
| 9090 | Prometheus | HTTP | — | Docker, monitoring stack |
| 3100 | Loki | HTTP | — | Docker, monitoring stack |

### 6.1 Known Port Collisions

1. **9191 Core Metrics vs Uvicorn Workers (B4 — LOW):**
   - `src/core/main.py` line 45: `start_llm_metrics_server(port=9191)` fires during startup
   - With `--workers 2`, the second worker fails to bind port 9191
   - ~10 failures/minute expected, **non-fatal** — root process + first worker serve traffic normally

2. **9191 Core vs Hermes Gateway (POTENTIAL):**
   - `systemd/hermes-gateway.service` comment line 7: "Hermes Agent exposes an API gateway on port 9191 (configurable)"
   - If both `guinevere-core` (metrics server) and `hermes-gateway` (Prometheus metrics) bind 9191 simultaneously, the second will fail
   - Currently not an issue because `guinevere-mcp` is disabled (it doesn't use 9191), but core + hermes-gateway both running implies a potential conflict

---

## 7. Start Order (Bottom-Up)

```
1. docker.service                              (external, assumed running)
2. guinevere-9router                            (external, port 20128)
3. guinevere-core                               (uvicorn :8000 — FOUNDATION)
4a. guinevere-discord                           (parallel — after core)
4b. guinevere-loops                             (parallel — after core)
4c. guinevere-mcp                               (parallel — after core) ← DISABLED
4d. guinevere-surveillance                      (parallel — after core + docker)
4e. guinevere-monitoring                        (parallel — after docker, wants core)
4f. guinevere-obscura                           (parallel — standalone, only network)
4g. hermes-gateway                              (parallel — after core, wants redis)
5.  guinevere-scheduler                         (after loops)
```

---

## 8. Dependency Chain Details

### 8.1 guinevere-mcp (target service)

**Template:** `systemd/guinevere-mcp.service`
**Exec:** `.venv/bin/python -m src.mcp.manager`
**Entry point:** `src/mcp/manager.py` → `create_server()` → FastMCP instance + tool registration
**Depends on:**
- `guinevere-core.service` (Requires + After)
- `network.target` (After)
- `.env.mcp` environment file (for `REDIS_PASSWORD`)
- Python `mcp` (pip package, `mcp.server.fastmcp`) + all tool dependencies (httpx, psycopg, redis-py, etc.)
- PostgreSQL (for `postgres_tool`)
- Redis (for `redis_tool`, via `.env.mcp`)

**Ports:** No explicit port binding — FastMCP uses stdin/stdout transport by default (not HTTP server). The `FastMCP` instance doesn't open its own listening socket.

### 8.2 hermes-gateway

**Templates:** `systemd/hermes-gateway.service` (hardened) / `scripts/hermes-gateway.service` (simpler)
**Exec:** `hermes --config .../config.yaml gateway` or `hermes gateway run --accept-hooks`
**Depends on:**
- `guinevere-core.service` (Requires + After)
- `redis.service` (Wants — soft dependency)
- `network.target` (After)
- `.env.hermes` or `~/.hermes/.env` environment file
- Python `hermes-cli` (Hermes Agent package)
- 9Router at `localhost:20128` (model routing)

### 8.3 guinevere-core (foundation)

**Template:** Not in `systemd/` — only in `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`
**Exec:** `.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2`
**Depends on:**
- `docker.service` (Requires)
- `guinevere-9router` (Requires — **this service may not exist as a systemd unit**)
- `network.target`
- `.env.core` (for `GUINEVERE_9ROUTER_API_KEY`)
- PostgreSQL at `localhost:5433`
- Redis at `localhost:6380`

**Critical note:** The core service template references `Requires=guinevere-9router.service`, but this unit file does NOT exist in the Guinevere repository. If 9Router is managed outside systemd (e.g. PM2, Docker, manual start), this dependency may silently fail, though systemd allows missing `Requires` targets to not block startup.

---

## 9. Key Findings

### 9.1 BLOCKER: guinevere-mcp is disabled

- Service is `inactive (dead)` and **`disabled`** (not masked)
- Last known run: 2026-06-04 14:17:04 (clean shutdown)
- Cannot auto-start even on boot due to `disabled` state
- To restore: `sudo systemctl enable guinevere-mcp && sudo systemctl start guinevere-mcp`
- Once enabled, `Restart=always` with `RestartSec=10` will keep it running

### 9.2 Env file discrepancy for hermes-gateway

- `systemd/hermes-gateway.service` expects `.env.hermes` at `/home/guinevere/code/guinevere/.env.hermes`
- `scripts/hermes-gateway.service` expects `.env` at `/home/guinevere/.hermes/.env`
- VPS likely uses the scripts/ version based on stability-check evidence
- If deploying the `systemd/` hardened template, the env file path must be correct

### 9.3 Port 9191 collision risk

- `guinevere-core` metrics server (llm_metrics) binds port 9191
- `hermes-gateway` Prometheus metrics also targets port 9191
- Both running simultaneously → either core worker crashes or hermes fails to bind
- Currently not triggered because hermes is active and core is running with only ~10 errors/min (non-fatal)

### 9.4 guinevere-core.service not in systemd/ directory

- The core service template is only preserved as historical evidence (`docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`)
- No authoritative template in `systemd/` means the deployed version may drift without tracking

### 9.5 No service-level dependency on PostgreSQL or Redis

- Services connect to PostgreSQL and Redis via Python code, not via systemd unit dependencies
- `hermes-gateway` has `Wants=redis.service` (soft), but no service has `Requires=postgresql.service`
- If PostgreSQL or Redis goes down, services will fail at the application level (connection errors) rather than being blocked by systemd

### 9.6 Potential Restart Loop Risks

| Service | Restart Strategy | Risk |
|---|---|---|
| guinevere-core | `always`, RestartSec=10 | Protected by requiring docker + 9router |
| guinevere-loops | `always`, RestartSec=10 | Fast restart if crashes |
| guinevere-scheduler | `always`, RestartSec=10 | Depends on loops — if loops fails, scheduler can't run |
| guinevere-mcp | `always`, RestartSec=10 | Already disabled — no risk |
| guinevere-surveillance | `always`, RestartSec=10, SLB=5/300s | Rate-limited to prevent hammering |
| guinevere-monitoring | `on-failure`, SLB=3/60s | Conservative — prevents Docker restart loops |
| guinevere-obscura | `on-failure`, RestartSec=5 | Quick restart for CDP |
| hermes-gateway | `on-failure`, SLB=3/60s (hardened) or `always` (scripts) | Conservative or aggressive depending on deployed template |

### 9.7 Aizanta co-hosting constraints (from dependency-map.md)

| Resource | Allocation | Notes |
|---|---|---|
| VPS | hostdata.id 4C/16GB Ubuntu 24.04 | Shared with Aizanta |
| Cgroup cap | 8GB RAM via `guinevere.slice` | Hard limit |
| Port isolation | PostgreSQL 5433 (not 5432), Redis 6380 (not 6379) | Custom ports to avoid Aizanta conflict |
| Docker network | `guinevere-net` | Isolated from Aizanta |

---

## 10. Commands Used

All findings derived from read-only inspection:

```bash
# Repo template files
ls systemd/*.service
ls scripts/hermes-gateway.service
ls docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service

# Grep for guinevere-core references
grep -r "guinevere-core" systemd/

# Grep for env file references
grep -rn "\.env\.mcp\|\.env\.hermes\|\.env\.discord" systemd/

# Grep for port assignments
grep -rn "port.*8000\|port.*9191\|port.*9222" src/core/ src/mcp/

# Template env file contents
cat scripts/setup-service-envs.sh
```

Previous VPS inspection commands (from stability-check.md):
```bash
systemctl list-units --type=service --state=running | grep guinevere
systemctl is-active guinevere-mcp
systemctl status guinevere-mcp
journalctl -u guinevere-mcp --since "7 days ago"
```

---

## 11. Recommendations (Read-Only Findings)

1. **Restore guinevere-mcp**: `sudo systemctl enable guinevere-mcp && sudo systemctl start guinevere-mcp` — then verify it stays up with `Restart=always`
2. **Check 9191 port collision**: Verify whether `llm_metrics_server` in `src/core/main.py` and `hermes-gateway` Prometheus metrics actually conflict. If yes, reconfigure one to use a different port.
3. **Version-control guinevere-core.service**: Copy the deployed `/etc/systemd/system/guinevere-core.service` into `systemd/` to track changes.
4. **Unify hermes-gateway templates**: Decide which template (`systemd/` hardened vs `scripts/` simpler) is authoritative and remove/update the other to prevent drift.
5. **Add `.env.mcp` secrets**: The current setup script only adds `REDIS_PASSWORD` to `.env.mcp`, but MCP tools expect `BRAVE_API_KEY`, `EXA_API_KEY`, `GITHUB_PAT`, and `DATABASE_URL`. Missing these will cause tool-specific failures at runtime, not at service start.

---

*End of report — read-only findings, no modifications made.*
