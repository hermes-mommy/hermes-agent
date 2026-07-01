# P25 — systemd Service Design for Dedicated VPS 9Router

**Date**: 2026-06-25  
**Status**: COMPLETE  
**Scope**: P25 Research — systemd service design for new VPS 9Router  
**Reference**: Existing guinevere-9router.service (Hermes VPS), Node.js systemd patterns (P1 research)

---

## 1. Executive Summary

The new VPS 9Router will run as a systemd service (`nine-router.service`) under a dedicated user (`nine-router`), with its own resource slice (`nine-router.slice`), isolated from the existing Hermes production services. The service uses security hardening directives (ProtectSystem, NoNewPrivileges, etc.) and resource controls (MemoryHigh, CPUQuota) appropriate for a 2c/4GB VPS. Node.js heap is tuned to 2 GB via `NODE_OPTIONS`.

---

## 2. User & Directory Design

### 2.1 Dedicated User

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin nine-router
```

| Property | Value | Rationale |
|---|---|---|
| **Username** | `nine-router` | NOT `guinevere` — isolation from Hermes |
| **Type** | System user (--system) | No login shell needed |
| **Home** | None (--no-create-home) | Data lives in /var/lib/9router |
| **Shell** | /usr/sbin/nologin | No interactive login |

### 2.2 Directory Layout

```
/var/lib/9router/          # DATA_DIR — owned by nine-router:nine-router
├── db/
│   ├── data.sqlite        # Main SQLite database (migrated from local)
│   └── backups/           # Auto-generated backups
├── jwt-secret             # JWT signing secret (migrated)
├── machine-id             # Machine identity (migrated)
└── logs/                  # Runtime logs (if enabled)

/etc/9router/
└── env                    # Environment file (chmod 640, root:nine-router)

/usr/bin/9router           # npm global binary (NodeSource install)
/usr/lib/node_modules/9router/  # npm global package
```

### 2.3 Directory Creation

```bash
sudo mkdir -p /var/lib/9router/db/backups
sudo chown -R nine-router:nine-router /var/lib/9router
sudo chmod 755 /var/lib/9router
sudo chmod 755 /var/lib/9router/db

sudo mkdir -p /etc/9router
sudo chown root:nine-router /etc/9router
sudo chmod 750 /etc/9router
```

---

## 3. Complete systemd Unit File

### 3.1 nine-router.service

```ini
# /etc/systemd/system/nine-router.service
[Unit]
Description=9Router LLM Proxy (P25 — Coding Traffic)
Documentation=https://github.com/decolua/9router
After=network-online.target tailscaled.service
Wants=network-online.target tailscaled.service
RequiresMountsFor=/var/lib/9router

[Service]
Type=simple
User=nine-router
Group=nine-router
WorkingDirectory=/var/lib/9router
EnvironmentFile=/etc/9router/env
Environment=NODE_ENV=production
Environment=NODE_OPTIONS=--max-old-space-size=2048
ExecStart=/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
ExecStartPost=/bin/bash -c 'for i in {1..30}; do curl -sf http://localhost:20128/api/health && exit 0; sleep 1; done; exit 1'
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

# ── Resource Control ──────────────────────────────────
Slice=nine-router.slice
MemoryHigh=3G
MemoryMax=3.5G
CPUQuota=200%
LimitNOFILE=16384
LimitNPROC=256
TasksMax=256

# ── Security Hardening ────────────────────────────────
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/9router /tmp
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# ── Logging ───────────────────────────────────────────
StandardOutput=journal
StandardError=journal
SyslogIdentifier=9router-p25

[Install]
WantedBy=multi-user.target
```

### 3.2 Directive-by-Directive Rationale

| Directive | Value | Why |
|---|---|---|
| **Type** | simple | 9Router runs in foreground. No forking. |
| **User/Group** | nine-router | Dedicated non-root user. Isolated from guinevere. |
| **WorkingDirectory** | /var/lib/9router | DATA_DIR. 9Router resolves relative paths here. |
| **EnvironmentFile** | /etc/9router/env | Secrets in a separate file, chmod 640. |
| **NODE_ENV** | production | Disables dev-mode features, optimizes Next.js. |
| **NODE_OPTIONS** | --max-old-space-size=2048 | CRITICAL: caps V8 heap at 2 GB (not default 6 GB). |
| **ExecStart** | 9router CLI | Uses the CLI wrapper which handles auto-healing. |
| **--host 0.0.0.0** | Bind all interfaces | Needed for Tailscale access. UFW restricts to tailscale0. |
| **--no-browser** | No browser | VPS has no display. |
| **--skip-update** | No auto-update | Controlled upgrades via apt/npm. |
| **ExecStartPost** | Health check loop | Waits up to 30s for /api/health before systemd marks "started". |
| **Restart** | always | Auto-restart on any exit (crash, OOM, etc.). |
| **RestartSec** | 5 | 5-second cooldown between restarts. |
| **StartLimitBurst** | 3 | Give up after 3 rapid failures. |
| **MemoryHigh** | 3G | Soft limit — process gets throttled (not killed) when RSS exceeds this. |
| **MemoryMax** | 3.5G | Hard limit — process is OOM-killed if RSS exceeds this. |
| **CPUQuota** | 200% | 2 vCPUs max. |
| **LimitNOFILE** | 16384 | 2000 concurrent connections × 2 sockets + overhead. |
| **LimitNPROC** | 256 | Single process, minimal threads. |
| **NoNewPrivileges** | yes | Prevents privilege escalation via setuid/setgid. |
| **ProtectSystem** | strict | /usr and /etc are read-only to the process. |
| **ProtectHome** | yes | /home, /root, /run/user are inaccessible. |
| **ReadWritePaths** | /var/lib/9router /tmp | Only these paths are writable. |
| **PrivateTmp** | yes | Process gets its own private /tmp namespace. |
| **PrivateDevices** | yes | Minimal /dev (only /dev/null, /dev/zero, etc.). |
| **RestrictAddressFamilies** | AF_INET AF_INET6 AF_UNIX | Only allow TCP/IP + Unix sockets. No raw sockets, netlink, etc. |
| **SystemCallFilter** | @system-service | Whitelist of safe syscalls. |

---

## 4. Slice Definition

### 4.1 nine-router.slice

```ini
# /etc/systemd/system/nine-router.slice
[Unit]
Description=9Router resource control slice (P25 coding traffic)
Before=slices.target

[Slice]
MemoryMax=4G
MemoryHigh=3.5G
CPUQuota=200%
TasksMax=256
```

### 4.2 Why a Dedicated Slice

- **Isolation**: nine-router.slice is separate from guinevere.slice (Hermes services)
- **Resource accounting**: All 9Router processes are in one cgroup for monitoring
- **Hard limits**: The slice enforces MemoryMax even if the service unit doesn't

---

## 5. Environment File Design

### 5.1 /etc/9router/env

```bash
# /etc/9router/env
# chmod 640, owned by root:nine-router
# Generated during P25 migration — contains secrets

DATA_DIR=/var/lib/9router
PORT=20128
HOSTNAME=0.0.0.0
JWT_SECRET=<generated-or-migrated>
INITIAL_PASSWORD=<set-during-migration>
REQUIRE_API_KEY=false
ENABLE_REQUEST_LOGS=false
```

### 5.2 Security

```bash
sudo chown root:nine-router /etc/9router/env
sudo chmod 640 /etc/9router/env
```

- Only root and nine-router can read the env file
- Secrets are NOT in the systemd unit file (which is world-readable)
- The file is in /etc (not /var/lib/9router), so it's covered by ProtectSystem=strict

### 5.3 Environment Variables

| Variable | Value | Required | Notes |
|---|---|---|---|
| `DATA_DIR` | /var/lib/9router | Yes | Overrides default ~/.9router |
| `PORT` | 20128 | No | Default is 20128 anyway |
| `HOSTNAME` | 0.0.0.0 | No | Bind all interfaces |
| `JWT_SECRET` | (migrated or generated) | Yes | Preserve from local 9Router for dashboard continuity |
| `INITIAL_PASSWORD` | (set during migration) | Yes | Dashboard login |
| `REQUIRE_API_KEY` | false | No | Tailscale is the auth layer |
| `ENABLE_REQUEST_LOGS` | false | No | Enable for debugging, disable for production |
| `NODE_OPTIONS` | (set in systemd unit) | Yes | `--max-old-space-size=2048` |

---

## 6. Resource Control Rationale

### 6.1 Memory: 3G / 3.5G

- 4 GB total VPS RAM
- 1 GB reserved for OS (kernel, systemd, Tailscale, SSH, file cache)
- 3 GB for 9Router (Node.js heap + native memory)
- MemoryHigh=3G: early warning — process gets throttled but not killed
- MemoryMax=3.5G: hard ceiling — process killed if exceeded (prevents system-wide OOM)

### 6.2 CPU: 200%

- 2 vCPUs max
- 9Router is I/O-bound, not CPU-bound
- 200% is generous — actual usage is expected < 20%

### 6.3 File Descriptors: 16384

- Each HTTP connection uses 1-2 FDs
- 1000 concurrent × 2 (client + provider) = 2000 FDs
- 16384 provides 8x headroom
- Default Linux limit is 1024 (too low)

### 6.4 Processes: 256

- 9Router is a single Node.js process
- 256 is generous (allows for child processes, npm operations, etc.)

---

## 7. Security Hardening Explained

### 7.1 Why Each Directive

| Directive | What It Does | Attack It Prevents |
|---|---|---|
| **NoNewPrivileges=yes** | Blocks setuid, setgid, capset | Privilege escalation |
| **ProtectSystem=strict** | /usr and /etc read-only | Tampering with binaries or config |
| **ProtectHome=yes** | /home, /root inaccessible | Reading other users' data |
| **ReadWritePaths=** | Only these paths writable | Writing anywhere else on disk |
| **PrivateTmp=yes** | Isolated /tmp | Temp file race conditions |
| **PrivateDevices=yes** | Minimal /dev | Access to raw disk devices |
| **ProtectKernelTunables=yes** | /proc/sys read-only | Changing kernel parameters |
| **ProtectKernelModules=yes** | Can't load kernel modules | Rootkit installation |
| **ProtectControlGroups=yes** | Can't modify cgroups | Breaking out of resource limits |
| **RestrictAddressFamilies=** | Only TCP + Unix sockets | Raw socket attacks, netlink exploits |
| **SystemCallFilter=@system-service** | ~250 safe syscalls allowed | Syscall-based exploits |

### 7.2 What These DON'T Protect Against

- **Provider API key theft**: If someone gains root on the VPS, they can read `/var/lib/9router/db/data.sqlite`. systemd hardening doesn't protect against root compromise.
- **Tailscale compromise**: If someone gains access to your tailnet, they can reach the 9Router. Tailscale auth is the primary network security layer.

---

## 8. Node.js Heap Tuning

### 8.1 The Problem

The 9Router CLI spawns the server with `--max-old-space-size=6144` (6 GB). On a 4 GB VPS, this would:
1. Cause the V8 heap to grow until it consumes all available RAM
2. Trigger the Linux OOM killer
3. Kill the 9Router process

### 8.2 The Fix

```ini
Environment=NODE_OPTIONS=--max-old-space-size=2048
```

This caps the V8 old-space heap at 2 GB, leaving 2 GB for:
- OS kernel (~200 MB)
- File system cache (~500 MB — caches the 1.5 GB SQLite database)
- Native memory (better-sqlite3, libuv buffers) (~200 MB)
- Headroom (~1 GB)

### 8.3 Alternative: Direct Node Exec

If `NODE_OPTIONS` doesn't work with the 9Router CLI wrapper:

```ini
ExecStart=/usr/bin/node --max-old-space-size=2048 /usr/lib/node_modules/9router/app/server.js
Environment=PORT=20128
Environment=HOSTNAME=0.0.0.0
```

This bypasses the CLI wrapper and directly runs the server, losing auto-healing.

---

## 9. Health Check Design

### 9.1 ExecStartPost (Startup Health Check)

```bash
ExecStartPost=/bin/bash -c 'for i in {1..30}; do curl -sf http://localhost:20128/api/health && exit 0; sleep 1; done; exit 1'
```

- Waits up to 30 seconds for `/api/health` to return 200
- If it never responds, systemd marks the service as failed
- StartLimitBurst=3 means 3 failures → systemd stops trying

### 9.2 Optional: Timer-Based Health Check

```ini
# /etc/systemd/system/nine-router-healthcheck.service
[Unit]
Description=9Router Health Check

[Service]
Type=oneshot
ExecStart=/usr/bin/curl -sf http://localhost:20128/api/health

# /etc/systemd/system/nine-router-healthcheck.timer
[Unit]
Description=9Router Health Check Timer

[Timer]
OnUnitActiveSec=60s

[Install]
WantedBy=timers.target
```

### 9.3 Manual Health Check

```bash
# Check service status
systemctl status nine-router.service

# Check health endpoint
curl http://localhost:20128/api/health

# Check resource usage
systemctl show nine-router.service | grep -E 'MemoryCurrent|CPUUsage|NFileDescriptor'

# View recent logs
journalctl -u nine-router.service --since "5 minutes ago"
```

---

## 10. Startup Sequence

### 10.1 Dependency Chain

```
network-online.target
    └── tailscaled.service (Tailscale must be running)
        └── nine-router.service (9Router starts after Tailscale)
```

### 10.2 Startup Commands

```bash
# After installing the unit file:
sudo systemctl daemon-reload
sudo systemctl enable nine-router.service
sudo systemctl start nine-router.service

# Check status:
sudo systemctl status nine-router.service
# Should show: active (running)

# Follow logs:
sudo journalctl -u nine-router.service -f
```

### 10.3 Lifecycle Commands

```bash
sudo systemctl start nine-router.service     # Start
sudo systemctl stop nine-router.service      # Stop
sudo systemctl restart nine-router.service   # Restart
sudo systemctl reload nine-router.service    # Not supported (no HUP handler)
sudo systemctl status nine-router.service    # Status
sudo systemctl enable nine-router.service    # Auto-start on boot
sudo systemctl disable nine-router.service   # Disable auto-start
```

---

## 11. Monitoring & Logging

### 11.1 Log Access

```bash
# Follow live logs
journalctl -u nine-router.service -f

# Last 100 lines
journalctl -u nine-router.service -n 100

# Since a specific time
journalctl -u nine-router.service --since "2026-06-25 10:00:00"

# Errors only
journalctl -u nine-router.service -p err

# With syslog identifier
journalctl -t 9router-p25
```

### 11.2 Resource Monitoring

```bash
# Current memory usage
systemctl show nine-router.service -p MemoryCurrent

# Current CPU usage
systemctl show nine-router.service -p CPUUsageNSec

# File descriptor count
ls /proc/$(systemctl show nine-router.service -p MainPID --value)/fd | wc -l

# Check for OOM kills
dmesg | grep -i "nine-router" | grep -i "out of memory"
```

---

## 12. Comparison with Existing Hermes VPS Service

| Directive | Hermes VPS (guinevere-9router) | P25 VPS (nine-router) | Change Reason |
|---|---|---|---|
| **User** | guinevere | nine-router | Isolation |
| **Slice** | guinevere.slice | nine-router.slice | Isolation |
| **--host** | 127.0.0.1 | 0.0.0.0 | Tailscale access |
| **MemoryHigh** | 1G | 3G | Higher load target |
| **LimitNOFILE** | 8192 | 16384 | Higher connection count |
| **LimitNPROC** | 512 | 256 | Single process, lower is safer |
| **NODE_OPTIONS** | Not set | --max-old-space-size=2048 | Heap tuning for 4 GB |
| **ReadWritePaths** | /home/guinevere/.hermes, /home/guinevere/code/guinevere, /home/guinevere/data | /var/lib/9router, /tmp | Different data directory |
| **WorkingDirectory** | /home/guinevere/code/guinevere | /var/lib/9router | Different data directory |
| **EnvironmentFile** | secrets/.env.9router | /etc/9router/env | Standard location for system services |
| **ExecStartPost** | None | Health check loop | Reliability |
| **Security hardening** | Basic | Full (NoNewPrivileges, ProtectSystem, etc.) | Defense in depth |

---

## 13. Migration Steps (Service Setup)

```bash
# 1. Create user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin nine-router

# 2. Create directories
sudo mkdir -p /var/lib/9router/db/backups
sudo mkdir -p /etc/9router
sudo chown -R nine-router:nine-router /var/lib/9router
sudo chown root:nine-router /etc/9router
sudo chmod 750 /etc/9router

# 3. Create env file (after copying data.sqlite)
sudo tee /etc/9router/env > /dev/null << 'EOF'
DATA_DIR=/var/lib/9router
PORT=20128
HOSTNAME=0.0.0.0
JWT_SECRET=<from-local-jwt-secret>
INITIAL_PASSWORD=<set-secure-password>
REQUIRE_API_KEY=false
ENABLE_REQUEST_LOGS=false
EOF
sudo chown root:nine-router /etc/9router/env
sudo chmod 640 /etc/9router/env

# 4. Install slice
sudo tee /etc/systemd/system/nine-router.slice > /dev/null << 'EOF'
[Unit]
Description=9Router resource control slice (P25 coding traffic)
Before=slices.target

[Slice]
MemoryMax=4G
MemoryHigh=3.5G
CPUQuota=200%
TasksMax=256
EOF

# 5. Install service unit
sudo tee /etc/systemd/system/nine-router.service > /dev/null << 'EOF'
[Unit]
Description=9Router LLM Proxy (P25 — Coding Traffic)
Documentation=https://github.com/decolua/9router
After=network-online.target tailscaled.service
Wants=network-online.target tailscaled.service
RequiresMountsFor=/var/lib/9router

[Service]
Type=simple
User=nine-router
Group=nine-router
WorkingDirectory=/var/lib/9router
EnvironmentFile=/etc/9router/env
Environment=NODE_ENV=production
Environment=NODE_OPTIONS=--max-old-space-size=2048
ExecStart=/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
ExecStartPost=/bin/bash -c 'for i in {1..30}; do curl -sf http://localhost:20128/api/health && exit 0; sleep 1; done; exit 1'
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

Slice=nine-router.slice
MemoryHigh=3G
MemoryMax=3.5G
CPUQuota=200%
LimitNOFILE=16384
LimitNPROC=256
TasksMax=256

NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/9router /tmp
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

StandardOutput=journal
StandardError=journal
SyslogIdentifier=9router-p25

[Install]
WantedBy=multi-user.target
EOF

# 6. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable nine-router.service
sudo systemctl start nine-router.service

# 7. Verify
sudo systemctl status nine-router.service
curl http://localhost:20128/api/health
```

---

## 14. Verification Commands

```bash
# Service status
systemctl status nine-router.service
# Should show: Active: active (running)

# Health check
curl http://localhost:20128/api/health
# → {"ok":true}

# Model listing
curl http://localhost:20128/v1/models | jq '.data | length'
# → 24 (or whatever count)

# Check port binding
ss -tlnp | grep 20128
# Should show: 0.0.0.0:20128 (not 127.0.0.1)

# Check process ownership
ps aux | grep 9router
# Should show: nine-router (not guinevere, not root)

# Check cgroup
cat /proc/$(pgrep -f "9router")/cgroup
# Should show: nine-router.slice/nine-router.service

# Check resource limits
cat /proc/$(pgrep -f "9router")/limits | grep -E "open files|processes"
# Should show: Max open files = 16384, Max processes = 256

# Check file descriptors
ls /proc/$(pgrep -f "9router")/fd | wc -l
# Should be < 100 at idle

# Check memory
systemctl show nine-router.service -p MemoryCurrent
```

---

## 15. Footer

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-06-25 | P25 Research | systemd service design. No files modified. Based on existing guinevere-9router.service patterns and Node.js production best practices. |