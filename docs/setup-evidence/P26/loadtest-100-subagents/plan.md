# P26 Load Test Plan — 100+ Subagent Concurrent

**Date**: 2026-06-27  
**Target**: `http://100.104.210.75:20128/v1/chat/completions`  
**Model**: `subagent`  
**Prompt**: `"Reply exactly ok"`  
**max_tokens**: 8  
**temperature**: 0  
**Timeout**: 180s per request  
**Tool**: Custom Python async load test script (aiohttp)

---

## Phases

| Phase | Description | Concurrent Requests | Total Requests |
|-------|-------------|-------------------:|---------------:|
| A | Sanity check — 1 request | 1 | 1 |
| B | Light concurrency | 10 | 50 |
| C | Moderate concurrency | 25 | 100 |
| D | High concurrency | 50 | 200 |
| E | Full brutality | 100 | 300 |
| F* | Optional extreme (only if E passes) | 150 | 300 |

*Phase F only runs if Phase E has 0 hard errors and VPS remains stable.

## Hard Stop Criteria

If ANY of these trigger during any phase, stop ALL testing immediately:

1. **9Router unreachable** — endpoint returns connection refused/timeout for >30s
2. **PM2 restart increases** — check `pm2 status` shows increased restart count
3. **tailscaled down** — `systemctl is-active tailscaled` not active
4. **RAM available < 500MB** — VPS memory critically low
5. **HTTP 5xx > 5%** — upstream errors exceed threshold
6. **Timeout > 10%** — request timeout rate exceeds threshold
7. **Provider bans/cooldown storm** — rate-limit errors avalanche
8. **SSH unstable** — cannot connect to VPS

## Metrics Captured Per Phase

- Total requests
- Concurrency level
- Success count (HTTP 200)
- Fail count (non-200 + exceptions)
- HTTP status distribution
- Avg latency (seconds)
- p50 latency
- p90 latency
- p95 latency
- p99 latency
- Requests/sec
- Timeout count
- Provider error samples (redacted — no secrets)
- PM2 before/after (CPU, RAM, restarts)
- VPS before/after (load, memory)

## Error Classification

| Type | Classification |
|---|---|
| Client timeout | `client_timeout` (local machine can't wait) |
| 9Router error (5xx) | `ninerouter_fail` |
| Upstream provider error (4xx) | `upstream_limit` (e.g., 429 rate-limit, 401) |
| Connection refused | `connection_refused` |
| JSON parse error | `parse_error` |

## Execution Strategy

- Single Python script that runs all phases sequentially
- Each phase: spawn N concurrent workers via asyncio + aiohttp
- Workers send POST to `/v1/chat/completions` with model=subagent
- Collect all response times, status codes, errors
- Print summary per phase
- Between phases: capture VPS snapshot (SSH)
- CPU/mem monitoring during test via SSH polling

## Test Script

```python
# To be saved as /tmp/9router-loadtest.py on Windows local
# Uses: asyncio, aiohttp, json, sys, time, statistics
```
