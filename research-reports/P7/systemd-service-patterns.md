# P7 Systemd Service Patterns — Research Report

| Field | Value |
|---|---|
| **Phase** | P7 — Surveillance Integration |
| **Step** | P7-018: guinevere-surveillance.service |
| **Date** | 2026-06-02 |
| **Type** | Infrastructure research |
| **Status** | Complete |

---

## 1. Inventory of Service Files in Repository

### 1.1 Canonical systemd/ directory (production units)

| File | Description | Type | User |
|---|---|---|---|
| `systemd/guinevere-loops.service` | Agent Loop Daemon | `exec` (long-running) | `guinevere` |
| `systemd/guinevere-scheduler.service` | Loop Scheduler Daemon | `exec` (long-running) | `guinevere` |

### 1.2 Deploy-specific units

| File | Description | Type | User |
|---|---|---|---|
| `deploy/discord/guinevere-discord.service` | Discord Bot | `exec` (long-running) | `guinevere` |

### 1.3 Evidence/reference copies

| File | Description |
|---|---|
| `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` | Core daemon reference (deployed to VPS) |

### 1.4 Maintenance scripts (timer-based oneshot)

| File | Description | Type | User |
|---|---|---|---|
| `scripts/guinevere-backup@.service` | Restic daily backup (template) | `oneshot` | `root` |
| `scripts/guinevere-prune-weekly@.service` | Restic weekly prune (template) | `oneshot` | `root` |
| `scripts/guinevere-backup@.timer` | Timer: daily 02:00 WIB | timer | — |
| `scripts/guinevere-backup-weekly@.timer` | Timer: weekly backup | timer | — |
| `scripts/guinevere-prune-weekly@.timer` | Timer: weekly prune | timer | — |

---

## 2. Full Content: Reference Service Files

### 2.1 guinevere-loops.service (PRIMARY REFERENCE for P7-018)

`ini
# systemd/guinevere-loops.service
[Unit]
Description=Guinevere Agent Loop Daemon
After=guinevere-core.service network.target
Requires=guinevere-core.service

[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
Environment=REDIS_PASSWORD=%E/REDIS_PASSWORD
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.loops.manager
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice

# Resource limits
MemoryHigh=1G
MemoryMax=2G
CPUQuota=200%

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence

[Install]
WantedBy=multi-user.target
`

### 2.2 guinevere-scheduler.service

`ini
# systemd/guinevere-scheduler.service
[Unit]
Description=Guinevere Loop Scheduler Daemon
After=guinevere-loops.service network.target
Requires=guinevere-loops.service

[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
Environment=REDIS_PASSWORD=%E/REDIS_PASSWORD
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.loops.scheduler
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice

# Resource limits
MemoryHigh=1G
MemoryMax=2G
CPUQuota=200%

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence

[Install]
WantedBy=multi-user.target
`

### 2.3 guinevere-discord.service (deploy/discord/)

`ini
# deploy/discord/guinevere-discord.service
[Unit]
Description=Guinevere Discord Bot
After=network-online.target guinevere-core.service
Wants=network-online.target

[Service]
Type=exec
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere

# Decrypt token via SOPS before starting
ExecStartPre=/usr/bin/sops --decrypt --input-type dotenv --output-type dotenv \
  /home/guinevere/code/guinevere/secrets/.env.discord.sops \
  > /run/guinevere-discord-token
ExecStartPre=/usr/bin/chmod 600 /run/guinevere-discord-token

EnvironmentFile=/run/guinevere-discord-token
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/home/guinevere/code/guinevere

ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot

ExecStopPost=/usr/bin/shred -u /run/guinevere-discord-token

Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5

KillSignal=SIGTERM
TimeoutStopSec=30

StandardOutput=journal
StandardError=journal

# Resource limits
Slice=guinevere.slice
MemoryHigh=512M
MemoryMax=768M
CPUQuota=100%

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs

[Install]
WantedBy=multi-user.target
`

### 2.4 guinevere-core.service (evidence reference copy)

`ini
# docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service
[Unit]
Description=Guinevere Core Daemon
After=docker.service network.target guinevere-9router.service
Requires=docker.service guinevere-9router.service

[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice

# Resource limits (guinevere.slice: 8GB RAM, 200% CPU = 2 vCPU)
MemoryHigh=1G
MemoryMax=2G
CPUQuota=200%

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence

[Install]
WantedBy=multi-user.target
`

---

## 3. guinevere.slice — Cgroup Resource Limits

### 3.1 Deployed slice definition

**VPS path**: `/etc/systemd/system/guinevere.slice`
**Repo copy**: `docs/setup-evidence/P0/STEP-P0-009/guinevere-slice.conf`

`ini
[Unit]
Description=Guinevere resource control slice (8GB RAM, 2 CPU core quota) per ADR-014
Before=slices.target

[Slice]
MemoryMax=8G
MemoryHigh=7G
CPUQuota=200%
IOWeight=50
TasksMax=512
`

### 3.2 Verified cgroup v2 knobs (live from VPS)

`
memory.max:  8589934592 (8 GiB)
memory.high: 7516192768 (7 GiB)
cpu.max:     200000 100000 (200%)
io.weight:   default 50
pids.max:    512
`

### 3.3 Slice enforcement rules

- ALL `guinevere-*.service` units MUST include `Slice=guinevere.slice`
- Slice-level limits cap ALL services combined (8GB RAM, 2 CPU cores)
- Per-service limits must be <= slice limits
- ADR-014 compliance: mandatory for all Guinevere services
- Aizanta services in `system.slice` are unaffected (sibling slices)

### 3.4 Per-service resource budget (current allocation)

| Service | MemoryHigh | MemoryMax | CPUQuota | Notes |
|---|---|---|---|---|
| guinevere-core | 1G | 2G | 200% | uvicorn 2 workers |
| guinevere-loops | 1G | 2G | 200% | Agent loop manager |
| guinevere-scheduler | 1G | 2G | 200% | Loop scheduler |
| guinevere-discord | 512M | 768M | 100% | Discord.py bot |
| **guinevere-surveillance (P7-018)** | **TBD** | **TBD** | **TBD** | **Async consumer** |
| **Slice total** | **7G** | **8G** | **200%** | **ADR-014 limit** |

**Budget constraint**: Adding guinevere-surveillance must not push slice total beyond 8G/200%.
Recommended: `MemoryHigh=512M, MemoryMax=768M, CPUQuota=100%` for async consumer worker.

---

## 4. Docker Compose Infrastructure

### 4.1 docker-compose.yml (P2 Gotify)

`yaml
# docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml
services:
  gotify:
    image: gotify/server:latest
    container_name: guinevere-gotify
    restart: unless-stopped
    ports:
      - "127.0.0.1:8081:80"
    volumes:
      - /home/guinevere/data/gotify:/app/data
    environment:
      GOTIFY_DEFAULTUSER_NAME: admin
      GOTIFY_DEFAULTUSER_PASS: 
    networks:
      - guinevere-net

networks:
  guinevere-net:
    external: true
`

### 4.2 Docker containers (PostgreSQL + Redis)

PostgreSQL and Redis run as Docker containers (not systemd native).
- PostgreSQL: `127.0.0.1:5433`, bind-mount data, `guinevere-net` bridge
- Redis: `127.0.0.1:6379` (shared with Aizanta)

**Critical**: `guinevere-core.service` uses `Requires=docker.service` (NOT `postgresql.service` or `redis-guinevere.service` — those don't exist on the VPS).

---

## 5. StepPrompts P7-018 Definition (Original, Needs Correction)

`ash
# From stepprompts/StepPrompts.md L7402-7418
sudo tee /etc/systemd/system/guinevere-surveillance.service << 'EOF'
[Unit]
Description=Guinevere Surveillance Consumer
After=guinevere-core.service redis-guinevere.service postgresql.service
[Service]
Type=simple
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.surveillance.consumer
Restart=always
Slice=guinevere.slice
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now guinevere-surveillance
`

### 5.1 Issues with StepPrompts P7-018 definition

| Issue | Current | Should Be |
|---|---|---|
| `After=` | `redis-guinevere.service postgresql.service` | `docker.service network.target` (those services don't exist) |
| `Requires=` | Missing | `docker.service` or at least `guinevere-core.service` |
| `Type=` | `simple` | `exec` (catches import/venv errors) |
| `Group=` | Missing | `guinevere` |
| `Environment=` | Missing | `PYTHONPATH`, `PYTHONDONTWRITEBYTECODE`, `VIRTUAL_ENV` |
| Resource limits | Missing | `MemoryHigh/MemoryMax/CPUQuota` |
| Security hardening | Missing | `NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, `ReadWritePaths` |
| `RestartSec=` | Missing | `10` |
| `StandardOutput/Err` | Missing | `journal` |
| SOPS decrypt | Missing | `ExecStartPre` for `surveillance.env` (HMAC secrets, Redis password) |

---

## 6. Deployment Guide Surveillance Service (Production-Ready Template)

From `docs/40-operations/44-DeploymentGuide_v1.0.md` section 3.2:

`ini
# /etc/systemd/system/guinevere-surveillance.service
[Unit]
Description=Guinevere Surveillance Receiver -- FastAPI endpoints
After=network-online.target docker.service pgbouncer.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/surveillance
EnvironmentFile=-/run/guinevere/surveillance.env
ExecStartPre=/usr/bin/sops --decrypt --output /run/guinevere/surveillance.env /home/guinevere/secrets/surveillance.env.sops
ExecStart=/home/guinevere/.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000 --workers 2 --timeout-keep-alive 65 --timeout-graceful-shutdown 30 --access-log --log-level info
Restart=always
RestartSec=10
MemoryMax=512M
MemoryHigh=448M
CPUQuota=100%
TasksMax=256
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/data /run/guinevere
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=true
ProtectKernelModules=true
ProtectKernelTunables=true
ProtectControlGroups=true
PrivateDevices=true
SystemCallArchitectures=native
CapabilityBoundingSet=
AmbientCapabilities=
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-surveillance
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
`

**Note**: The Deployment Guide version is the FastAPI receiver endpoint (uvicorn), NOT the async consumer worker. P7-018 is for the **async consumer** that reads from Redis Stream/DB2 and writes to PostgreSQL/TimescaleDB.

---

## 7. Recommended guinevere-surveillance.service for P7-018

Based on established patterns from `guinevere-loops.service` and `guinevere-scheduler.service`:

`ini
[Unit]
Description=Guinevere Surveillance Async Consumer
After=guinevere-core.service docker.service network.target
Requires=guinevere-core.service

[Service]
Type=exec
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
Environment=REDIS_PASSWORD=%E/REDIS_PASSWORD
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.surveillance.consumer
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice

# Resource limits (async consumer — lighter than core/loops)
MemoryHigh=512M
MemoryMax=768M
CPUQuota=100%

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence

[Install]
WantedBy=multi-user.target
`

### 7.1 Rationale for each directive

| Directive | Value | Rationale |
|---|---|---|
| `After=` | `guinevere-core.service docker.service network.target` | Core must be up (shared venv/paths); Docker for Redis/PG |
| `Requires=` | `guinevere-core.service` | Hard dependency on core daemon |
| `Type=exec` | `exec` | Catches venv/import errors at startup (established pattern) |
| `User=` | `guinevere` | Consistent with all other Guinevere services |
| `Group=` | `guinevere` | Discord bot pattern; tighter filesystem access |
| `PYTHONPATH` | `/home/guinevere/code/guinevere` | Matches loops/scheduler/core |
| `VIRTUAL_ENV` | Set | Matches loops/scheduler/core |
| `REDIS_PASSWORD` | `%E/REDIS_PASSWORD` | Systemd credential reference; consumer reads from Redis Stream |
| `ExecStart` | `python -m src.surveillance.consumer` | Module execution per StepPrompts |
| `MemoryHigh=512M` | Soft limit | Consumer should be lightweight |
| `MemoryMax=768M` | Hard limit | Stays within 8G slice budget |
| `CPUQuota=100%` | 1 vCPU | Consumer is I/O bound (Redis reads, DB writes) |
| `Slice=` | `guinevere.slice` | Mandatory per ADR-014 |
| `ReadWritePaths` | Standard paths | Same as loops/scheduler |

### 7.2 Redis consumer group pattern

From `research-reports/P7/fastapi-hmac-patterns.md`, the consumer uses Redis Stream with consumer groups:

`python
CONSUMER_GROUP = "surveillance-processors"
CONSUMER_NAME = f"processor-{socket.gethostname()}"

async def setup_consumer_group(redis: Redis):
    try:
        await redis.xgroup_create(
            SURVEILLANCE_STREAM, CONSUMER_GROUP, id="0", mkstream=True,
        )
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
`

The consumer reads from Redis Stream (DB2) and writes to PostgreSQL/TimescaleDB.

---

## 8. Deployment Commands

`ash
# Create unit file on VPS
sudo cp systemd/guinevere-surveillance.service /etc/systemd/system/

# Verify syntax
sudo systemd-analyze verify /etc/systemd/system/guinevere-surveillance.service

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable guinevere-surveillance

# Start
sudo systemctl start guinevere-surveillance

# Verify
sudo systemctl status guinevere-surveillance
sudo systemctl show guinevere-surveillance -p Slice  # Expected: guinevere.slice
journalctl -u guinevere-surveillance -n 20 --no-pager

# Verify cgroup membership
systemctl status guinevere-surveillance
# Expected CGroup: /guinevere.slice/guinevere-surveillance.service
`

---

## 9. Key Constraints and Warnings

1. **Slice budget**: Total per-service MemoryMax must not exceed 8G. With core (2G) + loops (2G) + scheduler (2G) + discord (768M) = 6.75G used. Remaining: ~1.25G. Surveillance consumer at 768M is safe.

2. **No `redis-guinevere.service`**: This unit name from StepPrompts does NOT exist on the VPS. Redis runs in Docker. Use `docker.service` as dependency.

3. **No `postgresql.service`**: Same issue — PostgreSQL runs in Docker. Use `docker.service`.

4. **`%E/REDIS_PASSWORD`**: Systemd credential reference pattern. Requires `/etc/credstore/` or equivalent setup. If not yet configured, use `Environment=REDIS_PASSWORD=` with SOPS-encrypted EnvironmentFile instead.

5. **ExecStart module path**: `src.surveillance.consumer` — this module must exist in the codebase before deployment.

6. **ReadWritePaths**: Must include paths where the consumer writes processed data or logs.

---

## 10. Source Files Referenced

| File | Purpose |
|---|---|
| `systemd/guinevere-loops.service` | Primary reference pattern |
| `systemd/guinevere-scheduler.service` | Secondary reference pattern |
| `deploy/discord/guinevere-discord.service` | SOPS decrypt pattern, Group directive |
| `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` | Core daemon reference |
| `docs/setup-evidence/P0/STEP-P0-009/guinevere-slice.conf` | Slice definition |
| `docs/setup-evidence/P0/STEP-P0-009/verification.md` | Slice verification evidence |
| `stepprompts/StepPrompts.md` L7396-7418 | P7-018 original definition |
| `docs/40-operations/44-DeploymentGuide_v1.0.md` L1167-1214 | Deployment guide surveillance unit |
| `research-reports/P7/fastapi-hmac-patterns.md` | Redis Stream consumer pattern |
| `research-reports/P1/python-systemd-service-best-practices.md` | Systemd best practices |
| `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` | Docker compose (Gotify) |
| `docs/setup-evidence/P2/STEP-P2-017/p2-017-implementation-summary.md` | Discord bot implementation evidence |
| `scripts/guinevere-backup@.service` | Oneshot service pattern |
| `scripts/guinevere-backup@.timer` | Timer pattern |
| `adr/ADR-014-vps-container-architecture.md` | ADR for VPS/container architecture |
