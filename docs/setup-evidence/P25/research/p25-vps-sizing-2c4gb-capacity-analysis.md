# P25 VPS Sizing: 2 vCPU / 4 GB RAM Capacity Analysis

**Target workload:** Dedicated 9Router instance serving Claude Code + OpenCode at ~1000 req/min
**Date:** 2026-06-25
**Author:** Capacity analysis for P25 dedicated coding-traffic VPS
**Scope:** NEW dedicated VPS (NOT existing guinevere-vps / Hermes VPS)

---

## 1. Executive Summary

**Verdict: CONDITIONAL PASS -- LOAD TEST REQUIRED**

A 2 vCPU / 4 GB RAM VPS is **conditionally sufficient** for a dedicated 9Router instance serving Claude Code and OpenCode at ~1000 req/min (16.7 req/sec). The conditionality rests on three variables:

| Variable | Pass Threshold | Fail Threshold |
|---|---|---|
| Average request duration | <= 30 seconds | > 60 seconds sustained |
| Sustained burst rate | <= 50 req/sec | > 83 req/sec sustained (5x average) |
| Node.js heap cap | Tuned to `--max-old-space-size=2048` | Left at default 6144 MB |

**Key findings:**

- **CPU is not the bottleneck.** 9Router is I/O-bound (proxying streams to upstream LLM providers). Steady-state CPU utilization is estimated at < 17% of one core.
- **Memory is the binding constraint.** At 500 concurrent in-flight requests (16.7 req/sec x 30s avg), total memory is estimated at ~1.2 GB. At 1000 concurrent (60s avg), ~2.2 GB. 4 GB leaves adequate headroom for the 10-30s range; at 60s sustained it is tight but survivable.
- **Network and sockets are not a concern.** ~1000 sockets at peak is well within Linux defaults. Tailscale overhead is negligible.
- **SQLite is not a bottleneck.** ~33 writes/sec in WAL mode is trivial.
- **A 5-minute sustained load test at 1000 req/min is mandatory** before declaring the VPS production-ready for this traffic level.

If 4 GB proves insufficient, the fallback is a 4 vCPU / 8 GB instance (~$24-48/month).

---

## 2. Request Volume Analysis

### 2.1 Steady-State Conversion

```
1000 req/min = 16.67 req/sec (average)
```

### 2.2 Burst Scenarios

Real coding traffic is bursty. Claude Code and OpenCode send multiple requests per prompt turn (tool calls, chained completions, retries). We model three burst tiers:

| Scenario | Multiplier | req/sec | req/min |
|---|---|---|---|
| Steady state | 1x | 16.7 | 1,000 |
| Moderate burst | 2x | 33.3 | 2,000 |
| Heavy burst | 5x | 83.3 | 5,000 |

Bursts are transient (typically 10-30 seconds). The system must absorb moderate bursts without error. Heavy bursts may cause latency increases but should not cause OOM or crashes.

---

## 3. Concurrency Model

### 3.1 Core Formula

```
concurrent_in_flight = req_per_sec * avg_duration_seconds
```

Each request to 9Router follows this lifecycle:

| Step | Duration | Nature |
|---|---|---|
| a. Parse HTTP request | ~0.1 ms | CPU-bound, trivial |
| b. Resolve model/provider (SQLite lookup) | ~0.5 ms | CPU + disk, synchronous |
| c. Forward to upstream provider | **LATENCY-DOMINATED** | Mostly waiting (network I/O) |
| d. Stream response back (SSE pipe) | **I/O-bound** | TransformStream + SSE chunk forwarding |

Steps c and d dominate. The 9Router process spends nearly all its time waiting on upstream provider responses, not doing local computation. This is the fundamental reason CPU is not the bottleneck.

### 3.2 In-Flight Estimates

For LLM coding tasks (Claude Code, OpenCode), typical response durations:

| Average Duration | 16.7 req/sec | 33.3 req/sec (2x burst) | 83.3 req/sec (5x burst) |
|---|---|---|---|
| 10 seconds (fast code answers) | **167** concurrent | 333 | 833 |
| 30 seconds (typical code generation) | **500** concurrent | 1,000 | 2,500 |
| 60 seconds (complex generation) | **1,000** concurrent | 2,000 | 5,000 |

**Design point:** 500 concurrent in-flight at steady state (30s avg) is the expected operating point.

### 3.3 Each In-Flight Request Holds

- HTTP request context (headers, body buffer if not yet forwarded): ~0.5-1 MB
- TransformStream instance + SSE state: ~0.5-1 MB
- Response accumulation buffer (if buffering for logging): ~0-2 MB
- SQLite write context (deferred): negligible

**Conservative per-request memory: 2 MB average** (some are < 1 MB, some streaming long responses peak higher).

---

## 4. Memory Analysis

### 4.1 Component Breakdown

| Component | Memory |
|---|---|
| Node.js runtime + V8 baseline | ~40 MB |
| Next.js application + routes | ~30-50 MB |
| SQLite cache (better-sqlite3, in-process) | ~20-50 MB |
| Application state (config, routing tables, provider map) | ~10-30 MB |
| **Base total** | **~100-200 MB** |

### 4.2 Per-Request Additional Memory

| Concurrent In-Flight | Per-Request (2 MB avg) | Additional Memory | Total Estimated |
|---|---|---|---|
| 167 (10s avg, steady) | 2 MB | 334 MB | ~500 MB |
| 500 (30s avg, steady) | 2 MB | 1,000 MB | ~1.2 GB |
| 1,000 (60s avg, steady) | 2 MB | 2,000 MB | ~2.2 GB |
| 500 + 333 burst (30s avg, 2x burst) | 2 MB | 1,666 MB | ~1.9 GB |

### 4.3 4 GB Budget Allocation

| Category | Allocation |
|---|---|
| OS + kernel + systemd services | ~400-600 MB |
| Node.js heap (capped at `--max-old-space-size=2048`) | ~2,048 MB max |
| OS page cache (SQLite + log files) | ~500-1,000 MB |
| Headroom (safety margin) | ~400-600 MB |
| **Total** | **~4,096 MB** |

### 4.4 Sufficiency Matrix

| Scenario | Estimated Usage | Fits in 4 GB? | Headroom |
|---|---|---|---|
| 10s avg, steady | ~500 MB | YES | ~3.5 GB free |
| 30s avg, steady | ~1.2 GB | YES | ~2.8 GB free |
| 60s avg, steady | ~2.2 GB | TIGHT | ~1.8 GB free (but OS + cache compete) |
| 30s avg, 2x burst | ~1.9 GB | YES | ~2.1 GB free |
| 60s avg, 2x burst | ~3.2 GB+ | RISKY | < 1 GB free, OOM possible |
| 60s avg, 5x burst | > 4 GB | NO | OOM likely |

**Critical tuning requirement:**

```
# MUST set Node.js heap limit (do NOT leave at default 6144 MB)
node --max-old-space-size=2048 node_modules/.bin/next start
```

The default `--max-old-space-size=6144` (6 GB) **will OOM on a 4 GB VPS** even without traffic. This must be corrected in the systemd unit file.

### 4.5 GC Heap High Watermark

Observed high watermark on the existing instance: ~1.0 GB. On the dedicated VPS with tuned heap:

- V8 GC will trigger major collections at ~1.5-1.8 GB
- With 2 GB heap cap, GC overhead remains manageable
- If GC pauses exceed 100ms under load, consider `--max-semi-space-size=64` to reduce pause duration at the cost of slightly higher baseline memory

---

## 5. CPU Analysis

### 5.1 Nature of the Workload

9Router is a **proxy**, not a compute engine. Per request:

| Operation | CPU Time | Notes |
|---|---|---|
| HTTP request parsing | ~0.1 ms | Node.js http parser |
| JSON body parse (if not streaming forward) | ~0.1-0.5 ms | Depends on body size |
| SQLite model/provider lookup | ~0.1-0.5 ms | Indexed lookup, synchronous |
| Header manipulation (forwarding) | ~0.05 ms | String operations |
| SSE chunk forwarding (per chunk) | ~0.01 ms | TransformStream pipe, minimal CPU |
| Response logging/buffering | ~0.1-0.5 ms | Deferred, batched |
| **Total CPU per request** | **~1-5 ms** | Mostly in request setup |

The stream forwarding phase (which is the longest phase by wall-clock time) consumes near-zero CPU -- it is pure I/O multiplexing by the Node.js event loop.

### 5.2 Utilization Estimates

| Scenario | req/sec | CPU/request | CPU-seconds/sec | % of 1 core | % of 2 vCPU |
|---|---|---|---|---|---|
| Steady state | 16.7 | 10 ms | 0.167 | 16.7% | 8.3% |
| 2x burst | 33.3 | 10 ms | 0.333 | 33.3% | 16.7% |
| 5x burst | 83.3 | 10 ms | 0.833 | 83.3% | 41.7% |
| Steady (worst case) | 16.7 | 50 ms | 0.835 | 83.5% | 41.7% |

**Verdict: 2 vCPU is MORE than sufficient.** Even at worst-case CPU-per-request and 5x burst, total CPU utilization remains under 50% of available capacity. CPU will never be the bottleneck for a streaming proxy workload.

### 5.3 Event Loop Considerations

The Node.js event loop is single-threaded. While CPU per request is low, sustained high concurrency can cause event loop lag if any synchronous operation blocks:

- **SQLite (better-sqlite3):** Synchronous I/O. A cold query on a 1.5 GB database could block for 1-10 ms. With WAL mode and warm page cache, typically < 1 ms. This is acceptable at 16.7 req/sec but becomes a concern at 80+ req/sec if every request hits SQLite.
- **JSON.parse/stringify on large payloads:** Code generation responses can be large. Parsing a 100 KB response takes ~0.5 ms. At 80 concurrent streams, the cumulative parse work is modest.
- **Mitigation:** Monitor event loop lag (`process.hrtime` delta check). If p99 lag exceeds 100 ms, consider moving SQLite lookups to a worker thread.

---

## 6. Network and Socket Analysis

### 6.1 Socket Count

Each in-flight request requires 2 sockets:

- Client -> 9Router (Claude Code / OpenCode -> proxy)
- 9Router -> Upstream provider (proxy -> Anthropic API / other)

| Concurrent In-Flight | Sockets Required |
|---|---|
| 167 | 334 |
| 500 | 1,000 |
| 1,000 | 2,000 |
| 2,500 (5x burst, 30s) | 5,000 |

### 6.2 Linux Kernel Limits

| Limit | Default | Required (500 concurrent) | Status |
|---|---|---|---|
| `net.core.somaxconn` | 4,096 | ~1,000 | PASS |
| `net.ipv4.ip_local_port_range` | 32768-60999 (~28k ports) | ~1,000 | PASS |
| `fs.file-max` | ~1M | ~1,100 | PASS |
| Per-process `ulimit -n` | 8,192 (typical) | ~1,100 | PASS |
| `net.ipv4.tcp_max_syn_backlog` | 4,096 | ~500 | PASS |

For 1000 concurrent (2000 sockets), all defaults still hold. No kernel tuning is required.

### 6.3 Tailscale Overhead

- Latency: ~1-5 ms additional (WireGuard encapsulation, local routing)
- Bandwidth: No cap for control-plane traffic; Tailscale operates at line speed on LAN/VPS
- Encryption: ChaCha20-Poly1305, hardware-accelerated on modern VPS CPUs
- Socket overhead: Negligible (Tailscale creates a virtual TUN device, not per-connection state)
- **Impact:** Tailscale adds ~1-5 ms to request latency. This is within noise for requests that take 10-60 seconds.

### 6.4 HTTP Keep-Alive and Connection Pooling

- Claude Code / OpenCode clients should use HTTP keep-alive to avoid TCP handshake overhead per request
- 9Router -> upstream provider connections should also be pooled (Node.js `http.Agent` with `keepAlive: true`)
- Connection pool size per upstream provider: 64-128 is typical and sufficient
- **Verify:** Check that 9Router uses an HTTP agent with keep-alive. If not, each upstream request incurs ~50-100 ms TCP + TLS handshake overhead.

---

## 7. SQLite Performance Analysis

### 7.1 Write Load

Per request, 9Router writes to:

| Table | Write Type | Frequency |
|---|---|---|
| `usageHistory` | INSERT | Every request (~16.7/sec) |
| `requestDetails` | INSERT (batched) | Every request, but batched every 5s or 20 records |

**Total write load:** ~33 writes/sec at steady state (16.7 usageHistory + 16.7 requestDetails).

### 7.2 WAL Mode Throughput

SQLite in WAL (Write-Ahead Logging) mode:

- Supports concurrent readers with a single writer
- Write throughput: easily 100-1,000+ writes/sec on SSD
- Each write at 16.7/sec is **0.3% of typical WAL capacity**
- WAL checkpoint (fsync): periodic, typically every 1000 pages or 1 second

**Verdict:** SQLite is not a bottleneck. At 33 writes/sec, even a spinning disk would suffice. On SSD (standard for VPS), SQLite is negligible.

### 7.3 Database Size and Caching

- Current database size: ~1.5 GB
- SQLite page cache (in-process): configurable via `PRAGMA cache_size`. Default is 2 MB (too small). Set to 64-128 MB for a 1.5 GB database.
- OS page cache: With 4 GB total RAM, ~500 MB-1 GB is available for file caching. A 1.5 GB database will be partially cached. Frequently accessed pages (routing tables, recent usageHistory) will be hot; older pages may require disk reads.
- **Impact:** Cold reads on uncached pages may take 1-5 ms instead of < 0.1 ms. At 16.7 req/sec this is acceptable.

### 7.4 Maintenance Concern: usageHistory Growth

- `usageHistory` is unbounded (INSERT per request, no automatic pruning)
- At 16.7 req/sec: ~1.44 million rows/day, ~43 million rows/month
- Table scan performance degrades with size
- **Mitigation:** Add a cron job or application-level pruning to delete `usageHistory` rows older than 7-30 days. This prevents the database from growing unbounded and keeps queries fast.

---

## 8. Log / Dashboard Write Amplification

### 8.1 Write Patterns

| Component | Write Frequency | Size | Amplification |
|---|---|---|---|
| `requestDetails` | Batched (every 5s or 20 records) | ~1-5 KB per record | Low -- FIFO capped at 200 records |
| `usageHistory` | Per request | ~0.5-1 KB per record | Medium -- unbounded, see Section 7.4 |
| Text log file | Selective (errors, debug) | ~0.1-1 KB per entry | Minimal |
| Dashboard state | In-memory, read infrequently | Negligible | None |

### 8.2 Write Amplification Assessment

- `requestDetails` is capped at 200 records with FIFO eviction. Write volume is bounded.
- `usageHistory` is the primary concern. At ~1 KB/row x 1.44M rows/day = ~1.4 GB/day of raw data. WAL mode means the WAL file will grow until checkpointed. Monitor WAL file size.
- Dashboard reads are periodic (user-triggered) and read from in-memory state or SQLite. No write amplification.
- **Total disk write rate:** ~33 writes/sec x ~2 KB average = ~66 KB/sec = ~5.5 GB/day. On a VPS with SSD and typical I/O limits (50-100 MB/sec), this is negligible.

---

## 9. OS Limits and Tuning

### 9.1 File Descriptors

| Source | Count |
|---|---|
| Sockets (500 concurrent x 2) | 1,000 |
| SQLite database files (main + WAL + SHM) | 3 |
| Log files | 1-3 |
| Application files (config, node_modules) | ~50-100 |
| **Total** | **~1,100-1,200** |

Default `ulimit -n` on Ubuntu 24.04: 8,192 (or 1,024 for some configurations).

**Action:** Verify and set in systemd unit:

```ini
[Service]
LimitNOFILE=8192
```

### 9.2 Systemd Unit Configuration

Recommended systemd unit for 9Router:

```ini
[Unit]
Description=9Router LLM Proxy
After=network.target tailscaled.service

[Service]
Type=simple
User=router
WorkingDirectory=/opt/9router
ExecStart=/usr/bin/node --max-old-space-size=2048 node_modules/.bin/next start -p 3000
Restart=always
RestartSec=5
Environment=NODE_ENV=production
LimitNOFILE=8192
# Memory accounting (optional, for monitoring)
MemoryAccounting=yes
MemoryMax=3500M
MemoryHigh=3000M

[Install]
WantedBy=multi-user.target
```

Key settings:
- `--max-old-space-size=2048`: Caps V8 heap at 2 GB (MUST NOT use default 6144 on 4 GB VPS)
- `LimitNOFILE=8192`: Adequate for 1000+ concurrent sockets
- `MemoryMax=3500M`: Hard kill if process exceeds 3.5 GB (prevents OOM-killer targeting other services)
- `MemoryHigh=3000M`: Triggers aggressive memory reclaim above 3 GB (smooth degradation vs hard kill)

### 9.3 Node.js Heap Recommendation

| Setting | Value | Rationale |
|---|---|---|
| `--max-old-space-size` | 2048 | Leaves ~2 GB for OS + page cache on 4 GB VPS |
| `--max-semi-space-size` | 64 (optional) | Reduces GC pause time at cost of ~64 MB more baseline |
| `--expose-gc` | Optional | For monitoring GC frequency and pause duration |

### 9.4 Swap

```bash
# Ensure swap is configured as a safety net (not for performance)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
# Add to /etc/fstab: /swapfile none swap sw 0 0
```

Swap is a safety net to prevent OOM-kill during transient memory spikes. If the system is actively swapping under normal load, the VPS is undersized. Set `vm.swappiness=10` to prefer keeping working set in RAM.

---

## 10. Final Recommendation

### Verdict: CONDITIONAL PASS

| Criterion | Status | Notes |
|---|---|---|
| CPU (2 vCPU) | **PASS** | < 17% steady-state, < 50% at 5x burst. Not the bottleneck. |
| Memory (4 GB) | **CONDITIONAL** | Sufficient for 10-30s avg duration. Tight at 60s. Requires heap tuning. |
| Network / sockets | **PASS** | ~1,000 sockets well within Linux defaults. Tailscale overhead negligible. |
| SQLite | **PASS** | 33 writes/sec in WAL mode is trivial. Prune usageHistory. |
| Disk I/O | **PASS** | ~66 KB/sec write rate is negligible on SSD. |
| OS limits | **PASS** | Default limits adequate. Set LimitNOFILE and MemoryMax in systemd. |

### Conditions for PASS

1. **Node.js heap MUST be tuned:** `--max-old-space-size=2048` in systemd unit
2. **Average request duration must be <= 30s** under sustained load (measure, do not assume)
3. **usageHistory must be pruned** (cron job or in-app, retain <= 30 days)
4. **Swap must be configured** as a 2 GB safety net
5. **Load test must pass** (see Section 12)

### Conditions for FAIL

- Average request duration > 60 seconds sustained
- Burst > 83 req/sec sustained for > 60 seconds
- Memory usage exceeds 3.5 GB under normal load (triggers MemoryMax)
- Event loop lag > 100ms at p99 under load test

---

## 11. Fallback VPS Size Recommendation

| Tier | Spec | Monthly Cost (est.) | When to Use |
|---|---|---|---|
| **Primary** | 2 vCPU / 4 GB | ~$12-24 | Default choice. Passes for 10-30s avg request duration. |
| **Fallback** | 4 vCPU / 8 GB | ~$24-48 | If load test fails at 4 GB, or if avg duration > 30s, or if burst > 50 req/sec sustained. |
| **Overkill** | 8 vCPU / 16 GB | ~$48-96 | Not needed unless > 5000 req/min or multiple proxy instances. |

**Upgrade path:** Start at 2c/4GB. Run load test. If it passes, deploy. If memory is the failure mode (OOM or heavy GC), upgrade to 4c/8GB. CPU will never require more than 2 vCPU for this workload.

**Cost note:** The difference between 2c/4GB and 4c/8GB is typically $12-24/month. Starting at 4c/8GB eliminates the sizing risk entirely for a modest cost increase. This may be preferred if the cost difference is immaterial.

---

## 12. Load Test Plan

A load test is **mandatory** before claiming the VPS is production-ready. The test must simulate realistic coding-traffic patterns.

### 12.1 Test Tool

Use **k6** (preferred) or **wrk2** with a custom script that sends OpenAI-compatible chat completion requests with streaming enabled.

```bash
# Install k6
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6
```

### 12.2 Test Script Requirements

- Target: `POST /v1/chat/completions` (OpenAI-compatible endpoint)
- Payload: Realistic coding prompt (~500-2000 tokens input)
- Response: Expect streaming SSE (check `stream: true`)
- Models: Rotate through configured models (Claude Sonnet, GPT-4o, etc.)
- Auth: Use a valid API key (Tailscale-internal, no public exposure)

### 12.3 Test Scenarios

| Scenario | Duration | req/sec | Total Requests | Purpose |
|---|---|---|---|---|
| Warm-up | 60s | 5 | 300 | Warm caches, establish baseline |
| Steady state | 5 min | 16.7 | 5,000 | Validate normal operation |
| 2x burst | 2 min | 33.3 | 4,000 | Validate burst absorption |
| Spike | 30s | 83.3 | 2,500 | Validate extreme burst (may degrade, must not crash) |
| Cool-down | 60s | 5 | 300 | Verify recovery after spike |

### 12.4 Pass Criteria

| Metric | Threshold | Measurement |
|---|---|---|
| Error rate (5xx) | 0% | k6 `http_req_failed` |
| p50 latency | < 500 ms (first byte) | k6 `http_req_waiting` |
| p95 latency | < 2,000 ms (first byte) | k6 `http_req_waiting` |
| p99 latency | < 5,000 ms (first byte) | k6 `http_req_waiting` |
| Memory (RSS) | < 3.0 GB | `ps` or cgroup metrics |
| CPU utilization | < 50% of 2 cores | `top` or `mpstat` |
| Event loop lag | < 100ms at p99 | Node.js `perf_hooks.monitorEventLoopDelay` |
| OOM kills | 0 | `dmesg | grep -i oom` |
| Swap usage | < 100 MB | `free -m` |

### 12.5 Monitoring During Test

```bash
# Terminal 1: System metrics (every 2s)
watch -n 2 'free -m && echo "---" && mpstat -P ALL 1 1 && echo "---" && ss -s'

# Terminal 2: Node.js process
watch -n 2 'ps aux | grep "node.*next" | grep -v grep'

# Terminal 3: OOM and errors
dmesg -w | grep -i -E "oom|kill|error"

# Terminal 4: Disk I/O
iostat -x 2
```

---

## 13. Metrics to Prove No Bottleneck

After load test, document these metrics to prove the VPS is not bottlenecked:

### 13.1 CPU Proof

```
# Metric: CPU utilization < 30% at steady state
# Tool: mpstat or top
# Command:
mpstat -P ALL 5 12  # 5s intervals, 12 samples (1 minute during steady load)
# Expected: %usr + %sys < 30% on each core
```

### 13.2 Memory Proof

```
# Metric: RSS < 2.5 GB, no OOM
# Tool: ps + cgroup
# Command:
ps -o pid,rss,vsz,comm -p $(pgrep -f "node.*next")
# Also: cat /sys/fs/cgroup/$(systemctl show 9router -p ControlGroup --value)/memory.current
# Expected: < 2.5 GB RSS, 0 OOM kills
```

### 13.3 Network Proof

```
# Metric: Socket count < 2000, no connection refused
# Tool: ss
# Command:
ss -s  # Summary of socket states
ss -tnp | grep -c ":3000"  # Connections to 9Router port
# Expected: < 2000 established, 0 refused
```

### 13.4 Event Loop Proof

```
# Metric: Event loop lag < 100ms at p99
# Tool: Node.js built-in (must be instrumented in 9Router)
# Code:
# const { monitorEventLoopDelay } = require('perf_hooks');
# const h = monitorEventLoopDelay({ resolution: 10 });
# h.enable();
# setInterval(() => { console.log('EL p99:', h.percentile(99)/1e6, 'ms'); h.reset(); }, 10000);
# Expected: p99 < 100ms
```

### 13.5 SQLite Proof

```
# Metric: Query latency < 5ms at p99
# Tool: Application-level timing (log slow queries)
# Expected: All queries < 5ms (WAL mode, warm cache)
# Check WAL file size: ls -lh *.sqlite-wal
# Expected: WAL file < 100 MB (checkpointing regularly)
```

---

## 14. Summary Decision Matrix

```
                    PASS    CONDITIONAL    FAIL
CPU (2 vCPU)         [X]
Memory (4 GB)                  [X]
Network/Sockets      [X]
SQLite               [X]
Disk I/O             [X]
OS Limits            [X]

Final Verdict:       CONDITIONAL PASS

Conditions:
  1. --max-old-space-size=2048 (mandatory)
  2. usageHistory pruning (mandatory)
  3. Swap configured (mandatory)
  4. Load test passes all thresholds (mandatory)
  5. Average request duration <= 30s (verify via load test)

If conditions met: 2c/4GB is sufficient for ~1000 req/min.
If conditions fail: upgrade to 4c/8GB.
```

---

## Footer

- **Document:** P25 VPS Sizing Analysis -- 2 vCPU / 4 GB Capacity
- **Created:** 2026-06-25
- **Purpose:** Engineering analysis to determine if 2c/4GB VPS can host dedicated 9Router for Claude Code + OpenCode at ~1000 req/min
- **Verdict:** CONDITIONAL PASS -- LOAD TEST REQUIRED
- **Next step:** Provision VPS, install 9Router, run load test per Section 12, document results
- **Related:** P25 (dedicated coding VPS), 9Router proxy architecture, Claude Code / OpenCode integration
