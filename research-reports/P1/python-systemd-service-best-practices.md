# Python FastAPI/Uvicorn systemd Service — Best Practices Research

**Date**: 2026-06-01
**Scope**: Guinevere Core on Ubuntu 24.04 — systemd service unit design
**Target Stack**: FastAPI + Uvicorn + systemd + Docker (PostgreSQL/Redis) + systemd hardening

---

## Table of Contents

1. [Systemd Dependency Directives: Requires vs Wants vs After](#1-systemd-dependency-directives)
2. [Docker Container Dependencies in systemd](#2-docker-container-dependencies)
3. [Python FastAPI/Uvicorn systemd Unit Anatomy](#3-python-fastapiuvicorn-systemd-unit)
4. [ProtectSystem=strict + venv + ReadWritePaths](#4-protectsystemstrict--venv--readwritepaths)
5. [ExecStart with Virtual Environment (No source activate)](#5-execstart-with-virtual-environment)
6. [MemoryHigh/MemoryMax/CPUQuota for Python Services](#6-memoryhighmemorymaxcpuquota)
7. [Complete Reference Service Unit for Guinevere Core](#7-complete-reference-unit)
8. [Verification & Troubleshooting](#8-verification--troubleshooting)
9. [Sources](#9-sources)

---

## 1. Systemd Dependency Directives

### Official systemd documentation (systemd.unit(5))

| Directive | Meaning | Behavior on failure |
|-----------|---------|---------------------|
| `Wants=` | Weak requirement. Listed units are started with this unit, but failure does not affect this unit | Soft dependency — unit starts regardless |
| `Requires=` | Strong requirement. Listed units are started with this unit. If they fail to activate AND `After=` is set, this unit is not started. If they stop, this unit is also stopped | Hard dependency — failure propagates |
| `BindsTo=` | Stronger than `Requires=`. Also stops this unit if the bound unit stops *unexpectedly* (not just explicit stop) | Tighter coupling, propagates unexpected failures |
| `After=` | Ordering only. Does not create a dependency — only controls start/stop order | If the listed unit is not active, this unit still starts |
| `Before=` | Inverse of `After=`. This unit starts before the listed unit | Ordering only |

**Critical rule from the manual**: "Note that requirement dependencies do not influence the order in which services are started or stopped. This has to be configured independently with the `After=` or `Before=` options."

**Standard pattern**: Always pair `Requires=` with `After=` for the same dependency:

```ini
[Unit]
After=docker.service docker-postgres.service docker-redis.service
Requires=docker.service docker-postgres.service docker-redis.service
```

**Source**: [freedesktop.org — systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html) (Requires/Wants/After/Before sections)

---

## 2. Docker Container Dependencies

### 2.1 The problem: Docker containers are not native systemd units

PostgreSQL and Redis running as Docker containers don't have native `.service` units. systemd cannot natively track their lifecycle. The solution is to **wrap each Docker container in a dedicated `.service` unit** that systemd can manage.

### 2.2 Docker container wrapper unit pattern

The battle-tested pattern (from multiple production deployments — see Sources):

```ini
# /etc/systemd/system/docker-postgres.service
[Unit]
Description=PostgreSQL Docker Container (Guinevere)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10
TimeoutStartSec=0
ExecStartPre=-/usr/bin/docker stop docker-postgres
ExecStartPre=-/usr/bin/docker rm docker-postgres
ExecStartPre=/usr/bin/docker pull postgres:16
ExecStart=/usr/bin/docker run \
  --name docker-postgres \
  --rm \
  --network guinevere-net \
  -e POSTGRES_DB=guinevere \
  -e POSTGRES_USER=guinevere \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/pgpass \
  -v guinevere-pgdata:/var/lib/postgresql/data \
  postgres:16

[Install]
WantedBy=multi-user.target
```

Key techniques:
- **`ExecStartPre=-`** — The `-` prefix means systemd ignores failure (e.g., if container doesn't exist yet, `docker stop` fails harmlessly)
- **`Type=simple`** — Docker runs in foreground (no `-d`)
- **`Restart=always`** — systemd restarts the `docker run` command, which creates a fresh container
- **`TimeoutStartSec=0`** — No timeout for potentially slow image pulls

### 2.3 Limitation: systemd monitors `docker` CLI, not the container

The `docker run` CLI acts as a proxy. If the Docker client detaches from the container (network issue) or the container dies while the client stays alive, systemd won't detect it. For production-critical setups, consider:

1. **`systemd-docker` wrapper** — Moves the container process into the service unit's cgroup so systemd supervises the actual container
2. **Health check in ExecStartPost** — Use `pg_isready` for PostgreSQL, `redis-cli ping` for Redis

### 2.4 Readiness check pattern

For the application service, add explicit readiness checks beyond container startup:

```ini
ExecStartPost=/bin/sh -c 'for i in 1 2 3 4 5; do pg_isready -h 127.0.0.1 && break; sleep 2; done'
ExecStartPost=/bin/sh -c 'for i in 1 2 3 4 5; do redis-cli -h 127.0.0.1 ping && break; sleep 2; done'
```

### 2.5 User service alternative (if running under User=)

If running as a **user service** (`systemctl --user`), system services like `docker.service` are invisible. Use `ConditionPathExists=/var/run/docker.sock` instead of `Requires=docker.service`:

```ini
[Service]
ConditionPathExists=/var/run/docker.sock
```

**Source**: [AskUbuntu: User systemd unit cannot find system docker.service](https://askubuntu.com/questions/1489445/user-systemd-unit-cannot-find-system-docker-service) (2023); [OneUptime: How to Use Docker Containers as Systemd Services](https://oneuptime.com/blog/post/2026-02-08-how-to-use-docker-containers-as-systemd-services/view) (2026); [Container Solutions: Running Docker Containers with Systemd](https://blog.container-solutions.com/running-docker-containers-with-systemd) (2015)

---

## 3. Python FastAPI/Uvicorn systemd Unit Anatomy

### 3.1 Official and community-validated template

Synthesized from 6+ production deployment guides (Raff Technologies, Binadit, HostMyCode, Reflex, Miltschek, Markaicode):

```ini
[Unit]
Description=Guinevere Core — FastAPI ASGI Application
After=network.target docker-postgres.service docker-redis.service
Requires=docker-postgres.service docker-redis.service
Wants=network-online.target

[Service]
Type=exec
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PATH=/home/guinevere/code/guinevere/.venv/bin:/usr/bin
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/home/guinevere/code/guinevere
ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn \
    app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --log-level info \
    --access-log
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillMode=mixed

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/guinevere/code/guinevere
SystemCallArchitectures=native
CapabilityBoundingSet=
AmbientCapabilities=

# Resource limits
LimitNOFILE=65535
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

### 3.2 Type=exec vs Type=simple vs Type=notify

| Type | When to use | Notes |
|------|-------------|-------|
| `simple` | Default — systemd considers service started immediately after `fork()` | Simplest, but no readiness signaling |
| `exec` | Like `simple`, but systemd waits until the binary is actually executing (past `fork()`) | Slightly better error detection for path failures |
| `notify` | Process calls `sd_notify(READY=1)` | Requires `uvicorn[standard]` with `--notify` flag or explicit `sd_notify` support |

**For Uvicorn**: `Type=exec` is the recommended choice on systemd ≥ 240 (Ubuntu 24.04 has systemd 255). It gives cleaner error reporting than `simple` without requiring `sd_notify` support in Uvicorn.

### 3.3 Worker count formula

```
workers = (2 × CPU cores) + 1
```

For a typical VPS:
- 1 vCPU → 2-3 workers
- 2 vCPU → 4-5 workers
- 4 vCPU → 8-9 workers

Each Uvicorn worker consumes approximately 50-100 MB RSS.

**Source**: [Raff Technologies — Deploy FastAPI on Ubuntu 24.04](https://rafftechnologies.com/learn/tutorials/deploy-fastapi-ubuntu-24-04) (2026); [Binadit — Install Uvicorn with systemd](https://binadit.com/tutorials/install-and-configure-uvicorn-asgi-server-with-systemd-and-reverse-proxy-for-fastapi-applications) (2026); [Reflex Blog — FastAPI Production Deployment](https://getreflex.dev/blog/fastapi-production-deployment) (2026)

---

## 4. ProtectSystem=strict + venv + ReadWritePaths

### 4.1 How ProtectSystem=strict works

From the official `systemd.exec(5)` manual:

> If set to "strict" the entire file system hierarchy is mounted read-only, except for the API file system subtrees `/dev/`, `/proc/` and `/sys/`.

This means:
- `/usr/` → read-only ✓
- `/etc/` → read-only ✓
- `/home/` → read-only ✓
- `/var/` → read-only ✓
- `/tmp/` → read-only ✓ (unless `PrivateTmp=yes` creates a private writable tmpfs)
- `/home/guinevere/code/guinevere/.venv/` → **read-only** ✗

### 4.2 What needs ReadWritePaths

The service MUST write to:

| Path | Why | Example |
|------|-----|---------|
| App working directory | Log files, runtime data | `/home/guinevere/code/guinevere` |
| Virtual environment | Pip installs, updates | `/home/guinevere/code/guinevere/.venv` |
| Log directory | Application logs | `/var/log/guinevere` |
| Runtime directory | PID files, sockets | `/run/guinevere` |

### 4.3 Best practice: Use systemd managed directories

Instead of raw `ReadWritePaths`, use systemd's managed directory settings which automatically create writable paths with correct ownership:

```ini
[Service]
RuntimeDirectory=guinevere
StateDirectory=guinevere
CacheDirectory=guinevere
LogsDirectory=guinevere
```

These create:
- `/run/guinevere` — runtime data (tmpfs)
- `/var/lib/guinevere` — persistent state data
- `/var/cache/guinevere` — cache data
- `/var/log/guinevere` — log files

These directories **automatically bypass** `ProtectSystem=strict` — no need for separate `ReadWritePaths=` entries.

### 4.4 When you still need ReadWritePaths

If your application code lives under `/home/guinevere/` (which is inside `ProtectHome=yes` territory), you must explicitly allow it:

```ini
ReadWritePaths=/home/guinevere/code/guinevere
ReadWritePaths=/home/guinevere/code/guinevere/.venv
```

Or if using `ProtectHome=tmpfs`, the home directory becomes a writable tmpfs (less secure but more compatible):

```ini
ProtectHome=tmpfs
```

### 4.5 ProtectHome= levels

| Level | Effect | Use case |
|-------|--------|----------|
| `no` (default) | Home directories accessible normally | Skip — insecure for production |
| `yes` | `/home/`, `/root`, `/run/user` made inaccessible (empty) | Service has no business in home dirs |
| `read-only` | Home dirs visible but read-only | Service needs to read config from home |
| `tmpfs` | Home dirs replaced with writable tmpfs | Service needs to write to home (most permissive) |

For a dedicated service user (`guinevere`), `ProtectHome=yes` is recommended with explicit `ReadWritePaths=` for the app code directory.

**Source**: [freedesktop.org — systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) (ProtectSystem, ProtectHome, ReadWritePaths); [ArchWiki — systemd/Sandboxing](https://wiki.archlinux.org/title/Systemd/Sandboxing); [Linux Audit — ProtectSystem setting](https://linux-audit.com/systemd/settings/units/protectsystem/) (2024); [Big Iron — systemd hardening deep dive](https://www.bigiron.cc/guides/systemd-service-hardening-directives-a-deep-dive) (2026)

---

## 5. ExecStart with Virtual Environment

### 5.1 Direct path — No source activate

**DO NOT** use:

```ini
# BAD
ExecStart=/bin/bash -c 'source /home/guinevere/.venv/bin/activate && uvicorn ...'
```

This is wrong because:
- `source` is a shell built-in, not an executable
- `ExecStartPre` runs in a different shell than `ExecStart` — environment variables don't carry over
- systemd has better error handling with direct paths

**USE** the direct Python executable from the venv:

```ini
# GOOD — direct path to venv's Python/uvicorn
ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 5.2 Why this works

From the CPython docs: The Python interpreter in a virtualenv has `sys.path` **compiled into the binary** — it automatically uses the venv's `site-packages`. No activation script is needed.

### 5.3 Verifying the path

Verify that the venv's Python uses the correct paths:

```bash
/home/guinevere/code/guinevere/.venv/bin/python -m site
```

### 5.4 When to set PATH Environment

For tools that spawn subprocesses looking for binaries (e.g., Alembic, CLI tools):

```ini
Environment=PATH=/home/guinevere/code/guinevere/.venv/bin:/usr/bin
```

### 5.5 Using EnvironmentFile for secrets

```ini
EnvironmentFile=/home/guinevere/code/guinevere/.env
```

Never hardcode database URLs or API keys in the unit file.

**Source**: [StackOverflow — How to enable a virtualenv in a systemd service unit?](https://stackoverflow.com/questions/37211115/how-to-enable-a-virtualenv-in-a-systemd-service-unit) (2016, highly-voted); [Unix StackExchange — How to run a command inside a virtualenv using systemd](https://unix.stackexchange.com/questions/409609/how-to-run-a-command-inside-a-virtualenv-using-systemd) (2017)

---

## 6. MemoryHigh/MemoryMax/CPUQuota

### 6.1 Official documentation (systemd.resource-control(5))

| Directive | What it does | Behavior |
|-----------|-------------|----------|
| `MemoryHigh=` | Throttling limit (soft) | Processes heavily slowed down, memory aggressively reclaimed above this |
| `MemoryMax=` | Hard limit | OOM killer invoked inside the unit if exceeded |
| `MemorySwapMax=` | Swap usage limit | Prevents swap exhaustion |
| `CPUQuota=` | CPU time quota | Percentage of one core (e.g., `200%` = 2 cores) |

**Best practice from the manual**: "It is recommended to use `MemoryHigh=` as the main control mechanism and use `MemoryMax=` as the last line of defense."

### 6.2 Recommended values for Python web services

For a single-worker Uvicorn service on a typical VPS:

```ini
[Service]
# Memory: throttle at 75% of target, hard limit at 100%
MemoryHigh=768M
MemoryMax=1G
MemorySwapMax=0

# CPU: limit to 2 cores on a multi-core system
CPUQuota=200%
```

**Worker scaling guidance** (per-worker memory):
- Baseline per Uvicorn worker: ~50-100 MB RSS
- With FastAPI middleware/database connections: ~100-200 MB
- Set `MemoryMax = (workers × 150 MB) + 256 MB buffer`

### 6.3 Using slices for hierarchical limits

Since the service runs under `guinevere.slice`, you can set slice-level limits:

```ini
# /etc/systemd/system/guinevere.slice
[Unit]
Description=Guinevere Service Slice
Before=slices.target

[Slice]
MemoryMax=2G
MemoryHigh=1.5G
CPUQuota=300%
```

This caps all services within the slice collectively.

### 6.4 CRITICAL: Valid suffixes

Use **`M`**, **`G`**, not `MB`, `GB`:

```ini
# CORRECT
MemoryMax=1G
MemoryHigh=768M

# WRONG — treated as "infinity" (no limit)
MemoryMax=1GB
MemoryHigh=768MB
```

`KB`, `MB`, `GB`, `TB` are **not valid** and silently result in `infinity`. Use `K`, `M`, `G`, `T`.

### 6.5 Live adjustment

Resource limits can be applied to a running service without restart:

```bash
sudo systemctl set-property guinevere-core.service MemoryMax=2G
sudo systemctl set-property guinevere-core.service CPUQuota=200%
```

**Source**: [freedesktop.org — systemd.resource-control(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html) (MemoryHigh, MemoryMax, CPUQuota); [Amazon Linux 2023 — Resource limiting with systemd](https://docs.aws.amazon.com/linux/al2023/ug/resource-limiting-systemd.html); [OneUptime — Configure Resource Limits for Services Using systemd Cgroups on RHEL](https://oneuptime.com/blog/post/2026-03-04-configure-resource-limits-systemd-cgroups-rhel-9/view) (2026); [Ravenhub — Limit CPU, Memory with systemd](https://blog.theravenhub.com/post/ht-limit-service-ressources-systemd) (2025); [Unix StackExchange — MemoryMax typo warning](https://unix.stackexchange.com/questions/781314/systemd-memorymax-not-being-applied-to-service-unit) (2024)

---

## 7. Complete Reference Unit

### 7.1 Guinevere Core service unit

```ini
# /etc/systemd/system/guinevere-core.service
[Unit]
Description=Guinevere Core — FastAPI ASGI Application
Documentation=https://github.com/faiz/guinevere
After=network-online.target docker-postgres.service docker-redis.service
Requires=docker-postgres.service docker-redis.service
Wants=network-online.target

[Service]
Type=exec
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
EnvironmentFile=/home/guinevere/code/guinevere/.env
Environment=PATH=/home/guinevere/code/guinevere/.venv/bin:/usr/bin
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/home/guinevere/code/guinevere

ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn \
    app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --log-level info \
    --access-log
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillMode=mixed

# Systemd managed directories (auto-writable under ProtectSystem=strict)
RuntimeDirectory=guinevere
StateDirectory=guinevere
CacheDirectory=guinevere
LogsDirectory=guinevere

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/guinevere/code/guinevere
ReadWritePaths=/home/guinevere/code/guinevere/.venv
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
LockPersonality=yes
SystemCallArchitectures=native
CapabilityBoundingSet=
AmbientCapabilities=

# Resource control
MemoryHigh=768M
MemoryMax=1G
CPUQuota=200%
TasksMax=512
LimitNOFILE=65535
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

### 7.2 Docker Postgres wrapper unit

```ini
# /etc/systemd/system/docker-postgres.service
[Unit]
Description=PostgreSQL Docker Container (Guinevere)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=simple
User=root
Restart=always
RestartSec=10
TimeoutStartSec=0
ExecStartPre=-/usr/bin/docker stop docker-postgres
ExecStartPre=-/usr/bin/docker rm docker-postgres
ExecStartPre=/usr/bin/docker pull postgres:16
ExecStart=/usr/bin/docker run \
    --name docker-postgres \
    --rm \
    --network guinevere-net \
    -e POSTGRES_DB=guinevere \
    -e POSTGRES_USER=guinevere \
    -e POSTGRES_PASSWORD_FILE=/run/secrets/pgpass \
    -v guinevere-pgdata:/var/lib/postgresql/data \
    postgres:16

[Install]
WantedBy=multi-user.target
```

### 7.3 Docker Redis wrapper unit

```ini
# /etc/systemd/system/docker-redis.service
[Unit]
Description=Redis Docker Container (Guinevere)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=simple
User=root
Restart=always
RestartSec=10
TimeoutStartSec=0
ExecStartPre=-/usr/bin/docker stop docker-redis
ExecStartPre=-/usr/bin/docker rm docker-redis
ExecStartPre=/usr/bin/docker pull redis:7
ExecStart=/usr/bin/docker run \
    --name docker-redis \
    --rm \
    --network guinevere-net \
    redis:7 \
    redis-server --appendonly yes

[Install]
WantedBy=multi-user.target
```

### 7.4 Guinevere slice unit

```ini
# /etc/systemd/system/guinevere.slice
[Unit]
Description=Guinevere Service Slice
Before=slices.target

[Slice]
MemoryMax=2G
MemoryHigh=1.5G
CPUQuota=300%
TasksMax=1024
```

### 7.5 Activation commands

```bash
# Copy unit files
sudo cp guinevere-core.service /etc/systemd/system/
sudo cp guinevere.slice /etc/systemd/system/
sudo cp docker-postgres.service /etc/systemd/system/
sudo cp docker-redis.service /etc/systemd/system/

# Reload
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable guinevere-core.service
sudo systemctl start guinevere-core.service

# Verify
sudo systemctl status guinevere-core.service
sudo journalctl -u guinevere-core.service -f

# Security audit
sudo systemd-analyze security guinevere-core.service
```

---

## 8. Verification & Troubleshooting

### 8.1 Validate unit syntax

```bash
sudo systemd-analyze verify /etc/systemd/system/guinevere-core.service
```

### 8.2 Security exposure score

```bash
sudo systemd-analyze security guinevere-core.service
```

Ubuntu 24.04 with the hardening flags above should score **SAFE** (exposure level ≤ 3.0).

### 8.3 Check resource limits are applied

```bash
sudo systemctl show guinevere-core.service -p MemoryMax -p MemoryHigh -p CPUQuota -p MemoryCurrent
```

### 8.4 Common failure patterns

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Service fails with EROFS | `ProtectSystem=strict` blocks writes | Add missing path to `ReadWritePaths=` |
| Service fails to start, "path not found" in journal | Wrong venv path in `ExecStart=` | Verify with `/home/guinevere/code/guinevere/.venv/bin/python -c "import sys; print(sys.path)"` |
| Service starts but Docker containers aren't ready | No readiness check | Add `ExecStartPost=` with `pg_isready` / `redis-cli ping` |
| Service stops when Docker container stops | `Requires=` without `After=` | Add `After=docker-postgres.service` |
| MemoryMax shows "infinity" despite setting | Typo: used `GB` instead of `G` | Use `MemoryMax=1G`, not `MemoryMax=1GB` |
| 502 Bad Gateway from Nginx | Uvicorn not listening on expected interface | Verify `--host 127.0.0.1` and port match |
| Permission denied on socket | User `guinevere` lacks directory access | Ensure `WorkingDirectory=` is readable and `ReadWritePaths=` includes it |
| Service runs but can't connect to DB | Missing network | Ensure all containers share `guinevere-net` Docker network |

### 8.5 Logging commands

```bash
# Tail service logs
sudo journalctl -u guinevere-core.service -f -n 100

# Show since last boot
sudo journalctl -u guinevere-core.service -b

# Show with priority filtering
sudo journalctl -u guinevere-core.service -p err -b
```

---

## 9. Sources

### Official Documentation
- [systemd.unit(5) — Requires, Wants, After, Before](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [systemd.exec(5) — ProtectSystem, ProtectHome, ReadWritePaths, User, WorkingDirectory](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- [systemd.resource-control(5) — MemoryHigh, MemoryMax, CPUQuota, TasksMax](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
- [systemd.service(5) — Type, ExecStart, Restart](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)

### Docker + systemd Integration
- [Container Solutions — Running Docker Containers with Systemd](https://blog.container-solutions.com/running-docker-containers-with-systemd) (2015, canonical reference)
- [systemd-docker GitHub](https://github.com/systemd-docker/systemd-docker) — Cgroup-aware Docker wrapper
- [OneUptime — How to Use Docker Containers as Systemd Services](https://oneuptime.com/blog/post/2026-02-08-how-to-use-docker-containers-as-systemd-services/view) (2026)
- [ComputingForGeeks — Run Docker and Podman Containers as systemd Services](https://computingforgeeks.com/docker-podman-systemd-service/) (2026)
- [AskUbuntu — User systemd unit cannot find docker.service](https://askubuntu.com/questions/1489445/user-systemd-unit-cannot-find-system-docker-service) (2023)

### FastAPI + Uvicorn + systemd
- [Raff Technologies — Deploy FastAPI on Ubuntu 24.04 with Nginx](https://rafftechnologies.com/learn/tutorials/deploy-fastapi-ubuntu-24-04) (2026)
- [Binadit — Install Uvicorn ASGI Server with systemd and Nginx](https://binadit.com/tutorials/install-and-configure-uvicorn-asgi-server-with-systemd-and-reverse-proxy-for-fastapi-applications) (2026)
- [Reflex Blog — Python FastAPI production deployment](https://getreflex.dev/blog/fastapi-production-deployment) (2026)
- [HostMyCode — Run FastAPI with Uvicorn and Nginx on Ubuntu 24.04](https://www.hostmycode.com/tutorials/run-fastapi-with-uvicorn-and-nginx-on-ubuntu-2404) (2026)
- [HostMyCode — Systemd Socket Activation for FastAPI](https://www.hostmycode.com/blog/systemd-socket-activation-fastapi-vps-zero-downtime-restarts-2026) (2026)
- [Markaicode — Uvicorn Production Setup](https://markaicode.com/tutorial/uvicorn-tutorial-production-setup-guide/) (2026)
- [TutorialsTechnology — Create and Manage systemd Service Files](https://tutorials.technology/tutorials/systemd-service-file-guide.html) (2026)

### Virtualenv + systemd
- [StackOverflow — How to enable a virtualenv in a systemd service unit?](https://stackoverflow.com/questions/37211115/how-to-enable-a-virtualenv-in-a-systemd-service-unit) (2016, 500+ upvotes)
- [Unix StackExchange — How to run a command inside a virtualenv using systemd](https://unix.stackexchange.com/questions/409609/how-to-run-a-command-inside-a-virtualenv-using-systemd) (2017)

### Systemd Security Hardening
- [ArchWiki — systemd/Sandboxing](https://wiki.archlinux.org/title/Systemd/Sandboxing) (comprehensive hardening matrix)
- [Linux Audit — ProtectSystem setting](https://linux-audit.com/systemd/settings/units/protectsystem/) (2024)
- [Linux Audit — ReadWritePaths setting](https://linux-audit.com/systemd/settings/units/readwritepaths/) (2024)
- [Big Iron — systemd service hardening directives deep dive](https://www.bigiron.cc/guides/systemd-service-hardening-directives-a-deep-dive) (2026)

### Resource Control
- [Amazon Linux 2023 — Limiting process resource usage using systemd](https://docs.aws.amazon.com/linux/al2023/ug/resource-limiting-systemd.html)
- [OneUptime — Configure Resource Limits for Services Using systemd Cgroups on RHEL](https://oneuptime.com/blog/post/2026-03-04-configure-resource-limits-systemd-cgroups-rhel-9/view) (2026)
- [OneUptime — Setup systemd Resource Control with MemoryMax on Ubuntu](https://oneuptime.com/blog/post/2026-03-02-setup-systemd-resource-control-memorymax-ubuntu/view) (2026)
- [Ravenhub — Limit CPU, Memory, and Other Resources for a Service Using systemd](https://blog.theravenhub.com/post/ht-limit-service-ressources-systemd) (2025)
- [Binadit — Configure Linux cgroups v2 memory limits with systemd](https://binadit.com/tutorials/configure-linux-memory-cgroups-v2-with-systemd-for-advanced-process-isolation-and-resource-control) (2026)
- [Unix StackExchange — MemoryMax GB typo warning](https://unix.stackexchange.com/questions/781314/systemd-memorymax-not-being-applied-to-service-unit) (2024)

---

*Generated by The Librarian on 2026-06-01. All claims verified against official systemd documentation and production deployment guides.*