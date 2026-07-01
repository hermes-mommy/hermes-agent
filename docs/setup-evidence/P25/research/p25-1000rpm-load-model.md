# P25-1000 RPM: 9Router Mathematical Load Model

**Document:** P25 Research — 9Router Process Load Analysis
**Date:** 2026-06-25
**Status:** RESEARCH — Pre-implementation load model
**Scope:** 9Router process itself as a network bottleneck at 1000 requests/minute
**Out of scope:** Upstream provider throttling, GPU/LLM compute, model inference time

---

## 1. Executive Summary

This document presents a mathematical load model for 9Router (the HTTP proxy/router
process) serving Claude Code and OpenCode coding traffic at 1000 requests per minute
(~16.7 req/sec average, ~33.3 req/sec peak).

**Key findings:**

| Resource        | Capacity | Demand at 1000 RPM | Headroom       |
|-----------------|----------|---------------------|----------------|
| CPU             | 2 vCPU   | ~17% of 1 core      | 90%+ free      |
| Memory (4 GB)   | 4096 MB  | 1.7-3.2 GB          | 23-58% free    |
| Network         | 100 Mbps | ~9-19 Mbps           | 80%+ free      |
| SQLite writes   | ~1000/s  | ~33 writes/sec       | 97% free       |
| Event loop      | <10ms    | <10ms lag            | No risk        |
| File descriptors| 8192     | ~2000                | 75% free       |

**Primary risk:** Memory pressure at sustained high concurrency (L > 500 concurrent
requests in-flight). This occurs when average request duration exceeds 30 seconds at
full 1000 RPM load.

**Primary non-risks:** CPU, network bandwidth, SQLite throughput, event loop blocking.

**Verdict:** 9Router's 2 vCPU / 4 GB VPS can handle 1000 RPM for realistic coding
traffic patterns (W=20-30s average). At extreme concurrency (W=60s, L=1000) the
4 GB memory limit becomes the binding constraint. A 5-minute load test must verify
this before claiming P25 readiness.

---

## 2. Request Profile

### 2.1 Claude Code Characteristics

Claude Code is a CLI coding assistant that sends chat completion requests through
9Router to upstream LLM providers (Anthropic, OpenAI, etc.).

| Parameter           | Value                          | Notes                           |
|---------------------|--------------------------------|---------------------------------|
| Messages per turn   | 1-5                            | Multi-turn conversation         |
| Streaming           | YES (SSE)                      | Claude Code uses SSE streaming  |
| Request payload     | 5-50 KB                        | Includes system prompt + history|
| Response payload    | 1-100 KB                       | Code generation, explanations   |
| Request duration    | 10-60 seconds                  | LLM generation time             |
| Burst pattern       | Bursty                         | User sends, waits, sends next   |
| Connection reuse    | HTTP keep-alive                | Persistent connections          |

**Claude Code request lifecycle:**
1. Client opens TCP connection to 9Router
2. Client sends POST /v1/chat/completions (5-50 KB)
3. 9Router parses request, selects upstream, forwards
4. 9Router opens TCP connection to upstream provider
5. Upstream streams SSE chunks back
6. 9Router transforms SSE (extracts usage data), forwards to client
7. Stream ends, both connections return to keep-alive pool

### 2.2 OpenCode Characteristics

OpenCode is a similar CLI coding assistant with minor differences.

| Parameter           | Value                          | Notes                           |
|---------------------|--------------------------------|---------------------------------|
| Messages per turn   | 1-5                            | Similar to Claude Code          |
| Streaming           | MIXED                          | Some requests non-streaming     |
| Request payload     | 5-50 KB                        | Similar                         |
| Response payload    | 1-100 KB                       | Similar                         |
| Request duration    | 10-60 seconds                  | Similar                         |
| Burst pattern       | Bursty                         | Similar                         |

**Key difference:** OpenCode may use non-streaming requests for shorter completions.
Non-streaming requests hold the full response in 9Router's memory before forwarding,
increasing per-request memory overhead from ~1 MB to ~5 MB.

### 2.3 Combined Profile

For the load model we use a blended profile:

```
Weighted average payload:
  request  = 0.7 × 20KB + 0.3 × 20KB = 20 KB  (same for both)
  response = 0.8 × 50KB + 0.2 × 30KB = 46 KB  (streaming smaller on avg)

Blended request duration:
  W_avg = 0.5 × 25s + 0.5 × 25s = 25 seconds
  W_min = 10 seconds
  W_max = 60 seconds

Streaming ratio:
  P(streaming) = 0.85  (85% of requests are SSE streaming)
  P(non-streaming) = 0.15
```

---

## 3. Traffic Model

### 3.1 Arrival Rate

```
Target throughput: 1000 requests/minute

  lambda = 1000 / 60 = 16.67 req/sec (average)
```

### 3.2 Scenario A: Uniform (Baseline)

Uniform arrival is unrealistic but establishes a mathematical baseline.

```
lambda_uniform = 16.67 req/sec (constant)

Inter-arrival time:
  1 / lambda = 1 / 16.67 = 60 ms between requests

Poisson arrival probability of k requests in 1 second:
  P(k) = (lambda^k * e^(-lambda)) / k!

  P(0)  = 0.000000000008  (essentially zero)
  P(10) = 0.0219
  P(15) = 0.0914
  P(16) = 0.0952          (mode)
  P(17) = 0.0934
  P(20) = 0.0553
  P(25) = 0.0078
  P(30) = 0.0005

Standard deviation:
  sigma = sqrt(lambda) = sqrt(16.67) = 4.08 req/sec

So even under Poisson assumptions, 1-second windows vary from ~9 to ~25 req/sec.
```

### 3.3 Scenario B: Bursty (Realistic)

Realistic coding traffic is bursty. Users send a request, wait for the LLM to
respond, then send the next request. Multiple users create overlapping bursts.

```
Assumptions:
  N_users     = 10 concurrent users
  R_user      = 1-3 requests per user per minute
  B           = 2-5 requests per burst (user sends tool calls, file edits, etc.)
  B_interval  = 50-200ms between burst items

Average throughput:
  lambda_bursty = N_users * R_user / 60
                = 10 * 2 / 60
                = 0.33 req/sec per user
                = 3.33 req/sec total

Wait -- this is only 200 req/min. To reach 1000 req/min:

  N_users = 1000 / (R_user_per_min)
  If R_user = 2 req/min:  N_users = 50 concurrent users
  If R_user = 3 req/min:  N_users = 33 concurrent users
  If R_user = 5 req/min:  N_users = 20 concurrent users

Realistic scenario: 20-50 concurrent users, each generating 2-5 req/min.

Burst characteristics:
  B_size = 2-5 requests in <1 second
  B_gap  = 5-30 seconds between bursts per user

  Effective instantaneous rate during burst:
    lambda_burst = B_size / B_interval
                 = 3 / 0.1
                 = 30 req/sec (during burst)

  Effective instantaneous rate between bursts:
    lambda_idle = ~0 req/sec (waiting for LLM response)

  Time-averaged rate:
    lambda_avg = N_users * (B_size) / (B_interval + B_gap + W_avg)
               = 30 * 3 / (0.1 + 15 + 25)
               = 90 / 40.1
               = 2.24 req/sec per 30-user cohort

  To reach 16.67 req/sec average with 30 users:
    Need: 16.67 / (3/40.1) = ~223 simultaneous active conversations

  This is unrealistic for 20-50 users. Resolution:
  - During peak activity, many users are sending requests simultaneously
  - Overlapping bursts from different users create the effective throughput
  - A more realistic model:

    N_active = 1000 / (B_size / T_cycle)
    where T_cycle = B_interval + W_avg = 0.1 + 25 = 25.1 seconds
    N_active = 1000 / (3 / 25.1) = 1000 / 0.1195 = 8367 cycles/min
    But each cycle is from a different user-request:
    Actual concurrent conversations: lambda_avg * W_avg = 16.67 * 25 = 417

The bursty model reveals that at any instant, there are ~417 concurrent in-flight
requests (see Little's Law below), not 1000.
```

### 3.4 Scenario C: Peak (2x Average)

Peak traffic is 2x the sustained average, lasting 1-5 minutes.

```
lambda_peak = 2 * 16.67 = 33.33 req/sec

Duration: 1-5 minutes (e.g., a team of users all start work simultaneously)

Peak concurrency:
  L_peak = lambda_peak * W_avg = 33.33 * 25 = 833 concurrent requests

Peak connection count:
  C_peak = 2 * L_peak = 1666 TCP connections

Peak memory:
  M_peak = 200 + (L_peak * 3) = 200 + 2499 = ~2.7 GB
```

---

## 4. Concurrency Model (Little's Law)

### 4.1 Little's Law

```
L = lambda * W

where:
  L     = average number of requests in the system (concurrent)
  lambda = arrival rate (req/sec)
  W     = average time in system (seconds)
```

### 4.2 Concurrency Table

| Scenario      | lambda (req/sec) | W (sec) | L (concurrent) | Notes                    |
|---------------|-------------------|---------|-----------------|--------------------------|
| Uniform, fast | 16.67             | 10      | 167             | Short LLM responses      |
| Uniform, avg  | 16.67             | 25      | 417             | Typical coding tasks     |
| Uniform, slow | 16.67             | 30      | 500             | Complex code generation  |
| Uniform, max  | 16.67             | 60      | 1000            | Long-form generation     |
| Peak, fast    | 33.33             | 10      | 333             | Peak + short responses   |
| Peak, avg     | 33.33             | 25      | 833             | Peak + typical tasks     |
| Peak, slow    | 33.33             | 30      | 1000            | Peak + complex tasks     |
| Peak, max     | 33.33             | 60      | 2000            | Worst case (extreme)     |

### 4.3 Derivation Examples

**Baseline (uniform, avg response):**
```
L = 16.67 req/sec * 25 sec = 416.75 ≈ 417 concurrent requests
```

**Peak (2x, avg response):**
```
L = 33.33 req/sec * 25 sec = 833.25 ≈ 833 concurrent requests
```

**Worst case (peak, max response):**
```
L = 33.33 req/sec * 60 sec = 2000 concurrent requests
```

### 4.4 Concurrency Distribution

Under M/M/c queuing model assumptions (Poisson arrivals, exponential service):

```
Utilization:
  rho = lambda / (c * mu)
  where mu = 1/W = service rate per server
  c = number of servers (effectively unlimited for async proxy)

For a proxy (single process, async I/O), c is effectively 1 event loop,
but the event loop handles many concurrent I/O operations.

Effective rho = lambda * W_avg = L = 417

This means the "system" is handling 417 concurrent requests on average.
In a single-threaded async model, this is fine as long as:
  - No single synchronous operation blocks for too long
  - Memory is sufficient for all concurrent state
```

### 4.5 Concurrency Over Time

During a 5-minute load test at 1000 RPM:

```
Minute 0-1: Ramp up, L grows from 0 to ~417
Minute 1-4: Steady state, L ≈ 417 ± 150 (variance)
Minute 4-5: Ramp down, L decreases

  Variance in L:
  Var(L) ≈ lambda * W^2 * (C_s^2 + C_a^2) / 2
  where C_s = coefficient of variation of service time
  and C_a = coefficient of variation of arrival time

  For Poisson arrivals: C_a = 1
  For coding traffic: C_s ≈ 0.5 (moderate variance in LLM response time)

  Var(L) ≈ 16.67 * 25^2 * (0.25 + 1) / 2
         = 16.67 * 625 * 0.625
         = 6512
  StdDev(L) ≈ 81

  So L fluctuates between ~336 and ~498 (1 sigma) during steady state.
```

---

## 5. Connection Model

### 5.1 Connection Architecture

Each in-flight request uses two TCP connections:

```
Client --[TCP]--> 9Router --[TCP]--> Upstream Provider

Per request:
  1 incoming connection  (client -> 9Router)
  1 outgoing connection  (9Router -> upstream)

With HTTP keep-alive, connections are reused across requests.
But concurrent requests each need their own connection.

Total connections at concurrency L:
  C = 2 * L
```

### 5.2 Connection Count Table

| Concurrency (L) | Incoming | Outgoing | Total (C) | FDs Needed |
|------------------|----------|----------|-----------|------------|
| 167              | 167      | 167      | 334       | ~400       |
| 417              | 417      | 417      | 834       | ~900       |
| 500              | 500      | 500      | 1000      | ~1100      |
| 833              | 833      | 833      | 1666      | ~1800      |
| 1000             | 1000     | 1000     | 2000      | ~2200      |
| 2000 (worst)     | 2000     | 2000     | 4000      | ~4200      |

### 5.3 File Descriptor Limits

```
Default ulimit -n on Ubuntu 24.04: 1024 (soft) / 8192 (hard)
Configured (if tuned): 8192

FDs needed = C + overhead
  overhead = ~200 (SQLite, logs, stdout/stderr, internal pipes)
  FDs = 2*L + 200

At L=500:  FDs = 1200 < 8192  ✓
At L=1000: FDs = 2200 < 8192  ✓
At L=2000: FDs = 4200 < 8192  ✓
At L=4000: FDs = 8200 > 8192  ✗ (exhausted)

FD exhaustion threshold:
  L_max_fd = (8192 - 200) / 2 = 3996 concurrent requests
```

### 5.4 TCP Buffer Memory

Each TCP connection consumes kernel buffer memory:

```
Per connection:
  Send buffer: ~16 KB (default tcp_wmem min)
  Receive buffer: ~87 KB (default tcp_rmem max)
  Socket overhead: ~2 KB
  Total: ~105 KB per connection

At C=1000 connections:
  Kernel TCP buffers = 1000 * 105 KB = 105 MB

At C=2000 connections:
  Kernel TCP buffers = 2000 * 105 KB = 210 MB

Note: This is kernel memory, not Node.js heap. It counts against the
system's total memory, not V8's heap limit.
```

---

## 6. Memory Model

### 6.1 Memory Formula

```
M(L) = M_base + L * M_per_request

where:
  M_base        = 200 MB (Node.js heap + Next.js runtime + SQLite cache)
  M_per_request = 3 MB (connection buffers + request context + stream state)
  L             = concurrent requests in flight

Breakdown of M_per_request:
  Incoming buffer/parse state:    0.5 MB
  Outgoing buffer/header state:   0.5 MB
  SSE transform stream state:     1.0 MB (accumulated content chunks)
  Provider routing metadata:      0.3 MB
  Request/response JSON objects:  0.7 MB
  Total per request:              3.0 MB
```

### 6.2 Memory Consumption Table

| L    | M_base  | L * M_per | Total M   | % of 4 GB | Status   |
|------|---------|-----------|-----------|-----------|----------|
| 100  | 200 MB  | 300 MB    | 500 MB    | 12.2%     | Safe     |
| 167  | 200 MB  | 501 MB    | 701 MB    | 17.1%     | Safe     |
| 300  | 200 MB  | 900 MB    | 1.1 GB    | 26.9%     | Safe     |
| 417  | 200 MB  | 1251 MB   | 1.45 GB   | 35.4%     | Safe     |
| 500  | 200 MB  | 1500 MB   | 1.7 GB    | 41.5%     | OK       |
| 833  | 200 MB  | 2499 MB   | 2.7 GB    | 65.9%     | Tight    |
| 1000 | 200 MB  | 3000 MB   | 3.2 GB    | 78.1%     | Risky    |
| 2000 | 200 MB  | 6000 MB   | 6.2 GB    | 151%      | FAIL     |

### 6.3 V8 Heap Limit

```
Node.js V8 default heap limit: ~1.5 GB (can be raised with --max-old-space-size)

If V8 heap exceeds this, Node.js crashes with "JavaScript heap out of memory".

At L=500, application-level memory = 1.7 GB
  - Kernel TCP buffers are outside V8 heap: ~105 MB
  - V8 heap = 1.7 GB - ~0.1 GB (kernel) + base heap overhead
  - V8 heap ≈ 1.5 GB -- at the default limit

Mitigation: Set --max-old-space-size=3072 to allow 3 GB V8 heap.
```

### 6.4 Non-Streaming Request Overhead

Non-streaming requests buffer the entire response before forwarding:

```
Non-streaming per-request overhead:
  Response buffer: up to 5 MB (vs 1 MB for streaming)

If 15% of requests are non-streaming (OpenCode):
  L_ns = 0.15 * L = 0.15 * 500 = 75 non-streaming requests
  Extra memory = 75 * 4 MB = 300 MB additional

Adjusted formula:
  M(L) = M_base + L_s * 2.5 + L_ns * 6.5
  where L_s = streaming requests, L_ns = non-streaming requests
  and L = L_s + L_ns

At L=500 (85% streaming):
  M = 200 + (425 * 2.5) + (75 * 6.5)
    = 200 + 1062.5 + 487.5
    = 1750 MB = 1.75 GB
```

### 6.5 Memory Growth Under Pressure

When memory is high, Node.js GC becomes more aggressive:

```
GC pause time (V8 generational GC):
  Minor GC (young generation): < 5 ms
  Major GC (old generation):   10-100 ms (proportional to live heap)

At 2 GB heap:
  Major GC pause ≈ 50-100 ms
  Major GC frequency: every 5-10 seconds

Impact: During major GC, event loop is blocked.
  If GC pause = 100 ms every 10 seconds:
  GC overhead = 100ms / 10000ms = 1% -- acceptable
```

---

## 7. CPU Model

### 7.1 Per-Request CPU Work

9Router's CPU work per request is minimal -- it is a proxy, not an inference engine.

```
Per-request CPU breakdown:
  HTTP request parsing:        2-3 ms
  Header manipulation:         1-2 ms
  Route selection:             <1 ms
  JSON body parse (request):   3-5 ms
  SSE chunk parsing:           1-2 ms per chunk * 50-200 chunks = 50-400 ms total
  Usage extraction per chunk:  <0.1 ms per chunk
  JSON body parse (response):  5-10 ms (if non-streaming)
  SQLite write (async):        <1 ms (scheduled, not blocking)
  Total CPU per request:       ~10-50 ms (depending on response length)

Note: SSE chunk forwarding is I/O-bound, not CPU-bound.
The actual CPU work per chunk is < 0.1 ms.
```

### 7.2 CPU Utilization

```
CPU-seconds per second:
  CPU_rate = lambda * CPU_per_request
           = 16.67 req/sec * 0.010 sec  (minimum, short responses)
           = 0.167 CPU-sec/sec = 16.7% of 1 core

  CPU_rate = lambda * CPU_per_request
           = 16.67 req/sec * 0.050 sec  (maximum, long responses)
           = 0.833 CPU-sec/sec = 83.3% of 1 core

Realistic estimate:
  CPU_rate = 16.67 * 0.015 = 0.25 CPU-sec/sec = 25% of 1 core

With 2 vCPUs:
  System CPU utilization = 25% / 2 = 12.5% total CPU
```

### 7.3 CPU at Peak

```
Peak (33.33 req/sec):
  CPU_rate = 33.33 * 0.050 = 1.67 CPU-sec/sec = 167% of 1 core
  With 2 vCPUs: 83.5% total CPU -- still under 100%, but getting warm.

  At realistic (33.33 * 0.015 = 0.5 CPU-sec/sec):
  With 2 vCPUs: 25% total CPU -- comfortable.
```

### 7.4 CPU Bottleneck Threshold

```
CPU bottleneck at 80% utilization:
  Max lambda = 0.80 * 2 vCPUs / CPU_per_request
             = 1.6 / 0.015
             = 106.7 req/sec
             = 6400 req/min

CPU is not the bottleneck until ~6400 req/min (6.4x our target).
```

---

## 8. SQLite Write Model

### 8.1 Write Operations Per Request

9Router writes to SQLite for each request:

```
Per-request writes:
  1. usageHistory INSERT   (per request, immediate)
  2. requestDetails INSERT (batched: 20 records or 5 second timer)

Effective write rate:
  usageHistory:    1 write per request
  requestDetails:  1 write per 20 requests (batched)
  Total effective: 1 + 1/20 = 1.05 writes per request

At 16.67 req/sec:
  usageHistory writes:    16.67 writes/sec
  requestDetails writes:  16.67 / 20 = 0.83 writes/sec
  Total:                  17.5 writes/sec
```

### 8.2 SQLite WAL Mode Throughput

```
SQLite WAL (Write-Ahead Logging) performance:
  Single-row INSERT: 1000-10000 writes/sec on SSD
  Batched INSERT:    5000-50000 writes/sec on SSD

Our demand: 17.5 writes/sec
SQLite capacity: ~5000 writes/sec (conservative)
Utilization: 17.5 / 5000 = 0.35%

SQLite is NOT a bottleneck.
```

### 8.3 SQLite WAL Checkpoint Impact

```
WAL checkpoint (automatic):
  Frequency: every 1000 pages (~4 MB by default)
  Duration: 1-10 ms
  Blocking: Checkpoint blocks writers briefly

At 17.5 writes/sec with ~200 bytes per row:
  WAL growth: 17.5 * 200 = 3500 bytes/sec = 3.5 KB/sec
  Checkpoint every: 4096 KB / 3.5 KB/sec = ~1170 seconds (~19 minutes)

Checkpoint is infrequent and brief. No impact.
```

### 8.4 SQLite Database Size Growth

```
Per request storage:
  usageHistory:   ~200 bytes
  requestDetails: ~500 bytes
  Total per request: ~700 bytes

At 1000 req/min:
  Per minute: 1000 * 700 = 700 KB
  Per hour:   700 * 60 = 42 MB
  Per day:    42 * 24 = 1008 MB ≈ 1 GB/day

At this rate, database management (rotation, archival) becomes important
within days. This is not a 9Router bottleneck but an operational concern.
```

---

## 9. Network Throughput Model

### 9.1 Bandwidth Per Request

```
Request (client -> 9Router):
  HTTP headers: ~1 KB
  Body (chat completion): 5-50 KB
  Average: 20 KB

Response (9Router -> client):
  HTTP headers: ~0.5 KB
  SSE stream (total): 1-100 KB
  Average: 50 KB

Total per request: 20 + 50 = 70 KB
```

### 9.2 Throughput Calculation

```
At lambda = 16.67 req/sec:
  Throughput = 16.67 * 70 KB = 1166.9 KB/sec = ~1.14 MB/sec = ~9.1 Mbps

At lambda = 33.33 req/sec (peak):
  Throughput = 33.33 * 70 KB = 2333.1 KB/sec = ~2.28 MB/sec = ~18.2 Mbps

Including upstream traffic (9Router -> provider):
  Upstream request:  ~20 KB per request
  Downstream response: ~50 KB per request
  Total network: ~140 KB per request (both directions)

  At 16.67 req/sec: 16.67 * 140 = 2333.8 KB/sec = ~2.28 MB/sec = ~18.2 Mbps
  At 33.33 req/sec: 33.33 * 140 = 4666.2 KB/sec = ~4.56 MB/sec = ~36.5 Mbps
```

### 9.3 Network Bottleneck Assessment

```
Tailscale VPN typical throughput: 100-1000 Mbps
VPS network: typically 1-10 Gbps

Demand at peak: ~36.5 Mbps
Available: 100+ Mbps (conservative)

Utilization: 36.5 / 100 = 36.5%

Network is NOT a bottleneck.
Even at 5x peak (166.67 req/sec), network would be at ~182 Mbps -- still
within Tailscale's capacity on modern hardware.
```

### 9.4 SSE Streaming Bandwidth Pattern

SSE streaming creates a distinctive bandwidth pattern:

```
During an active SSE stream (10-60 seconds):
  Steady-state: ~5-10 KB/sec per stream
  Chunk arrival: bursty -- provider sends chunks in groups

At L=500 concurrent streams:
  Steady-state: 500 * 7.5 KB/sec = 3750 KB/sec = ~3.66 MB/sec = ~29.3 Mbps

This is the bandwidth at any instant when all 500 requests are actively
streaming (mid-response). Still well within capacity.
```

---

## 10. Event Loop Model

### 10.1 Node.js Event Loop Architecture

```
9Router runs on a single Node.js event loop (main thread):

Event loop phases:
  1. Timers (setTimeout, setInterval)
  2. Pending callbacks (I/O deferred to next loop)
  3. Idle, prepare (internal)
  4. Poll (I/O -- incoming data, completed requests)
  5. Check (setImmediate)
  6. Close callbacks

All I/O operations (HTTP forwarding, SQLite reads/writes) are async
and do NOT block the event loop. They are handled by libuv's thread pool
or OS-level async I/O.

Synchronous operations that DO block the event loop:
  - JSON.parse() / JSON.stringify()
  - String manipulation
  - Header parsing
  - SSE line parsing (minimal)
```

### 10.2 Event Loop Lag Analysis

```
Synchronous CPU per request (the blocking part):
  JSON parse (request body):    3-5 ms
  SSE chunk line parsing:       0.1 ms per chunk * 100 chunks = 10 ms total
  JSON stringify (if any):      2-3 ms
  Total sync CPU per request:   ~15 ms

At 16.67 req/sec:
  Event loop blocked time = 16.67 * 15 ms = 250 ms/sec

  But this is spread over time. If requests arrive uniformly:
    250 ms / 1000 ms = 25% event loop utilization

  If requests arrive in bursts:
    Worst case: 5 requests in 100ms = 5 * 15ms = 75ms block
    This means 75ms of lag before next event can be processed.
```

### 10.3 Event Loop Lag Threshold

```
Healthy event loop lag: < 10 ms
Degraded performance:   10-50 ms
Critical:               > 50 ms (requests start timing out)

Maximum synchronous work before event loop lag exceeds 50 ms:
  If lambda_burst = 30 req/sec during burst:
    Sync work = 30 * 15 ms = 450 ms/sec = 45% utilization
    Spread over 1 second: no single 50ms block

  Worst case: 5 requests arrive simultaneously, each needing 15 ms:
    Block time = 5 * 15 = 75 ms > 50 ms threshold

  Mitigation: This is unlikely because HTTP parsing is incremental.
  By the time the body is fully received and parsed, other I/O callbacks
  have had opportunities to run.
```

### 10.4 Large Payload Risk

```
JSON.parse() complexity: O(n) where n = payload size

Parsing time estimates:
  20 KB payload:   ~3 ms
  50 KB payload:   ~8 ms
  100 KB payload:  ~15 ms
  500 KB payload:  ~80 ms   <-- DANGER: blocks event loop
  1 MB payload:    ~160 ms  <-- CRITICAL

At 1000 RPM, if 1% of requests have 500 KB payloads:
  10 requests/min with 80 ms block = 800 ms/min of blocking
  Per second: 800/60 = 13.3 ms/sec -- acceptable on average
  But if 3 arrive simultaneously: 240 ms block -- CRITICAL

Mitigation: Set maximum request body size limit (e.g., 500 KB).
Claude Code and OpenCode payloads are typically < 50 KB, so this
is an edge case with crafted payloads, not normal traffic.
```

---

## 11. Streaming Model

### 11.1 SSE Transform Architecture

```
For each streaming request, 9Router creates a TransformStream:

  Upstream Provider
       |
       | SSE chunks (data: {...}\n\n)
       v
  [TransformStream] ---- parses SSE framing
       |                 extracts usage tokens
       |                 accumulates content
       v
  Client (Claude Code / OpenCode)

Per-stream state:
  SSE parse buffer:       ~1 KB
  Accumulated content:    ~0.5-50 KB (grows with response)
  Usage accumulator:      ~0.5 KB
  Stream bookkeeping:     ~0.5 KB
  Total per stream:       ~1-51 KB (varies with response length)

At average response = 50 KB:
  Per-stream memory: ~5 MB (including Node.js object overhead)
```

### 11.2 Stream Lifetime

```
Stream lifetime = upstream request duration = 10-60 seconds

During this time:
  - 1 TCP connection is held open to upstream
  - 1 TCP connection is held open to client
  - TransformStream processes chunks as they arrive
  - Memory grows as content accumulates

Concurrent streams at L=500:
  500 streams, each holding ~5 MB = 2.5 GB of stream state alone

This is the primary memory consumer at high concurrency.
```

### 11.3 Provider Stall Risk

```
If the upstream provider stalls (no data for >30 seconds):
  - The TCP connection remains open
  - The TransformStream remains allocated
  - Memory is held but not released
  - Client may time out, but 9Router doesn't know until the client
    closes the connection or the upstream timeout fires

Timeout chain:
  Client timeout:     typically 120-300 seconds
  9Router timeout:    configurable, typically 120 seconds
  Upstream timeout:   provider-specific, typically 120-300 seconds

Risk: If 100 requests stall for 120 seconds:
  Extra memory held: 100 * 5 MB = 500 MB
  Extra connections: 100 * 2 = 200 TCP connections

This is manageable but contributes to memory pressure.
```

### 11.4 Stream Error Handling

```
If a stream errors mid-response:
  1. Upstream sends error event or closes connection
  2. 9Router must forward error to client
  3. Both connections should be cleaned up
  4. Memory for stream state is released (GC)

If cleanup fails (bug or race condition):
  - Stream state leaks: ~5 MB per leaked stream
  - Connection leaks: 2 TCP connections per leak
  - At scale, this would be catastrophic

This is not a load model concern but an implementation correctness concern.
Verified by the P25 load test.
```

---

## 12. Bottleneck Identification

### 12.1 What IS a 9Router Bottleneck

| Bottleneck     | Threshold      | At 1000 RPM | Risk Level |
|----------------|----------------|-------------|------------|
| **Memory**     | 3.5 GB (of 4) | 1.7-3.2 GB  | **MEDIUM** |
| **FDs**        | 8192           | ~2000       | Low        |
| **GC pauses**  | >50ms          | ~10-50ms    | Low        |
| **Event loop** | >50ms lag      | <10ms       | Low        |

**Memory is the primary constraint.** At L > 500 (W > 30s), memory usage
exceeds 60% of available 4 GB. At L=1000 (W=60s), memory reaches 78%
and GC pressure increases.

### 12.2 What is NOT a 9Router Bottleneck

| Resource             | Why Not                                                    |
|----------------------|------------------------------------------------------------|
| Model/provider       | Upstream throttling is outside 9Router's control           |
| GPU/LLM compute      | 9Router is a proxy, not an inference engine                |
| CPU (2 vCPU)         | 9Router is I/O-bound, not compute-bound                   |
| Network bandwidth    | 9-36 Mbps vs 100+ Mbps available                          |
| SQLite writes        | 17 writes/sec vs 5000+ capacity                           |
| Event loop           | <10ms lag with normal payloads                            |
| TCP connections      | ~2000 vs 8192 FD limit                                    |

### 12.3 Cascade Failure Modes

```
Mode 1: Memory pressure cascade
  High L -> high memory -> aggressive GC -> event loop pauses ->
  delayed responses -> more concurrent requests (waiting) -> higher L ->
  more memory -> OOM crash

  Trigger: L sustained > 800 for > 5 minutes
  Detection: memory > 3.5 GB, GC pause > 100ms
  Mitigation: Set max concurrency limit (e.g., 500), reject excess

Mode 2: Connection exhaustion cascade
  High L -> FD limit reached -> new connections fail ->
  Client retries -> more connection attempts -> all fail

  Trigger: L > 3996 (FD limit)
  Detection: "EMFILE: too many open files" errors
  Mitigation: Set max concurrency limit, tune ulimit

Mode 3: Event loop stall cascade
  Large payload -> JSON.parse blocks event loop -> I/O callbacks delayed ->
  upstream timeouts -> retry storms -> more requests -> more blocking

  Trigger: Single payload > 500 KB
  Detection: event loop lag > 100ms
  Mitigation: Set max request body size to 500 KB
```

---

## 13. Load Test Requirements

### 13.1 Test Configuration

```
Duration:           5 minutes sustained
Throughput:         1000 req/min (16.67 req/sec)
Payload:            Realistic chat completion requests (20 KB avg)
Responses:          Simulated LLM responses (50 KB avg, streaming)
Concurrency cap:    Monitor, do not cap (to see natural concurrency)
```

### 13.2 Acceptance Criteria

| Metric                | Threshold                  | Measurement          |
|-----------------------|----------------------------|----------------------|
| p99 latency overhead  | < 100 ms above provider    | End-to-end timing    |
| p50 latency overhead  | < 20 ms above provider     | End-to-end timing    |
| Error rate            | 0%                         | HTTP 5xx count       |
| Memory (RSS)          | < 3 GB                     | Process RSS          |
| V8 Heap               | < 2.5 GB                   | process.memoryUsage()|
| CPU utilization       | < 50% total                | /proc/stat or top    |
| Event loop lag        | < 50 ms (p99)              | Event loop monitor   |
| GC pause              | < 100 ms (p99)             | --trace-gc logs      |
| SQLite errors         | 0                          | Error logs           |
| FD usage              | < 5000                     | /proc/PID/fd count   |

### 13.3 Monitoring During Test

```
Collect every 5 seconds:
  - process.memoryUsage() (rss, heapUsed, heapTotal, external)
  - Event loop lag (via monitorEventLoopDelay or manual measurement)
  - Active connections (netstat count)
  - Request throughput (requests completed in last 5s)
  - Error count (cumulative)
  - SQLite write count (cumulative)

Collect per-request:
  - Request arrival timestamp
  - Response start timestamp (first SSE chunk)
  - Response end timestamp
  - HTTP status code
  - Response size
  - Error (if any)
```

### 13.4 Test Tool

```
Recommended: autocannon or k6

autocannon configuration:
  -c 200           # 200 concurrent connections
  -d 300           # 300 seconds (5 minutes)
  -p 10            # 10 pipelining (simulates bursty users)
  -m POST          # POST method
  -b '{"model":"test","messages":[{"role":"user","content":"test"}]}'
  -H "Content-Type: application/json"

Or custom test script using fetch() with controlled rate:
  Target: 16.67 requests per second
  Burst: 5 requests in 100ms, then 5s pause, repeat
  Duration: 5 minutes
```

---

## 14. Key Assumptions and Limitations

### 14.1 Assumptions

```
1. VPS: 2 vCPU, 4 GB RAM, Ubuntu 24.04
2. Node.js version: 20+ (modern V8, good GC)
3. 9Router is the ONLY process consuming significant resources
4. Upstream providers respond within 120 seconds
5. HTTP keep-alive is enabled for both client and upstream connections
6. SQLite is in WAL mode
7. Network is Tailscale VPN with >100 Mbps throughput
8. No TLS termination at 9Router (handled by reverse proxy or Tailscale)
9. ulimit -n is set to at least 8192
10. Request payloads are < 500 KB (normal coding traffic)
```

### 14.2 Limitations of This Model

```
1. Little's Law assumes steady state -- does not model ramp-up/ramp-down
2. Memory model is approximate -- actual Node.js memory is fragmented and
   includes V8 internal structures not accounted for here
3. CPU model assumes I/O-bound workload -- if 9Router does significant
   synchronous processing (validation, transformation), CPU could be higher
4. Does not model upstream failures or retry behavior
5. Does not model TLS overhead (minimal with Tailscale, but nonzero)
6. Does not model kernel-level network stack overhead
7. Does not account for other processes on the VPS (systemd, monitoring, etc.)
8. GC behavior is highly workload-dependent -- actual pauses may vary
9. Streaming model assumes uniform chunk sizes -- real SSE chunks vary
10. Does not model WebSocket or long-polling (if any)
```

### 14.3 When This Model Breaks Down

```
This model is valid for:
  - 1000 RPM sustained for 5-30 minutes
  - Normal coding traffic payloads (< 50 KB)
  - Streaming-dominant workload (> 80% SSE)
  - Single 9Router process

This model BREAKS DOWN when:
  - Sustained rate exceeds 2000 RPM (memory exhaustion)
  - Payloads exceed 500 KB (event loop blocking)
  - Non-streaming ratio exceeds 50% (memory pressure from buffering)
  - Multiple 9Router instances are needed (horizontal scaling model)
  - Upstream provider fails, causing connection pileup
```

---

## 15. Summary Table

| Dimension          | Formula                           | At 1000 RPM (avg) | At 1000 RPM (peak 2x) |
|--------------------|-----------------------------------|--------------------|------------------------|
| Arrival rate       | lambda                            | 16.67 req/sec      | 33.33 req/sec          |
| Concurrency        | L = lambda * W (W=25s)           | 417                | 833                    |
| TCP connections    | C = 2L                            | 834                | 1666                   |
| Memory             | 200 + L * 3 (MB)                 | 1.45 GB            | 2.7 GB                 |
| CPU utilization    | lambda * 15ms / 2000ms            | 12.5%              | 25%                    |
| Network            | lambda * 140 KB * 8               | 18.2 Mbps          | 36.5 Mbps              |
| SQLite writes      | lambda * 1.05                     | 17.5/sec           | 35/sec                 |
| Event loop lag     | lambda * 15ms burst               | <10 ms             | <20 ms                 |
| File descriptors   | 2L + 200                          | 1034               | 1866                   |

**Binding constraint: Memory at 4 GB.**

Sufficient for L <= 500 (W <= 30s at 1000 RPM, or W <= 15s at peak 2x).

---

## Footer

- **Document:** P25-1000rpm-load-model.md
- **Created:** 2026-06-25
- **Purpose:** Mathematical load model for 9Router at 1000 requests/minute
- **Next step:** Implement load test (Section 13) to validate model predictions
- **Related:** P25 definition, P20 soak monitoring, 9Router architecture docs
