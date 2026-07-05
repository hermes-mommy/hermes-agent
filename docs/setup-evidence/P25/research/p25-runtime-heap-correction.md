# P25 Runtime Heap Correction: 9Router v0.5.4 Heap Control Mechanism

> **Document type**: Research correction (previous P25 heap claims invalidated by source inspection)
> **Date**: 2026-06-26
> **Author**: P25 research agent
> **Status**: CORRECTIVE -- supersedes prior heap sections in P25 research notes

---

## 1. Executive Summary

Previous P25 research claimed that `NODE_OPTIONS=--max-old-space-size=2048` could control 9Router's V8 heap size. **This is wrong.** Source inspection of `cli.js` reveals that 9Router v0.5.4 spawns a child Node.js process with an explicit `--max-old-space-size` flag hardcoded to 12,288 MB (12 GB) by default. Per Node.js precedence rules, explicit command-line flags override `NODE_OPTIONS`, making the env var approach ineffective.

The correct mechanism is the `NINEROUTER_NODE_HEAP_MB` environment variable, which `cli.js` reads before spawning the child. Without setting this on a 2c/4 GB VPS, 9Router will attempt to allocate 12 GB of heap and be immediately OOM-killed.

**Action required**: All P25 migration documentation and systemd unit files must use `NINEROUTER_NODE_HEAP_MB`, not `NODE_OPTIONS`, for heap control.

---

## 2. The Heap Control Mechanism (Full Source Trace)

### 2.1 Runtime binary selection (cli.js line 137)

```javascript
const RUNTIME = process.execPath;
```

This resolves to the Node.js binary that is running `cli.js` itself. The child server process uses the same binary.

### 2.2 Heap size resolution (cli.js line 558)

```javascript
const SERVER_HEAP_MB = Number.parseInt(process.env.NINEROUTER_NODE_HEAP_MB || "12288", 10);
```

`cli.js` reads `NINEROUTER_NODE_HEAP_MB` from the environment. If unset or empty, it defaults to `"12288"` (12 GB). The value is parsed as an integer.

**Key point**: This variable is consumed by the *parent* process (cli.js). It never reaches the child process environment.

### 2.3 Child process spawn (cli.js line 578)

```javascript
const child = spawn(RUNTIME, [`--max-old-space-size=${SERVER_HEAP_MB}`, serverPath], {
  cwd: standaloneDir,
  stdio: showLog ? "inherit" : ["ignore", "ignore", "pipe"],
  detached: true,
  windowsHide: true,
  env: {
    ...buildEnvWithRuntime(process.env),
    PORT: port.toString(),
    HOSTNAME: host
  }
});
```

The resolved `SERVER_HEAP_MB` value is baked into the spawn arguments array as `--max-old-space-size=<value>`. This is a direct V8 flag passed to the child's argv, not an environment variable.

### 2.4 The child environment

The child process receives a **custom** environment, not the full parent environment:

```javascript
env: {
  ...buildEnvWithRuntime(process.env),
  PORT: port.toString(),
  HOSTNAME: host
}
```

`buildEnvWithRuntime` adds `NODE_PATH` to include SQLite runtime modules and copies a subset of the parent env. However, this is irrelevant to heap control -- the heap is controlled by the explicit argv flag, not by any environment variable in the child.

---

## 3. Why NODE_OPTIONS is Insufficient

### 3.1 Node.js precedence rules

From the official Node.js documentation:

> "Command-line options passed to the node binary take precedence over options specified in NODE_OPTIONS."

### 3.2 What happens with NODE_OPTIONS

If an operator sets `NODE_OPTIONS=--max-old-space-size=2048`, the child process sees:

```
argv:  [node, --max-old-space-size=12288, server.js]
env:   NODE_OPTIONS=--max-old-space-size=2048
```

V8 resolves the heap size by processing all sources and taking the explicit command-line flag. The result is **12,288 MB**, not 2,048 MB. The `NODE_OPTIONS` value is silently ignored for `--max-old-space-size` because an explicit flag is present.

### 3.3 Why this matters

The `NODE_OPTIONS` approach is not merely "less optimal" -- it is **completely ineffective**. An operator who believes they have capped the heap at 2 GB via `NODE_OPTIONS` will still see the process consume up to 12 GB. On a 4 GB VPS, this means an OOM kill within seconds of startup.

### 3.4 What NODE_OPTIONS CAN control

`NODE_OPTIONS` is still useful for V8 flags that are **not** overridden by explicit spawn args. For example:

```bash
NODE_OPTIONS=--max-semi-space-size=64
```

This would apply to the child process since it is not present in the explicit spawn args. But `--max-old-space-size` is always overridden.

---

## 4. The Correct Way: NINEROUTER_NODE_HEAP_MB

### 4.1 How it works

`NINEROUTER_NODE_HEAP_MB` is read by the parent process (`cli.js`) before spawning the child. The value is interpolated into the explicit `--max-old-space-size` flag, which the child then honors.

### 4.2 Setting it interactively

```bash
export NINEROUTER_NODE_HEAP_MB=2048
ninerouter start
```

### 4.3 Setting it in systemd

```ini
[Service]
Environment=NINEROUTER_NODE_HEAP_MB=2048
```

This is applied to the `ExecStart` process (cli.js), which reads it and passes it to the child via the explicit flag.

### 4.4 Validation

After setting, confirm with:

```bash
# Check the parent process picked it up
cat /proc/$(pgrep -f "cli.js")/environ | tr '\0' '\n' | grep NINEROUTER_NODE_HEAP_MB

# Check the child process received the correct --max-old-space-size
cat /proc/$(pgrep -f "server.js")/cmdline | tr '\0' '\n' | grep max-old-space-size
```

The second command should show `--max-old-space-size=2048`.

---

## 5. Stale Claims Corrected

| Previous Claim | Why Wrong | Correct Claim |
|---|---|---|
| "Set `NODE_OPTIONS=--max-old-space-size=2048`" | `NODE_OPTIONS` is overridden by explicit spawn args in cli.js | Set `NINEROUTER_NODE_HEAP_MB=2048` |
| "Default heap is 6 GB (6144)" | 6144 was from an older version; v0.5.4 line 558 defaults to `"12288"` | Default is 12 GB (12288) |
| "Heap can be tuned via `NODE_OPTIONS`" | Child process spawn uses explicit `--max-old-space-size`; Node.js docs state CLI flags override `NODE_OPTIONS` | Must use `NINEROUTER_NODE_HEAP_MB` env var |
| "`systemd Environment=NODE_OPTIONS=...`" | Would have NO effect on the actual heap; the child receives an explicit flag that takes precedence | systemd must set `Environment=NINEROUTER_NODE_HEAP_MB=2048` |

---

## 6. Impact on 2c/4GB VPS

### 6.1 The problem

- Default heap in 9Router v0.5.4: **12 GB** (`12288` MB)
- Total RAM on target VPS: **4 GB**
- Available after OS/reserved: approximately **3.2-3.5 GB**

The default 12 GB heap allocation will cause the V8 runtime to attempt to commit far more memory than exists. The Linux OOM killer will terminate the process, likely within seconds of startup.

### 6.2 Recommended heap setting

| VPS RAM | Recommended `NINEROUTER_NODE_HEAP_MB` | Rationale |
|---|---|---|
| 2 GB | 1024 | Leaves ~1 GB for OS, Redis, other services |
| 4 GB | 2048 | Leaves ~2 GB for OS, Redis, Alembic, bot process |
| 8 GB | 4096 | Generous headroom for 9Router alone |

For the Guinevere P25 target (2c/4 GB VPS), **2048** is the correct value.

### 6.3 Without correction

If the P25 migration proceeds without setting `NINEROUTER_NODE_HEAP_MB`:

1. 9Router starts via systemd
2. cli.js reads `NINEROUTER_NODE_HEAP_MB` as unset, defaults to 12288
3. cli.js spawns `node --max-old-space-size=12288 server.js`
4. V8 begins allocating heap up to 12 GB
5. Linux OOM killer terminates the process (exit code 137 or signal 9)
6. systemd reports service failure
7. Migration is blocked

**This is a BLOCKING issue for P25 migration if not corrected in the systemd unit.**

---

## 7. systemd Configuration

### 7.1 Correct unit file fragment

```ini
[Unit]
Description=9Router v0.5.4 Server
After=network.target redis.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/opt/ninerouter

# CORRECT: NINEROUTER_NODE_HEAP_MB controls --max-old-space-size in cli.js
Environment=NINEROUTER_NODE_HEAP_MB=2048

ExecStart=/usr/bin/node /opt/ninerouter/cli.js start
Restart=on-failure
RestartSec=5

# Memory safety guardrail
MemoryMax=3G
MemoryHigh=2G

[Install]
WantedBy=multi-user.target
```

### 7.2 Why NOT to use NODE_OPTIONS in the unit file

```ini
# WRONG -- has no effect on heap when cli.js spawns with explicit --max-old-space-size
Environment=NODE_OPTIONS=--max-old-space-size=2048
```

This was the previous recommendation. It is ineffective because:

1. cli.js reads `NINEROUTER_NODE_HEAP_MB` (not `NODE_OPTIONS`) for the heap value
2. cli.js spawns the child with an explicit `--max-old-space-size=12288` flag
3. The child's V8 prioritizes the explicit flag over `NODE_OPTIONS`
4. Net result: heap is still 12 GB regardless of `NODE_OPTIONS`

### 7.3 The MemoryMax/MemoryHigh systemd directives

Even with `NINEROUTER_NODE_HEAP_MB=2048` correctly set, systemd's `MemoryMax=3G` directive provides a defense-in-depth cgroup limit. If V8 plus native allocations exceed 3 GB, the kernel cgroup OOM killer terminates the process before the system-wide OOM killer is triggered. This protects other services (Redis, the bot process) on the same VPS.

---

## 8. The Complete Env Var Chain

```
Operator sets: NINEROUTER_NODE_HEAP_MB=2048  (via systemd Environment= or export)
    |
    v
cli.js reads: process.env.NINEROUTER_NODE_HEAP_MB  -->  "2048"
    |
    v
cli.js computes: SERVER_HEAP_MB = Number.parseInt("2048", 10)  -->  2048
    |
    v
cli.js spawns: node --max-old-space-size=2048 server.js
    |
    v
Child process: V8 heap ceiling = 2 GB
    |
    v
systemd cgroup: MemoryMax=3G  (defense-in-depth, independent of V8)
```

**Key insight**: `NINEROUTER_NODE_HEAP_MB` is consumed by the parent (cli.js) and never appears in the child's environment. The child only sees the resolved `--max-old-space-size` value in its argv.

---

## 9. Verification Test

### 9.1 Pre-flight (before starting 9Router)

```bash
# Confirm the env var is set in the systemd unit
systemctl show ninerouter.service | grep NINEROUTER_NODE_HEAP_MB
# Expected: Environment=NINEROUTER_NODE_HEAP_MB=2048
```

### 9.2 Runtime verification (after starting 9Router)

```bash
# Get the child server process PID
SERVER_PID=$(pgrep -f "server.js" | head -1)

# Inspect its command line
cat /proc/$SERVER_PID/cmdline | tr '\0' '\n'
# Expected output (partial):
#   node
#   --max-old-space-size=2048
#   /opt/ninerouter/server.js
```

### 9.3 Memory verification (runtime)

```bash
# Check current heap usage
node -e "
  const http = require('http');
  http.get('http://localhost:<9ROUTER_PORT>/health', (res) => {
    let data = '';
    res.on('data', (chunk) => data += chunk);
    res.on('end', () => console.log(data));
  });
"

# Or check RSS directly
ps -o pid,rss,vsz,comm -p $SERVER_PID
# RSS should be well under 2048 MB (~2,097,152 KB)
```

### 9.4 Failure mode test (confirm NODE_OPTIONS does NOT work)

```bash
# Set NODE_OPTIONS to a small heap
export NODE_OPTIONS=--max-old-space-size=512
# Do NOT set NINEROUTER_NODE_HEAP_MB

# Start 9Router
ninerouter start

# Check child process --max-old-space-size
cat /proc/$(pgrep -f "server.js")/cmdline | tr '\0' '\n' | grep max-old-space-size
# Shows: --max-old-space-size=12288  (NOT 512)
# This confirms NODE_OPTIONS has no effect
```

---

## 10. Footer

This document corrects the heap control section of prior P25 research. The source of truth is `cli.js` in 9Router v0.5.4. Any future P25 migration documentation, batch plans, or systemd unit templates MUST reference `NINEROUTER_NODE_HEAP_MB` and MUST NOT reference `NODE_OPTIONS` for heap control.

| Field | Value |
|---|---|
| Corrected claim count | 4 |
| Default heap (v0.5.4) | 12,288 MB (12 GB) |
| Correct env var | `NINEROUTER_NODE_HEAP_MB` |
| Recommended value for 4 GB VPS | 2048 |
| Previous (wrong) approach | `NODE_OPTIONS=--max-old-space-size=2048` |
| Severity | BLOCKING -- 9Router will OOM on 4 GB VPS without this fix |
| Source file | cli.js lines 137, 558, 578 |
