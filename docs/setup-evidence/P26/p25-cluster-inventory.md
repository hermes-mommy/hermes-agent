# P26: 9Router Cluster Mode — Inventory

**Date**: 2026-06-26  
**Purpose**: Current state snapshot before cluster-mode change

---

## 1. VPS Hardware

| Metric | Value |
|---|---|
| CPU | 2 cores (OpenVZ shared) |
| RAM | 3.9GB total, 276MB used, 3.7GB available |
| Disk | 50GB, ~44GB free |
| OS | Linux 6.8.0, Virtuozzo container |
| Network | venet0 (OpenVZ), tailscale0 (userspace-networking) |

## 2. 9Router Runtime

| Metric | Value |
|---|---|
| Version | 0.5.8 (source build from decolua/9router) |
| Workers | 1 (PID 22306, next-server) |
| Port | 20128 (0.0.0.0:20128) |
| Process manager | systemd (Type=simple) |
| WorkingDir | /root/9router/.next/standalone |
| Entry point | /usr/bin/node custom-server.js |
| Heap | NODE_OPTIONS=--max-old-space-size=3584 (3.5GB) |
| Build | /root/9router/ (full source) |

## 3. Systemd Service

```
[Unit]
Description=9Router LLM Proxy
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/9router/.next/standalone
Environment="NODE_ENV=production"
Environment="NODE_OPTIONS=--max-old-space-size=3584"
ExecStart=/usr/bin/node custom-server.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 4. SQLite Database

| Metric | Value |
|---|---|
| File | /var/lib/9router/db/data.sqlite |
| Size | 896KB |
| Tables | 11 |
| journal_mode | WAL |
| synchronous | 2 (NORMAL) |
| busy_timeout | 5000ms (per-connection, applied by schema) |
| cache_size | 64MB (per-connection, applied by schema) |
| Adapter | better-sqlite3 (native, confirmed in node_modules) |

## 5. 9Router .env

```
DATA_DIR=/var/lib/9router
HOSTNAME=0.0.0.0
PORT=20128
JWT_SECRET=<64-char hex>
API_KEY_SECRET=<64-char hex>
REQUIRE_API_KEY=true
STORAGE_ENCRYPTION_KEY=<64-char hex>
OMNIROUTE_ALLOW_PRIVATE_PROVIDER_URLS=true
```

## 6. Apache Status

| Metric | Value |
|---|---|
| Status | ACTIVE |
| Processes | 2 (apache2) |
| RSS | ~10MB total |
| Port | 80 |
| Purpose | Unknown (no deployed apps) |
| Impact | Wastes ~10MB RAM |

## 7. Multi-Worker Safety Analysis

### Stateless Operations (SAFE)
- API key validation: HMAC-SHA256 + SQLite read (per-request)
- LLM proxying: stateless HTTP forward
- Model listing: SQLite read-only query
- SSE streaming: per-connection, no shared state

### Potentially Problematic
- **Usage logging**: writes to usageHistory/usageDaily (WAL mode handles concurrent writes)
- **Migration on startup**: per-adapter WeakSet guard (one-time, safe)
- **WAL checkpoint**: 60s timer per worker (redundant but harmless)
- **SQLite write contention**: SQLITE_BUSY possible on high write load, busy_timeout=5000ms handles it

### CRITICAL: Must Use better-sqlite3
- sql.js (WASM fallback) shares memory across workers → data loss risk
- VPS currently uses better-sqlite3 (native) → confirmed safe

## 8. Network

| Rule | Interface | Action |
|---|---|---|
| ACCEPT | tailscale0 | dport 20128 |
| DROP | venet0 | dport 20128 |

Tailscale IP: 100.104.210.75  
Public IP: 49.12.82.34 (port 20128 BLOCKED)

## 9. Client Endpoints

| Client | File | URL |
|---|---|---|
| OpenCode | ~/.config/opencode/opencode.json | http://100.104.210.75:20128/v1 |
| Claude Code | ~/.claude/settings.json | http://100.104.210.75:20128/v1 |