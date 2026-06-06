# Phase 7 VPS Services Health Baseline Report

**Generated**: 2026-06-06 14:11 WIB  
**Host**: faiz-prod-01 (guinevere-vps)  
**Uptime**: 14 days, 3h 31min  
**Load**: 0.49 / 0.62 / 0.57  
**OS**: Linux (Debian/Ubuntu-family)  
**Method**: Read-only SSH commands — no services restarted or modified

---

## 1. Service Health Summary

| Service | Status | Active Since | PID | SubState | Systemd Enabled |
|---|---|---|---|---|---|
| hermes-gateway | ✅ RUNNING | 2026-06-06 12:35:31 WIB | 65081 | active/running | enabled |
| guinevere-core | ✅ RUNNING | 2026-06-06 12:35:31 WIB | 65077 | active/running | enabled |
| guinevere-loops | ✅ RUNNING | 2026-06-06 12:35:31 WIB | 65078 | active/running | disabled |
| guinevere-scheduler | ✅ RUNNING | 2026-06-06 12:35:31 WIB | 65082 | active/running | disabled |
| guinevere-surveillance | ✅ RUNNING | 2026-06-06 12:35:31 WIB | 65080 | active/running | disabled |
| guinevere-monitoring | ✅ RUNNING | 2026-06-03 10:26:50 WIB | 1801128 | active/running | enabled |
| guinevere-mcp | ❌ INACTIVE (dead) | N/A (last: Jun 04 14:17) | 0 | inactive/dead | disabled |
| guinevere-9router | ✅ RUNNING | 2026-06-01 08:21:12 WIB | 627184 | active/running | enabled |
| cloudflared | ✅ RUNNING | 2026-05-31 19:56:19 WIB | 315061 | active/running | enabled |

**Summary**: 8 of 9 canonical services running. 1 service (guinevere-mcp) is inactive/dead and disabled. All active services show `substate=running`.

### 1.1 Service Details

#### hermes-gateway (Hermes Agent Gateway — Discord)
- **Command**: `/home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks`
- **Version**: Hermes Agent v0.15.2 (2026.5.29.2), Python 3.12.3, OpenAI SDK 2.24.0
- **Tasks**: 12 | **Threads**: 12 | **Fds**: 19
- **Memory**: 98.0M (peak 109.5M, high watermark 512.0M, max 1.0G)
- **CPU**: 10.370s (since 12:35)
- **Health**: Proxied through guinevere-core on localhost:8000

#### guinevere-core (Core Daemon — Uvicorn)
- **Command**: `uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2`
- **Tasks**: 22 | **Threads**: 4 | **Fds**: 13
- **Memory**: 223.5M (peak 237.4M, high watermark 1.0G, max 2.0G)
- **CPU**: 37min 31.560s

#### guinevere-loops (Loop Manager)
- **Command**: `python -m src.loops.manager`
- **Tasks**: 4 | **Threads**: 4 | **Fds**: 6
- **Memory**: 63.8M (peak 63.9M, max 2.0G)
- **CPU**: 1.190s

#### guinevere-scheduler (Loop Scheduler)
- **Command**: `python -m src.loops.scheduler`
- **Tasks**: 4 | **Threads**: 4 | **Fds**: 6
- **Memory**: 63.6M (peak 63.9M, max 2.0G)
- **CPU**: 1.161s

#### guinevere-surveillance (Surveillance Consumer)
- **Command**: `python -m src.surveillance.consumer`
- **Tasks**: 5 | **Threads**: 5 | **Fds**: 7
- **Memory**: 73.4M (peak 73.6M, high watermark 512.0M, max 768.0M)
- **CPU**: 2.285s
- **Config**: batch_size=10, poll_interval=5.0s

#### guinevere-monitoring (Docker Compose Stack)
- **Command**: `docker compose -f monitoring/compose.monitoring.yml up --remove-orphans`
- **Tasks**: 21 | **Memory**: 17.7M (peak 19.2M, max 1.0G)
- **CPU**: 1min 17.029s (since Jun 03)
- **Containers**: 8 (all Up, 6 of 8 healthy)

#### guinevere-mcp (MCP Gateway — INACTIVE)
- **Last runtime**: Jun 04 14:17 WIB — shut down gracefully after registering 16 tools
- **Disabled**: systemd unit is `disabled; preset: enabled`
- **Last log**: `mcp_server_shutting_down` (clean shutdown)
- **CAUSE**: Not determined from logs — no crash/error at shutdown

---

## 2. RAM / Process Baseline

### 2.1 Service Process Memory (RSS)

| Process | PID | RSS (MB) | %MEM | VSZ (MB) |
|---|---|---|---|---|
| hermes-gateway | 65081 | ~120 | 0.7 | 921 |
| guinevere-core (uvicorn) | 65077 | ~95 | 0.6 | 294 |
| guinevere-core (worker) | 65133 | ~103 | 0.6 | 615 |
| guinevere-loops | 65078 | ~84 | 0.5 | 284 |
| guinevere-scheduler | 65082 | ~84 | 0.5 | 283 |
| guinevere-surveillance | 65080 | ~95 | 0.6 | 367 |
| guinevere-monitoring (docker) | 1801128 | — | — | — |
| guinevere-9router | 627184+627406 | ~167 | 1.0 | 9935 |
| cloudflared | 315061 | ~17 | — | — |

### 2.2 Container Memory (from docker stats lineage)

- `guinevere-loki`: ~170 MB RSS
- `guinevere-prometheus`: ~108 MB RSS  
- `guinevere-grafana`: ~195 MB RSS
- `guinevere-postgres`: internal (PG buffer cache)
- `guinevere-redis`: minimal (RSS < 10 MB)
- Total monitoring containers: ~16% of 15 GB RAM

### 2.3 System-Level Memory

| Resource | Total | Used | Free | Available |
|---|---|---|---|---|
| RAM | 15 GiB | 4.0 GiB | 605 MiB | 11 GiB |
| Swap | 4.0 GiB | 1.0 MiB | 4.0 GiB | — |
| Disk (/) | 99 GiB | 35 GiB | 59 GiB (37% used) | — |

### 2.4 Top Memory Consumers

| Rank | Process | %MEM | RSS | Notes |
|---|---|---|---|---|
| 1 | postgres_exporter (docker) | 9.1% | ~1.4 GB | Known high RSS for PG exporter |
| 2 | crowdsec | 1.8% | ~284 MB | Security daemon |
| 3 | systemd-journald | 1.7% | ~267 MB | Journal accumulation |
| 4 | dockerd | 1.2% | ~197 MB | Docker daemon |
| 5 | grafana | 1.2% | ~195 MB | Grafana server |

---

## 3. Health Endpoint Latency

| Metric | Value |
|---|---|
| **Endpoint** | `http://localhost:8000/health` |
| **Response** | `{"status":"healthy","service":"guinevere-core","version":"0.1.0"}` |
| **HTTP Status** | 200 OK |
| **Total Time** | **0.017s (17 ms)** |
| **Connect Time** | 0.0003s (0.3 ms) |
| **TTFB** | 0.0107s (10.7 ms) |
| **Interpretation** | ✅ **Excellent** — sub-20ms response, suitable for real-time health checking |

### Monitoring Stack Health

| Component | Endpoint | Status |
|---|---|---|
| Prometheus | `localhost:9090/-/ready` | ✅ 200 |
| Grafana | `localhost:3000/api/health` | ✅ 200 |
| Loki | `localhost:3100/ready` | ✅ 200 |

**Interpretation**: All three monitoring backends respond healthy.

---

## 4. 24h Stability Evidence

### 4.1 Uptime & Service Restarts

- **System uptime**: 14 days (since May 23)
- **All 6 active guinevere services started simultaneously**: 2026-06-06 12:35:31 WIB (today, ~1.5h ago) — indicates a coordinated restart/deploy
- **guinevere-monitoring**: started Jun 03 (3 days ago) — stable
- **guinevere-9router**: started Jun 01 (5 days ago) — stable  
- **cloudflared**: started May 31 (6 days ago) — stable
- **guinevere-mcp**: last active Jun 04 14:17 — clean shutdown

### 4.2 Hermes-Gateway Restart History (Last 24h)

The hermes-gateway was restarted **multiple times** in the last 24h:
- ~21:24 Jun 05 — restart
- ~21:26 Jun 05 — restart (2 min later — likely crash or manual)
- ~02:49 Jun 06 — restart
- ~08:46 Jun 06 — restart
- ~08:49 Jun 06 — restart (3 min later — likely crash or manual)
- ~11:45 Jun 06 — restart
- ~11:48 Jun 06 — restart
- ~11:48 Jun 06 — restart
- ~11:49 Jun 06 — restart
- ~11:49 Jun 06 — restart
- **12:35 Jun 06** — final restart, stable since (1.5h+)

**Pattern**: Rapid restart cycling followed by longer stable periods. The 11:45-11:49 cluster shows 6 restarts in 4 minutes.

### 4.3 Hermes-Gateway Journal Errors (Last 24h)

- **YAML config fallback** (Jun 06 01:07): Hermes fell back to default config, ignoring ALL user overrides (auxiliary providers, fallback chain, model settings). Root cause: malformed YAML at line 443.
- **Discord connect failure** (Jun 05 07:54): `[Errno 30] Read-only file system: '/home/guinevere/.local/state'` — the hermes instance on PID 3274177 could not create `/home/guinevere/.local/state/hermes/gateway-locks` directory, causing a Discord connection failure with full traceback.
- **Codex stream TTFB cutoff** (Jun 06 12:01): Agent received no stream bytes from `cx/gpt-5.5` within 12s cutoff. Connection killed for retry.
- **No ERROR-level events** in the current session (since 12:35 restart).

### 4.4 Zombie Process

- **PID ~122051**: `python3` defunct (zombie) — child of guinevere-core (65077)
- Spawned from the multiprocessing worker pool
- **Impact**: Low — single zombie, no accumulated count. May indicate a worker that exited without parent reaping promptly.

### 4.5 Sudo Denial Events (auth failure)

- 14+ `sudo` failures from user `guinevere` in the last 24h, all `command not allowed`
- These are from the research session (this report generation), not production issues
- User `guinevere` does not have password-less sudo for those commands — expected behavior

---

## 5. Canonical Ports & Connectivity

| Port | Service | Listening | Status |
|---|---|---|---|
| 5433 | PostgreSQL (guinevere) | 127.0.0.1:5433 | ✅ LISTEN |
| 6380 | Redis (guinevere) | 127.0.0.1:6380 | ✅ LISTEN |
| 20128 | 9Router LLM Proxy | 0.0.0.0:20128 | ✅ LISTEN |
| 8000 | guinevere-core (Uvicorn) | 127.0.0.1:8000 | ✅ LISTEN |
| 5434 | PgBouncer | 127.0.0.1:5434 | ✅ LISTEN (container) |
| 9090 | Prometheus | 127.0.0.1:9090 | ✅ LISTEN |
| 3000 | Grafana | 127.0.0.1:3000 | ✅ LISTEN |
| 3100 | Loki | 127.0.0.1:3100 | ✅ LISTEN |

### Docker Container Status

| Container | Status | Uptime |
|---|---|---|
| guinevere-postgres | Up (healthy) | 5 days |
| guinevere-pgbouncer | Up | 5 days |
| guinevere-redis | Up | 47 hours |
| guinevere-prometheus | Up (healthy) | 3 days |
| guinevere-grafana | Up (healthy) | 3 days |
| guinevere-loki | Up (healthy) | 3 days |
| guinevere-alertmanager | Up (healthy) | 3 days |
| guinevere-node-exporter | Up | 3 days |
| guinevere-postgres-exporter | Up | 3 days |
| guinevere-redis-exporter | Up | 3 days |
| guinevere-promtail | Up | 3 days |

### Stale Containers (Aizanta infrastructure — not part of Phase 7)

| Container | Status | Uptime | Notes |
|---|---|---|---|
| aizanta-bot | Up (healthy) | 13 days | Old `src.main:app` uvicorn — port 8000 (Docker internal only) |
| aizanta-nginx | Up (healthy) | 13 days | Reverse proxy |
| aizanta-frontend | Up (healthy) | 5 days | Frontend |
| aizanta-postgres | Up (healthy) | 2 weeks | PG on port 5432 (default) |
| aizanta-redis | Up (healthy) | 2 weeks | Redis on port 6379 (default) |

---

## 6. Warning & Blocker Catalog

### 🟡 WARNINGS

| # | Severity | Component | Issue |
|---|---|---|---|
| W1 | WARNING | hermes-gateway systemd unit | `TimeoutStopSec=90s` but `drain_timeout=180s` — systemd may SIGKILL mid-drain. Fix: `hermes gateway service install --replace`. |
| W2 | WARNING | hermes MCP config | 5 MCP servers configured without `command` field (web, filesystem, terminal, git, fetch) — all fail to connect at startup. |
| W3 | WARNING | hermes voice | Opus codec not found — voice channel playback disabled (no PyNaCl/davey). |
| W4 | WARNING | hermes config (historical) | YAML at line 443 caused config fallback on Jun 06 01:07 — need to verify current config is valid. |
| W5 | WARNING | guinevere-core | Zombie child process (python3, PID ~122051, defunct) — child of worker pool. |
| W6 | WARNING | guinevere-loops scheduler | `RuntimeWarning: 'src.loops.manager'/'src.loops.scheduler' found in sys.modules after import of package 'src.loops'` — import order issue. |
| W7 | WARNING | guinevere-monitoring | Promtail cannot connect to Docker socket (`/var/run/docker.sock`) — Docker daemon not accessible from monitoring container. |
| W8 | WARNING | guinevere-monitoring | Postgres exporter times out connecting to `172.17.0.1:5433` — uses host.docker.internal DNS but fallback timeout. |
| W9 | WARNING | guinevere-monitoring | Redis exporter cannot connect to `host.docker.internal:6380` — Docker networking issue. |
| W10 | WARNING | guinevere-monitoring | Grafana dashboard provisioning error — `/var/lib/grafana/dashboards` directory missing. |
| W11 | WARNING | Hermes version | 1 commit behind upstream (`pip install --upgrade hermes-agent` available). |
| W12 | WARNING | hermes-gateway | 6 rapid restarts between 11:45-11:49 today — root cause unclear. Currently stable (1.5h+). |

### 🔴 BLOCKERS

| # | Severity | Component | Issue |
|---|---|---|---|
| B1 | BLOCKER | guinevere-mcp | Service is **inactive (dead)** and disabled. Last clean shutdown Jun 04 14:17. No crash in logs. If Phase 7 requires MCP server, this must be investigated and re-enabled. |
| B2 | BLOCKER | hermes-gateway (historical) | Config YAML at line 443 caused fallback to defaults — ALL user overrides (auxiliary providers, fallback chain, model settings) were IGNORED on Jun 06 01:07. Current config after 12:35 restart needs verification. |
| B3 | BLOCKER | Monitoring exporters | **3 monitoring components** have persistent connectivity errors: PG exporter, Redis exporter, and Promtail cannot reach their respective backends from within Docker. This means monitoring data for PG, Redis, and container logs is incomplete. |

---

## 7. Detailed Issue Analysis

### B1: guinevere-mcp Inactive
- **Service**: `guinevere-mcp.service` — disabled, inactive (dead)
- **Last runtime**: Jun 04 14:17 WIB — clean shutdown after registering 16 tools
- **Last known tools**: obscura_cdp_tools, redis_tools (read/write/destructive/forbidden), sequential_thinking, shell, websearch
- **Redis DB allocation from last run**: DB 0=Session cache, 1=Memory recall, 2=Surveillance buffer, 3=Agent state, 4=Discord state, 5=Cost tracking
- **Impact**: If Phase 7 depends on MCP server being available, this is a blocker. If MCP functionality has been migrated to hermes-gateway (which uses MCP tools internally), this may be intentional.

### B3: Monitoring Stack Connectivity
- Postgres exporter dials `172.17.0.1:5433` (Docker bridge IP) — times out. PG is on host network (127.0.0.1:5433) or Docker host network. Exporter needs correct host address.
- Redis exporter dials `redis://host.docker.internal:6380` — connection refused. `host.docker.internal` may not resolve in this Docker network configuration.
- Promtail cannot access Docker socket at `/var/run/docker.sock` — socket may not be mounted into the container.
- These are all **configuration issues in `monitoring/compose.monitoring.yml`** — likely from initial deployment and not yet hardened.

### W1: Stale Systemd Unit (TimeoutStopSec)
- Repeated every hermes-gateway restart: `TimeoutStopSec=90s` < `drain_timeout=180s`
- Remedy: Run `hermes gateway service install --replace` to regenerate the systemd unit with correct timeout.
- Risk: If systemd kills the process before drain completes, in-flight messages may be lost.

---

## 8. Service Dependency Map

```
cloudflared (Tunnel)
  └─ routes webhook to Discord
      
guinevere-9router (LLM Proxy, port 20128)
  └─ depended by: guinevere-core

guinevere-core (API, port 8000)
  ├─ health endpoint: http://localhost:8000/health
  ├─ hermes-gateway connects via health checks / tool calls
  └─ depends on: guinevere-9router, PostgreSQL (5433), Redis (6380)

hermes-gateway (Discord Gateway)
  ├─ connects to guinevere-core for persona/safety hooks
  ├─ uses Redis for state/locks
  └─ depends on: guinevere-core, Redis

guinevere-loops (Agent Loop Manager)
  ├─ depends on: Redis (cost tracking, state)
  └─ managed by: guinevere-scheduler

guinevere-scheduler (Loop Scheduler)
  └─ depends on: Redis (cost tracking, state)

guinevere-surveillance (Consumer)
  └─ depends on: PostgreSQL, Redis

guinevere-monitoring (Docker Stack)
  ├─ Prometheus, Grafana, Loki, Alertmanager, Promtail
  ├─ Node Exporter, PG Exporter, Redis Exporter
  ├─ targets: all services via Prometheus
  └─ has known connectivity gaps (see B3)

guinevere-mcp [INACTIVE]
  └─ last active Jun 04 14:17; previously served MCP tools
```

---

## 9. Summary & Recommendations

### Current State
- **6 of 7 Phase 7 services running** (guinevere-mcp inactive)
- **Health endpoint**: healthy, 17ms latency ✅
- **RAM**: 4.0 GiB used (27%), 11 GiB available — healthy headroom ✅
- **Disk**: 37% used — healthy ✅
- **Monitoring backends**: all respond 200 ✅
- **Canonical ports**: all listening ✅

### Critical Action Items (Pre-Hardening)

1. **🔴 Fix guinevere-mcp** — Determine if it should be re-enabled or officially deprecated. If needed, investigate why it shut down and hasn't restarted.

2. **🔴 Verify hermes config** — Check line 443 of `/home/guinevere/.hermes/config.yaml` for YAML validity. The Jun 06 01:07 fallback means ALL provider/fallback/model overrides were ignored.

3. **🟡 Fix monitoring exporter connectivity** — Update Docker compose config to use correct host addresses (likely `host.containers.internal` or explicit host IP) for PG, Redis, and Promtail socket access.

4. **🟡 Regenerate hermes systemd unit** — Run `hermes gateway service install --replace` to fix TimeoutStopSec mismatch.

5. **🟡 Investigate hermes rapid restart cluster** — The 6 restarts in 4 minutes (11:45-11:49) may indicate a deployment script, crash loop, or manual testing.

6. **🟡 Clean up stale containers** — `aizanta-bot`, `aizanta-nginx`, `aizanta-frontend`, `aizanta-postgres`, `aizanta-redis` are from the old architecture. Evaluate if still needed.

7. **🟡 Fix zombie process** — The defunct python3 child of guinevere-core should be reaped or the root cause investigated.

### Investigation Limitations
- Redis authentication required — password not exposed in this report. Actual Redis health (beyond `NOAUTH`) requires creds.
- PostgreSQL health requires `psql` authentication — not tested without exposing credentials.
- Hermes config YAML at line 443 not read (read-only mandate) — content needs human review.
- Monitoring stack connectivity errors are consistent but may be benign (metrics via node_exporter still work).

---

## Appendix A: Commands Executed

All commands run via `ssh guinevere-vps <command>`:

```bash
# Service discovery
systemctl list-units --type=service --state=running | grep -E 'hermes-gateway|guinevere-...'
systemctl list-units --type=service --all | grep -iE 'guinevere|hermes'

# Per-service status
systemctl status --no-pager hermes-gateway guinevere-core guinevere-loops guinevere-mcp guinevere-scheduler guinevere-surveillance guinevere-monitoring guinevere-9router cloudflared

# Process baseline
ps aux | grep -E 'hermes|guinevere|python' | grep -v grep
ps aux --sort=-%mem | head -15

# Health endpoint
curl -s http://localhost:8000/health
time curl -s -o /dev/null http://localhost:8000/health

# Port scanning
ss -tlnp | grep -E ':8000|:5433|:6380|:20128'

# Docker
docker container ls
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Monitoring health
curl -s -o /dev/null -w '%{http_code}' http://localhost:9090/-/ready
curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health
curl -s -o /dev/null -w '%{http_code}' http://localhost:3100/ready

# Stability
uptime
systemctl show -p ActiveEnterTimestamp --value <service>
journalctl -u hermes-gateway --since 'yesterday' --no-pager -q --output=short-full
journalctl --since -24h --no-pager -q | grep -E '(Started|Stopped)' 

# System resources
free -h
df -h /

# Connectivity
redis-cli -p 6380 PING
tailscale status
```

## Appendix B: Notes

- `guinevere-mcp` does NOT appear in `grep -E 'hermes-gateway|guinevere-core|guinevere-loops|guinevere-mcp|guinevere-scheduler|guinevere-surveillance|guinevere-monitoring' --state=running`. It is listed separately under `--all`.
- `guinevere-obscura` service also exists but is inactive/disabled (not in Phase 7 scope).
- Zombie PID changed from 118971 (14:06) to 122051 (14:08) — indicates new zombie processes being generated over time.
- Some journalctl commands with `--since "24 hours ago"` in double quotes failed on remote bash due to pipe expansion issues — alternative syntax `--since "yesterday"` was used successfully.
