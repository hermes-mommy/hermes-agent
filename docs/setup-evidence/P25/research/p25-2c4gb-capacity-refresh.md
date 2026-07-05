# P25-2c4GB Capacity Refresh: 9Router v0.5.4 on 2-Core / 4 GB VPS

> **Date**: 2026-06-25
> **Author**: Guinevere (autonomous research)
> **Status**: Research COMPLETE -- awaiting operator approval
> **Version corrected**: 9Router 0.5.4 (previous analysis used stale 0.4.71 data)

---

## 1. Executive Summary

This report refreshes the capacity analysis for running 9Router v0.5.4 on the existing 2-core / 4 GB VPS. Previous analysis was based on incorrect version data (0.4.71) and wrong default heap assumptions (6 GB). The corrected analysis shows:

- **Default heap is now 12 GB** (via `NINEROUTER_NODE_HEAP_MB`), up from the previously assumed 6 GB.
- **Heap control mechanism changed** from `NODE_OPTIONS` to `NINEROUTER_NODE_HEAP_MB` environment variable.
- **92 providers** confirmed (not 2 as previously assumed), with 11 provider combos.
- **Framework**: Next.js 16.1.6 standalone, confirmed.
- **Database**: 1.5 GB SQLite, confirmed.

**Verdict: CONDITIONAL PASS** -- 9Router v0.5.4 can run on 2c/4GB **only if** `NINEROUTER_NODE_HEAP_MB=2048` is set in the systemd unit. Without this, the 12 GB default heap will cause immediate OOM kill on a 4 GB VPS.

---

## 2. What Changed from Previous Analysis

| Parameter | Previous (stale) | Corrected (v0.5.4) | Impact |
|---|---|---|---|
| Version | 0.4.71 | **0.5.4** | Different software entirely |
| Default heap | 6 GB | **12 GB** | WORSE -- higher OOM risk |
| Heap control | `NODE_OPTIONS=--max-old-space-size` | **`NINEROUTER_NODE_HEAP_MB`** | Different mechanism, must update systemd unit |
| Framework | Assumed Next.js | **Next.js 16.1.6 standalone (confirmed)** | No change, just confirmed |
| Providers | 2 | **92** | More complex DB queries, no runtime impact |
| Provider combos | 6 | **11** | No runtime impact |
| Database size | Estimated | **1.5 GB SQLite (confirmed)** | Needs OS page cache allocation |
| Custom server | Unknown | **custom-server.js wraps HTTP for real IP** | Adds minimal overhead |
| Conclusion | CONDITIONAL PASS | **CONDITIONAL PASS (stricter conditions)** | See Section 10 |

**Key takeaway**: The software version and heap configuration have changed significantly. The conclusion is the same (conditional pass) but the conditions are stricter because the default heap doubled.

---

## 3. Request Volume Model

### Steady-State Targets

| Metric | Value | Notes |
|---|---|---|
| Target throughput | 1,000 req/min = **16.7 req/sec** | Expected sustained load |
| Burst (2x) | **33.3 req/sec** | Short bursts, typical during team activity |
| Peak (5x) | **83.3 req/sec** | Rare, brief spikes (e.g., mass deployment) |

### Request Character

- LLM proxy requests: streaming responses from upstream providers.
- Average response time: 10-30 seconds for coding tasks.
- Request payload: small (prompts, 1-10 KB).
- Response payload: large (streaming completions, 10-500 KB).

---

## 4. Concurrency Model (Little's Law)

Little's Law: **L = lambda x W** (concurrent requests = arrival rate x average time in system).

| Scenario | Arrival Rate (lambda) | Avg Duration (W) | Concurrency (L) | Notes |
|---|---|---|---|---|
| Fast completions | 16.7 req/sec | 10s | **167** | Simple queries |
| Typical coding | 16.7 req/sec | 20s | **333** | Normal workload |
| Slow completions | 16.7 req/sec | 30s | **500** | Complex refactors |
| Worst case | 16.7 req/sec | 60s | **1,000** | Long-running tasks (rare) |

**Realistic operating point**: L = 300-500 concurrent requests for typical coding workloads (10-30s average duration).

At burst (2x): L = 667-1,000 concurrent.
At peak (5x): L = 1,667-5,000 concurrent -- this would require horizontal scaling.

**Design target**: L = 500 concurrent as normal maximum, L = 1,000 as absolute ceiling.

---

## 5. Memory Analysis

### The 12 GB Default Heap Problem

9Router v0.5.4 defaults to a **12 GB heap** via the `NINEROUTER_NODE_HEAP_MB` environment variable. On a 4 GB VPS:

- 12 GB heap allocation > 4 GB total RAM = **immediate OOM kill**.
- This is not a gradual problem; the process will not start.
- **Resolution**: Set `NINEROUTER_NODE_HEAP_MB=2048` in the systemd unit.

### Memory Budget with 2 GB Heap

| Component | Memory | Notes |
|---|---|---|
| Node.js heap (set) | 2,048 MB | Via `NINEROUTER_NODE_HEAP_MB=2048` |
| Base footprint | ~200 MB | Next.js + SQLite cache + runtime |
| Per-request (streaming) | ~1.5 MB avg | Buffer allocation for streaming responses |
| At L=167 (10s) | 200 + 250 = **450 MB** | Comfortable |
| At L=333 (20s) | 200 + 500 = **700 MB** | Comfortable |
| At L=500 (30s) | 200 + 750 = **950 MB** | OK, leaves 1 GB heap headroom |
| At L=1000 (60s) | 200 + 1500 = **1,700 MB** | Tight but within 2 GB heap |

### Full System Memory Budget (4 GB VPS)

| Component | Allocation | Notes |
|---|---|---|
| OS + kernel | ~500 MB | Ubuntu 24.04 baseline |
| 9Router (heap) | 2,048 MB | Set via env var |
| 9Router (RSS overhead) | ~300 MB | Non-heap allocations |
| OS file cache | ~950 MB | Caches 1.5 GB SQLite (partial) |
| Buffer / headroom | ~200 MB | Swap avoidance |
| **Total** | **~4,000 MB** | Tight but feasible |

**Risk**: At L=1000 with 2 GB heap, the heap is nearly full. The OS file cache will shrink, slowing SQLite reads. This is acceptable if load test confirms stability.

### Swap Considerations

- 4 GB VPS typically has 1-2 GB swap configured.
- Swap usage degrades performance (Node.js GC stalls).
- **Target**: Zero swap usage under normal load (L <= 500).
- Monitor with `vmstat 1` -- any `si/so` activity under load is a warning sign.

---

## 6. CPU Analysis

9Router is an **I/O-bound streaming proxy**, not a compute engine.

### Per-Request CPU Cost

| Operation | CPU Time | Notes |
|---|---|---|
| HTTP parse (request) | ~0.5 ms | Fastify/Node.js native |
| Provider routing | ~1 ms | Lookup in 92-provider table |
| SQLite write (usage) | ~2 ms | WAL mode insert |
| Stream proxy | ~5-10 ms per chunk | Buffer copy, no transform |
| **Total per request** | **~10-15 ms** | |

### Aggregate CPU Load

| Throughput | CPU per core (2 vCPU) | Notes |
|---|---|---|
| 16.7 req/sec | 16.7 x 10ms = **16.7%** | Well within budget |
| 33.3 req/sec | 33.3 x 10ms = **33.3%** | Comfortable |
| 83.3 req/sec | 83.3 x 10ms = **83.3%** | High but manageable on 2 cores |

**Conclusion**: CPU is **not a bottleneck**. Even at 5x burst (83.3 req/sec), 2 vCPUs can handle the load. The bottleneck is memory, not CPU.

### Event Loop Lag

- Node.js single-threaded event loop is the real CPU constraint.
- At 16.7 req/sec: event loop lag < 5ms (safe).
- At 83.3 req/sec: event loop lag may reach 20-30ms (acceptable).
- **Gate**: Event loop lag must remain < 50ms during load test.

---

## 7. Network & Connection Analysis

### TCP Connections

| Layer | Connections at L=500 | Notes |
|---|---|---|
| Client -> 9Router | 500 | Incoming HTTP/WebSocket |
| 9Router -> Provider | 500 | Outgoing HTTPS to upstream LLM |
| **Total** | **1,000** | |

### File Descriptors

- 1,000 TCP connections + ~200 overhead (SQLite, logs, internal) = **~1,200 FDs**.
- Default `ulimit -n`: 16,384 on Ubuntu 24.04.
- **No issue** -- well within limits.

### Tailscale Network Overhead

- Tailscale adds ~5-20ms per hop (WireGuard tunnel).
- For LLM requests with 10-60s response times, this is **negligible** (< 0.2% overhead).
- Tailscale NAT traversal may add connection setup time on first request (100-500ms), amortized over long-lived connections.

### Bandwidth

- 16.7 req/sec x 500 KB avg response = **~8.3 MB/sec = ~66 Mbps**.
- Typical VPS: 1 Gbps shared.
- **No issue** -- 6.6% of available bandwidth.

---

## 8. SQLite Performance Analysis

### Write Load

| Metric | Value | Notes |
|---|---|---|
| Requests/sec | 16.7 | Steady state |
| Writes/request | ~2 | usageHistory + requestDetails |
| Writes/sec | **~33** | Steady state |
| Burst writes/sec | **~66** | At 2x burst |

### SQLite Capacity

- WAL mode handles **100+ writes/sec** easily on SSD.
- 33 writes/sec = **33% of WAL capacity** (comfortable).
- 1.5 GB database with WAL: checkpoint every 1,000 pages (~4 MB) by default.

### Cache Performance

- SQLite page cache: configurable, default 2 MB (in-process).
- OS page cache: **~950 MB available** (from memory budget).
- 1.5 GB database: **63% cached** in OS page cache.
- Hot working set (recent requests, provider table): likely < 100 MB, fully cached.

### Maintenance Requirements

- **usageHistory pruning**: Must implement 30-day retention policy.
- Without pruning, database grows unbounded, degrading read performance.
- `VACUUM` should run weekly during low-traffic window.
- Monitor with `PRAGMA page_count` and `PRAGMA freelist_count`.

---

## 9. The 12 GB Heap Problem (Blocking Issue)

### Problem Statement

9Router v0.5.4 sets its default V8 heap to **12 GB** via the `NINEROUTER_NODE_HEAP_MB` environment variable. This is designed for dedicated servers with 16-32 GB RAM. On a 4 GB VPS:

```
V8 requests 12 GB heap
  -> Kernel cannot allocate 12 GB from 4 GB physical + swap
  -> OOM killer invoked
  -> 9Router process killed immediately
  -> Service fails to start
```

### Resolution

The systemd unit **MUST** set `NINEROUTER_NODE_HEAP_MB=2048`:

```ini
[Service]
Environment="NINEROUTER_NODE_HEAP_MB=2048"
```

This caps the V8 heap at 2 GB, leaving 2 GB for OS, SQLite cache, and non-heap allocations.

### Verification

After deployment, verify the heap limit is active:

```bash
# Check systemd environment
systemctl show ninerouter --property=Environment

# Check Node.js heap in process
node -e "console.log(v8.getHeapStatistics().heap_size_limit / 1024 / 1024)"
# Should report ~2048 MB
```

### What Happens If This Is Missed

- **Immediate failure**: 9Router will OOM on startup.
- **No degradation**: It either starts (with heap limit) or doesn't (without).
- **No data loss**: SQLite WAL ensures database integrity even on OOM kill.
- **Detection**: Obvious -- service won't start, `dmesg` shows OOM kill.

---

## 10. Final Recommendation

### VERDICT: CONDITIONAL PASS

9Router v0.5.4 **can** run on a 2-core / 4 GB VPS, subject to mandatory conditions.

The capacity analysis confirms that the 2c/4GB hardware is sufficient for the target load of 1,000 req/min with typical coding request durations (10-30s). The primary constraint is memory, which is addressable by setting the heap limit.

### Confidence Level: MEDIUM

- Memory analysis is theoretical (based on Node.js V8 behavior patterns).
- Actual memory usage depends on 9Router's internal implementation.
- **A load test (Section 13) is mandatory before production use.**

---

## 11. Conditions for PASS

| # | Condition | Priority | Rationale |
|---|---|---|---|
| 1 | `NINEROUTER_NODE_HEAP_MB=2048` in systemd unit | **MANDATORY** | Without this, 12 GB default causes OOM on startup |
| 2 | Average request duration <= 30s | Expected | Typical for coding tasks; longer durations increase concurrency |
| 3 | Load test passes (Section 13) | **MANDATORY** | Validates theoretical analysis with real workload |
| 4 | usageHistory pruned (30-day retention) | Required | Prevents unbounded database growth |
| 5 | Swap monitoring enabled | Recommended | Early warning for memory pressure |
| 6 | Event loop lag monitoring | Recommended | Catches CPU-bound regression |

---

## 12. Fallback Plan

If load test fails or conditions cannot be met:

### Option A: Upgrade to 4c/8GB

| Spec | Current | Upgrade | Cost Impact |
|---|---|---|---|
| vCPUs | 2 | 4 | +2 cores |
| RAM | 4 GB | 8 GB | +4 GB |
| Default heap | 12 GB (blocked) | 12 GB (can allow up to 6 GB) | More headroom |

With 8 GB RAM:
- `NINEROUTER_NODE_HEAP_MB=6144` (6 GB heap) becomes viable.
- 8 GB = 6 GB heap + 1.5 GB SQLite cache + 500 MB OS = comfortable.
- No conditions required beyond basic monitoring.

### Option B: Horizontal Scale

- Deploy a second 2c/4GB instance behind a load balancer.
- Each instance handles ~500 req/min.
- More complex (Tailscale mesh, shared SQLite needs read replicas or external DB).

### Option C: Reduce Load Target

- If 1,000 req/min is not actually needed, reduce target to 500 req/min.
- At 500 req/min: L=250 concurrent (30s avg), memory ~575 MB.
- Very comfortable on 2c/4GB with 2 GB heap.

**Recommended fallback**: Option A (upgrade to 4c/8GB) -- simplest, most reliable.

---

## 13. Load Test Gate Requirements

### Test Configuration

| Parameter | Value | Notes |
|---|---|---|
| Duration | 5 minutes sustained | Not burst -- sustained throughput |
| Target rate | 1,000 req/min (16.7 req/sec) | Matches steady-state design target |
| Request type | Realistic coding prompts | Mix of short (5s) and long (30s) completions |
| Concurrent connections | 300-500 | Matches Little's Law prediction |
| Provider mix | Distributed across active providers | Not single-provider hammering |

### Pass Criteria

| Metric | Threshold | Failure Action |
|---|---|---|
| Memory (RSS) | < 3,000 MB | Upgrade to 4c/8GB |
| Memory (heap used) | < 1,800 MB (of 2,048 limit) | Investigate leak, or increase heap (and RAM) |
| CPU utilization | < 50% (across 2 cores) | Investigate event loop lag |
| Event loop lag | < 50 ms | Profile and optimize hot path |
| Error rate | 0% | Investigate root cause |
| Swap usage | 0 pages | Increase RAM or reduce heap |
| NINEROUTER_NODE_HEAP_MB respected | heap_size_limit <= 2048 MB | Fix systemd configuration |

### Test Commands

```bash
# Monitor during load test (run in separate terminal)
watch -n 1 'ps aux | grep ninerouter'
vmstat 1
iostat -x 1

# Check heap limit
node -e "
  const v8 = require('v8');
  const stats = v8.getHeapStatistics();
  console.log('Heap limit:', (stats.heap_size_limit / 1024 / 1024).toFixed(0), 'MB');
"

# SQLite monitoring
sqlite3 /path/to/ninerouter.db "PRAGMA page_count; PRAGMA freelist_count;"
```

### Post-Test Validation

1. Confirm all 5 pass criteria were met throughout the 5-minute window.
2. Check `journalctl -u ninerouter` for any warnings or errors.
3. Verify SQLite integrity: `sqlite3 db "PRAGMA integrity_check;"`.
4. Review `dmesg` for any OOM killer activity (should be empty).

---

## 14. Footer

- **Document**: P25-2c4GB Capacity Refresh
- **Version**: 1.0 (corrected from stale 0.4.71 analysis)
- **Status**: Research COMPLETE
- **Next step**: Operator approval, then load test implementation
- **Related**: P25 9Router deployment planning

---

*This analysis corrects the previous stale assessment that was based on 9Router v0.4.71 with incorrect heap assumptions. The corrected version (0.5.4) has a higher default heap (12 GB vs 6 GB), making the `NINEROUTER_NODE_HEAP_MB=2048` setting even more critical. The conditional pass verdict is maintained but with stricter mandatory conditions.*
