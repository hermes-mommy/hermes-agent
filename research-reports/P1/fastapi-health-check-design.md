# FastAPI Health Check Design — Research Report

**Scope**: P1-019 — Service health check endpoint for Guinevere core
**Date**: 2026-06-01
**Sources**: Official FastAPI docs, GitHub repos (ii-agent, fastapi-microservice-health-check, fastapi-watch, pulsecheck-py), production guides (CommonTrace, Index.dev, ASOasis, EngineersOfAI, Nurbak)

---

## 1. Core Architecture: Two-Endpoint Pattern

The unanimous industry consensus across all sources is to **separate liveness from readiness** into distinct endpoints. This is critical for Kubernetes/container orchestrator compatibility.

### 1a. Liveness — `/health/live` or `/health`

| Aspect | Recommendation |
|---|---|
| Purpose | "Is the process alive and responding?" |
| Dependencies checked | **None**. No DB, no Redis, no downstream |
| Expected response | `{"status": "healthy", "service": "guinevere-core", "version": "0.1.0"}` |
| HTTP status | Always `200` if process is running |
| Latency target | p95 < 50ms — must be instantaneous |
| Kubernetes mapping | `livenessProbe` |
| Failure action | Restart the pod |

**Implementation (production-grade from ii-agent)**:

```python
@router.get("/health")
async def health_check_liveness():
    """
    Liveness probe — is the application running?
    Used by container orchestrators to determine if the app needs restarting.
    """
    return {"status": "healthy", "service": "guinevere-core", "version": "0.1.0"}
```

([ii-agent/health.py](https://github.com/Intelligent-Internet/ii-agent/blob/main/src/ii_agent_tools/app/routers/health.py#L11-L23))

### 1b. Readiness — `/health/ready`

| Aspect | Recommendation |
|---|---|
| Purpose | "Can the app serve traffic?" |
| Dependencies checked | PostgreSQL, Redis, 9Router (via HTTP check) |
| Expected response | Per-dependency status with overall aggregate |
| HTTP status | `200` if healthy, `503` if critical deps fail |
| Latency target | p95 < 200ms — strict timeouts per check |
| Kubernetes mapping | `readinessProbe` |
| Failure action | Remove from load balancer (NOT restart) |

**Implementation (adapted from fastapi-microservice-health-check)**:

```python
@router.get("/health/ready")
async def health_check_readiness(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    httpx_client: AsyncClient = Depends(get_httpx_client)
):
    """
    Readiness probe — verifies all critical dependencies are available.
    Returns 200 only when all critical services respond.
    """
    checks = {}

    # Run all checks in PARALLEL with individual timeouts
    db_check = _check_with_timeout("postgres", _check_postgres(db), timeout=3.0)
    redis_check = _check_with_timeout("redis", _check_redis(redis), timeout=2.0)
    router_check = _check_with_timeout("9router", _check_9router(httpx_client), timeout=5.0)

    results = await asyncio.gather(db_check, redis_check, router_check, return_exceptions=True)

    all_healthy = True
    for result in results:
        checks[result["service"]] = result
        if result["status"] != "healthy":
            all_healthy = False

    overall = "healthy" if all_healthy else "degraded"
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "service": "guinevere-core",
            "version": "0.1.0",
            "checks": checks
        }
    )
```

([DanielPopoola/fastapi-microservice-health-check](https://github.com/DanielPopoola/fastapi-microservice-health-check) — health check architecture reference)

---

## 2. Structured Health Response Format

Based on production patterns from **pulsecheck-py**, **healthkit**, **fastapi-watch**, and **CommonTrace**:

### Recommended Schema

```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "service": "guinevere-core",
  "version": "0.1.0",
  "checks": {
    "postgres": {
      "status": "healthy" | "degraded" | "unhealthy",
      "latency_ms": 4.3,
      "error": null
    },
    "redis": {
      "status": "healthy" | "degraded" | "unhealthy",
      "latency_ms": 1.2,
      "error": null
    },
    "9router": {
      "status": "healthy" | "degraded" | "unhealthy",
      "latency_ms": 23.7,
      "error": null
    }
  }
}
```

### Three-State Health Model

| State | Meaning | HTTP Status | Action |
|---|---|---|---|
| `healthy` | All critical deps responding | `200` | Normal traffic |
| `degraded` | Non-critical dep failing or slow response | `200` or `503` | Alert, keep serving |
| `unhealthy` | Critical dep down | `503` | Remove from LB |

Sources:
- [pulsecheck-py v0.2.0](https://pypi.org/project/pulsecheck-py/) — HEALTHY/DEGRADED/UNHEALTHY three-state model
- [CommonTrace health check](https://www.commontrace.org/trace/fastapi-health-check-endpoint-with-dependency-checks/) — degraded vs unhealthy distinction
- [healthkit v0.1.0](https://pypi.org/project/healthkit/) — per-check latency tracking

### Timeout Budget per Dependency

| Dependency | Timeout | Rationale |
|---|---|---|
| PostgreSQL | 3.0s | `SELECT 1` is trivial; >3s means connectivity issue |
| Redis | 2.0s | `PING` should be <1ms; 2s grace for network congestion |
| 9Router (HTTP) | 5.0s | HTTP call may have latency; 5s is generous |

**Critical rule**: Total timeout must be ≤ Kubernetes probe timeout (default 5-10s). Use `asyncio.gather` + individual `asyncio.wait_for` per check.

---

## 3. How to Verify Each Dependency

### PostgreSQL (asyncpg)

```python
async def check_postgres(pool) -> dict:
    """Verify PostgreSQL connectivity with SELECT 1."""
    start = time.monotonic()
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        latency_ms = (time.monotonic() - start) * 1000
        return {"status": "healthy", "latency_ms": round(latency_ms, 1)}
    except Exception as e:
        return {"status": "unhealthy", "error": type(e).__name__, "latency_ms": 0}
```

**Why `SELECT 1`**: Lightest possible query — tests connection without data access.

### Redis (redis-py async)

```python
async def check_redis(client) -> dict:
    """Verify Redis connectivity with PING."""
    start = time.monotonic()
    try:
        await client.ping()
        latency_ms = (time.monotonic() - start) * 1000
        return {"status": "healthy", "latency_ms": round(latency_ms, 1)}
    except Exception as e:
        return {"status": "unhealthy", "error": type(e).__name__, "latency_ms": 0}
```

### 9Router / Downstream HTTP (httpx)

```python
async def check_9router(client: AsyncClient) -> dict:
    """Verify 9Router health via HTTP GET."""
    start = time.monotonic()
    try:
        resp = await client.get(
            "http://127.0.0.1:20128/health",
            timeout=5.0
        )
        latency_ms = (time.monotonic() - start) * 1000
        if resp.status_code == 200:
            return {"status": "healthy", "latency_ms": round(latency_ms, 1)}
        else:
            return {"status": "degraded", "error": f"HTTP {resp.status_code}", "latency_ms": round(latency_ms, 1)}
    except Exception as e:
        return {"status": "unhealthy", "error": type(e).__name__, "latency_ms": 0}
```

Source: [CommonTrace — FastAPI health check with async dependencies](https://www.commontrace.org/trace/fastapi-health-check-endpoint-with-dependency-checks/)

### Parallel Execution with Individual Timeouts

```python
async def run_checks(checks: list) -> list:
    """Run all health checks in parallel with individual timeout protection.

    Each check is a coroutine wrapped in asyncio.wait_for with its own timeout.
    A hung check does NOT block other checks.
    """
    tasks = [
        asyncio.wait_for(check(), timeout=timeout)
        for check, timeout in checks
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

Source: [EngineersOfAI — Health Checks & Readiness](https://engineersofai.com/docs/python/python-production-engineering/Module%202%20%E2%80%94%20Python%20Observability/Health-Checks-and-Readiness)

---

## 4. What NOT to Include (Anti-Patterns)

### ❌ BLOCKING — Never do these

| Anti-Pattern | Consequence | Fix |
|---|---|---|
| **Expose secrets** (DB URL, passwords, stack traces) | Credential leak — health endpoints are often unauthenticated | Return status only, no configuration |
| **Return 200 with error in body** | Load balancer sends traffic to broken instance | Return `503` when critical deps fail |
| **Sequential dependency checks** | Health endpoint slower than probe timeout → false restarts | Use `asyncio.gather` for parallel checks |
| **No per-check timeout** | One hung DB check blocks all checks indefinitely | Always wrap in `asyncio.wait_for` |
| **Check non-critical deps in readiness** | Pod removed from LB for irrelevant failures (analytics, feature flags) | Only check critical deps |
| **Same endpoint for liveness and readiness** | DB failure causes pod restarts (cascading failure) | Separate endpoints per K8s semantics |
| **Cache health responses** | CDN caching `200 OK` → traffic routed to dead instance for full cache TTL | `Cache-Control: no-cache, no-store, must-revalidate` |
| **Large queries or business logic in checks** | Slow, costly, and may mask real problems | Only `SELECT 1` / `PING` / lightweight HEAD |
| **Check every dependency in every container** | Worker checking DB it doesn't use → false positive | Only check deps relevant to the container role |

### What IS safe to include
- `version` — useful for debugging which deployment is serving
- `timestamp` / `uptime_seconds` — operational context
- `latency_ms` per check — useful for trend analysis
- Per-dependency status breakdown — speeds up triage

Sources:
- [ASOasis — Production-Grade Health Check Design](https://asoasis.tech/articles/2026-04-07-0253-rest-api-health-check-endpoint-design/)
- [EngineersOfAI — Anti-Patterns Table](https://engineersofai.com/docs/python/python-production-engineering/Module%202%20%E2%80%94%20Python%20Observability/Health-Checks-and-Readiness)
- [Nurbak — Build It Right 2026](https://nurbak.com/en/blog/health-check-endpoint/)
- [Index.dev — Best Practices](https://www.index.dev/blog/how-to-implement-health-check-in-python)

---

## 5. Kubernetes / Container Semantics Summary

| Probe | Endpoint | HTTP on Failure | K8s Action |
|---|---|---|---|
| `livenessProbe` | `/health` | `200` → alive; non-200 → restart pod | Restart container |
| `readinessProbe` | `/health/ready` | `200` → ready; `503` → no traffic | Remove from Service endpoints |
| `startupProbe` *(optional)* | `/health/startup` | `503` until initialization complete | Delay liveness checks during slow startup |

### Docker Compose Healthcheck

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 40s
```

**Important**: Use `/health` (liveness) for Docker healthcheck, NOT `/health/ready`. Docker only uses the healthcheck for restart decisions, same as liveness semantics.

Source: [CommonTrace — Docker healthcheck example](https://www.commontrace.org/trace/fastapi-health-check-endpoint-with-dependency-checks/)

---

## 6. Available Libraries (Evaluate, likely NOT needed)

For Guinevere's simple 3-dependency health check, a custom implementation is **preferred over a library** — the custom code is ~50 lines and avoids dependency overhead.

| Library | When to Use |
|---|---|
| [fastapi-watch](https://pypi.org/project/fastapi-watch/) | Need real-traffic probes + dashboard + Prometheus metrics (v1.6.1, 2026) |
| [pulsecheck-py](https://pypi.org/project/pulsecheck-py/) | Need framework-agnostic checks with FastAPI adapter (v0.2.0, 2026) |
| [dephealth](https://pypi.org/project/dephealth/) | Need Prometheus metrics built-in + multiple DB backends (v0.8.2, 2026) |
| [fast-healthchecks](https://pypi.org/project/fast-healthchecks/) | Need multiple ASGI framework support (FastAPI + Litestar + FastStream) |
| [fastapi-health](https://pypi.org/project/fastapi-health/) | Simplest approach — just callables list (v0.4.0) |

**Recommendation for Guinevere**: **Skip libraries.** Write a custom `app/routers/health.py` with ~50-80 lines of async Python using `asyncio.gather` + `asyncio.wait_for`. This avoids version coupling, keeps the codebase lean, and is trivially testable.

---

## 7. Recommended File Structure for Guinevere

```
app/
├── routers/
│   ├── __init__.py
│   ├── health.py           # /health (liveness) + /health/ready (readiness)
│   └── ...
├── core/
│   ├── health.py           # Check functions (check_postgres, check_redis, check_9router)
│   └── ...
├── main.py
└── tests/
    ├── test_health.py      # Integration tests with httpx AsyncClient
    └── ...
```

---

## 8. Security Considerations

1. **No auth for `/health` (liveness)** — orchestrators need unauthenticated access inside the cluster network
2. **No auth for `/health/ready`** — same reason; control via network policy (not exposed to public internet)
3. **Never expose `/health/ready` on public-facing ports** — use internal-only port or network policy
4. **Detailed/verbose health = authenticated endpoint** — if a `/health/detailed` endpoint is added later, protect it
5. **Rate limiting**: Exempt cluster IPs; apply light limits to public monitors
6. **Response headers**: Always include `Cache-Control: no-cache, no-store, must-revalidate`

Source: [ASOasis — Security & Network Boundary](https://asoasis.tech/articles/2026-04-07-0253-rest-api-health-check-endpoint-design/)

---

## Key Takeaways

1. **Two endpoints**: `/health` (liveness, no deps) + `/health/ready` (readiness, all deps)
2. **Parallel checks**: `asyncio.gather` with individual `asyncio.wait_for` timeouts
3. **Three-state per dependency**: healthy / degraded / unhealthy, not just pass/fail
4. **Critical deps only**: PG, Redis, 9Router — not optional services
5. **Never expose secrets**: Status only, no connection strings or stack traces
6. **Skip libraries**: Custom code is cleaner for 3-dependency checks
7. **Always return correct HTTP status**: `200` for healthy, `503` for degraded/unhealthy

---

## Sources

| Source | URL |
|---|---|
| FastAPI docs | https://fastapi.tiangolo.com |
| ii-agent (production health check) | https://github.com/Intelligent-Internet/ii-agent/blob/main/src/ii_agent_tools/app/routers/health.py |
| fastapi-microservice-health-check | https://github.com/DanielPopoola/fastapi-microservice-health-check |
| CommonTrace — health check with deps | https://www.commontrace.org/trace/fastapi-health-check-endpoint-with-dependency-checks/ |
| Index.dev — FastAPI health check best practices | https://www.index.dev/blog/how-to-implement-health-check-in-python |
| EngineersOfAI — Anti-patterns table | https://engineersofai.com/docs/python/python-production-engineering/Module%202%20%E2%80%94%20Python%20Observability/Health-Checks-and-Readiness |
| ASOasis — Production-grade design | https://asoasis.tech/articles/2026-04-07-0253-rest-api-health-check-endpoint-design/ |
| Nurbak — Build it right 2026 | https://nurbak.com/en/blog/health-check-endpoint/ |
| pulsecheck-py (three-state model) | https://pypi.org/project/pulsecheck-py/ |
| healthkit (latency per check) | https://pypi.org/project/healthkit/ |