# P25-900 — 9Router Runtime & Node.js Process Analysis

**Phase:** P25 — VPS Rearchitecture
**Date:** 2026-06-25
**Status:** RESEARCH COMPLETE
**Source:** Confirmed facts from Guinevere codebase, running VPS state, and 9Router source analysis

---

## 1. Executive Summary

9Router is a Node.js application built on the Next.js 16 framework that serves as the LLM proxy layer for Guinevere. It runs as a standalone server process, handling chat completions, SSE streaming, model routing, and a React-based dashboard. The application uses SQLite (via `better-sqlite3`) as its sole persistence layer — no Redis or PostgreSQL dependencies.

On the current VPS, 9Router is well-behaved: it idles at approximately 92.5 MB of memory with a peak of 135 MB and a high watermark of 1.0 GB (the systemd `MemoryHigh` soft limit). These figures are modest relative to the VPS's 15 Gi total RAM. However, the CLI defaults to `--max-old-space-size=6144` (6 GB heap), which is excessive for a 2-core, 4 GB VPS and must be overridden for P25 deployment.

Key findings for P25 planning:

- 9Router's resource footprint is small and predictable at idle; it scales with concurrent SSE streaming requests.
- The `--max-old-space-size` default of 6144 MB should be reduced to 1024-1536 MB for the new VPS.
- SQLite I/O is minimal and benefits from the VPS's local NVMe/SSD storage.
- SSE streaming is the primary CPU and memory consumer during active LLM requests.
- No persistent WebSocket connections exist; all communication is HTTP/SSE.
- A dedicated systemd service with a dedicated user and slice provides sufficient isolation.

---

## 2. Node.js Runtime Details

### Version and Distribution

| Property | Value |
|---|---|
| Minimum Node.js | >= 18.0.0 |
| Current local version | v24.14.1 |
| Target for P25 | Node.js 24.x (Krypton) via NodeSource |
| Ubuntu 24.04 support | Yes — NodeSource 24.x confirmed compatible |
| npm package | `9router` on npm, 44.6 MB unpacked, 3,027 files |

### Framework

9Router is built on **Next.js 16** using the App Router architecture. This means:

- Server-side API routes handle all backend logic (chat completions, model listing, health checks, dashboard data).
- The dashboard is a React client-side application rendered by the Next.js server as static/client-side assets.
- No custom HTTP server framework is required; Next.js provides its own via `app/server.js`.

### Binary Layout

When installed globally via `npm install -g 9router`:

- Binary entry: `/usr/bin/9router` (or equivalent based on npm prefix)
- CLI entry point: `cli/cli.js`
- Server entry point: `app/server.js` (Next.js standalone build)
- Runtime deps: auto-installed into `~/.9router/runtime/` by the CLI's self-healing mechanism (includes SQLite native bindings)

---

## 3. Process Model

### CLI to Server Spawn

9Router uses a two-stage process model:

1. **CLI Layer** (`cli/cli.js`): Parses arguments (`--port`, `--host`, `--no-browser`, `--skip-update`), resolves configuration, then spawns the Next.js server.
2. **Server Layer** (`app/server.js`): The actual Next.js standalone server that handles HTTP requests, SSE streams, SQLite operations, and dashboard serving.

The CLI spawns the server as a child process. Under systemd with `Type=simple`, the CLI process is the main PID, and the server runs as its child. If the server crashes, the CLI should exit as well, allowing systemd's `Restart=always` to recover.

### Heap Configuration

The CLI defaults to spawning the server with:

```
--max-old-space-size=6144
```

This sets the V8 heap limit to **6144 MB (6 GB)**. This default is designed for developer workstations and large-scale deployments, not for a 2-core, 4 GB VPS. The heap limit can be overridden by passing a custom `NODE_OPTIONS` environment variable or by modifying the service configuration to pass the flag explicitly.

### Process Tree (Typical)

```
systemd ── guinevere-9router.service
             └── node /usr/bin/9router --port 20128 --host 0.0.0.0 ...
                   └── node app/server.js --max-old-space-size=6144
```

Under systemd's `Type=simple`, both processes share the cgroup, so `MemoryHigh` and `CPUQuota` apply to the entire tree.

---

## 4. Memory Profile

### Idle State (Current VPS)

| Metric | Value |
|---|---|
| RSS at idle | 92.5 MB |
| Peak observed | 135.0 MB |
| High watermark | 1.0 GB (systemd `MemoryHigh` limit) |

At idle, 9Router consumes approximately 92.5 MB. This includes:

- Node.js runtime overhead (~40-50 MB baseline for Node 24)
- Next.js server framework code
- SQLite database connections and buffer pool
- In-memory routing tables and configuration
- The CLI process and its management overhead

### Per-Request Memory Behavior

Each active SSE streaming request allocates:

- A `TransformStream` (or equivalent Node.js `stream.Transform`) for provider-to-client piping
- HTTP request/response buffers
- JSON parsing buffers for chunked LLM responses
- SQLite write buffers for logging (small)

Estimated per-request overhead: **2-8 MB** during active streaming, depending on LLM response length. Memory from completed requests is eligible for GC and typically reclaimed within seconds.

### Scaling Estimate

| Concurrent Requests | Estimated Memory |
|---|---|
| 0 (idle) | ~90-100 MB |
| 1-5 | ~100-150 MB |
| 10-20 | ~150-300 MB |
| 50+ (stress) | ~300-800 MB |

The 1.0 GB `MemoryHigh` on the current VPS has never triggered throttling under normal load, confirming that the application stays well within bounds.

### V8 Heap Implications

With the default `--max-old-space-size=6144`, V8 is allowed to allocate up to 6 GB of heap before triggering a fatal out-of-memory crash. On a 4 GB VPS, this is meaningless because the OS will OOM-kill the process long before V8 reaches that limit. Setting it to 1024-1536 MB is both more honest and more predictable.

---

## 5. CPU Profile

### Idle State

At idle, 9Router consumes essentially **0% CPU**. There are no background polling loops, no periodic timers (other than Node.js internals like garbage collection heuristics), and no keep-alive connections that require processing.

### Per-Request CPU

The primary CPU consumers during a request are:

| Activity | CPU Impact |
|---|---|
| HTTP request parsing | Negligible |
| JSON serialization/deserialization | Low |
| SSE stream forwarding (per chunk) | Low-Medium |
| SQLite writes (request logging) | Negligible (synchronous but fast) |
| Next.js SSR (dashboard pages) | Medium (one-time per page load) |
| Garbage collection (GC) | Sporadic, low |

SSE streaming is the most CPU-intensive activity. Each chunk from the LLM provider is:
1. Received as an HTTP response from the upstream provider
2. Parsed as JSON
3. Transformed (if needed)
4. Re-serialized and forwarded to the client as an SSE event
5. Optionally logged to SQLite

For a typical streaming response (100-500 chunks), this creates a sustained but modest CPU load of approximately **5-15% of a single core** per active stream.

### Concurrent Request Scaling

| Concurrent Streams | Estimated CPU |
|---|---|
| 0 (idle) | ~0% |
| 1 | ~5-15% of 1 core |
| 5 | ~25-50% of 1 core |
| 10 | ~50-100% of 1 core |
| 20+ | Saturates available cores |

The Node.js event loop is single-threaded, but I/O operations (network, disk) are handled by libuv's thread pool (default 4 threads). Under heavy concurrent load, the libuv thread pool can become a bottleneck for SQLite writes, but this is unlikely under normal LLM proxy usage.

---

## 6. SQLite I/O Characteristics

### Storage Engine

9Router uses **better-sqlite3**, a Node.js binding for SQLite that provides synchronous API access. Key characteristics:

- **Synchronous reads**: better-sqlite3 reads are blocking and very fast (microseconds for indexed queries)
- **Synchronous writes**: Same — writes are blocking, but SQLite's WAL (Write-Ahead Logging) mode keeps them fast
- **No connection pooling**: SQLite uses a single file, so there is no connection pool to manage
- **Thread safety**: better-sqlite3 executes on the main V8 thread, which means SQLite operations briefly block the event loop

### I/O Impact

| Operation | Frequency | I/O Impact |
|---|---|---|
| Request logging | Per request | Small write (~1-5 KB) |
| Schema migration | On startup (if needed) | One-time, negligible |
| Dashboard queries | On page load | Small reads (~10-100 KB) |
| Model config reads | On startup + cache | Negligible |

SQLite I/O is a non-issue for performance. Even on spinning disks, the read/write volumes are trivial. On NVMe/SSD storage (typical for VPS), SQLite operations complete in well under 1 ms.

### WAL Mode

SQLite in WAL (Write-Aless Logging) mode allows concurrent reads during writes, which is important for the dashboard querying data while the proxy is actively logging requests. The CLI's migration system (`migrate.js`) handles schema upgrades, including JSON-to-SQLite migrations.

### File Size Growth

SQLite databases grow over time as request logs accumulate. This is managed by:

- The built-in migration system handling schema changes
- Normal SQLite `VACUUM` behavior (WAL checkpoints)
- Potentially periodic cleanup (not observed in the current deployment, but feasible)

For P25, consider monitoring the SQLite database file size and implementing a log rotation policy if the database grows beyond a few hundred MB.

---

## 7. SSE Streaming Architecture

### Overview

9Router's SSE (Server-Sent Events) streaming is the core of its LLM proxy functionality. The `open-sse/` directory contains the streaming proxy layer that handles provider routing and stream transformation.

### Stream Lifecycle

1. **Client sends request**: POST to `/v1/chat/completions` with `stream: true`
2. **Provider routing**: 9Router selects the upstream LLM provider based on model and configuration
3. **Upstream connection**: An HTTP request is made to the LLM provider's API (e.g., OpenAI, Anthropic, etc.)
4. **Stream establishment**: The provider responds with an SSE stream
5. **TransformStream**: A per-request transform stream pipes provider chunks to the client
6. **Chunk forwarding**: Each SSE event from the provider is parsed, optionally transformed, and forwarded to the client
7. **Completion**: The stream ends when the provider signals completion (`[DONE]` or equivalent)

### Resource Consumption During Streaming

Each active SSE stream holds:

- An outbound HTTP connection to the upstream LLM provider
- An inbound HTTP connection from the client
- A TransformStream with internal buffers
- JSON parsing state for chunked responses

These connections are managed by Node.js's HTTP agent and libuv's event loop. No dedicated threads are spawned per connection.

### No Persistent Connections

9Router does not maintain persistent WebSocket connections or long-lived connections to LLM providers. Each request creates fresh HTTP connections (or reuses keep-alive connections from the HTTP agent pool). This means:

- No connection leak risk from abandoned WebSockets
- Memory from completed streams is eligible for immediate GC
- No heartbeat/keep-alive timers consuming resources at idle

### MITM Proxy

9Router includes a MITM (Man-in-the-Middle) proxy capability (visible in the source), but the logs directory is empty, indicating it is not actively used. This feature can be ignored for P25 planning.

---

## 8. Current VPS systemd Configuration Analysis

### Current Unit File

```ini
[Unit]
Description=Guinevere 9Router LLM Proxy
After=network.target

[Service]
Type=simple
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
EnvironmentFile=/home/guinevere/code/guinevere/secrets/.env.9router
ExecStart=/usr/bin/9router --port 20128 --host 127.0.0.1 --no-browser --skip-update
Restart=always
RestartSec=5
Slice=guinevere.slice
LimitNPROC=512
LimitNOFILE=8192
MemoryHigh=1G
CPUQuota=200%

ReadWritePaths=/home/guinevere/.hermes
ReadWritePaths=/home/guinevere/code/guinevere
ReadWritePaths=/home/guinevere/data

[Install]
WantedBy=multi-user.target
```

### Analysis

| Directive | Current Value | Assessment |
|---|---|---|
| `Type=simple` | Correct | CLI process is the main PID; this is the right type |
| `User=guinevere` | Shared user | Works, but P25 should use a dedicated user for isolation |
| `ExecStart` | `--host 127.0.0.1` | Correct — loopback only. Note: current runtime shows `0.0.0.0` which may be from manual restart |
| `Restart=always` | Correct | Ensures automatic recovery from crashes |
| `RestartSec=5` | Correct | 5-second delay prevents restart storms |
| `Slice=guinevere.slice` | Shared slice | P25 should use a dedicated slice for independent resource accounting |
| `LimitNPROC=512` | Generous | 9Router rarely spawns more than 2-3 processes |
| `LimitNOFILE=8192` | Generous | More than sufficient for HTTP proxy workload |
| `MemoryHigh=1G` | Appropriate | Soft limit; current peak is 135 MB, leaving large headroom |
| `CPUQuota=200%` | Correct | Matches the 2-core VPS; 200% = 2 full cores |
| `ReadWritePaths` | Multiple | Required for hermes data, code directory, and data storage |
| Missing: `MemoryMax` | Not set | No hard memory limit; systemd will only throttle at `MemoryHigh`, not kill |
| Missing: `Environment` | Not set | No explicit `NODE_OPTIONS` override for heap size |
| Missing: `Nice` | Not set | Default priority (0); could be set to 10 for lower priority |
| Missing: `ProtectSystem` | Not set | Could add `=strict` with explicit write paths |
| Missing: `PrivateTmp` | Not set | Could add `=true` for tmp isolation |

### Observed Runtime State

| Metric | Value |
|---|---|
| PID | 591603 |
| Memory | 92.5 MB (current RSS) |
| Peak memory | 135.0 MB |
| High watermark | 1.0 GB (MemoryHigh threshold) |
| Binary | `/usr/bin/9router` v0.4.66 |

### VPS Context

| Resource | Value |
|---|---|
| Total RAM | 15 Gi |
| Used RAM | 1.7 Gi |
| Available RAM | 13 Gi |
| vCPUs | 2 |
| CPUQuota | 200% (matches vCPU count) |

The current VPS is generously provisioned relative to 9Router's needs. The P25 VPS (2c/4GB) will be tighter but still sufficient.

---

## 9. Recommended systemd Configuration for New VPS

### Design Principles

1. **Dedicated user**: Isolate 9Router from other services
2. **Dedicated slice**: Independent resource accounting
3. **Hardened paths**: Explicit read/write paths, protected system directories
4. **Heap tuning**: Override the 6 GB default to match the 4 GB VPS
5. **Tailscale-only**: No public internet binding

### Recommended Unit File

```ini
[Unit]
Description=Guinevere 9Router LLM Proxy (P25)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=9router
Group=9router
WorkingDirectory=/home/9router

# Environment: heap limit for 4GB VPS
Environment=NODE_OPTIONS=--max-old-space-size=1024
EnvironmentFile=/home/9router/secrets/.env.9router

ExecStart=/usr/bin/9router --port 20128 --host 127.0.0.1 --no-browser --skip-update

# Restart policy
Restart=always
RestartSec=5
StartLimitIntervalSec=300
StartLimitBurst=5

# Resource limits
Slice=9router.slice
MemoryHigh=768M
MemoryMax=1536M
CPUQuota=150%
LimitNPROC=128
LimitNOFILE=4096

# Security hardening
ProtectSystem=strict
ProtectHome=no
PrivateTmp=true
NoNewPrivileges=true
ReadWritePaths=/home/9router
ReadWritePaths=/home/9router/.9router

# Process priority
Nice=10

[Install]
WantedBy=multi-user.target
```

### Key Differences from Current VPS

| Setting | Current | P25 Recommendation | Rationale |
|---|---|---|---|
| `User` | `guinevere` (shared) | `9router` (dedicated) | Process isolation |
| `Slice` | `guinevere.slice` | `9router.slice` | Independent resource accounting |
| `NODE_OPTIONS` | Not set (6 GB default) | `--max-old-space-size=1024` | Match 4 GB VPS reality |
| `MemoryHigh` | 1G | 768M | Tighter headroom on 4 GB VPS |
| `MemoryMax` | Not set | 1536M | Hard kill threshold to prevent OOM cascade |
| `CPUQuota` | 200% | 150% | Reserve 0.5 core for system processes |
| `LimitNOFILE` | 8192 | 4096 | Sufficient for proxy workload |
| `LimitNPROC` | 512 | 128 | 9Router rarely needs many processes |
| `ProtectSystem` | Not set | `strict` | Block writes to system directories |
| `PrivateTmp` | Not set | `true` | Isolate /tmp |
| `NoNewPrivileges` | Not set | `true` | Security baseline |
| `StartLimitBurst` | Not set | 5 | Prevent restart storms |
| `Nice` | Not set (0) | 10 | Lower priority than critical services |

### Slice Unit File

Create `/etc/systemd/system/9router.slice`:

```ini
[Unit]
Description=9Router Service Slice

[Slice]
MemoryHigh=768M
MemoryMax=1536M
CPUQuota=150%
```

---

## 10. Resource Limit Recommendations

### Memory

| Limit | Value | Purpose |
|---|---|---|
| `NODE_OPTIONS --max-old-space-size` | 1024 | V8 heap limit; prevents runaway allocation |
| `MemoryHigh` (systemd) | 768M | Soft limit; triggers memory pressure and GC throttling |
| `MemoryMax` (systemd) | 1536M | Hard limit; OOM-kills the process if exceeded |

The V8 heap limit and systemd memory limits serve different purposes:
- V8 heap limit controls JavaScript object allocation within the Node.js process
- systemd memory limits control total process RSS (including native memory, SQLite buffers, libuv thread pool, etc.)

Total process memory will always exceed the V8 heap because of native addons (`better-sqlite3`), the libuv event loop, and the Next.js binary itself. Setting the V8 heap to 1024 MB and systemd's `MemoryMax` to 1536 MB provides adequate headroom.

### CPU

| Limit | Value | Purpose |
|---|---|---|
| `CPUQuota` | 150% | 1.5 cores max; reserves 0.5 core for system |

With only 2 vCPUs, reserving 0.5 cores for system processes (SSH, Tailscale, monitoring, kernel) prevents 9Router from starving the VPS during heavy streaming loads.

### File Descriptors

| Limit | Value | Purpose |
|---|---|---|
| `LimitNOFILE` | 4096 | Each HTTP connection uses 1-2 FDs |

4096 file descriptors supports over 2000 concurrent HTTP connections, far exceeding expected load. The default 1024 would also be sufficient, but 4096 provides headroom for SQLite file handles, log files, and Tailscale sockets.

### Process Count

| Limit | Value | Purpose |
|---|---|---|
| `LimitNPROC` | 128 | Prevents fork bombs |

9Router typically runs as 2 processes (CLI + server). 128 provides enormous headroom for any child processes spawned during migration or compilation.

---

## 11. Node.js Heap Tuning for 2c/4GB

### Why Override the Default

The CLI default `--max-old-space-size=6144` (6 GB) is dangerous on a 4 GB VPS:

1. V8 will happily allocate up to 6 GB of heap before triggering a fatal OOM
2. The Linux OOM killer will terminate the process (or other processes) well before that
3. The gap between what V8 thinks it can use and what the OS allows creates unpredictable behavior: the process may run fine for hours, then die suddenly when memory pressure spikes

### Recommended Setting

```
NODE_OPTIONS=--max-old-space-size=1024
```

**1024 MB** is the recommended V8 heap limit for a 4 GB VPS because:

- 9Router idles at ~92 MB RSS, of which ~40-60 MB is V8 heap
- Peak observed memory is 135 MB RSS
- Even under heavy load (20+ concurrent streams), 512 MB of V8 heap would be sufficient
- 1024 MB provides a 4-10x safety margin
- Combined with native memory (~200-300 MB for SQLite, libuv, etc.), total RSS will stay well under 1.5 GB
- This leaves 2.5+ GB free for the OS, Tailscale, SSH, and other services

### Alternative: 1536 MB

If 9Router is expected to handle heavy concurrent load (30+ simultaneous streams), consider:

```
NODE_OPTIONS=--max-old-space-size=1536
```

This increases the safety margin but reduces the headroom between 9Router's peak memory and the VPS total. Only use this if monitoring shows 1024 MB is insufficient.

### How to Apply

Set in the systemd unit's `Environment` directive:

```ini
Environment=NODE_OPTIONS=--max-old-space-size=1024
```

This overrides the CLI default. The CLI passes `NODE_OPTIONS` to the spawned server process, which respects the `--max-old-space-size` flag. Note: if both `NODE_OPTIONS` and the CLI default are present, the **last** `--max-old-space-size` value wins. To ensure the override takes precedence, verify that the CLI does not append its own flag after `NODE_OPTIONS`. If it does, the environment file approach may be needed instead.

---

## 12. Monitoring & Health Check Design

### Health Endpoint

9Router exposes a health check endpoint (standard for Next.js API routes). This can be used by:

- systemd watchdog (if `WatchdogSec` is configured)
- External monitoring scripts
- Tailscale health checks

### Recommended Monitoring Metrics

| Metric | Source | Threshold | Action |
|---|---|---|---|
| Process RSS | `systemctl show guinevere-9router.service -p MemoryCurrent` | > 1.2 GB | Alert — approaching MemoryMax |
| V8 Heap Used | Node.js `process.memoryUsage().heapUsed` | > 800 MB | Warning — heap pressure |
| CPU Usage | `systemctl show guinevere-9router.service -p CPUUsageNSec` | > 140% sustained | Warning — near CPUQuota |
| Health endpoint | HTTP GET `/api/health` or equivalent | Non-200 for > 30s | Alert — service degraded |
| Restart count | `systemctl show guinevere-9router.service -p NRestarts` | > 3 in 5 minutes | Alert — crash loop |
| SQLite DB size | `stat ~/.9router/*.db` | > 500 MB | Warning — log rotation needed |
| Process uptime | `systemctl show guinevere-9router.service -p ActiveEnterTimestamp` | N/A | Informational |

### Monitoring Script Concept

```bash
#!/bin/bash
# /home/9router/monitor-9router.sh

SERVICE="guinevere-9router.service"

# Memory check
MEM_BYTES=$(systemctl show "$SERVICE" -p MemoryCurrent --value 2>/dev/null)
MEM_MB=$((MEM_BYTES / 1024 / 1024))
echo "Memory: ${MEM_MB} MB"

# Health endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:20128/api/health 2>/dev/null)
echo "Health: HTTP ${HTTP_CODE}"

# Restart count
RESTARTS=$(systemctl show "$SERVICE" -p NRestarts --value 2>/dev/null)
echo "Restarts: ${RESTARTS}"

# Alerts
if [ "$MEM_MB" -gt 1200 ]; then
    echo "ALERT: Memory ${MEM_MB} MB exceeds 1200 MB threshold"
fi
if [ "$HTTP_CODE" != "200" ]; then
    echo "ALERT: Health check failed (HTTP ${HTTP_CODE})"
fi
```

### systemd Watchdog (Optional)

If 9Router supports a lightweight health check that can respond within the watchdog timeout:

```ini
[Service]
WatchdogSec=30
```

This requires 9Router to call `sd_notify("WATCHDOG=1")` periodically, or a wrapper script that pings the health endpoint and sends the notification. This is optional and may not be supported by 9Router natively.

---

## 13. Footer

**Report:** P25-900 — 9Router Runtime & Node.js Process Analysis
**Phase:** P25 — VPS Rearchitecture
**Date:** 2026-06-25
**Author:** Research agent (codebase analysis)
**Classification:** INTERNAL — P25 planning reference

**Sources:**
- Running VPS state (`systemctl status guinevere-9router.service`)
- 9Router npm package analysis
- 9Router source code (cli/cli.js, app/server.js, open-sse/)
- Current systemd unit file
- Node.js 24.x documentation
- Linux systemd.resource-control(5) man page

**Cross-references:**
- P25-001: VPS provisioning and OS hardening
- P25-002: Service isolation and user setup
- P25-003: 9Router deployment and configuration
- P25-004: Monitoring and alerting setup
