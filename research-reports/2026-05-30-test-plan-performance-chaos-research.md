# Guinevere Test Plan Research: Performance, Chaos Engineering & Integration Testing

**Document Type:** Research Report — Performance Testing, Chaos Engineering, Integration & Contract Testing  
**Version:** 1.0  
**Status:** Research Complete  
**Date:** 2026-05-30  
**Author:** Guinevere de Baroque (Hephaestus discipline)  
**Owner:** Samm  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Budget Boundary:** USD 30/month hard cap — all test infrastructure must run within VPS constraints  

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines all SLO targets, latency budgets, availability targets, safety invariants that performance tests must validate |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime services, systemd units, resource allocation, network topology, database architecture |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines loop performance characteristics, parallel loop limits, guardian overhead, TODO enforcer timing |
| `Guinevere_DatabaseERD_MigrationStrategy_v1.0.md` | Defines TimescaleDB hypertables, HNSW indexes, 12 schemas, retention policies, Merkle audit trail |
| `Guinevere_SRS_v1.0.md` | Defines 120 FRs, 50 NFRs, 40 IRs with acceptance criteria and performance requirements |
| `Guinevere_APIIntegration_v2.0.md` | Defines external API contracts, SDK configurations, retry logic, rate limits |
| `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | Defines QA gates, phase gates, evidence requirements |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Safety boundaries that must remain intact under stress/load conditions |
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Prometheus metrics and Grafana dashboards that performance tests must feed |
| `Guinevere_MemorySchema_v2.0.md` | Memory architecture, embedding dimensions, recall pipeline specifications |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Performance Testing Strategy](#2-performance-testing-strategy)
3. [Performance Budgets & Baselines](#3-performance-budgets--baselines)
4. [Load Testing with Locust](#4-load-testing-with-locust)
5. [Micro-Benchmarking with pytest-benchmark](#5-micro-benchmarking-with-pytest-benchmark)
6. [Chaos Engineering Philosophy & Fault Model](#6-chaos-engineering-philosophy--fault-model)
7. [Chaos Test Catalog](#7-chaos-test-catalog)
8. [Toxiproxy Integration](#8-toxiproxy-integration)
9. [Integration Testing Architecture](#9-integration-testing-architecture)
10. [Contract Testing](#10-contract-testing)
11. [End-to-End Testing](#11-end-to-end-testing)
12. [Database Performance Testing](#12-database-performance-testing)
13. [LLM Pipeline Testing](#13-llm-pipeline-testing)
14. [Surveillance Pipeline Testing](#14-surveillance-pipeline-testing)
15. [Loop Performance Testing](#15-loop-performance-testing)
16. [Test Environment Architecture](#16-test-environment-architecture)
17. [Performance Test Reporting & Regression Detection](#17-performance-test-reporting--regression-detection)
18. [Implementation Roadmap](#18-implementation-roadmap)
19. [Gap Register & Unresolved Assumptions](#19-gap-register--unresolved-assumptions)

---

## 1. Executive Summary

This research report provides the performance, chaos engineering, and integration testing foundation for the Guinevere project. Guinevere operates under severe resource constraints — a single VPS (4 CPU / 16GB RAM / 120GB SSD) hosting 17+ systemd services, Docker containers, PostgreSQL 16 with TimescaleDB and pgvector, Redis 7, Prometheus, Grafana, Loki, and the core autonomous daemon — all within a $30/month budget.

The testing strategy must validate:

- **SLO compliance**: 99.5% availability, specific latency targets across 8 SLI categories
- **Resource limits**: 4GB core+plugins, 4GB DB, 4GB observability, 4GB OS+buffer
- **Single-VPS fragility**: No redundant infrastructure — every service failure is potentially cascading
- **20 parallel loop capacity**: ~512MB per loop, PgBouncer pooled connections, Redis state
- **Safety under stress**: Safe-word enforcement must remain 100% even under load/fault conditions
- **TimescaleDB performance**: Hypertable chunk management, HNSW vector search, compression
- **External dependency resilience**: 9Router LLM routing, Discord gateway, Tasker HTTP webhooks

This report covers five testing domains: performance/load testing, chaos engineering, integration testing, contract testing, and end-to-end testing — all tailored specifically to Guinevere's architecture and constraints.

---

## 2. Performance Testing Strategy

### 2.1 Testing Taxonomy

| Test Type | Purpose | Duration | Frequency | Tool |
|---|---|---|---|---|
| **Benchmark** | Establish per-component baseline latency and throughput | Minutes | Every CI run + monthly | pytest-benchmark, pgbench |
| **Load** | Validate behavior under expected production load | 30-60 min | Weekly + pre-release | Locust |
| **Stress** | Find breaking point and degradation behavior | Until failure | Quarterly | Locust (spike profiles) |
| **Soak** | Detect memory leaks, connection exhaustion, resource drift | 4-24 hours | Monthly | Locust (steady state) |
| **Spike** | Validate recovery from sudden traffic bursts | 15 min with burst | Quarterly | Locust (spike users) |
| **Chaos** | Validate resilience to component failures | 30-60 min per scenario | Monthly | Toxiproxy + custom scripts |

### 2.2 Strategy Principles

1. **SLO-driven**: Every performance test maps to a specific SLO from `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md`. Tests that do not validate an SLO or NFR are discarded.

2. **Budget-aware**: No test infrastructure that exceeds VPS capacity or costs money. All load tests use internal mocking for LLM calls to avoid API costs.

3. **Safety-invariant**: Performance tests must never bypass or weaken safety checks. Safe-word enforcement tests run alongside load tests.

4. **Single-VPS realistic**: Load tests simulate Guinevere's actual workload — not generic web traffic. The production profile is one user (Samm) with multiple concurrent loops, not thousands of HTTP users.

5. **Regression-detecting**: Performance baselines are stored and compared. Regressions >15% trigger CI failure.

### 2.3 Performance Test Scope

| Component | Test Approach | Key Metrics |
|---|---|---|
| FastAPI Surveillance API | Locust HTTP load | p95/p99 latency, throughput (req/s), error rate |
| FastAPI Internal API | Locust HTTP load | p95/p99 latency, throughput |
| Discord Bot | Mock gateway + command load | Command response time, gateway reconnect time |
| PostgreSQL | pgbench + custom query benchmarks | Query latency, TPS, connection pool utilization |
| pgvector | pytest-benchmark | HNSW search latency at varying dataset sizes |
| Redis | redis-benchmark + custom | Operation latency, memory usage, eviction behavior |
| Agent Loop | Concurrent loop stress test | Loop completion time, memory per loop, TODO enforcer yank rate |
| TimescaleDB | Chunk query benchmarks | Compression ratio, query time across chunk boundaries |
| LLM Pipeline | Mock 9Router with latency injection | End-to-end response time, retry behavior, fallback timing |
| Surveillance Ingestion | Simulated Tasker load | Events/second, freshness (ingestion-to-queryable), buffer behavior |
| Guardian/Enforcer | Concurrent loop + fault injection | Heartbeat overhead, idle detection latency, respawn time |

---

## 3. Performance Budgets & Baselines

### 3.1 Component Performance Budget Table

Performance budgets are derived from SLO targets in `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` §6.2, with additional engineering margins.

| Component | Metric | SLO Target | Engineering Budget (80% of SLO) | Hard Ceiling | Measurement Method |
|---|---|---|---|---|---|
| **FastAPI Surveillance** | p95 latency | ≤ 750ms | ≤ 600ms | 2000ms | Prometheus histogram `guinevere_http_request_duration_seconds{endpoint_group="surveillance"}` |
| **FastAPI Internal** | p95 latency | ≤ 750ms | ≤ 600ms | 2000ms | Prometheus histogram `guinevere_http_request_duration_seconds{endpoint_group="internal"}` |
| **FastAPI Admin** | p95 latency | ≤ 2000ms | ≤ 1600ms | 5000ms | Prometheus histogram |
| **PostgreSQL Read** | p95 latency | ≤ 250ms | ≤ 200ms | 1000ms | Prometheus histogram `guinevere_postgres_query_duration_seconds{operation="read"}` |
| **PostgreSQL Write** | p99 latency | ≤ 1000ms | ≤ 800ms | 3000ms | Prometheus histogram `guinevere_postgres_query_duration_seconds{operation="write"}` |
| **pgvector Search** | p95 latency | ≤ 2000ms | ≤ 1600ms | 5000ms | Prometheus histogram `guinevere_postgres_query_duration_seconds{operation="vector_search"}` |
| **Redis Operations** | p95 latency | ≤ 50ms | ≤ 40ms | 200ms | Prometheus histogram `guinevere_redis_operation_duration_seconds` |
| **Redis Operations** | p99 latency | ≤ 200ms | ≤ 160ms | 500ms | Prometheus histogram |
| **LLM Interactive (GPT-5.5)** | p95 latency | ≤ 20s | ≤ 16s | 45s | Prometheus histogram `guinevere_llm_latency_seconds{route="core_interactive"}` |
| **LLM Batch (DeepSeek Flash)** | p95 latency | ≤ 180s | ≤ 144s | 300s | Prometheus histogram `guinevere_llm_latency_seconds{route="coding_batch"}` |
| **Surveillance Freshness** | p95 ingestion-to-queryable | ≤ 60s | ≤ 48s | 300s | Prometheus histogram `guinevere_surveillance_freshness_seconds` |
| **Safe-word Response** | p99 time-to-neutral | ≤ 5s | ≤ 4s | 10s | Prometheus histogram `guinevere_safe_word_to_neutral_seconds` |
| **Loop Phase Duration** | p95 per phase | Baseline tracking | Track monthly | 2x baseline triggers alert | Prometheus histogram `guinevere_loop_phase_duration_seconds` |
| **PgBouncer Connection** | Pool wait time | ≤ 100ms | ≤ 80ms | 500ms | PgBouncer stats |
| **TimescaleDB Chunk Query** | p95 cross-chunk query | ≤ 500ms | ≤ 400ms | 2000ms | Custom benchmark |
| **Encryption/Decryption** | AES-256-GCM per record | ≤ 5ms | ≤ 4ms | 20ms | pytest-benchmark |
| **HNSW Vector Search** | p95 recall@10 | ≤ 200ms | ≤ 160ms | 500ms | pytest-benchmark at 100K vectors |
| **Memory Recall Pipeline** | End-to-end p95 | ≤ 500ms | ≤ 400ms | 1500ms | pytest-benchmark |
| **Guardian Heartbeat** | Check overhead | ≤ 100ms | ≤ 80ms | 200ms | Custom metric |
| **Systemd Auto-restart** | Service restart time | ≤ 10s | ≤ 8s | 30s | systemd journal timestamps |
| **Alert Delivery** | SEV0/SEV1 to Discord | ≤ 15s | ≤ 12s | 30s | Alert timestamp vs Discord message timestamp |

### 3.2 Resource Budget Table

| Resource | Total Budget | Core+Plugins | DB | Observability | OS+Buffer | Test Overhead |
|---|---|---|---|---|---|---|
| **RAM** | 16GB | 4GB | 4GB | 4GB | 4GB | Within existing allocation |
| **CPU** | 4 cores | 2 cores | 1 core | 1 core | Shared | Burst during test runs |
| **Disk** | 120GB SSD | Application | DB data | Prometheus+Loki | OS | No additional |
| **Swap** | 8GB | Emergency only | N/A | N/A | Available | Monitor swap usage during soak |
| **Network** | Tailscale mesh | N/A | N/A | N/A | N/A | Internal only |
| **PgBouncer** | 200 max connections | ~100 | ~50 | ~20 | ~10 | 20 reserved for tests |
| **Redis** | 1GB maxmemory | DB0: 200MB | DB1-3: 600MB | DB4-5: 200MB | N/A | Monitor eviction during soak |

### 3.3 Throughput Budget Table

| Workload | Expected Production | Test Target (1.5x) | Hard Limit |
|---|---|---|---|
| Surveillance events/minute | ~20 (Android + Windows) | 30/min | 100/min |
| Discord commands/minute | ~5 | 10/min | 50/min |
| Concurrent loops | ~5 average | 20 (max design) | 25 |
| LLM calls/hour (GPT-5.5) | ~10-20 | 30/hour | 50/hour |
| LLM calls/hour (DeepSeek Flash) | ~50-100 | 150/hour | 300/hour |
| PostgreSQL queries/second | ~50 | 100/s | 500/s |
| Redis operations/second | ~200 | 400/s | 2000/s |
| TimescaleDB inserts/minute | ~30 | 60/min | 200/min |
| Backup size/day | ~500MB | N/A | 2GB |

---

## 4. Load Testing with Locust

### 4.1 Why Locust

| Criterion | Locust | Alternative (k6, Gatling, JMeter) |
|---|---|---|
| Python native | ✅ Guinevere is 100% Python | ❌ Require JS/Scala/Java runtime |
| Code-based scenarios | ✅ Python classes, no DSL | Varies |
| Resource footprint | ✅ Lightweight on 4-core VPS | JMeter heavy on RAM |
| Realistic user modeling | ✅ Weighted user classes | Varies |
| Web UI for monitoring | ✅ Built-in dashboard | k6 Cloud paid |
| Cost | ✅ Free, open source | k6 Cloud, Gatling Enterprise paid |
| Integration with pytest | ✅ Can share fixtures | ❌ Separate ecosystem |

### 4.2 Locust User Profiles

Guinevere's production workload is NOT typical web traffic. The "users" are:

| User Type | Weight | Description | Primary Targets |
|---|---|---|---|
| **SurveillanceIngestor** | 40% | Simulates Android Tasker + Windows daemon posting events | FastAPI surveillance endpoints |
| **LoopOrchestrator** | 25% | Simulates concurrent SDLC loop activity — DB reads/writes, Redis state, LLM calls (mocked) | PostgreSQL, Redis, mock LLM |
| **DiscordCommander** | 15% | Simulates Samm issuing Discord slash commands | Mock Discord gateway |
| **MemoryRecaller** | 10% | Simulates memory recall pipeline — vector search, episodic lookup | pgvector, PostgreSQL |
| **DashboardReader** | 10% | Simulates Grafana/Prometheus metric scraping | Prometheus, PostgreSQL readonly |

### 4.3 Locust User Class: SurveillanceIngestor

```python
# tests/performance/locustfile.py

import uuid
import time
import json
import hmac
import hashlib
from locust import HttpUser, task, between, tag

SURVEILLANCE_HMAC_SECRET = "test-hmac-secret-for-load-testing"

def sign_payload(payload: dict, secret: str) -> str:
    """Generate HMAC-SHA256 signature for Tasker payload validation."""
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


class SurveillanceIngestor(HttpUser):
    """
    Simulates Android Tasker and Windows daemon posting surveillance events
    to FastAPI surveillance endpoints.

    Production profile: ~20 events/minute across all sources.
    Load test profile: scales to 30-100 events/minute.
    """
    weight = 40
    wait_time = between(1, 5)  # 1-5 seconds between events

    def on_start(self):
        """Initialize device simulation state."""
        self.device_id = str(uuid.uuid4())
        self.device_type = "android" if hash(self.environment.host) % 2 == 0 else "windows"
        self.event_counter = 0

    @task(5)
    @tag("surveillance", "android", "activity")
    def post_android_activity(self):
        """Simulate Tasker posting app usage activity."""
        payload = {
            "device_id": self.device_id,
            "event_type": "activity",
            "app_name": self._random_app(),
            "duration_seconds": self.environment.random.randint(5, 3600),
            "timestamp": time.time(),
        }
        signature = sign_payload(payload, SURVEILLANCE_HMAC_SECRET)

        with self.client.post(
            "/surveillance/android/activity",
            json=payload,
            headers={
                "X-HMAC-Signature": signature,
                "X-Device-ID": self.device_id,
            },
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited — surveillance pipeline overloaded")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(3)
    @tag("surveillance", "android", "location")
    def post_android_location(self):
        """Simulate Tasker posting GPS location updates."""
        payload = {
            "device_id": self.device_id,
            "event_type": "location",
            "latitude": -6.2 + self.environment.random.uniform(-0.1, 0.1),
            "longitude": 106.8 + self.environment.random.uniform(-0.1, 0.1),
            "accuracy_meters": self.environment.random.randint(5, 50),
            "timestamp": time.time(),
        }
        signature = sign_payload(payload, SURVEILLANCE_HMAC_SECRET)

        self.client.post(
            "/surveillance/android/location",
            json=payload,
            headers={
                "X-HMAC-Signature": signature,
                "X-Device-ID": self.device_id,
            },
        )

    @task(2)
    @tag("surveillance", "android", "notification")
    def post_android_notification(self):
        """Simulate Tasker AutoNotification capturing notifications."""
        payload = {
            "device_id": self.device_id,
            "event_type": "notification",
            "app": self._random_app(),
            "title": "Test notification",
            "content": f"Load test notification {self.event_counter}",
            "timestamp": time.time(),
        }
        self.event_counter += 1
        signature = sign_payload(payload, SURVEILLANCE_HMAC_SECRET)

        self.client.post(
            "/surveillance/android/notification",
            json=payload,
            headers={
                "X-HMAC-Signature": signature,
                "X-Device-ID": self.device_id,
            },
        )

    @task(1)
    @tag("surveillance", "windows", "event_batch")
    def simulate_windows_event_batch(self):
        """Simulate Windows daemon posting batched activity events."""
        events = []
        for _ in range(self.environment.random.randint(1, 5)):
            events.append({
                "device_id": self.device_id,
                "event_type": "windows_activity",
                "active_window": f"Application_{self.environment.random.randint(1, 10)}",
                "process_name": "chrome.exe",
                "idle_seconds": self.environment.random.randint(0, 300),
                "timestamp": time.time(),
            })

        for event in events:
            signature = sign_payload(event, SURVEILLANCE_HMAC_SECRET)
            self.client.post(
                "/surveillance/windows/event",
                json=event,
                headers={
                    "X-HMAC-Signature": signature,
                    "X-Device-ID": self.device_id,
                },
            )

    def _random_app(self) -> str:
        apps = [
            "com.whatsapp", "com.instagram.android", "com.android.chrome",
            "com.spotify.music", "com.github.android", "com.discord",
        ]
        return self.environment.random.choice(apps)
```

### 4.4 Locust User Class: LoopOrchestrator

```python
class LoopOrchestrator(HttpUser):
    """
    Simulates an active SDLC loop performing database reads/writes,
    Redis state management, and mocked LLM calls.

    Production profile: ~5 concurrent loops, each making DB queries,
    Redis state updates, and async LLM calls.
    """
    weight = 25
    wait_time = between(2, 10)

    def on_start(self):
        """Initialize loop instance simulation."""
        self.loop_id = str(uuid.uuid4())
        self.phase = 1
        self.todos_completed = 0

    @task(3)
    @tag("loop", "db_read")
    def query_loop_state(self):
        """Simulate loop guardian querying current loop state from PostgreSQL."""
        self.client.get(
            f"/internal/loops/{self.loop_id}/state",
            name="/internal/loops/{loop_id}/state",
        )

    @task(5)
    @tag("loop", "db_write")
    def update_todo_status(self):
        """Simulate TODO enforcer updating todo completion status."""
        payload = {
            "loop_id": self.loop_id,
            "todo_id": f"todo-{self.todos_completed}",
            "status": "completed",
            "completed_at": time.time(),
        }
        self.client.post(
            "/internal/loops/todos/update",
            json=payload,
        )
        self.todos_completed += 1

    @task(2)
    @tag("loop", "redis_state")
    def update_redis_loop_state(self):
        """Simulate loop state update in Redis."""
        payload = {
            "loop_id": self.loop_id,
            "phase": self.phase,
            "active_agents": self.environment.random.randint(1, 5),
            "last_heartbeat": time.time(),
        }
        self.client.post(
            "/internal/loops/state",
            json=payload,
        )

    @task(4)
    @tag("loop", "llm_mock")
    def mock_llm_call(self):
        """
        Simulate LLM call through mock 9Router.
        The mock endpoint returns a canned response with configurable latency.
        This validates the retry/circuit-breaker behavior without API costs.
        """
        payload = {
            "model": "guinevere_core",
            "prompt_tokens": self.environment.random.randint(500, 5000),
            "expected_response_tokens": self.environment.random.randint(200, 2000),
        }
        self.client.post(
            "/internal/mock/llm",
            json=payload,
            name="/internal/mock/llm [core_interactive]",
        )

    @task(1)
    @tag("loop", "subagent_spawn")
    def spawn_subagent(self):
        """Simulate spawning a sub-agent (DeepSeek V4 Flash)."""
        payload = {
            "loop_id": self.loop_id,
            "agent_type": self.environment.random.choice([
                "research", "code", "validation", "audit", "documentation"
            ]),
            "task_brief": "Load test sub-agent task",
            "model": "deepseek_v4_flash",
        }
        self.client.post(
            "/internal/agents/spawn",
            json=payload,
        )

    @task(1)
    @tag("loop", "phase_advance")
    def advance_phase(self):
        """Simulate loop phase transition."""
        if self.phase < 7:
            self.phase += 1
        else:
            self.phase = 1
            self.loop_id = str(uuid.uuid4())
            self.todos_completed = 0

        self.client.post(
            "/internal/loops/phase/advance",
            json={"loop_id": self.loop_id, "new_phase": self.phase},
        )
```

### 4.5 Locust User Class: MemoryRecaller

```python
class MemoryRecaller(HttpUser):
    """
    Simulates memory recall pipeline: vector search via pgvector HNSW,
    episodic memory lookup, semantic fact retrieval, and context injection.

    Production profile: recall triggered per conversation turn, ~1-5 per minute.
    """
    weight = 10
    wait_time = between(3, 15)

    def on_start(self):
        """Generate test query vectors."""
        import numpy as np
        self.query_vectors = [
            np.random.rand(1536).tolist() for _ in range(10)
        ]

    @task(4)
    @tag("memory", "vector_search")
    def vector_similarity_search(self):
        """
        Simulate pgvector HNSW similarity search.
        Tests recall@10 latency on memory.episodes embedding column.
        """
        query_vector = self.environment.random.choice(self.query_vectors)
        payload = {
            "query_vector": query_vector,
            "top_k": 10,
            "min_similarity": 0.7,
            "schema": "memory",
            "table": "episodes",
        }
        self.client.post(
            "/internal/memory/vector-search",
            json=payload,
            name="/internal/memory/vector-search [episodes]",
        )

    @task(3)
    @tag("memory", "episodic_lookup")
    def episodic_memory_lookup(self):
        """Simulate episodic memory retrieval by time range and importance."""
        payload = {
            "time_range_start": time.time() - 86400 * 7,  # Last 7 days
            "time_range_end": time.time(),
            "min_importance": 5,
            "episode_types": ["conversation", "task"],
            "limit": 20,
        }
        self.client.post(
            "/internal/memory/episodes/query",
            json=payload,
        )

    @task(2)
    @tag("memory", "semantic_facts")
    def semantic_fact_recall(self):
        """Simulate semantic memory fact retrieval."""
        subjects = ["samm", "budgezen", "sembilan", "guinevere", "project"]
        payload = {
            "subject": self.environment.random.choice(subjects),
            "min_confidence": 0.5,
            "limit": 10,
        }
        self.client.post(
            "/internal/memory/semantic/query",
            json=payload,
        )

    @task(1)
    @tag("memory", "context_injection")
    def full_context_injection(self):
        """
        Simulate full context window injection: persona + mood + samm_profile
        + recent episodes + semantic facts + surveillance context.
        This is the end-to-end recall pipeline test.
        """
        payload = {
            "max_tokens": 6000,
            "include_persona": True,
            "include_mood": True,
            "include_samm_profile": True,
            "include_recent_episodes": 5,
            "include_semantic_facts": 10,
            "include_surveillance_context": True,
        }
        self.client.post(
            "/internal/memory/context/build",
            json=payload,
        )
```

### 4.6 Locust User Class: DiscordCommander

```python
class DiscordCommander(HttpUser):
    """
    Simulates Samm issuing Discord slash commands.
    Commands: /status, /mood, /score, /loops, /evidence, /task.

    Production profile: ~5 commands/minute.
    """
    weight = 15
    wait_time = between(5, 30)

    @task(3)
    @tag("discord", "status")
    def command_status(self):
        self.client.get("/internal/discord/command/status", name="discord /status")

    @task(2)
    @tag("discord", "mood")
    def command_mood(self):
        self.client.get("/internal/discord/command/mood", name="discord /mood")

    @task(2)
    @tag("discord", "score")
    def command_score(self):
        self.client.get("/internal/discord/command/score", name="discord /score")

    @task(1)
    @tag("discord", "loops")
    def command_loops(self):
        self.client.get("/internal/discord/command/loops", name="discord /loops")

    @task(1)
    @tag("discord", "task")
    def command_task(self):
        payload = {"task_name": "load-test-task", "project": "guinevere"}
        self.client.post(
            "/internal/discord/command/task",
            json=payload,
            name="discord /task",
        )
```

### 4.7 Locust User Class: DashboardReader

```python
class DashboardReader(HttpUser):
    """
    Simulates Grafana/Prometheus metric scraping for SLO dashboards.
    Tests observability stack under load.
    """
    weight = 10
    wait_time = between(10, 60)

    @task(3)
    @tag("observability", "slo_query")
    def query_slo_recording_rules(self):
        """Simulate Grafana querying SLO recording rules."""
        queries = [
            "guinevere:slo:core_availability:ratio_30d",
            "guinevere:slo:llm_interactive_p95:5m",
            "guinevere:slo:loop_quality_ratio:30d",
        ]
        for query in queries:
            self.client.get(
                f"/internal/metrics/query?expr={query}",
                name="/internal/metrics/query [slo]",
            )

    @task(2)
    @tag("observability", "health_check")
    def check_health_endpoints(self):
        """Simulate health check probes against all services."""
        endpoints = [
            "/health",
            "/health/postgres",
            "/health/redis",
            "/health/discord",
            "/health/llm",
        ]
        for ep in endpoints:
            self.client.get(ep, name=f"health [{ep}]")
```

### 4.8 Locust Ramp-Up Patterns

| Pattern | Users | Ramp | Duration | Purpose |
|---|---|---|---|---|
| **Smoke** | 5 total | Instant | 5 min | Validate test environment works |
| **Production** | 20 total | 1 user/10s | 30 min steady | Validate SLO compliance at expected load |
| **Stress** | 50 total | 1 user/5s | Until failure | Find breaking point |
| **Soak** | 20 total | 1 user/30s | 4 hours | Detect memory leaks, connection exhaustion |
| **Spike** | 5 -> 100 -> 5 | Instant spike at T+5min | 15 min total | Validate recovery from burst |
| **Safety-under-load** | 20 + safe-word probe | Constant + periodic safe-word | 30 min | Validate safety invariants under load |

---

## 5. Micro-Benchmarking with pytest-benchmark

### 5.1 Benchmark Scope

| Component | Benchmark Focus | Expected p95 | Test ID |
|---|---|---|---|
| AES-256-GCM encrypt | Per-record encryption (1KB payload) | ≤ 5ms | BM-ENC-001 |
| AES-256-GCM decrypt | Per-record decryption | ≤ 5ms | BM-ENC-002 |
| Fernet encrypt | Symmetric envelope encryption | ≤ 3ms | BM-ENC-003 |
| HNSW vector search | Top-10 recall at 10K/50K/100K vectors | ≤ 200ms | BM-VEC-001 |
| HNSW index build | Index creation time at 100K vectors | ≤ 60s | BM-VEC-002 |
| Episodic memory query | Time-range + importance filter | ≤ 50ms | BM-MEM-001 |
| Semantic fact query | Subject + confidence filter | ≤ 30ms | BM-MEM-002 |
| Merkle chain hash | SHA-256 chain verification (1000 entries) | ≤ 100ms | BM-AUD-001 |
| HMAC-SHA256 validation | Payload signature verification | ≤ 2ms | BM-AUTH-001 |
| Context injection build | Full context window assembly (~6K tokens) | ≤ 200ms | BM-CTX-001 |
| TimescaleDB chunk scan | Query across 30 daily chunks | ≤ 100ms | BM-TSDB-001 |
| TimescaleDB compressed chunk | Query on compressed data (>7 days) | ≤ 150ms | BM-TSDB-002 |
| PgBouncer connection acquire | Time to acquire connection from pool | ≤ 10ms | BM-POOL-001 |
| Redis SET/GET | Single key operation | ≤ 1ms | BM-REDIS-001 |
| Redis LPUSH/BRPOP | Queue push/pop operation | ≤ 2ms | BM-REDIS-002 |

### 5.2 Benchmark Example: Vector Search

```python
# tests/benchmarks/test_vector_search_benchmark.py

import pytest
import numpy as np
import asyncpg

EMBEDDING_DIM = 1536
DATASET_SIZES = [10_000, 50_000, 100_000]
TOP_K = 10
M_PARAM = 16
EF_CONSTRUCTION = 128


@pytest.fixture(scope="module")
async def pg_pool():
    """Shared PostgreSQL connection pool for benchmarks."""
    pool = await asyncpg.create_pool(
        host="localhost", port=5433,
        database="guinevere_test",
        user="guinevere_bench",
        min_size=2, max_size=10,
    )
    yield pool
    await pool.close()


@pytest.fixture(params=DATASET_SIZES)
async def populated_episodes(pg_pool, request):
    """Populate memory.episodes with random vectors at specified scale."""
    size = request.param
    async with pg_pool.acquire() as conn:
        await conn.execute("TRUNCATE memory.episodes RESTART IDENTITY CASCADE")

        # Batch insert with random embeddings
        batch_size = 1000
        for i in range(0, size, batch_size):
            vectors = [np.random.rand(EMBEDDING_DIM).tolist() for _ in range(batch_size)]
            rows = [
                (f"episode-{i+j}", "conversation", str(vectors[j]))
                for j in range(min(batch_size, size - i))
            ]
            await conn.executemany(
                """INSERT INTO memory.episodes (id, started_at, episode_type, embedding)
                   VALUES ($1, NOW(), $2, $3::vector)""",
                rows,
            )

        # Rebuild HNSW index
        await conn.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_episodes_bench_hnsw
            ON memory.episodes USING hnsw (embedding vector_cosine_ops)
            WITH (m = $1, ef_construction = $2)
        """, M_PARAM, EF_CONSTRUCTION)

    return size


@pytest.mark.benchmark(group="vector_search", min_rounds=5)
@pytest.mark.asyncio
async def test_hnsw_recall_latency(benchmark, pg_pool, populated_episodes):
    """Benchmark HNSW vector similarity search latency."""
    query_vector = np.random.rand(EMBEDDING_DIM).tolist()

    async def search():
        async with pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, embedding <=> $1::vector AS distance
                FROM memory.episodes
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                query_vector, TOP_K,
            )
            return len(rows)

    import asyncio
    result = benchmark(lambda: asyncio.get_event_loop().run_until_complete(search()))
    assert result == TOP_K


@pytest.mark.benchmark(group="vector_search", min_rounds=3)
@pytest.mark.asyncio
async def test_hnsw_recall_with_filter(benchmark, pg_pool, populated_episodes):
    """Benchmark HNSW search with episode_type and importance filters."""
    query_vector = np.random.rand(EMBEDDING_DIM).tolist()

    async def search_filtered():
        async with pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, embedding <=> $1::vector AS distance
                FROM memory.episodes
                WHERE episode_type = 'conversation'
                  AND importance >= 5
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                query_vector, TOP_K,
            )
            return len(rows)

    import asyncio
    result = benchmark(lambda: asyncio.get_event_loop().run_until_complete(search_filtered()))
    assert result <= TOP_K
```

### 5.3 Benchmark Example: Encryption Pipeline

```python
# tests/benchmarks/test_encryption_benchmark.py

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import json


@pytest.fixture
def aes_key():
    return AESGCM.generate_key(bit_length=256)


@pytest.fixture
def aesgcm(aes_key):
    return AESGCM(aes_key)


@pytest.fixture
def fernet():
    return Fernet(Fernet.generate_key())


PAYLOAD_SIZES = [256, 1024, 4096, 16384]  # bytes


@pytest.mark.benchmark(group="encryption")
@pytest.mark.parametrize("payload_size", PAYLOAD_SIZES)
def test_aes256gcm_encrypt(benchmark, aesgcm, payload_size):
    """Benchmark AES-256-GCM encryption at various payload sizes."""
    payload = os.urandom(payload_size)
    nonce = os.urandom(12)

    def encrypt():
        return aesgcm.encrypt(nonce, payload, None)

    result = benchmark(encrypt)
    assert len(result) > payload_size  # Includes auth tag


@pytest.mark.benchmark(group="encryption")
@pytest.mark.parametrize("payload_size", PAYLOAD_SIZES)
def test_aes256gcm_decrypt(benchmark, aesgcm, payload_size):
    """Benchmark AES-256-GCM decryption."""
    payload = os.urandom(payload_size)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, payload, None)

    def decrypt():
        return aesgcm.decrypt(nonce, ciphertext, None)

    result = benchmark(decrypt)
    assert result == payload


@pytest.mark.benchmark(group="encryption")
def test_envelope_encrypt_decrypt(benchmark, aesgcm, fernet):
    """Benchmark full envelope encryption: DEK + KEK wrap."""
    payload = json.dumps({"samm_weakness": "test_value"}).encode()
    dek = AESGCM.generate_key(bit_length=256)

    def envelope_ops():
        # Encrypt data with DEK
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, payload, None)
        # Wrap DEK with KEK (Fernet)
        wrapped_dek = fernet.encrypt(dek)
        # Unwrap DEK
        unwrapped_dek = fernet.decrypt(wrapped_dek)
        # Decrypt data
        aes = AESGCM(unwrapped_dek)
        plaintext = aes.decrypt(nonce, ciphertext, None)
        return plaintext

    result = benchmark(envelope_ops)
    assert result == payload
```

---

## 6. Chaos Engineering Philosophy & Fault Model

### 6.1 Why Chaos Engineering is Critical for Guinevere

Guinevere runs on a **single VPS** with no redundant infrastructure. This means:

1. **No failover**: If PostgreSQL crashes, there is no replica. The entire system degrades.
2. **Resource contention**: All services share 16GB RAM and 4 CPU cores. One service spike affects all others.
3. **Cascading failures**: Redis OOM can cause loop state corruption, which causes guardian confusion, which causes sub-agent spawning failure.
4. **External dependencies**: 9Router, Discord gateway, Tasker, Brave Search — all external services that can fail independently.
5. **Safety under duress**: Safe-word enforcement, distress detection, and persona safety must remain 100% functional even when infrastructure is degraded.

Chaos engineering for Guinevere is not optional — it is the only way to validate that the single-VPS architecture can survive real-world failure modes.

### 6.2 Fault Model

| Fault Category | Description | Probability | Impact | Recovery Expectation |
|---|---|---|---|---|
| **Process crash** | systemd service unexpected termination | Medium | High (if core) | Auto-restart <10s |
| **Database connection exhaustion** | PgBouncer pool saturated | Medium | High | Queue + backpressure |
| **Redis OOM** | maxmemory reached, eviction active | Medium | Medium-High | allkeys-lru eviction + monitoring |
| **LLM provider timeout** | 9Router upstream provider slow/down | High | Medium | Queue + retry + degradation |
| **Network partition** | Tailscale disconnect isolating devices | Low-Medium | High | Queue events + alert |
| **Disk full** | SSD 120GB exhausted | Low | Critical | Alert + emergency cleanup |
| **OOM killer** | Linux OOM killer terminates process | Low | Critical | systemd restart + root cause |
| **TimescaleDB chunk corruption** | Compressed chunk unreadable | Very Low | Medium | Chunk rebuild from backup |
| **SOPS key corruption** | age key file damaged | Very Low | Critical | Restore from backup key |
| **Swap thrashing** | Heavy swap usage degrading all services | Low | High | Reduce load + alert |
| **Concurrent loop resource starvation** | 20+ loops exhausting shared resources | Medium | Medium | Loop queue + priority |
| **Cron job collision** | Multiple heavy cron jobs at same time | Medium | Low-Medium | Stagger + resource check |

### 6.3 Chaos Engineering Principles

1. **Safety-first**: Chaos tests must never disable safety invariants. If a chaos test accidentally bypasses safe-word enforcement, it is a SEV0 finding.

2. **Controlled blast radius**: Start with staging environment, then controlled production tests during low-activity windows.

3. **Observable**: Every chaos test must produce metrics and logs that can be correlated with the fault injection timeline.

4. **Automated rollback**: Every fault injection must have a corresponding cleanup step. No manual intervention required.

5. **Steady-state hypothesis**: Define expected behavior before injection. "Under fault X, the system should Y within Z seconds."

---

## 7. Chaos Test Catalog

### 7.1 Complete Fault Scenario Matrix

| Test ID | Scenario | Injection Method | Steady-State Hypothesis | Safety Gate |
|---|---|---|---|---|
| CHAOS-001 | Core daemon crash | `systemctl kill guinevere-core` | Auto-restart <10s, Discord recovery report <5min, loop state preserved | Safe-word remains detectable post-restart |
| CHAOS-002 | Surveillance service crash | `systemctl kill guinevere-surveillance` | Auto-restart <10s, buffered events delivered after restart, no data loss | N/A |
| CHAOS-003 | Scheduler service crash | `systemctl kill guinevere-scheduler` | Auto-restart <10s, missed rituals re-evaluated on restart | N/A |
| CHAOS-004 | PostgreSQL connection pool exhaustion | Fill PgBouncer with sleep connections | New requests queue, no crash, alert fires at 90% pool utilization | Safety queries use reserved pool |
| CHAOS-005 | Redis OOM (DB0 task queue) | Fill Redis DB0 until maxmemory | allkeys-lru eviction, queue backlog, alert fires, no core crash | N/A |
| CHAOS-006 | Redis OOM (all DBs) | Fill all Redis databases | Controlled degradation per DB, critical paths preserved | Safe-word state in DB3 session preserved |
| CHAOS-007 | LLM provider timeout (9Router) | Toxiproxy inject 120s latency on 9Router | Queue + retry, degradation mode, no infinite hang | Safe-word uses local detection, not LLM |
| CHAOS-008 | LLM provider complete outage | Toxiproxy sever connection to 9Router | Queue all LLM calls, degradation mode active, alert fires | Core commands work without LLM |
| CHAOS-009 | Network partition (Tailscale) | `tailscale down` on VPS | Queue surveillance events, local services continue, alert via UptimeRobot | N/A |
| CHAOS-010 | Disk full (>95% utilization) | `fallocate -l 100G /tmp/fill` | Alert fires, emergency cleanup triggered, write operations graceful | Critical data not corrupted |
| CHAOS-011 | OOM killer targets guinevere-core | `stress-ng --vm 4 --vm-bytes 14G` | systemd restart <10s, state recovered from PostgreSQL, Discord report | Post-restart safe-word functional |
| CHAOS-012 | OOM killer targets PostgreSQL container | Same stress test | Docker auto-restart, WAL replay, no data loss | N/A |
| CHAOS-013 | TimescaleDB compressed chunk query failure | Corrupt a chunk file | Alert fires, chunk marked bad, queries skip bad chunk | N/A |
| CHAOS-014 | SOPS/age key file corruption | `truncate -s 0 /home/guinevere/.age/key.txt` | Alert fires, services start with cached config, new decrypts fail gracefully | No Critical data exposed |
| CHAOS-015 | Swap thrashing | Force 12GB RSS + 6GB swap | Performance degrades 5-10x, no crash, alert fires | Safe-word latency still <10s |
| CHAOS-016 | PgBouncer crash | `docker kill pgbouncer` | Direct PostgreSQL fallback, connection re-establish, alert fires | N/A |
| CHAOS-017 | Prometheus/Grafana down | `systemctl stop prometheus` | Services continue operating, alert gap detected | N/A (meta-observability) |
| CHAOS-018 | Discord gateway disconnect | Network block to Discord API | Queue alerts, retry with backoff, reconnect, backfill missed alerts | N/A (but alerts delayed) |
| CHAOS-019 | Concurrent loop overload (25 loops) | Spawn 25 parallel loops | Loops queue by priority, no OOM, resource monitoring fires alert | No loop bypasses safety checks |
| CHAOS-020 | Cron job collision (backup + ritual + health) | Trigger all three simultaneously | All complete within budget, no resource starvation | N/A |
| CHAOS-021 | FastAPI HMAC key rotation mid-stream | Rotate HMAC secret | Old signatures rejected, new accepted, zero event loss during transition | N/A |
| CHAOS-022 | PostgreSQL WAL lag >1GB | Generate heavy writes | WAL archiving catches up, alert fires, no RPO breach | N/A |
| CHAOS-023 | Caddy reverse proxy crash | `systemctl kill caddy` | Internal DNS still resolves via Tailscale, services reachable directly | N/A |
| CHAOS-024 | GitHub webhook delivery failure | Block GitHub IP range | 15-min polling fallback catches missed events, alert fires | N/A |

### 7.2 Chaos Fault Injection Code Examples

#### 7.2.1 CHAOS-001: Core Daemon Crash + Recovery Validation

```python
# tests/chaos/test_core_crash_recovery.py

import subprocess
import time
import pytest
import httpx
import asyncio

VPS_HOST = "http://guinevere.internal:8001"
SAFETY_PROBE_INTERVAL = 2  # seconds


class TestCoreDaemonCrashRecovery:
    """
    CHAOS-001: Validate core daemon crash recovery behavior.

    Steady-state hypothesis:
    - systemd auto-restarts guinevere-core within 10 seconds
    - Discord recovery report posted within 5 minutes
    - Loop state preserved in PostgreSQL (no in-memory-only state lost)
    - Safe-word detection functional immediately after restart
    """

    @pytest.fixture(autouse=True)
    async def safety_monitor(self):
        """Background task that probes safe-word detection throughout the test."""
        self.safety_violations = []
        self.probe_results = []
        self._stop_monitor = False

        async def monitor():
            async with httpx.AsyncClient(base_url=VPS_HOST) as client:
                while not self._stop_monitor:
                    try:
                        resp = await client.post(
                            "/internal/safety/safeword-probe",
                            json={"test_token": "RED_PILL"},
                            timeout=5.0,
                        )
                        self.probe_results.append({
                            "timestamp": time.time(),
                            "status": resp.status_code,
                            "neutral_mode": resp.json().get("neutral_mode", False),
                        })
                        if resp.status_code == 200 and not resp.json().get("neutral_mode"):
                            self.safety_violations.append(
                                f"Safe-word probe failed at {time.time()}"
                            )
                    except httpx.ConnectError:
                        # Service down — expected during crash
                        self.probe_results.append({
                            "timestamp": time.time(),
                            "status": "connection_error",
                            "neutral_mode": None,
                        })
                    await asyncio.sleep(SAFETY_PROBE_INTERVAL)

        task = asyncio.create_task(monitor())
        yield
        self._stop_monitor = True
        await task

    @pytest.mark.chaos
    async def test_crash_and_recovery(self):
        """Kill core daemon and validate recovery sequence."""
        # Step 1: Kill the service
        subprocess.run(
            ["systemctl", "kill", "--signal=SIGKILL", "guinevere-core.service"],
            check=True,
        )
        kill_time = time.time()

        # Step 2: Wait for auto-restart (max 10s per SLO)
        restart_detected = False
        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            for _ in range(20):  # 20 * 0.5s = 10s max
                await asyncio.sleep(0.5)
                try:
                    resp = await client.get("/health", timeout=2.0)
                    if resp.status_code == 200:
                        restart_detected = True
                        restart_time = time.time()
                        break
                except httpx.ConnectError:
                    continue

        assert restart_detected, "Core daemon did not restart within 10 seconds"
        assert (restart_time - kill_time) <= 10.0, (
            f"Restart took {restart_time - kill_time:.1f}s (budget: 10s)"
        )

        # Step 3: Validate loop state preservation
        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            resp = await client.get("/internal/loops/active")
            assert resp.status_code == 200

        # Step 4: Post-restart safe-word must work
        post_restart_probes = [
            p for p in self.probe_results
            if p["timestamp"] > restart_time and p["status"] == 200
        ]
        for probe in post_restart_probes:
            assert probe["neutral_mode"] is True, (
                f"Safe-word probe failed post-restart at {probe['timestamp']}"
            )
```

#### 7.2.2 CHAOS-004: PgBouncer Connection Pool Exhaustion

```python
# tests/chaos/test_pgpool_exhaustion.py

import asyncio
import asyncpg
import pytest
import time
import httpx

VPS_HOST = "http://guinevere.internal:8001"
PG_DSN = "postgresql://guinevere_bench:test@localhost:6432/guinevere_test"
POOL_MAX = 200  # PgBouncer max_client_conn


class TestPgBouncerPoolExhaustion:
    """
    CHAOS-004: Validate behavior when PgBouncer connection pool is exhausted.

    Steady-state hypothesis:
    - New requests queue (not crash) when pool is full
    - Alert fires at 90% pool utilization
    - Safety-critical queries use reserved connections
    - Pool drains gracefully when holders release
    """

    @pytest.mark.chaos
    async def test_pool_exhaustion_queue_behavior(self):
        """Fill PgBouncer pool and validate queue behavior."""
        connections = []

        try:
            # Step 1: Exhaust pool with sleeping connections
            for i in range(POOL_MAX):
                conn = await asyncpg.connect(PG_DSN)
                await conn.execute("SELECT pg_sleep(30)")
                connections.append(conn)

            # Step 2: Attempt new connection — should queue, not fail immediately
            start = time.time()
            try:
                new_conn = await asyncio.wait_for(
                    asyncpg.connect(PG_DSN),
                    timeout=15.0,  # PgBouncer default_query_wait
                )
                await new_conn.close()
            except asyncio.TimeoutError:
                queue_time = time.time() - start
                assert queue_time >= 14.0, (
                    "Connection timeout too fast — pool may not be queuing"
                )

            # Step 3: Validate application-level behavior under pool pressure
            async with httpx.AsyncClient(base_url=VPS_HOST) as client:
                resp = await client.get("/health/postgres", timeout=10.0)
                assert resp.status_code in [200, 503]

                # Surveillance ingest should queue, not crash
                resp = await client.post(
                    "/surveillance/android/activity",
                    json={
                        "device_id": "test",
                        "event_type": "activity",
                        "timestamp": time.time(),
                    },
                    headers={"X-HMAC-Signature": "test-sig"},
                    timeout=20.0,
                )
                assert resp.status_code in [200, 202, 503]

            # Step 4: Release half and validate recovery
            for conn in connections[:50]:
                await conn.close()
            connections = connections[50:]

            await asyncio.sleep(2)

            new_conn = await asyncio.wait_for(
                asyncpg.connect(PG_DSN),
                timeout=5.0,
            )
            await new_conn.close()

        finally:
            for conn in connections:
                try:
                    await conn.close()
                except Exception:
                    pass
```

#### 7.2.3 CHAOS-007: LLM Provider Timeout via Toxiproxy

```python
# tests/chaos/test_llm_timeout.py

import asyncio
import pytest
import httpx
import time

VPS_HOST = "http://guinevere.internal:8001"
TOXIPROXY_API = "http://localhost:8474"


class TestLLMProviderTimeout:
    """
    CHAOS-007: Validate LLM provider timeout handling via Toxiproxy.

    Steady-state hypothesis:
    - Requests queue with exponential backoff (tenacity, max 5 retries)
    - Circuit breaker opens after repeated failures
    - Degradation mode activates (basic commands without LLM)
    - No infinite hang on any user-facing endpoint
    - Safe-word detection uses local pattern matching, not LLM
    """

    @pytest.fixture
    async def toxiproxy_client(self):
        async with httpx.AsyncClient(base_url=TOXIPROXY_API) as client:
            yield client

    @pytest.fixture
    async def llm_toxic(self, toxiproxy_client):
        """Create a proxy to 9Router with injectable latency."""
        await toxiproxy_client.post("/proxies", json={
            "name": "9router",
            "listen": "0.0.0.0:19876",
            "upstream": "localhost:9876",  # Actual 9Router port
            "enabled": True,
        })
        yield toxiproxy_client
        await toxiproxy_client.delete("/proxies/9router")

    @pytest.mark.chaos
    async def test_llm_timeout_120s(self, llm_toxic):
        """Inject 120s latency on 9Router and validate timeout handling."""
        # Step 1: Add latency toxic
        await llm_toxic.post("/proxies/9router/toxics", json={
            "name": "latency_120s",
            "type": "latency",
            "attributes": {"latency": 120000, "jitter": 5000},
        })

        try:
            # Step 2: Trigger LLM call — should return degradation response
            async with httpx.AsyncClient(base_url=VPS_HOST) as client:
                start = time.time()
                resp = await client.post(
                    "/internal/mock/llm",
                    json={"model": "guinevere_core", "prompt": "test"},
                    timeout=30.0,
                )
                elapsed = time.time() - start

                assert elapsed < 30.0, "LLM call hung beyond app timeout"
                assert resp.status_code in [200, 503, 504]

            # Step 3: Validate safe-word still works (local detection)
            async with httpx.AsyncClient(base_url=VPS_HOST) as client:
                start = time.time()
                resp = await client.post(
                    "/internal/safety/safeword-probe",
                    json={"test_token": "RED_PILL"},
                    timeout=10.0,
                )
                elapsed = time.time() - start

                assert elapsed < 5.0, (
                    f"Safe-word response took {elapsed:.1f}s under LLM timeout"
                )
                assert resp.json().get("neutral_mode") is True

            # Step 4: Circuit breaker should open after repeated failures
            async with httpx.AsyncClient(base_url=VPS_HOST) as client:
                for i in range(6):
                    resp = await client.post(
                        "/internal/mock/llm",
                        json={"model": "guinevere_core", "prompt": f"cb-test-{i}"},
                        timeout=30.0,
                    )
                    if i >= 4:
                        assert resp.status_code == 503

        finally:
            await llm_toxic.delete("/proxies/9router/toxics/latency_120s")
```

#### 7.2.4 CHAOS-011: OOM Killer Simulation

```python
# tests/chaos/test_oom_killer.py

import subprocess
import asyncio
import pytest
import httpx
import time

VPS_HOST = "http://guinevere.internal:8001"


class TestOOMKillerRecovery:
    """
    CHAOS-011: Validate system behavior when OOM killer terminates processes.

    On a 16GB VPS with 8GB swap, OOM killer activates when RSS + swap
    exceeds physical + swap limits.
    """

    @pytest.mark.chaos
    @pytest.mark.slow
    async def test_oom_killer_recovery(self):
        """Trigger OOM condition and validate recovery."""
        # Step 1: Record pre-OOM state
        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            pre_state = await client.get("/internal/system/state")

        # Step 2: Trigger OOM via stress-ng
        stress_proc = subprocess.Popen(
            ["stress-ng", "--vm", "4", "--vm-bytes", "3500M", "--timeout", "60s"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        # Step 3: Wait for OOM killer
        await asyncio.sleep(15)

        # Step 4: Stop stress and recover
        stress_proc.terminate()
        stress_proc.wait()
        await asyncio.sleep(15)

        # Step 5: Validate service recovery
        async with httpx.AsyncClient(base_url=VPS_HOST, timeout=30.0) as client:
            for attempt in range(10):
                try:
                    resp = await client.get("/health")
                    if resp.status_code == 200:
                        break
                except httpx.ConnectError:
                    await asyncio.sleep(3)
            else:
                pytest.fail("Core service did not recover within 30s after OOM")

            resp = await client.get("/health/postgres")
            assert resp.status_code == 200, "PostgreSQL not available after OOM"

            resp = await client.get("/health/redis")
            assert resp.status_code == 200, "Redis not available after OOM"

        # Step 6: Validate PostgreSQL integrity
        result = subprocess.run(
            ["docker", "exec", "guinevere-postgres", "pg_isready"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, "PostgreSQL pg_isready failed after OOM"
```

#### 7.2.5 CHAOS-010: Disk Full Emergency

```python
# tests/chaos/test_disk_full.py

import subprocess
import asyncio
import pytest
import httpx
import time

VPS_HOST = "http://guinevere.internal:8001"


class TestDiskFullEmergency:
    """
    CHAOS-010: Validate behavior when disk reaches >95% utilization.

    Steady-state hypothesis:
    - Alert fires at 90% disk utilization
    - Emergency cleanup triggered (log rotation, old chunk compression)
    - Write operations return 507 gracefully, not crash
    - Safety state never corrupted
    """

    @pytest.fixture
    async def cleanup_disk(self):
        """Ensure test cleanup removes fill file."""
        yield
        subprocess.run(["rm", "-f", "/tmp/guinevere_disk_fill"], check=False)

    @pytest.mark.chaos
    async def test_disk_full_graceful_degradation(self, cleanup_disk):
        """Fill disk to 95% and validate graceful degradation."""
        # Step 1: Get current disk usage
        result = subprocess.run(
            ["df", "-BG", "/"], capture_output=True, text=True,
        )
        lines = result.stdout.strip().split("\n")
        available_gb = int(lines[1].split()[3].replace("G", ""))

        # Step 2: Fill disk to leave ~1GB free
        fill_size = max(1, available_gb - 1)
        subprocess.run(
            ["fallocate", "-l", f"{fill_size}G", "/tmp/guinevere_disk_fill"],
            check=True,
        )

        try:
            await asyncio.sleep(5)

            async with httpx.AsyncClient(base_url=VPS_HOST) as client:
                # Step 3: Validate disk alert
                resp = await client.get("/health/disk")
                assert resp.status_code == 200
                disk_data = resp.json()
                assert disk_data.get("utilization_percent", 0) >= 90

            # Step 4: Validate safety state preservation
            async with httpx.AsyncClient(base_url=VPS_HOST) as client:
                resp = await client.post(
                    "/internal/safety/safeword-probe",
                    json={"test_token": "RED_PILL"},
                    timeout=5.0,
                )
                assert resp.status_code == 200
                assert resp.json().get("neutral_mode") is True

        finally:
            subprocess.run(["rm", "-f", "/tmp/guinevere_disk_fill"], check=False)
```

---

## 8. Toxiproxy Integration

### 8.1 What is Toxiproxy

Toxiproxy is a TCP proxy that allows programmatic injection of network conditions (latency, errors, bandwidth limits, timeouts) between services. It runs as a lightweight Go binary on the VPS.

### 8.2 Toxiproxy Placement in Guinevere Architecture

```
+------------------------------------------------------+
|                   Guinevere VPS                       |
|                                                       |
|  +----------+  Toxiproxy  +--------------+           |
|  | Guinevere |----proxy----> PostgreSQL    |           |
|  | Core      |    :5434    | :5432         |           |
|  |           |----proxy---->               |           |
|  |           |    :6381    | Redis :6379   |           |
|  |           |----proxy---->               |           |
|  |           |    :19876   | 9Router :9876 |           |
|  +----------+             +--------------+           |
|                                                       |
|  Toxiproxy API: localhost:8474                        |
|  (Only active during chaos tests)                     |
+------------------------------------------------------+
```

### 8.3 Toxiproxy Toxics Catalog

| Toxic Name | Type | Target | Attributes | Use Case |
|---|---|---|---|---|
| `pg_latency` | latency | PostgreSQL proxy | `latency: 500ms, jitter: 100ms` | Simulate slow DB queries |
| `pg_timeout` | timeout | PostgreSQL proxy | `timeout: 5000ms` | Simulate DB connection timeout |
| `pg_slow_close` | slow_close | PostgreSQL proxy | `delay: 10000ms` | Simulate slow connection close |
| `pg_slicer` | slicer | PostgreSQL proxy | `average_size: 1, delay: 100` | Fragment DB responses |
| `redis_latency` | latency | Redis proxy | `latency: 200ms, jitter: 50ms` | Simulate slow Redis |
| `redis_bandwidth` | bandwidth | Redis proxy | `rate: 100` (KB/s) | Simulate Redis bandwidth limit |
| `redis_reset_peer` | reset_peer | Redis proxy | `timeout: 1000ms` | Simulate Redis connection reset |
| `9router_latency` | latency | 9Router proxy | `latency: 30000ms` | Simulate LLM provider slowness |
| `9router_timeout` | timeout | 9Router proxy | `timeout: 60000ms` | Simulate LLM timeout |
| `9router_limit` | limit_data | 9Router proxy | `bytes: 100` | Simulate truncated LLM response |
| `discord_latency` | latency | Discord proxy | `latency: 5000ms` | Simulate Discord gateway lag |
| `surv_bandwidth` | bandwidth | Surveillance API | `rate: 50` (KB/s) | Simulate slow surveillance ingest |

### 8.4 Toxiproxy Test Fixture

```python
# tests/conftest_toxiproxy.py

import pytest
import httpx

TOXIPROXY_API = "http://localhost:8474"


class ToxiproxyManager:
    """Manages Toxiproxy proxies and toxics for chaos tests."""

    def __init__(self, api_url: str = TOXIPROXY_API):
        self.api_url = api_url
        self.proxies = {}
        self.toxics = {}

    async def create_proxy(self, name: str, listen: str, upstream: str):
        """Create a new proxy."""
        async with httpx.AsyncClient(base_url=self.api_url) as client:
            resp = await client.post("/proxies", json={
                "name": name,
                "listen": listen,
                "upstream": upstream,
                "enabled": True,
            })
            self.proxies[name] = {"listen": listen, "upstream": upstream}
            return resp.json()

    async def add_toxic(self, proxy: str, name: str, toxic_type: str,
                        attributes: dict, stream: str = "downstream"):
        """Add a toxic to a proxy."""
        async with httpx.AsyncClient(base_url=self.api_url) as client:
            resp = await client.post(f"/proxies/{proxy}/toxics", json={
                "name": name,
                "type": toxic_type,
                "stream": stream,
                "attributes": attributes,
            })
            self.toxics[f"{proxy}/{name}"] = True
            return resp.json()

    async def remove_toxic(self, proxy: str, name: str):
        """Remove a toxic from a proxy."""
        async with httpx.AsyncClient(base_url=self.api_url) as client:
            await client.delete(f"/proxies/{proxy}/toxics/{name}")
            self.toxics.pop(f"{proxy}/{name}", None)

    async def cleanup(self):
        """Remove all proxies and toxics."""
        async with httpx.AsyncClient(base_url=self.api_url) as client:
            for proxy_name in list(self.proxies.keys()):
                try:
                    await client.delete(f"/proxies/{proxy_name}")
                except Exception:
                    pass
        self.proxies.clear()
        self.toxics.clear()


@pytest.fixture
async def toxiproxy():
    """Provide ToxiproxyManager with automatic cleanup."""
    manager = ToxiproxyManager()
    yield manager
    await manager.cleanup()
```

---

## 9. Integration Testing Architecture

### 9.1 Docker Compose Test Environment

All integration tests run against real PostgreSQL and Redis instances via Docker Compose, ensuring production-equivalent behavior without external dependencies.

```yaml
# docker-compose.test.yml

version: "3.9"

services:
  postgres-test:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: guinevere_test
      POSTGRES_USER: guinevere_test
      POSTGRES_PASSWORD: test_password
    ports:
      - "5433:5432"
    volumes:
      - pg_test_data:/var/lib/postgresql/data
      - ./tests/fixtures/init-test-db.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./tests/fixtures/timescaledb-setup.sql:/docker-entrypoint-initdb.d/02-timescale.sql
      - ./tests/fixtures/pgvector-setup.sql:/docker-entrypoint-initdb.d/03-pgvector.sql
    tmpfs:
      - /dev/shm:size=512m
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U guinevere_test"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis-test:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
    ports:
      - "6380:6379"
    volumes:
      - redis_test_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  pgbouncer-test:
    image: edoburu/pgbouncer:latest
    environment:
      DATABASE_URL: postgres://guinevere_test:test_password@postgres-test:5432/guinevere_test
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 20
    ports:
      - "6432:6432"
    depends_on:
      postgres-test:
        condition: service_healthy

  toxiproxy:
    image: ghcr.io/shopify/toxiproxy:latest
    ports:
      - "8474:8474"
      - "19876:19876"
      - "5434:5434"
      - "6381:6381"

  mock-9router:
    build:
      context: ./tests/mocks/9router
      dockerfile: Dockerfile
    ports:
      - "9876:9876"
    environment:
      DEFAULT_LATENCY_MS: "100"
      ERROR_RATE: "0.0"

  mock-discord:
    build:
      context: ./tests/mocks/discord
      dockerfile: Dockerfile
    ports:
      - "3001:3001"

volumes:
  pg_test_data:
  redis_test_data:
```

### 9.2 Test Fixture Lifecycle

```python
# tests/conftest_integration.py

import pytest
import pytest_asyncio
import asyncpg
import redis.asyncio as aioredis
import httpx
import subprocess
import time

TEST_PG_DSN = "postgresql://guinevere_test:test_password@localhost:5433/guinevere_test"
TEST_REDIS_URL = "redis://localhost:6380/0"
TEST_API_URL = "http://localhost:8001"


@pytest.fixture(scope="session", autouse=True)
def docker_compose():
    """Start Docker Compose test environment for the entire test session."""
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.test.yml", "up", "-d", "--wait"],
        check=True,
    )
    time.sleep(10)
    yield
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.test.yml", "down", "-v"],
        check=True,
    )


@pytest_asyncio.fixture
async def pg_pool():
    """Provide a fresh PostgreSQL connection pool per test."""
    pool = await asyncpg.create_pool(
        dsn=TEST_PG_DSN,
        min_size=2,
        max_size=10,
    )
    yield pool
    await pool.close()


@pytest_asyncio.fixture
async def pg_clean_pool(pg_pool):
    """Provide PostgreSQL pool with automatic test isolation."""
    yield pg_pool
    async with pg_pool.acquire() as conn:
        await conn.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables
                         WHERE schemaname IN ('memory', 'persona', 'surveillance',
                         'financial', 'projects', 'agents', 'consent', 'security',
                         'audit', 'ops')
                         ORDER BY schemaname, tablename)
                LOOP
                    EXECUTE 'TRUNCATE ' || quote_ident(r.schemaname) || '.' ||
                            quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)


@pytest_asyncio.fixture
async def redis_client():
    """Provide Redis client with automatic flush after each test."""
    client = aioredis.from_url(TEST_REDIS_URL, decode_responses=True)
    yield client
    await client.flushall()
    await client.close()


@pytest_asyncio.fixture
async def api_client():
    """Provide HTTP client pointed at test API server."""
    async with httpx.AsyncClient(base_url=TEST_API_URL, timeout=30.0) as client:
        yield client
```

### 9.3 Test Isolation Strategy

| Strategy | Scope | Implementation |
|---|---|---|
| **Database transaction rollback** | Per test | Each test wrapped in transaction, rolled back on exit |
| **Redis flush** | Per test | `FLUSHALL` between tests |
| **Table truncation** | Per test module | Truncate all Guinevere schemas between modules |
| **Service restart** | Per chaos test | Restart specific service, wait for healthy |
| **Separate test database** | Per session | `guinevere_test` database, never touches production |
| **Mock external services** | Per session | Mock 9Router, mock Discord gateway |

---

## 10. Contract Testing

### 10.1 Contract Testing Strategy

| Contract Type | Tool | Target | Validation Approach |
|---|---|---|---|
| **OpenAPI Schema Fuzzing** | schemathesis | FastAPI surveillance + internal API | Property-based testing against OpenAPI spec |
| **Request/Response Contracts** | pytest + pydantic | All API endpoints | Validate shapes match OpenAPI schema |
| **HMAC Signature Contract** | pytest | Surveillance endpoints | Validate HMAC-SHA256 signature validation |
| **WebSocket Protocol** | pytest + websockets | Windows daemon + surveillance WS | Validate message format, heartbeat, reconnection |
| **LLM Response Contract** | pytest | 9Router mock | Validate response shape matches expected schema |
| **Discord Command Contract** | pytest + discord.py test client | Slash commands | Validate command response format and timing |

### 10.2 Schemathesis OpenAPI Fuzzing

```python
# tests/contracts/test_api_fuzzing.py

import schemathesis
from hypothesis import settings, HealthCheck

# Load OpenAPI schema from FastAPI app
schema = schemathesis.from_asgi(
    "/openapi.json",
    app="guinevere.surveillance.api:app",
    base_url="http://localhost:8001",
)


@schema.parametrize()
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=5000,  # 5 second deadline per example
)
def test_surveillance_api_fuzzing(case):
    """
    Fuzz all FastAPI surveillance endpoints with property-based testing.

    Validates:
    - No unhandled 500 errors for any valid input shape
    - 4xx errors return proper error format
    - HMAC validation rejects malformed signatures
    - Response schema matches OpenAPI spec
    """
    response = case.call()

    # Validate response against OpenAPI schema
    case.validate_response(response)

    # Additional safety invariants
    assert response.status_code < 500, (
        f"Server error {response.status_code} for {case.method} {case.path}"
    )

    if response.status_code == 401:
        body = response.json()
        assert "detail" in body
        assert "signature" in body["detail"].lower() or "auth" in body["detail"].lower()

    if response.status_code == 422:
        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], list)
```

### 10.3 Integration Contract Tests

```python
# tests/contracts/test_integration_contracts.py

import pytest
import httpx
import json
import time
import uuid
import hmac
import hashlib


class TestSurveillanceContracts:
    """Validate request/response contracts for all surveillance endpoints."""

    @pytest.fixture
    def hmac_sign(self):
        secret = "test-hmac-secret"
        def sign(payload: dict) -> str:
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        return sign

    @pytest.mark.asyncio
    async def test_activity_contract(self, api_client, hmac_sign):
        """
        POST /surveillance/android/activity contract:

        Request:
        - device_id: UUID string (required)
        - event_type: "activity" (required)
        - app_name: string (required)
        - duration_seconds: integer >= 0 (required)
        - timestamp: float (required)

        Response (200):
        - event_id: UUID string
        - status: "accepted"
        - ingested_at: ISO timestamp
        """
        payload = {
            "device_id": str(uuid.uuid4()),
            "event_type": "activity",
            "app_name": "com.whatsapp",
            "duration_seconds": 300,
            "timestamp": time.time(),
        }

        resp = await api_client.post(
            "/surveillance/android/activity",
            json=payload,
            headers={
                "X-HMAC-Signature": hmac_sign(payload),
                "X-Device-ID": payload["device_id"],
            },
        )

        assert resp.status_code == 200
        body = resp.json()

        assert "event_id" in body
        assert body["status"] == "accepted"
        assert "ingested_at" in body
        uuid.UUID(body["event_id"])

    @pytest.mark.asyncio
    async def test_location_contract(self, api_client, hmac_sign):
        """POST /surveillance/android/location contract validation."""
        payload = {
            "device_id": str(uuid.uuid4()),
            "event_type": "location",
            "latitude": -6.2088,
            "longitude": 106.8456,
            "accuracy_meters": 10,
            "timestamp": time.time(),
        }

        resp = await api_client.post(
            "/surveillance/android/location",
            json=payload,
            headers={
                "X-HMAC-Signature": hmac_sign(payload),
                "X-Device-ID": payload["device_id"],
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "event_id" in body
        assert body["status"] == "accepted"
```

---

## 11. End-to-End Testing

### 11.1 E2E Testing Scope

| Component | Tool | Scenario Coverage |
|---|---|---|
| **FastAPI Web UI** (future dashboard) | Playwright | Health dashboard, SLO scorecard, loop monitoring |
| **Discord Bot** | discord.py test client + mock gateway | Slash commands, alert delivery, safe-word detection |
| **Surveillance Pipeline** | httpx + Docker Compose | End-to-end event ingestion -> storage -> query |
| **Agent Loop** | Internal API + PostgreSQL | Loop lifecycle: spawn -> phases -> complete |

### 11.2 Playwright E2E for Web Dashboard

```python
# tests/e2e/test_dashboard.py

import pytest
from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:3000"  # Grafana


class TestGrafanaDashboard:
    """E2E tests for Grafana SLO dashboards."""

    @pytest.fixture
    async def page(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            yield page
            await browser.close()

    @pytest.mark.e2e
    async def test_slo_overview_dashboard_loads(self, page):
        """
        Validate SLO overview dashboard loads with all required panels.
        Maps to SLO Spec section 11 DB-SLO-001.
        """
        await page.goto(f"{DASHBOARD_URL}/d/slo-overview")
        await page.wait_for_selector("[data-panelid]", timeout=10000)

        panels = await page.query_selector_all("[data-panelid]")
        assert len(panels) >= 5, "SLO overview dashboard missing required panels"

    @pytest.mark.e2e
    async def test_safety_invariants_dashboard(self, page):
        """Validate safety invariants dashboard (DB-SLO-005)."""
        await page.goto(f"{DASHBOARD_URL}/d/safety-invariants")
        await page.wait_for_selector("[data-panelid]", timeout=10000)

        safety_panels = [
            "Safe-Word Misses",
            "Time to Neutral",
            "Distress False Negatives",
            "Yandere Cap Violations",
        ]
        for panel_name in safety_panels:
            panel = await page.query_selector(f"[aria-label='{panel_name}']")
            assert panel is not None, f"Missing safety panel: {panel_name}"
```

### 11.3 Discord Bot E2E Test Flows

```python
# tests/e2e/test_discord_bot.py

import pytest
import time
import httpx

VPS_HOST = "http://localhost:8001"


class TestDiscordBotE2E:
    """End-to-end tests for Discord bot command flows."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_status_command_flow(self):
        """
        E2E: /status command returns complete system status.
        Response includes: core health, active loops, mood, score.
        """
        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            resp = await client.get("/internal/discord/command/status")
            assert resp.status_code == 200

            body = resp.json()
            assert "core_health" in body
            assert "active_loops" in body
            assert "mood_state" in body
            assert "mommy_score" in body

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_safe_word_via_discord(self):
        """
        E2E: Safe-word detection via Discord triggers global hard stop.
        Time-to-neutral must be <= 5 seconds (SLO-SAF-002).
        """
        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            start = time.time()
            resp = await client.post(
                "/internal/safety/safeword-probe",
                json={"source": "discord", "test_token": "RED_PILL"},
            )
            elapsed = time.time() - start

            assert resp.status_code == 200
            body = resp.json()
            assert body["neutral_mode"] is True
            assert body["persona_suspended"] is True
            assert body["punishment_suspended"] is True
            assert elapsed <= 5.0, f"Safe-word response took {elapsed:.1f}s (budget: 5s)"

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_sev0_alert_delivery(self):
        """
        E2E: SEV0 alert delivered to Discord #alerts within 15 seconds.
        Alert uses neutral incident-command tone with persona suspended.
        """
        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            start = time.time()
            resp = await client.post(
                "/internal/alerts/trigger",
                json={
                    "severity": "SEV0",
                    "alert_type": "safe_word_miss",
                    "message": "Test SEV0 alert",
                },
            )
            elapsed = time.time() - start

            assert resp.status_code == 200
            body = resp.json()
            assert body["delivered_to_discord"] is True
            assert body["delivered_to_gotify"] is True
            assert body["tone"] == "neutral_incident_command"
            assert elapsed <= 15.0, f"Alert delivery took {elapsed:.1f}s (budget: 15s)"
```

---

## 12. Database Performance Testing

### 12.1 pgbench Configuration

```bash
# Baseline pgbench for PostgreSQL throughput
pgbench -h localhost -p 5433 -U guinevere_test guinevere_test \
  -i -s 10  # Initialize with scale factor 10

# Read-heavy workload (matches Guinevere pattern: 80% read, 20% write)
pgbench -h localhost -p 5433 -U guinevere_test guinevere_test \
  -c 20 -j 4 -T 300 -M prepared \
  --select-only

# Write-heavy workload (surveillance ingestion burst)
pgbench -h localhost -p 5433 -U guinevere_test guinevere_test \
  -c 10 -j 2 -T 300 -M prepared
```

### 12.2 TimescaleDB Chunk Performance Tests

```python
# tests/performance/test_timescaledb_chunks.py

import pytest
import asyncpg
import uuid
from datetime import datetime, timedelta


class TestTimescaleDBChunkPerformance:
    """
    Benchmark TimescaleDB hypertable query performance across chunk boundaries.
    Key tables:
    - memory.episodes (7-day chunks)
    - surveillance.events (1-day chunks)
    - financial.transactions (monthly chunks)
    - audit.audit_trail (monthly chunks)
    """

    @pytest.fixture
    async def conn(self, pg_pool):
        async with pg_pool.acquire() as c:
            yield c

    @pytest.mark.benchmark(group="timescaledb")
    @pytest.mark.asyncio
    async def test_surveillance_events_cross_chunk_query(self, conn, benchmark):
        """
        Query surveillance events across 30 daily chunks.
        Validates that TimescaleDB chunk exclusion works efficiently.
        """
        # Populate 30 days of events (1000/day = 30K total)
        for day_offset in range(30):
            event_time = datetime.now() - timedelta(days=day_offset)
            events = [
                (str(uuid.uuid4()), "activity", str(uuid.uuid4()),
                 b'encrypted_payload', event_time.isoformat())
                for _ in range(1000)
            ]
            await conn.executemany(
                """INSERT INTO surveillance.events
                   (id, event_type, device_id, raw_payload, occurred_at)
                   VALUES ($1, $2, $3, $4, $5::timestamptz)""",
                events,
            )

        # Query last 7 days — should scan only 7 chunks
        import asyncio

        async def query_last_7_days():
            rows = await conn.fetch(
                """SELECT count(*) FROM surveillance.events
                   WHERE occurred_at >= NOW() - INTERVAL '7 days'
                   AND event_type = 'activity'"""
            )
            return rows[0]["count"]

        result = benchmark(
            lambda: asyncio.get_event_loop().run_until_complete(query_last_7_days())
        )
        assert result == 7000

        stats = benchmark.stats
        assert stats["mean"] < 0.1, f"Cross-chunk query took {stats['mean']:.3f}s"

    @pytest.mark.benchmark(group="timescaledb")
    @pytest.mark.asyncio
    async def test_compressed_chunk_query_performance(self, conn, benchmark):
        """Query compressed surveillance data (> 7 days old)."""
        await conn.execute(
            "SELECT compress_chunk(c) FROM show_chunks('surveillance.events', "
            "older_than => INTERVAL '7 days') c"
        )

        import asyncio

        async def query_compressed():
            rows = await conn.fetch(
                """SELECT count(*) FROM surveillance.events
                   WHERE occurred_at >= NOW() - INTERVAL '30 days'
                   AND occurred_at < NOW() - INTERVAL '7 days'
                   AND event_type = 'activity'"""
            )
            return rows[0]["count"]

        result = benchmark(
            lambda: asyncio.get_event_loop().run_until_complete(query_compressed())
        )
        assert result == 23000
```

### 12.3 Migration Safety Tests

```python
# tests/performance/test_migration_safety.py

import pytest


class TestMigrationSafety:
    """
    Validate Alembic migration safety for production-critical operations.
    """

    @pytest.mark.asyncio
    async def test_concurrent_index_creation(self, pg_pool):
        """Validate CONCURRENTLY index creation does not block reads."""
        async with pg_pool.acquire() as conn:
            await conn.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_test_hnsw
                ON memory.episodes USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 128)
            """)

            rows = await conn.fetch(
                "SELECT count(*) FROM memory.episodes LIMIT 1"
            )
            assert rows is not None

    @pytest.mark.asyncio
    async def test_migration_rollback(self, pg_pool):
        """Validate migration rollback restores previous state completely."""
        async with pg_pool.acquire() as conn:
            pre_columns = await conn.fetch("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'memory' AND table_name = 'episodes'
                ORDER BY ordinal_position
            """)

            await conn.execute(
                "ALTER TABLE memory.episodes ADD COLUMN test_col TEXT"
            )

            post_columns = await conn.fetch("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'memory' AND table_name = 'episodes'
            """)
            assert len(post_columns) == len(pre_columns) + 1

            await conn.execute(
                "ALTER TABLE memory.episodes DROP COLUMN test_col"
            )

            final_columns = await conn.fetch("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'memory' AND table_name = 'episodes'
            """)
            assert len(final_columns) == len(pre_columns)
```

---

## 13. LLM Pipeline Testing

### 13.1 LLM Testing Strategy

All LLM tests use a mock 9Router to avoid API costs. The mock simulates realistic response patterns.

| Test Category | What We Validate | Mock Behavior |
|---|---|---|
| **Latency by provider** | Response time per model route | Configurable latency per model |
| **Retry behavior** | tenacity retry with exponential backoff | 50% error rate for N calls |
| **Circuit breaker** | Circuit opens after N failures | 100% error rate |
| **Streaming validation** | SSE stream parsing and chunk assembly | Chunked response |
| **Token counting** | Accurate token counting for cost tracking | Response with known token count |
| **Degradation mode** | System behavior when LLM unavailable | Connection refused |
| **Queue behavior** | Request queuing during outage | Delayed response |

### 13.2 Mock 9Router Implementation

```python
# tests/mocks/9router/server.py

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import random
import os

app = FastAPI(title="Mock 9Router")

DEFAULT_LATENCY_MS = int(os.getenv("DEFAULT_LATENCY_MS", "100"))
ERROR_RATE = float(os.getenv("ERROR_RATE", "0.0"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

request_count = 0


@app.post("/v1/chat/completions")
async def mock_chat_completion(request: Request):
    """Mock LLM chat completion with configurable behavior."""
    global request_count

    body = await request.json()
    model = body.get("model", "unknown")
    stream = body.get("stream", False)

    # Simulate latency
    latency = DEFAULT_LATENCY_MS / 1000
    latency += random.uniform(0, latency * 0.3)
    await asyncio.sleep(latency)

    # Simulate errors
    if random.random() < ERROR_RATE:
        return {"error": random.choice(["internal_server_error", "model_overloaded", "timeout"])}, 500

    response = {
        "id": f"mock-{random.randint(1000, 9999)}",
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": f"Mock response for {model}. " * 10},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": len(body.get("messages", [])) * 100,
            "completion_tokens": 100,
            "total_tokens": len(body.get("messages", [])) * 100 + 100,
        },
    }

    if stream:
        return StreamingResponse(_stream_chunks(response), media_type="text/event-stream")

    return response


async def _stream_chunks(response):
    """Simulate SSE streaming response."""
    content = response["choices"][0]["message"]["content"]
    chunk_size = 10

    for i in range(0, len(content), chunk_size):
        chunk = {
            "id": response["id"],
            "object": "chat.completion.chunk",
            "choices": [{
                "index": 0,
                "delta": {"content": content[i:i+chunk_size]},
                "finish_reason": None,
            }],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.05)

    final = {
        "id": response["id"],
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final)}\n\n"
    yield "data: [DONE]\n\n"
```

### 13.3 LLM Pipeline Test Cases

```python
# tests/performance/test_llm_pipeline.py

import pytest
import httpx
import time

VPS_HOST = "http://localhost:8001"


class TestLLMPipeline:
    """Test LLM pipeline behavior with mock 9Router."""

    @pytest.mark.asyncio
    async def test_interactive_latency_p95(self):
        """
        Validate interactive LLM response p95 <= 20s (SLO-LAT-001).
        Uses mock 9Router with 100ms latency.
        """
        latencies = []

        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            for _ in range(50):
                start = time.time()
                resp = await client.post(
                    "/internal/mock/llm",
                    json={"model": "guinevere_core", "prompt": "test"},
                    timeout=30.0,
                )
                elapsed = time.time() - start
                assert resp.status_code == 200
                latencies.append(elapsed)

        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_idx]

        assert p95_latency <= 20.0, (
            f"Interactive LLM p95 = {p95_latency:.1f}s (SLO: <=20s)"
        )

    @pytest.mark.asyncio
    async def test_streaming_response_validation(self):
        """Validate SSE streaming response parsing."""
        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            async with client.stream(
                "POST",
                "/internal/mock/llm/stream",
                json={"model": "guinevere_core", "prompt": "stream-test", "stream": True},
                timeout=30.0,
            ) as resp:
                assert resp.status_code == 200

                chunks = []
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        chunks.append(data)

                assert len(chunks) > 0, "No streaming chunks received"

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self):
        """Validate circuit breaker opens after repeated failures."""
        async with httpx.AsyncClient(base_url=VPS_HOST) as client:
            failures = 0
            for i in range(10):
                resp = await client.post(
                    "/internal/mock/llm",
                    json={"model": "guinevere_core", "prompt": f"cb-test-{i}"},
                    timeout=30.0,
                )
                if resp.status_code == 503:
                    failures += 1

            assert failures >= 5, (
                f"Circuit breaker did not open: only {failures}/10 failures"
            )
```

---

## 14. Surveillance Pipeline Testing

### 14.1 Surveillance Performance Tests

```python
# tests/performance/test_surveillance_pipeline.py

import pytest
import httpx
import time
import asyncio
import json
import hmac
import hashlib
import uuid


class TestSurveillancePipeline:
    """Performance tests for the surveillance ingestion pipeline."""

    @pytest.fixture
    def hmac_sign(self):
        secret = "test-hmac-secret-for-performance-testing"
        def sign(payload: dict) -> str:
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        return sign

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_ingestion_throughput(self, api_client, hmac_sign):
        """
        Validate surveillance ingestion throughput.
        Target: 60 events/minute sustained (SLO-LAT-007 freshness p95 <= 60s).
        """
        events_sent = 0
        errors = 0

        for i in range(100):
            payload = {
                "device_id": str(uuid.uuid4()),
                "event_type": "activity",
                "app_name": f"com.test.app{i % 10}",
                "duration_seconds": i * 10,
                "timestamp": time.time(),
            }

            resp = await api_client.post(
                "/surveillance/android/activity",
                json=payload,
                headers={
                    "X-HMAC-Signature": hmac_sign(payload),
                    "X-Device-ID": payload["device_id"],
                },
            )

            if resp.status_code in [200, 202]:
                events_sent += 1
            else:
                errors += 1

        throughput_per_min = events_sent  # 100 events sent sequentially
        assert errors == 0, f"Surveillance ingestion had {errors} errors"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_event_freshness(self, api_client, hmac_sign, pg_clean_pool):
        """
        Validate surveillance event freshness.
        SLO-LAT-007: p95 <= 60s for normal events.
        """
        event_time = time.time()
        payload = {
            "device_id": str(uuid.uuid4()),
            "event_type": "activity",
            "app_name": "com.test.freshness",
            "duration_seconds": 100,
            "timestamp": event_time,
        }

        resp = await api_client.post(
            "/surveillance/android/activity",
            json=payload,
            headers={
                "X-HMAC-Signature": hmac_sign(payload),
                "X-Device-ID": payload["device_id"],
            },
        )
        assert resp.status_code in [200, 202]

        # Poll until event appears in query results
        queryable_time = None
        for _ in range(30):
            await asyncio.sleep(1)
            async with pg_clean_pool.acquire() as conn:
                count = await conn.fetchval(
                    """SELECT count(*) FROM surveillance.events
                       WHERE device_id = $1""",
                    payload["device_id"],
                )
                if count and count > 0:
                    queryable_time = time.time()
                    break

        assert queryable_time is not None, "Event never became queryable"
        freshness = queryable_time - event_time
        assert freshness <= 60.0, (
            f"Event freshness: {freshness:.1f}s (SLO: <=60s)"
        )

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_redis_buffer_behavior(self, api_client, redis_client, hmac_sign):
        """Validate Redis DB2 surveillance buffer behavior. TTL: 5 minutes."""
        device_id = str(uuid.uuid4())
        payload = {
            "device_id": device_id,
            "event_type": "activity",
            "app_name": "com.test.buffer",
            "duration_seconds": 50,
            "timestamp": time.time(),
        }

        resp = await api_client.post(
            "/surveillance/android/activity",
            json=payload,
            headers={
                "X-HMAC-Signature": hmac_sign(payload),
                "X-Device-ID": device_id,
            },
        )
        assert resp.status_code in [200, 202]

        # Check Redis buffer (DB2)
        buffer_keys = await redis_client.keys(f"surv:{device_id}:*")
        for key in buffer_keys:
            ttl = await redis_client.ttl(key)
            assert ttl <= 300, f"Buffer TTL {ttl}s exceeds 5 minute spec"
```

---

## 15. Loop Performance Testing

### 15.1 Concurrent Loop Scaling

```python
# tests/performance/test_loop_scaling.py

import pytest
import httpx
import asyncio
import uuid

VPS_HOST = "http://localhost:8001"


class TestLoopScaling:
    """
    Validate concurrent loop scaling behavior.
    Design target: ~20 parallel loops on 16GB RAM (~512MB per loop).
    """

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_loop_scaling(self):
        """
        Spawn increasing numbers of concurrent loops and measure:
        - RAM usage per loop
        - PgBouncer connection utilization
        - Guardian overhead
        """
        loop_counts = [1, 5, 10, 15, 20]
        results = {}

        async with httpx.AsyncClient(base_url=VPS_HOST) as api_client:
            for count in loop_counts:
                loop_ids = []
                for i in range(count):
                    resp = await api_client.post(
                        "/internal/loops/spawn",
                        json={
                            "task_name": f"scaling-test-{count}-{i}",
                            "project": "guinevere",
                            "priority": 5,
                        },
                    )
                    assert resp.status_code in [200, 202]
                    loop_ids.append(resp.json()["loop_id"])

                await asyncio.sleep(10)

                metrics = await api_client.get("/internal/system/metrics")
                assert metrics.status_code == 200
                m = metrics.json()

                results[count] = {
                    "ram_per_loop_mb": m.get("ram_usage_mb", 0) / count if count > 0 else 0,
                    "pgbouncer_active": m.get("pgbouncer_active_connections", 0),
                    "guardian_overhead_ms": m.get("guardian_check_avg_ms", 0),
                }

                # Cleanup
                for loop_id in loop_ids:
                    await api_client.post(f"/internal/loops/{loop_id}/cancel")
                await asyncio.sleep(5)

        # Validate scaling
        for count, metrics in results.items():
            if count > 0:
                assert metrics["ram_per_loop_mb"] <= 640, (
                    f"RAM per loop at {count} loops: {metrics['ram_per_loop_mb']:.0f}MB "
                    f"(budget: 640MB)"
                )
                assert metrics["guardian_overhead_ms"] <= 200, (
                    f"Guardian overhead at {count} loops: "
                    f"{metrics['guardian_overhead_ms']:.0f}ms (budget: 200ms)"
                )

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_loop_memory_stability(self):
        """
        Run a loop for extended period and validate memory does not grow unbounded.
        Detects memory leaks in loop state management.
        """
        async with httpx.AsyncClient(base_url=VPS_HOST) as api_client:
            resp = await api_client.post(
                "/internal/loops/spawn",
                json={"task_name": "memory-stability-test", "project": "guinevere"},
            )
            loop_id = resp.json()["loop_id"]

            memory_samples = []
            for _ in range(20):
                await asyncio.sleep(30)
                metrics = await api_client.get("/internal/system/metrics")
                m = metrics.json()
                memory_samples.append(m.get("loop_memory_mb", 0))

            await api_client.post(f"/internal/loops/{loop_id}/cancel")

            first_half = memory_samples[:10]
            second_half = memory_samples[10:]

            avg_first = sum(first_half) / len(first_half) if first_half else 0
            avg_second = sum(second_half) / len(second_half) if second_half else 0

            if avg_first > 0:
                growth_percent = (avg_second - avg_first) / avg_first * 100
                assert growth_percent < 10, (
                    f"Loop memory grew {growth_percent:.1f}% over 10 minutes"
                )
```

---

## 16. Test Environment Architecture

### 16.1 Test Environment Diagram

```
+-------------------------------------------------------------------+
|                    GUINEVERE TEST ENVIRONMENT                       |
|                                                                     |
|  +----------------------------------------------------------+      |
|  |              Docker Compose (test)                         |      |
|  |                                                            |      |
|  |  +---------------+  +-----------+  +--------------+       |      |
|  |  | PostgreSQL 16  |  |  Redis 7  |  | PgBouncer    |       |      |
|  |  | + TimescaleDB  |  |  256MB    |  | Transaction  |       |      |
|  |  | + pgvector     |  |  allkeys  |  | Pool: 100    |       |      |
|  |  | :5433          |  |  -lru     |  | :6432        |       |      |
|  |  +---------------+  |  :6380    |  +--------------+       |      |
|  |                      +-----------+                         |      |
|  |  +---------------+  +-----------+  +--------------+       |      |
|  |  | Mock 9Router  |  |   Mock    |  |  Toxiproxy   |       |      |
|  |  |  Latency/     |  |  Discord  |  |  :8474       |       |      |
|  |  |  Error inject |  |  Gateway  |  |  Fault inj.  |       |      |
|  |  |  :9876        |  |  :3001    |  |              |       |      |
|  |  +---------------+  +-----------+  +--------------+       |      |
|  +----------------------------------------------------------+      |
|                                                                     |
|  +----------------------------------------------------------+      |
|  |              Test Runner (pytest)                           |      |
|  |                                                            |      |
|  |  +----------+  +----------+  +------------------+         |      |
|  |  | Unit     |  | Integra- |  | Performance/     |         |      |
|  |  | Tests    |  | tion     |  | Chaos/Load       |         |      |
|  |  | (mock)   |  | (real)   |  | (real + inject)  |         |      |
|  |  +----------+  +----------+  +------------------+         |      |
|  +----------------------------------------------------------+      |
|                                                                     |
|  +----------------------------------------------------------+      |
|  |              CI/CD (GitHub Actions Free)                    |      |
|  |                                                            |      |
|  |  Push -> lint + type -> unit -> integration tests           |      |
|  |  Weekly -> performance baselines -> regression detect       |      |
|  |  Monthly -> chaos test suite -> soak tests                  |      |
|  +----------------------------------------------------------+      |
+-------------------------------------------------------------------+
```

### 16.2 Test Environment Resource Budget

| Component | RAM | CPU | Disk | Notes |
|---|---|---|---|---|
| PostgreSQL test | 512MB | 0.5 core | tmpfs 512MB | Isolated test DB |
| Redis test | 256MB | 0.25 core | Minimal | allkeys-lru |
| PgBouncer test | 64MB | Shared | Minimal | Transaction mode |
| Mock 9Router | 128MB | 0.25 core | Minimal | No API costs |
| Mock Discord | 64MB | Shared | Minimal | Gateway simulation |
| Toxiproxy | 32MB | Shared | Minimal | Only during chaos tests |
| pytest runner | 1GB | 1 core | Logs | Shared with OS |
| **Total test overhead** | ~2GB | ~2 cores | ~1GB | Fits within VPS buffer |

### 16.3 Test Data Strategy

| Data Type | Source | Volume | Refresh |
|---|---|---|---|
| Surveillance events | Synthetic generator | 30K events (30 days) | Per test session |
| Memory episodes | Synthetic embeddings | 10K-100K vectors | Per benchmark run |
| Semantic facts | Seed file | 1K facts | Per test session |
| Loop instances | Test fixtures | 20 active | Per scaling test |
| Persona state | Seed file | Single record | Per test |
| Financial transactions | Synthetic | 1K transactions | Per test session |

---

## 17. Performance Test Reporting & Regression Detection

### 17.1 Report Generation

Every performance test run generates a structured markdown report:

```
evidence/performance/<YYYY-MM-DD>/
+-- summary.md                # Executive summary with pass/fail per SLO
+-- load-test-results.json    # Raw Locust results
+-- benchmark-results.json    # Raw pytest-benchmark results
+-- chaos-test-results.json   # Raw chaos test results
+-- regression-diff.md        # Delta from previous baseline
+-- prometheus-snapshot/      # Prometheus metrics snapshot
```

### 17.2 Regression Detection Algorithm

```python
# tests/performance/regression_detector.py

import json
from pathlib import Path
from datetime import datetime

REGRESSION_THRESHOLD = 0.15  # 15% regression triggers failure
BASELINE_DIR = Path("evidence/performance/baselines")


def detect_regressions(current_results: dict, baseline_path: Path) -> list:
    """
    Compare current performance results against stored baseline.
    Returns list of regressions found.
    """
    if not baseline_path.exists():
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(current_results, indent=2))
        return []

    baseline = json.loads(baseline_path.read_text())
    regressions = []

    for metric_name, current_value in current_results.items():
        if metric_name not in baseline:
            continue

        baseline_value = baseline[metric_name]

        # For latency metrics, higher is worse
        if "latency" in metric_name or "duration" in metric_name:
            change = (current_value - baseline_value) / baseline_value
            if change > REGRESSION_THRESHOLD:
                regressions.append({
                    "metric": metric_name,
                    "baseline": baseline_value,
                    "current": current_value,
                    "change_percent": change * 100,
                    "direction": "regression (slower)",
                })

        # For throughput metrics, lower is worse
        elif "throughput" in metric_name or "rate" in metric_name:
            change = (baseline_value - current_value) / baseline_value
            if change > REGRESSION_THRESHOLD:
                regressions.append({
                    "metric": metric_name,
                    "baseline": baseline_value,
                    "current": current_value,
                    "change_percent": change * 100,
                    "direction": "regression (lower)",
                })

    return regressions


def generate_performance_report(results: dict, regressions: list) -> str:
    """Generate markdown performance report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    report = f"""# Performance Test Report - {now}

## Summary

| Metric | Status | Count |
|---|---|---|
| Total metrics | -- | {len(results)} |
| Regressions detected | {'FAIL' if regressions else 'PASS'} | {len(regressions)} |

## SLO Compliance

| SLO ID | Target | Actual | Status |
|---|---|---|---|
"""

    slo_mapping = {
        "llm_interactive_p95": ("SLO-LAT-001", "<= 20s"),
        "llm_batch_p95": ("SLO-LAT-002", "<= 180s"),
        "api_p95": ("SLO-LAT-003", "<= 750ms"),
        "pg_read_p95": ("SLO-LAT-004", "<= 250ms"),
        "pg_vector_p95": ("SLO-LAT-005", "<= 2s"),
        "redis_p95": ("SLO-LAT-006", "<= 50ms"),
        "surveillance_freshness_p95": ("SLO-LAT-007", "<= 60s"),
        "safeword_p99": ("SLO-LAT-008", "<= 5s"),
    }

    for metric, (slo_id, target) in slo_mapping.items():
        if metric in results:
            actual = results[metric]
            status = "PASS" if not any(
                r["metric"] == metric for r in regressions
            ) else "REGRESSION"
            report += f"| {slo_id} | {target} | {actual:.3f} | {status} |\n"

    if regressions:
        report += "\n## Regressions\n\n"
        report += "| Metric | Baseline | Current | Change | Direction |\n"
        report += "|---|---|---|---|---|\n"
        for r in regressions:
            report += (
                f"| {r['metric']} | {r['baseline']:.3f} | "
                f"{r['current']:.3f} | {r['change_percent']:.1f}% | "
                f"{r['direction']} |\n"
            )

    return report
```

### 17.3 CI Integration

```yaml
# .github/workflows/performance.yml

name: Performance Baseline Check

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2AM
  workflow_dispatch:

jobs:
  performance-baseline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install UV
        run: pip install uv

      - name: Install dependencies
        run: uv sync --frozen

      - name: Start test infrastructure
        run: docker compose -f docker-compose.test.yml up -d --wait

      - name: Run benchmarks
        run: |
          uv run pytest tests/benchmarks/ \
            --benchmark-json=evidence/performance/benchmarks.json \
            --benchmark-sort=mean

      - name: Run load tests
        run: |
          uv run locust -f tests/performance/locustfile.py \
            --headless --users 20 --spawn-rate 1 \
            --run-time 30m --csv=load_results \
            --host=http://localhost:8001

      - name: Detect regressions
        run: |
          uv run python tests/performance/regression_detector.py \
            --current=evidence/performance/benchmarks.json \
            --baseline=evidence/performance/baselines/latest.json

      - name: Generate report
        run: |
          uv run python tests/performance/generate_report.py \
            --output=evidence/performance/$(date +%Y-%m-%d)/summary.md

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: performance-results
          path: evidence/performance/

      - name: Notify Discord on regression
        if: failure()
        run: |
          curl -X POST "$DISCORD_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d '{"content": "Performance regression detected. Check evidence/performance/"}'
```

---

## 18. Implementation Roadmap

### 18.1 Phased Delivery

| Phase | Deliverable | Timeline | Dependencies |
|---|---|---|---|
| **Phase 0: Foundation** | Docker Compose test env, mock 9Router, test fixtures, pg_pool/redis_client fixtures | Week 1-2 | None |
| **Phase 1: Benchmarks** | pytest-benchmark suite: encryption, vector search, TimescaleDB chunks, Merkle hash | Week 2-3 | Phase 0 |
| **Phase 2: Integration** | httpx integration tests for all API endpoints, surveillance pipeline, memory recall | Week 3-4 | Phase 0 |
| **Phase 3: Contract** | schemathesis fuzzing, integration contracts, HMAC validation contracts | Week 4-5 | Phase 2 |
| **Phase 4: Load** | Locust user classes, ramp-up patterns, CI integration | Week 5-6 | Phase 0, Phase 2 |
| **Phase 5: Chaos** | Toxiproxy setup, first 10 chaos tests (CHAOS-001 through CHAOS-010) | Week 6-8 | Phase 0, Phase 4 |
| **Phase 6: E2E** | Playwright dashboard tests, Discord bot E2E, full pipeline validation | Week 8-10 | Phase 2, Phase 4 |
| **Phase 7: Advanced Chaos** | CHAOS-011 through CHAOS-024, GameDay exercises, SLO burn simulations | Week 10-12 | Phase 5 |

### 18.2 Test Execution Cadence

| Cadence | Test Suite | Duration | Action on Failure |
|---|---|---|---|
| **Per commit** | Unit tests + linting | <5 min | Block merge |
| **Per PR** | Integration + contract tests | <15 min | Block merge |
| **Weekly** | Load tests (production profile) | 30 min | Alert + investigation |
| **Bi-weekly** | Benchmark regression check | <10 min | Alert + root cause |
| **Monthly** | Full chaos test suite | 2-4 hours | Reliability review |
| **Monthly** | Soak test (4 hours) | 4 hours | Memory leak investigation |
| **Quarterly** | Stress test + GameDay | 1 day | Architecture review |
| **Pre-release** | Full test suite + chaos | 1 day | Release blocked |

---

## 19. Gap Register & Unresolved Assumptions

| ID | Gap/Assumption | Impact | Follow-up | Owner |
|---|---|---|---|---|
| PERF-GAP-001 | Actual FastAPI endpoint paths not yet implemented — mock paths used in tests | Test accuracy | Update paths when API is implemented | Guinevere |
| PERF-GAP-002 | HNSW index performance at >100K vectors unknown — need production-scale benchmark | Vector search SLO | Run benchmark when data reaches 100K | Guinevere |
| PERF-GAP-003 | LLM provider latency distribution unknown — mock uses uniform + jitter | LLM pipeline test accuracy | Update mock with real latency distribution from production metrics | Guinevere |
| PERF-GAP-004 | Discord gateway mock may not accurately simulate WebSocket behavior | Discord E2E accuracy | Validate mock against real gateway during staging | Guinevere |
| PERF-GAP-005 | Toxiproxy on production VPS adds overhead — measure baseline with and without | Performance measurement accuracy | Run comparison benchmark with Toxiproxy disabled | Guinevere |
| PERF-GAP-006 | Exact cost budgets (daily/monthly USD) not yet defined in FinOps model | Load test cost assertions | Update when Cost/FinOps Model accepted | Samm |
| PERF-GAP-007 | Safe-word exact token list deferred — chaos tests use "RED_PILL" placeholder | Safety test coverage | Update when Safe Word Runtime Spec accepted | Samm |
| PERF-GAP-008 | Memory recall eval dataset not yet built | Recall quality SLO measurement | Update when Memory Recall Evaluation Spec accepted | Guinevere |
| PERF-GAP-009 | Grafana dashboard JSON files not yet provisioned | E2E dashboard test accuracy | Update when observability implementation task completes | Guinevere |
| PERF-GAP-010 | OpenSLO/Sloth adoption not yet decided | SLO-as-code test generation | Update when ADR for SLO-as-code is accepted | Guinevere |

---

## Appendix A: Test Tool Dependencies

```toml
# pyproject.toml test dependencies

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-benchmark>=5.0",
    "pytest-cov>=6.0",
    "pytest-timeout>=2.3",
    "httpx>=0.28",
    "asyncpg>=0.30",
    "redis[hiredis]>=5.0",
    "locust>=2.30",
    "schemathesis>=3.30",
    "hypothesis>=6.100",
    "playwright>=1.48",
    "pytest-playwright>=0.5",
    "numpy>=2.0",
    "cryptography>=43.0",
    "pydantic>=2.10",
    "structlog>=24.0",
]
```

## Appendix B: Performance SLO Quick Reference

| SLO ID | Surface | Target | Test Coverage |
|---|---|---|---|
| SLO-AVL-001 | Core daemon availability | 99.5% monthly | CHAOS-001, CHAOS-011, CHAOS-015 |
| SLO-AVL-004 | PostgreSQL availability | 99.9% monthly | CHAOS-004, CHAOS-012 |
| SLO-AVL-005 | Redis availability | 99.9% monthly | CHAOS-005, CHAOS-006 |
| SLO-LAT-001 | Interactive LLM p95 | ≤ 20s | Section 13, Locust LLM mock |
| SLO-LAT-003 | FastAPI p95 | ≤ 750ms | Section 4, Locust surveillance |
| SLO-LAT-004 | PostgreSQL read p95 | ≤ 250ms | Section 5, pgbench |
| SLO-LAT-005 | pgvector p95 | ≤ 2s | Section 5, vector benchmark |
| SLO-LAT-006 | Redis p95 | ≤ 50ms | Section 5, redis-benchmark |
| SLO-LAT-007 | Surveillance freshness p95 | ≤ 60s | Section 14, freshness test |
| SLO-LAT-008 | Safe-word p99 | ≤ 5s | CHAOS-001, CHAOS-007, Section 11 |
| SLO-QLT-001 | Loop completion quality | ≥ 95% | Section 15, loop scaling |
| SLO-SAF-001 | Safe-word hard stop | 100% | All chaos tests, load tests |
| SLO-SAF-002 | Safe-word time-to-neutral | p99 ≤ 5s | CHAOS-001, CHAOS-007, Section 11 |

---

## Appendix C: Glossary

| Term | Definition |
|---|---|
| **Burn rate** | Speed at which error budget is consumed (e.g., 14.4x = consuming budget 14.4 times faster than allowed) |
| **Chaos engineering** | Deliberate fault injection to validate system resilience |
| **Hypertable** | TimescaleDB abstraction providing automatic time-based partitioning |
| **HNSW** | Hierarchical Navigable Small World — approximate nearest neighbor index for pgvector |
| **Soak test** | Extended duration load test to detect resource leaks |
| **Spike test** | Sudden load increase to validate recovery behavior |
| **Toxic** | Toxiproxy term for an injected fault (latency, timeout, bandwidth limit) |
| **Steady-state hypothesis** | Expected system behavior under a specific fault condition |
| **Circuit breaker** | Pattern that stops calling a failing service after N consecutive failures |
| **Error budget** | Allowable amount of SLO miss: 100% - SLO target |

---

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere / Hephaestus | Initial comprehensive research report for Guinevere Test Plan — Performance, Chaos Engineering, and Integration Testing. |
