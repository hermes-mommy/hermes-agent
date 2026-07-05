# P25 Load Test Design: 9Router v0.5.4 on 2c/4GB VPS

**Document**: P25 Load Test Design Refresh
**Date**: 2026-06-26
**Status**: DESIGN — not yet executed
**Target**: 9Router v0.5.4 on VPS (2 vCPU, 4 GB RAM, Ubuntu 24.04)

---

## 1. Executive Summary

This document designs a comprehensive load test for 9Router v0.5.4 running on a 2-core / 4 GB VPS. The core objective is to verify that 9Router can sustain **1000 requests per minute** as a reverse-proxy layer without exceeding system resources or burning provider API quota.

The design uses a **mock upstream server** that returns OpenAI-compatible streaming responses. This isolates the test to 9Router's proxy overhead — connection management, request routing, header rewriting, SSE streaming, and event-loop pressure — without incurring any LLM inference cost. A small real-provider smoke test (10-20 requests, ~$0.05 total) validates end-to-end wiring separately.

The test suite consists of five phases:

| Phase | Goal | Duration |
|-------|------|----------|
| 0 | Health check | 1 min |
| 1 | Sustained load at 1000 req/min via mock | 5 min |
| 2 | Burst at 3000 req/min via mock | 30 sec |
| 3 | 100 concurrent streaming connections | 5 min |
| 4 | Real-provider smoke (10-20 requests) | 2 min |
| 5 | Results analysis | post-test |

Pass/fail is determined by a hard gate on error rate (< 1%), p95 latency (< 200 ms proxy overhead), memory (< 3 GB RSS), and zero SQLite errors. If any gate fails, the VPS is not production-ready for the target load.

---

## 2. Test Philosophy: Proxy Overhead, Not Provider Latency

### Why This Distinction Matters

9Router is a **reverse proxy**, not an LLM. Its job is to receive requests, route them to the correct upstream provider, stream responses back, and handle auth/rate-limiting/usage tracking. The latency a user perceives is:

```
User → 9Router → Provider → 9Router → User
         ^^^^^^
         This is what we measure
```

The provider's inference time (often 1-30 seconds) dwarfs 9Router's proxy overhead (expected 5-50 ms). Running 1000 req/min against real providers would:

1. **Burn provider quota** — DeepSeek, OpenRouter, and MiMo all bill per token
2. **Conflate provider latency with proxy overhead** — impossible to isolate
3. **Risk rate-limit bans** — hitting providers at 17 req/sec is aggressive
4. **Cost real money** — even cheap providers accumulate at this rate

### What the Mock Upstream Tests

By replacing the provider with a mock server that returns instant (or configurable-delay) responses, we isolate:

- **Connection handling**: Can 9Router maintain 50-200 concurrent HTTP connections?
- **Event-loop throughput**: Does Node.js event loop lag under 17 req/sec sustained?
- **Memory management**: Do streaming connections leak memory over 5+ minutes?
- **Error handling**: Does 9Router return clean errors when overloaded?
- **Header/protocol fidelity**: Are OpenAI-compatible responses passed through correctly?
- **SQLite pressure**: Does the usage ledger stay healthy under concurrent writes?

### What the Mock Upstream Does NOT Test

- Real provider API latency variations
- Provider-specific error formats (429, 500, context-length errors)
- Token counting accuracy against real models
- Actual LLM output quality

These are tested separately in the small real-provider smoke test (Phase 4).

---

## 3. Mock Upstream Design

### Requirements

The mock upstream must:

1. Listen on a configurable port (default: `20129`)
2. Accept `POST /v1/chat/completions` — matching the OpenAI API shape
3. Return SSE-formatted streaming responses identical to OpenAI's format
4. Support configurable response latency (simulating different provider speeds)
5. Return realistic `usage` fields (prompt_tokens, completion_tokens, total_tokens)
6. Handle concurrent connections (up to 200 simultaneous)
7. Be stateless — no request correlation needed

### Server Implementation

```javascript
// mock-upstream.js
// Lightweight mock OpenAI-compatible streaming server for load testing.
// Run: node mock-upstream.js
// Default port: 20129

const http = require('http');

// Configurable delay between SSE chunks (ms). Adjust to simulate provider speed.
const CHUNK_DELAY_MS = parseInt(process.env.MOCK_CHUNK_DELAY || '50', 10);
const PORT = parseInt(process.env.MOCK_PORT || '20129', 10);

// Mock response content — short enough to be fast, long enough to be realistic.
const MOCK_CONTENT = 'This is a mock response for load testing purposes. ' +
  'The quick brown fox jumps over the lazy dog. ' +
  'Lorem ipsum dolor sit amet, consectetur adipiscing elit.';

let requestCount = 0;

const server = http.createServer((req, res) => {
  // CORS headers for flexibility
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.url === '/v1/chat/completions' && req.method === 'POST') {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
      let parsed;
      try {
        parsed = JSON.parse(body);
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { message: 'Invalid JSON', type: 'invalid_request_error' } }));
        return;
      }

      const responseId = `chatcmpl-mock-${Date.now()}-${requestCount++}`;
      const model = parsed.model || 'mock-model';
      const words = MOCK_CONTENT.split(' ');
      const isStream = parsed.stream === true;

      if (isStream) {
        // --- Streaming response (SSE) ---
        res.writeHead(200, {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'X-Request-Id': responseId,
        });

        // First chunk: role assignment
        res.write(`data: ${JSON.stringify({
          id: responseId,
          object: 'chat.completion.chunk',
          created: Math.floor(Date.now() / 1000),
          model,
          choices: [{
            index: 0,
            delta: { role: 'assistant', content: '' },
            finish_reason: null,
          }],
        })}\n\n`);

        // Content chunks with configurable delay
        let i = 0;
        const interval = setInterval(() => {
          if (i >= words.length) {
            clearInterval(interval);

            // Final chunk with usage data
            res.write(`data: ${JSON.stringify({
              id: responseId,
              object: 'chat.completion.chunk',
              created: Math.floor(Date.now() / 1000),
              model,
              choices: [{
                index: 0,
                delta: {},
                finish_reason: 'stop',
              }],
              usage: {
                prompt_tokens: 25,
                completion_tokens: words.length,
                total_tokens: 25 + words.length,
              },
            })}\n\n`);

            res.write('data: [DONE]\n\n');
            res.end();
            return;
          }

          res.write(`data: ${JSON.stringify({
            id: responseId,
            object: 'chat.completion.chunk',
            created: Math.floor(Date.now() / 1000),
            model,
            choices: [{
              index: 0,
              delta: { content: words[i] + ' ' },
              finish_reason: null,
            }],
          })}\n\n`);
          i++;
        }, CHUNK_DELAY_MS);

        // Handle client disconnect
        req.on('close', () => {
          clearInterval(interval);
        });

      } else {
        // --- Non-streaming response ---
        res.writeHead(200, {
          'Content-Type': 'application/json',
          'X-Request-Id': responseId,
        });

        res.end(JSON.stringify({
          id: responseId,
          object: 'chat.completion',
          created: Math.floor(Date.now() / 1000),
          model,
          choices: [{
            index: 0,
            message: { role: 'assistant', content: MOCK_CONTENT },
            finish_reason: 'stop',
          }],
          usage: {
            prompt_tokens: 25,
            completion_tokens: words.length,
            total_tokens: 25 + words.length,
          },
        }));
      }
    });

  } else if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', requests_served: requestCount }));

  } else {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: { message: 'Not found' } }));
  }
});

server.listen(PORT, () => {
  console.log(`Mock upstream running on http://localhost:${PORT}`);
  console.log(`  Chunk delay: ${CHUNK_DELAY_MS}ms`);
  console.log(`  Endpoint: POST /v1/chat/completions`);
});
```

### Mock Upstream Rationale

| Decision | Reason |
|----------|--------|
| Node.js (not Python) | Minimal dependencies; same runtime as 9Router; avoids Python startup overhead |
| Configurable `CHUNK_DELAY_MS` | Lets us simulate fast (10ms) and slow (30s) providers via env var |
| 12-word response | ~500ms streaming at 50ms/chunk; enough to test SSE without being slow |
| `/health` endpoint | Lets monitoring scripts confirm mock is alive before test |
| Stateless | No request logging; pure throughput target; avoids memory accumulation |
| `X-Request-Id` header | Lets us correlate requests if needed for debugging |

### Configuring 9Router to Use Mock Upstream

Before running load tests, 9Router must be configured with a provider pointing to the mock server. Add a provider entry in 9Router's config:

```yaml
# In 9Router config — add a mock provider
providers:
  mock:
    base_url: http://127.0.0.1:20129/v1
    api_key: mock-key-not-used
    models:
      - mock-model
```

The k6 scripts then target `mock/mock-model` as the model name, and 9Router routes those requests to the mock upstream.

### Delay Configuration Matrix

| `MOCK_CHUNK_DELAY` | 12-word response time | Use case |
|---------------------|-----------------------|----------|
| 10ms | ~120ms | Baseline proxy overhead measurement |
| 50ms | ~600ms | Default; realistic fast-provider simulation |
| 100ms | ~1.2s | Medium-latency provider simulation |
| 500ms | ~6s | Slow provider simulation |
| 1000ms | ~12s | Very slow provider (GPT-5-class reasoning) |
| 5000ms | ~60s | Extreme long-tail; tests connection timeout handling |

For the primary load test, use **50ms** (default). Run a quick sweep at 10ms and 500ms to measure latency variance.

---

## 4. k6 Script Design

### 4.1 Sustained Load Script

```javascript
// k6-sustained-load.js
// Phase 1+2: Sustained 1000 req/min then burst 3000 req/min against 9Router mock upstream.
//
// Usage:
//   MOCK_BASE_URL=http://100.x.y.z:20128 k6 run k6-sustained-load.js
//
// Requires: k6 v0.47+ (constant-arrival-rate executor)

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// --- Custom metrics ---
const errorRate = new Rate('custom_errors');
const proxyLatency = new Trend('proxy_latency_ms');
const requestCount = new Counter('total_requests');
const streamCompletions = new Rate('stream_complete');

// --- Configuration ---
const BASE_URL = __ENV.MOCK_BASE_URL || 'http://127.0.0.1:20128';

// Model routes — adjust to match 9Router provider config for mock upstream
const MODELS = [
  'mock/mock-model',
];

// Realistic payloads that vary per request
const PAYLOADS = [
  {
    messages: [{ role: 'user', content: 'Write a hello world function in Python' }],
    stream: true,
    max_tokens: 100,
    temperature: 0.7,
  },
  {
    messages: [{ role: 'user', content: 'Explain what a binary tree is' }],
    stream: true,
    max_tokens: 100,
    temperature: 0.7,
  },
  {
    messages: [{ role: 'user', content: 'What is the time complexity of quicksort?' }],
    stream: false,
    max_tokens: 50,
    temperature: 0.0,
  },
  {
    messages: [{ role: 'user', content: 'List 3 benefits of using TypeScript over JavaScript' }],
    stream: true,
    max_tokens: 80,
    temperature: 0.5,
  },
  {
    messages: [{ role: 'user', content: 'How does a hash table work?' }],
    stream: false,
    max_tokens: 60,
    temperature: 0.0,
  },
];

export const options = {
  thresholds: {
    // Hard gates — test fails if these breach
    'http_req_failed': ['rate<0.01'],           // < 1% HTTP errors
    'http_req_duration': ['p(95)<200'],          // p95 proxy overhead < 200ms
    'http_req_duration': ['p(99)<500'],          // p99 proxy overhead < 500ms
    'custom_errors': ['rate<0.01'],              // < 1% custom errors
    'stream_complete': ['rate>0.99'],            // > 99% streams complete
  },

  scenarios: {
    // Phase 1: Sustained load — 1000 req/min for 5 minutes
    sustained: {
      executor: 'constant-arrival-rate',
      rate: 17,              // ~17 req/sec = ~1020 req/min
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 50,
      maxVUs: 200,
      startTime: '0s',
    },

    // Phase 2: Burst — 50 req/sec for 30 seconds (3000 req/min)
    burst: {
      executor: 'constant-arrival-rate',
      rate: 50,              // 50 req/sec = 3000 req/min
      timeUnit: '1s',
      duration: '30s',
      preAllocatedVUs: 100,
      maxVUs: 300,
      startTime: '5m30s',   // Start after sustained phase ends + 30s cool-down
    },
  },
};

export default function () {
  // Pick random payload and model
  const payload = PAYLOADS[Math.floor(Math.random() * PAYLOADS.length)];
  const model = MODELS[Math.floor(Math.random() * MODELS.length)];

  const body = JSON.stringify({
    model,
    ...payload,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer mock-key-for-load-test',
    },
    timeout: '120s',
    tags: { model, stream: String(payload.stream) },
  };

  const start = Date.now();
  const response = http.post(`${BASE_URL}/v1/chat/completions`, body, params);
  const elapsed = Date.now() - start;

  // Record custom metrics
  requestCount.add(1);
  proxyLatency.add(elapsed);

  // Status check
  const statusOk = check(response, {
    'status is 200': (r) => r.status === 200,
    'no server error': (r) => r.status < 500,
    'response has body': (r) => r.body && r.body.length > 0,
  });

  errorRate.add(!statusOk);

  // For streaming responses, check that we got SSE data
  if (payload.stream) {
    const hasSSE = check(response, {
      'has SSE data': (r) => r.body && (r.body.includes('data:') || r.body.includes('chat.completion')),
    });
    streamCompletions.add(hasSSE);
  } else {
    streamCompletions.add(statusOk);
  }

  // Brief pause to spread load naturally
  sleep(0.05);
}

export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    duration_s: data.state.testRunDurationMs / 1000,
    total_requests: data.metrics.http_reqs?.values?.count || 0,
    error_rate: data.metrics.http_req_failed?.values?.rate || 0,
    p50_latency_ms: data.metrics.http_req_duration?.values?.['p(50)'] || 0,
    p95_latency_ms: data.metrics.http_req_duration?.values?.['p(95)'] || 0,
    p99_latency_ms: data.metrics.http_req_duration?.values?.['p(99)'] || 0,
    max_latency_ms: data.metrics.http_req_duration?.values?.max || 0,
    avg_latency_ms: data.metrics.http_req_duration?.values?.avg || 0,
    stream_completion_rate: data.metrics.stream_complete?.values?.rate || 0,
  };

  console.log('\n=== LOAD TEST RESULTS ===');
  console.log(JSON.stringify(summary, null, 2));
  console.log('=========================\n');

  return {
    'stdout': JSON.stringify(data, null, 2),
    './load-test-results.json': JSON.stringify(data, null, 2),
  };
}
```

### 4.2 Streaming Stability Script

```javascript
// k6-streaming-stability.js
// Phase 3: 100 concurrent long-lived streaming connections for 5 minutes.
// Tests memory leaks, connection stability, event-loop pressure.
//
// Usage:
//   MOCK_BASE_URL=http://100.x.y.z:20128 k6 run k6-streaming-stability.js
//
// NOTE: Run mock-upstream with MOCK_CHUNK_DELAY=2000 for this test
// to simulate 30-second streaming responses (15 words * 2000ms).

import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend, Gauge } from 'k6/metrics';

const BASE_URL = __ENV.MOCK_BASE_URL || 'http://127.0.0.1:20128';

const streamComplete = new Rate('stream_complete');
const streamLatency = new Trend('stream_duration_ms');
const activeStreams = new Gauge('active_concurrent_streams');

export const options = {
  thresholds: {
    'stream_complete': ['rate>0.99'],         // > 99% streams complete
    'stream_duration_ms': ['p(95)<45000'],    // p95 < 45s (includes mock delay)
  },

  scenarios: {
    long_streams: {
      executor: 'constant-vus',
      vus: 100,               // 100 concurrent connections
      duration: '5m',
    },
  },
};

export default function () {
  const body = JSON.stringify({
    model: 'mock/mock-model',
    messages: [{
      role: 'user',
      content: 'Write a detailed essay about the history of computing, covering at least 10 major milestones.',
    }],
    stream: true,
    max_tokens: 500,
    temperature: 0.8,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer mock-key-for-load-test',
    },
    timeout: '60s',
  };

  activeStreams.add(__VU);  // Track which VU is active

  const start = Date.now();
  const response = http.post(`${BASE_URL}/v1/chat/completions`, body, params);
  const elapsed = Date.now() - start;

  streamLatency.add(elapsed);

  const ok = check(response, {
    'status 200': (r) => r.status === 200,
    'has stream data': (r) => r.body && r.body.includes('data:'),
    'has DONE marker': (r) => r.body && r.body.includes('[DONE]'),
    'no truncation': (r) => r.body && r.body.includes('finish_reason'),
  });

  streamComplete.add(ok);
}
```

### 4.3 k6 Script Annotations

**Why `constant-arrival-rate`?**

The `constant-arrival-rate` executor guarantees a fixed number of iterations per time unit, regardless of how long each iteration takes. If a request takes 200ms, k6 immediately starts the next one. This is critical because we are testing proxy throughput, not latency — we want exactly N requests per second hitting 9Router, not N virtual users who may be idle.

**Why `preAllocatedVUs` vs `maxVUs`?**

- `preAllocatedVUs: 50` — k6 starts with 50 VUs ready to go. This avoids startup lag.
- `maxVUs: 200` — If 50 VUs are all busy (requests take longer than expected), k6 scales up to 200. This prevents dropped iterations.

**Why `sleep(0.05)` at the end of each iteration?**

A tiny 50ms pause prevents k6 from burning CPU on its own loop. The arrival-rate executor handles timing, but a small sleep gives the Go runtime breathing room.

**Why randomize payloads?**

Random payloads prevent 9Router from hitting any pathological caching or optimization path. Real traffic is variable; the test should be too.

---

## 5. Test Scenarios

### Phase 0: Health Check (1 minute)

**Goal**: Confirm 9Router and mock upstream are healthy before testing.

```bash
# On the VPS, run these before any load test:

# 1. Check 9Router is running
curl -s http://localhost:20128/api/health | jq .

# 2. Check 9Router returns model list
curl -s http://localhost:20128/v1/models | jq .

# 3. Check mock upstream is running
curl -s http://localhost:20129/health | jq .

# 4. Single request end-to-end: client → 9Router → mock → 9Router → client
curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock-key-for-load-test" \
  -d '{
    "model": "mock/mock-model",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'

# 5. Non-streaming request
curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock-key-for-load-test" \
  -d '{
    "model": "mock/mock-model",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }' | jq .
```

**PASS**: All 5 checks return valid responses. HTTP 200, valid JSON/SSE.
**FAIL**: Any check fails — fix before proceeding. Do not run load tests against a broken setup.

---

### Phase 1: Sustained Load — 1000 req/min (5 minutes)

**Goal**: Verify 9Router handles sustained 1000 req/min without errors, memory leaks, or excessive latency.

| Parameter | Value |
|-----------|-------|
| Request rate | 17 req/sec (~1020 req/min) |
| Duration | 5 minutes |
| Total requests | ~5,100 |
| Pre-allocated VUs | 50 |
| Max VUs | 200 |
| Mock upstream delay | 50ms per chunk |
| Expected total requests | ~5,100 |

**Run command**:
```bash
MOCK_BASE_URL=http://localhost:20128 k6 run k6-sustained-load.js
```

**Key observations during test**:
- Memory RSS should stay under 3 GB
- CPU should stay under 50% average
- Error rate should be 0%
- p95 latency should be under 200ms

---

### Phase 2: Burst Test — 3000 req/min (30 seconds)

**Goal**: Verify 9Router handles a 3x traffic spike without crashing or dropping requests.

| Parameter | Value |
|-----------|-------|
| Request rate | 50 req/sec (3000 req/min) |
| Duration | 30 seconds |
| Total requests | ~1,500 |
| Pre-allocated VUs | 100 |
| Max VUs | 300 |
| Mock upstream delay | 50ms per chunk |

**Run command**:
```bash
MOCK_BASE_URL=http://localhost:20128 k6 run --scenario-filter burst k6-sustained-load.js
```

Or run as part of the combined script (burst starts at 5m30s automatically).

**Key observations**:
- Memory may spike but should not exceed 3.5 GB
- Some requests may take longer but p99 should stay under 500ms
- No 5xx errors
- VPS should not OOM-kill 9Router

---

### Phase 3: Streaming Stability (100 concurrent connections, 5 minutes)

**Goal**: Verify that long-lived streaming connections do not leak memory or cause event-loop stalls.

| Parameter | Value |
|-----------|-------|
| Concurrent connections | 100 VUs |
| Duration | 5 minutes |
| Mock upstream delay | 2000ms per chunk (slow streaming) |
| Expected stream duration | ~30 seconds per request |
| Estimated total streams | ~1,000 |

**Run command**:
```bash
# First, restart mock upstream with slow delay:
MOCK_CHUNK_DELAY=2000 MOCK_PORT=20129 node mock-upstream.js &

# Then run:
MOCK_BASE_URL=http://localhost:20128 k6 run k6-streaming-stability.js
```

**Key observations**:
- Memory should not grow continuously (leak detection)
- All streams should complete with `[DONE]` marker
- No connection resets or timeouts
- Event-loop lag should stay under 50ms (measure via Node.js `--inspect` or 9Router's own metrics if available)

---

### Phase 4: Real Provider Smoke Test (10-20 requests)

**Goal**: Validate end-to-end wiring from 9Router through to a real LLM provider.

**This is NOT a load test.** It is a sanity check.

| Parameter | Value |
|-----------|-------|
| Total requests | 10-20 |
| Providers | DeepSeek (cheapest) |
| Models | `deepseek-chat` or `deepseek-v4-flash` |
| Estimated cost | $0.01 - $0.05 |
| Request rate | 1 per second (manual or slow k6) |
| Mix | 5 streaming, 5 non-streaming |

**Run command** (manual curl is fine):
```bash
# Streaming
for i in $(seq 1 5); do
  echo "--- Request $i ---"
  curl -s http://localhost:20128/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <real-key>" \
    -d '{
      "model": "ds/deepseek-chat",
      "messages": [{"role": "user", "content": "Say hello in one sentence."}],
      "stream": true,
      "max_tokens": 20
    }'
  echo ""
  sleep 1
done

# Non-streaming
for i in $(seq 1 5); do
  echo "--- Request $i ---"
  curl -s http://localhost:20128/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <real-key>" \
    -d '{
      "model": "ds/deepseek-chat",
      "messages": [{"role": "user", "content": "Say hello in one sentence."}],
      "stream": false,
      "max_tokens": 20
    }' | jq '.choices[0].message.content, .usage'
  echo ""
  sleep 1
done
```

**PASS**: All requests return valid responses. Usage data is populated. No proxy errors.
**FAIL**: Any 500 from 9Router, malformed SSE, or missing usage data.

---

### Phase 5: Results Analysis

After all phases complete, collect and analyze:

1. k6 JSON output (`load-test-results.json`)
2. VPS monitoring snapshots (memory, CPU, file descriptors)
3. Journal logs (errors, warnings)
4. SQLite integrity check (post-test)

See Section 11 for the analysis template.

---

## 6. PASS/FAIL Thresholds

### Hard Gates (any failure = test FAIL)

| Metric | PASS Threshold | FAIL Threshold | Notes |
|--------|---------------|----------------|-------|
| **Error rate** | < 1% | >= 1% | Any 5xx from 9Router counts as error |
| **p95 latency** | < 200ms | >= 500ms | 9Router proxy overhead only (mock upstream is fast) |
| **p99 latency** | < 500ms | >= 1000ms | Tail latency under sustained load |
| **Memory (RSS)** | < 3 GB | >= 3.5 GB | 75% of 4 GB VPS; leaves room for OS + monitoring |
| **CPU (sustained avg)** | < 50% of 2 vCPUs | >= 80% | Measured over 5-minute sustained phase |
| **Open file descriptors** | < 8,000 | >= 12,000 | 50% of typical 16384 `ulimit -n` |
| **Stream completion rate** | > 99% | < 99% | All streams must reach `[DONE]` cleanly |
| **SQLite errors** | 0 | > 0 | Any `SQLITE_BUSY`, `SQLITE_CORRUPT`, or lock timeout |

### Soft Metrics (warning, not automatic failure)

| Metric | Good | Warning | Notes |
|--------|------|---------|-------|
| **Event loop lag** | < 50ms | > 100ms | Measurable via `--inspect` or 9Router metrics endpoint |
| **Memory growth rate** | < 10 MB/min | > 50 MB/min | Possible leak if sustained |
| **Max VU usage** | < 100 | > 150 | High max VU means requests are taking too long |
| **p50 latency** | < 50ms | > 100ms | Median should be very low for mock upstream |

### Interpretation Guidelines

- **p95 < 50ms**: Excellent. 9Router adds negligible overhead.
- **p95 50-200ms**: Acceptable. Overhead is noticeable but tolerable.
- **p95 200-500ms**: Concerning. Investigate event-loop lag and connection pooling.
- **p95 > 500ms**: Fail. 9Router is the bottleneck, not the provider.
- **Memory < 500 MB at steady state**: Excellent. 9Router is lightweight.
- **Memory 500 MB - 2 GB**: Acceptable. Monitor for leaks.
- **Memory > 3 GB**: Fail. VPS will OOM under production load with real providers.

---

## 7. Monitoring Protocol

### Pre-Test Baseline

Capture baseline metrics before starting any load test:

```bash
# Baseline: memory, CPU, uptime, file descriptors
echo "=== BASELINE ==="
echo "--- Memory ---"
free -h
echo "--- CPU ---"
uptime
echo "--- 9Router process ---"
ps aux | grep -E '[9]router' | grep -v grep
echo "--- Open files ---"
ls /proc/$(pgrep -f "9router" | head -1)/fd 2>/dev/null | wc -l
echo "--- Systemd resource usage ---"
systemctl show nine-router.service -p MemoryCurrent -p CPUUsageNSec -p TasksCurrent
echo "--- Ulimit ---"
cat /proc/$(pgrep -f "9router" | head -1)/limits 2>/dev/null | grep "Max open files"
echo "--- SQLite file size ---"
ls -lh /path/to/9router/data/*.db 2>/dev/null || echo "DB path not found — adjust"
```

### During-Test Monitoring

Run these in **separate terminal sessions** (or a tmux/screen split) during the entire test:

```bash
# Terminal 1: Memory + CPU every 5 seconds
watch -n 5 'echo "=== $(date) ==="; \
  ps aux | grep -E "[9]router" | grep -v grep; \
  echo "--- System Memory ---"; \
  free -h; \
  echo "--- Systemd ---"; \
  systemctl show nine-router.service -p MemoryCurrent -p CPUUsageNSec'

# Terminal 2: File descriptor count every 5 seconds
watch -n 5 'echo "=== FDs: $(ls /proc/$(pgrep -f "9router" | head -1)/fd 2>/dev/null | wc -l) ==="'

# Terminal 3: Journal errors (live stream)
journalctl -u nine-router.service -f --since "1 minute ago" | \
  grep -iE 'error|warn|crash|oom|sqlite|busy|corrupt|fatal'

# Terminal 4: Network connections
watch -n 5 'ss -tnp | grep -E "20128|20129" | wc -l; \
  echo "--- ESTABLISHED ---"; \
  ss -tnp state established | grep -E "20128|20129" | wc -l; \
  echo "--- TIME_WAIT ---"; \
  ss -tnp state time-wait | grep -E "20128|20129" | wc -l'
```

### Post-Test Snapshot

After each test phase, immediately capture:

```bash
echo "=== POST-TEST $(date) ==="
echo "--- Memory ---"
free -h
echo "--- 9Router process ---"
ps aux | grep -E '[9]router' | grep -v grep
echo "--- Open files ---"
ls /proc/$(pgrep -f "9router" | head -1)/fd 2>/dev/null | wc -l
echo "--- Systemd ---"
systemctl show nine-router.service -p MemoryCurrent -p CPUUsageNSec -p TasksCurrent
echo "--- Recent journal errors ---"
journalctl -u nine-router.service --since "10 minutes ago" | \
  grep -iE 'error|warn|crash|oom|sqlite|busy|corrupt' | tail -20
echo "--- SQLite integrity (if applicable) ---"
# sqlite3 /path/to/9router/data/your.db "PRAGMA integrity_check;" 2>/dev/null || echo "Adjust DB path"
```

### Monitoring Cheat Sheet

| What | How | When | Threshold |
|------|-----|------|-----------|
| Memory RSS | `ps aux` or `systemctl show` | Every 5s during test | < 3 GB |
| CPU usage | `systemctl show CPUUsageNSec` or `top` | Every 5s during test | < 50% of 2 cores |
| File descriptors | `ls /proc/PID/fd \| wc -l` | Every 5s during test | < 8,000 |
| Journal errors | `journalctl -f` | Continuous | 0 errors |
| TCP connections | `ss -tnp` | Every 5s during test | Monitor for TIME_WAIT buildup |
| SQLite health | `PRAGMA integrity_check` | Post-test | `ok` |

---

## 8. Test Execution Order

Execute tests in this exact order. Do not skip steps.

```
STEP 0: VPS Preparation
  ├── Verify 9Router is running and healthy
  ├── Start mock upstream: MOCK_CHUNK_DELAY=50 node mock-upstream.js &
  ├── Verify mock upstream: curl http://localhost:20129/health
  ├── Configure 9Router with mock provider (if not already)
  ├── Single e2e request: client → 9Router → mock
  └── CAPTURE BASELINE metrics

STEP 1: Warm-up (k6-sustained-load.js — sustained only, 1 minute)
  ├── Rate: 100 req/min (1.7 req/sec)
  ├── Duration: 1 minute
  ├── Mock delay: 50ms
  ├── PURPOSE: Warm up connection pools, JIT caches, SQLite WAL
  └── CAPTURE metrics (compare to baseline — should be minimal delta)

STEP 2: Sustained Load (k6-sustained-load.js — sustained only, 5 minutes)
  ├── Rate: 1000 req/min (17 req/sec)
  ├── Duration: 5 minutes
  ├── Mock delay: 50ms
  ├── Expected requests: ~5,100
  ├── PURPOSE: Primary load test
  └── CAPTURE metrics + journal log

STEP 3: Cool-down (30 seconds, no load)
  ├── Wait for system to stabilize
  ├── Monitor memory returning to baseline
  └── Check for deferred journal errors

STEP 4: Burst Test (k6-sustained-load.js — burst only, 30 seconds)
  ├── Rate: 3000 req/min (50 req/sec)
  ├── Duration: 30 seconds
  ├── Mock delay: 50ms
  ├── Expected requests: ~1,500
  ├── PURPOSE: Spike behavior
  └── CAPTURE metrics

STEP 5: Cool-down (1 minute, no load)

STEP 6: Streaming Stability (k6-streaming-stability.js, 5 minutes)
  ├── Restart mock upstream: MOCK_CHUNK_DELAY=2000 node mock-upstream.js &
  ├── 100 concurrent VUs
  ├── Duration: 5 minutes
  ├── PURPOSE: Memory leak detection, long-lived connection stability
  └── CAPTURE metrics

STEP 7: Real Provider Smoke (manual, 10-20 requests)
  ├── Restart mock upstream at normal delay (or bypass for real provider)
  ├── 10 requests to DeepSeek (cheapest provider)
  ├── 5 streaming, 5 non-streaming
  ├── PURPOSE: End-to-end wiring validation
  └── CAPTURE response samples

STEP 8: Results Analysis
  ├── Compare all captured metrics to PASS/FAIL thresholds
  ├── Check journal for any errors across all phases
  ├── SQLite integrity check
  └── Write verdict: PASS / FAIL / CONDITIONAL
```

### Time Budget

| Step | Duration | Cumulative |
|------|----------|------------|
| Step 0: Preparation | 5 min | 5 min |
| Step 1: Warm-up | 1 min | 6 min |
| Step 2: Sustained | 5 min | 11 min |
| Step 3: Cool-down | 30 sec | 11.5 min |
| Step 4: Burst | 30 sec | 12 min |
| Step 5: Cool-down | 1 min | 13 min |
| Step 6: Streaming | 5 min | 18 min |
| Step 7: Smoke | 2 min | 20 min |
| Step 8: Analysis | 10 min | 30 min |
| **Total** | **~30 min** | |

---

## 9. Real Provider Smoke Test Details

### Why Only 10-20 Requests?

This test exists solely to verify that the full pipeline works end-to-end. It is not a performance test. The questions it answers:

1. Does 9Router correctly route to the real provider?
2. Does the provider respond with valid SSE through 9Router?
3. Are auth headers forwarded correctly?
4. Is usage/token data passed through?
5. Does 9Router handle a real provider's response timing?

### Provider Selection

Use the **cheapest** available provider. Priority order:

| Priority | Provider | Model | Approx. Cost per Request |
|----------|----------|-------|--------------------------|
| 1 | DeepSeek | `deepseek-chat` or `deepseek-v4-flash` | $0.001-0.003 |
| 2 | OpenRouter | Any cheap model routed via OpenRouter | $0.001-0.005 |
| 3 | MiMo | `mimo-v2.5-pro` | $0.002-0.005 |

### What to Check Per Request

For each of the 10-20 requests, verify:

```bash
# Capture full response for analysis
curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <key>" \
  -d '{"model":"ds/deepseek-chat","messages":[{"role":"user","content":"Hello"}],"stream":true,"max_tokens":20}' \
  2>&1 | tee /tmp/smoke-response-$(date +%s).txt

# Check for:
# 1. HTTP 200 status
# 2. SSE data: lines present
# 3. data: [DONE] at the end
# 4. Usage data in final chunk (if present)
# 5. No error objects in the stream
```

### Smoke Test Checklist

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Streaming response | `curl -N` | SSE chunks arrive, ends with `[DONE]` |
| Non-streaming response | `curl + jq` | Valid JSON with `choices[0].message.content` |
| Usage data | Inspect final chunk | `usage.total_tokens > 0` |
| Model routing | Check `model` field in response | Matches requested model or provider alias |
| Error handling | Send invalid model | 4xx with clear error message |
| Latency | Measure with `time` | Response starts within 5s (provider dependent) |

---

## 10. What NOT to Do

### Critical Prohibitions

| Prohibition | Why | What to Do Instead |
|-------------|-----|-------------------|
| **Do NOT run 1000 req/min against real providers** | Burns API quota, costs money, risks rate-limit bans | Use mock upstream for load tests; real providers for smoke only |
| **Do NOT run load test without monitoring** | You cannot diagnose what you did not measure | Run monitoring commands in parallel (Section 7) |
| **Do NOT skip the mock upstream** | Without it, you are testing provider latency, not 9Router overhead | Set up mock upstream before any load test |
| **Do NOT run burst test before sustained test** | Burst may mask slow memory leaks that only appear under sustained load | Always run sustained (5 min) before burst |
| **Do NOT test without warm-up** | Cold connections, empty pools, and JIT compilation skew early results | Run 1-minute warm-up at low rate first |
| **Do NOT trust a single test run** | Network jitter, GC pauses, and OS scheduling cause variance | Run each phase at least twice; compare results |
| **Do NOT ignore SQLite errors** | `SQLITE_BUSY` under load means write contention; will corrupt data in production | Zero tolerance for SQLite errors |
| **Do NOT test from your local machine through the internet** | Network latency adds 50-200ms, masking proxy overhead | Run k6 on the VPS itself, or use Tailscale LAN IP |
| **Do NOT modify 9Router config between test phases** | Invalidates comparison between phases | Fix config once before testing; do not touch during |

### Common Mistakes

1. **Testing latency, not throughput**: If p95 is 5 seconds because the mock upstream has a 5-second delay, that is not a 9Router problem. Always subtract mock delay from observed latency.

2. **Forgetting to restart mock upstream**: Between Phase 3 (slow mock) and Phase 4 (smoke test), restart with normal delay.

3. **Not checking `ulimit`**: If `ulimit -n` is 1024 (default on some systems), 9Router will crash at ~1000 connections. Set it to at least 16384:
   ```bash
   # Check current limit
   cat /proc/$(pgrep -f "9router" | head -1)/limits | grep "Max open files"

   # If too low, edit the systemd unit:
   # [Service]
   # LimitNOFILE=16384
   ```

4. **Running tests from a container without host networking**: Docker's network stack adds overhead. If 9Router runs in Docker, either:
   - Run k6 inside the same Docker network, or
   - Use `--network=host` for the container.

5. **Ignoring TIME_WAIT sockets**: After burst tests, many TCP connections enter `TIME_WAIT`. Wait 60 seconds before the next test or you will see `EADDRNOTAVAIL` errors.

---

## 11. Results Analysis Template

After completing all test phases, fill in this template:

```markdown
## P25 Load Test Results — [DATE]

### Environment
- VPS: [provider], 2 vCPU, 4 GB RAM, Ubuntu 24.04
- 9Router version: v0.5.4
- Node.js version: [x.y.z]
- Mock upstream delay: [50ms / 2000ms]
- Test duration: ~25 minutes

### Phase 1: Sustained Load (1000 req/min, 5 min)
| Metric | Result | Threshold | Status |
|--------|--------|-----------|--------|
| Total requests | [N] | ~5,100 | — |
| Error rate | [N%] | < 1% | PASS/FAIL |
| p50 latency | [Nms] | < 50ms | PASS/FAIL |
| p95 latency | [Nms] | < 200ms | PASS/FAIL |
| p99 latency | [Nms] | < 500ms | PASS/FAIL |
| Max latency | [Nms] | — | OBSERVE |
| Memory (start) | [N GB] | — | OBSERVE |
| Memory (end) | [N GB] | < 3 GB | PASS/FAIL |
| Memory growth | [N MB] | — | OBSERVE |
| CPU (avg) | [N%] | < 50% | PASS/FAIL |
| Open FDs | [N] | < 8,000 | PASS/FAIL |
| SQLite errors | [N] | 0 | PASS/FAIL |

### Phase 2: Burst (3000 req/min, 30 sec)
| Metric | Result | Threshold | Status |
|--------|--------|-----------|--------|
| Total requests | [N] | ~1,500 | — |
| Error rate | [N%] | < 1% | PASS/FAIL |
| p95 latency | [Nms] | < 200ms | PASS/FAIL |
| p99 latency | [Nms] | < 500ms | PASS/FAIL |
| Memory peak | [N GB] | < 3.5 GB | PASS/FAIL |
| VUs used (max) | [N] | < 300 | OBSERVE |

### Phase 3: Streaming Stability (100 VUs, 5 min)
| Metric | Result | Threshold | Status |
|--------|--------|-----------|--------|
| Total streams completed | [N] | — | OBSERVE |
| Stream completion rate | [N%] | > 99% | PASS/FAIL |
| Memory (start) | [N GB] | — | OBSERVE |
| Memory (end) | [N GB] | < 3 GB | PASS/FAIL |
| Memory growth rate | [N MB/min] | < 10 MB/min | OBSERVE |
| [DONE] marker present | [N%] | 100% | PASS/FAIL |

### Phase 4: Real Provider Smoke
| Check | Result | Status |
|-------|--------|--------|
| Streaming works | [YES/NO] | PASS/FAIL |
| Non-streaming works | [YES/NO] | PASS/FAIL |
| Usage data present | [YES/NO] | PASS/FAIL |
| Model routing correct | [YES/NO] | PASS/FAIL |
| Error handling works | [YES/NO] | PASS/FAIL |

### Journal Log Summary
- Errors: [count]
- Warnings: [count]
- Notable events: [list]

### Verdict
- **Hard gates passed**: [N/8]
- **Soft warnings**: [list]
- **Overall**: [PASS / FAIL / CONDITIONAL]
- **Notes**: [free text]

### Recommendations
1. [Actionable recommendation 1]
2. [Actionable recommendation 2]
3. [Actionable recommendation 3]
```

---

## 12. Footer

**Document**: P25 Load Test Design Refresh
**Created**: 2026-06-26
**Author**: Guinevere research agent
**Status**: DESIGN — ready for execution upon operator approval
**Dependencies**: k6 installed on VPS, mock-upstream.js deployed, 9Router v0.5.4 running
**Estimated execution time**: ~30 minutes (all phases)
**Estimated real-provider cost**: $0.01 - $0.05 (smoke test only)
**Risk**: None — mock upstream burns zero provider quota

---

*End of P25 Load Test Design Refresh*
