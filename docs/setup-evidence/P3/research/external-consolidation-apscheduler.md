# External Best-Practice Research: P3-015 Memory Consolidation & APScheduler Daily Jobs

**Date**: 2026-06-02  
**Scope**: APScheduler 4.x (AsyncScheduler) patterns, idempotent episodic-to-semantic consolidation, importance scoring, stale pruning, timezone handling, testing without systemd  
**Sources**: Official APScheduler docs, GitHub test suite, real-world OSS memory architectures (MIND, CraniMem, AutoMem, ZenBrain, YourMemory)

---

## Table of Contents

1. [APScheduler 4.x Architecture & Job Design](#1-apscheduler-4x-architecture--job-design)
2. [Async Database Job Patterns](#2-async-database-job-patterns)
3. [Daily Cron Scheduling & Timezone Handling](#3-daily-cron-scheduling--timezone-handling)
4. [Idempotent Episodic-to-Semantic Consolidation](#4-idempotent-episodic-to-semantic-consolidation)
5. [Importance Scoring & Forgetting Curves](#5-importance-scoring--forgetting-curves)
6. [Stale Pruning & Retention Configuration](#6-stale-pruning--retention-configuration)
7. [Job Registration Verification](#7-job-registration-verification)
8. [Deterministic Testing Without systemd](#8-deterministic-testing-without-systemd)
9. [Recommended Job Design](#9-recommended-job-design)
10. [Rollback Strategy](#10-rollback-strategy)

---

## 1. APScheduler 4.x Architecture & Job Design

### 1.1 AsyncScheduler (v4.x) — The Recommended Interface

APScheduler 4.x introduces `AsyncScheduler` (based on AnyIO, supporting both asyncio and Trio). The v3.x `AsyncIOScheduler` still exists but the 4.x API is the forward path.

**Key architectural points** ([source: userguide](https://apscheduler.readthedocs.io/en/master/userguide.html)):

- **Context manager is mandatory** for async: `async with AsyncScheduler() as scheduler:`
- **Two-tier concept**: *Schedules* (when to run) + *Tasks* (what to run) + *Jobs* (actual execution instances)
- **Built-in triggers**: `CronTrigger`, `IntervalTrigger`, `CalendarIntervalTrigger`, `OrTrigger`, `AndTrigger`
- **Persistence via data stores**: `SQLAlchemyDataStore` for PostgreSQL, with `AsyncpgEventBroker` for cross-process coordination
- **Job executors**: `async` (for coroutines), `threadpool`, `processpool`

### 1.2 Minimal AsyncScheduler with CronTrigger ([source](https://apscheduler.readthedocs.io/en/master/userguide.html))

```python
from apscheduler import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger

def daily_consolidation():
    """Runs memory consolidation logic."""
    ...

async def main():
    async with AsyncScheduler() as scheduler:
        await scheduler.add_schedule(
            daily_consolidation,
            CronTrigger(hour=3, minute=0, timezone="Asia/Bangkok"),
            id="daily_consolidation",
        )
        await scheduler.run_until_stopped()
```

### 1.3 AsyncScheduler with Persistent PostgreSQL Store

From the official [`async_postgres.py` example](https://github.com/agronholm/apscheduler/blob/master/examples/standalone/async_postgres.py):

```python
from sqlalchemy.ext.asyncio import create_async_engine
from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.interval import IntervalTrigger

async def main():
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    data_store = SQLAlchemyDataStore(engine)
    async with AsyncScheduler(data_store) as scheduler:
        await scheduler.add_schedule(tick, IntervalTrigger(seconds=1), id="tick")
        await scheduler.run_until_stopped()
```

### 1.4 Key Configuration Parameters

| Parameter | Default | Recommendation | Rationale |
|-----------|---------|----------------|-----------|
| `max_concurrent_jobs` | 100 | `1` for consolidation | Consolidation must be sequential to avoid race conditions on memory state |
| `cleanup_interval` | 900s | Keep default | Cleans up expired schedule acquisitions |
| `lease_duration` | 30s | Keep default | How long a scheduler holds a schedule lease |
| `task_defaults` | — | `coalesce=True` | Merge missed runs into a single execution |
| `job_executors` | async only | Add `threadpool` for blocking ops | If consolidation includes DB I/O, use threadpool executor |

---

## 2. Async Database Job Patterns

### 2.1 Transactional Outbox Pattern for Reliable Job Completion

From the deterministic-job-pipeline project ([source](https://github.com/imgeaslikok/deterministic-job-pipeline)):

The **Transactional Outbox pattern** ensures at-least-once delivery with deduplication:

```
1. Job row + outbox event written in same DB transaction
2. Periodic publisher reads pending outbox → dispatches
3. SELECT ... FOR UPDATE row-level locking prevents concurrent execution
4. UNIQUE(job_id, attempt_no) constraint as hard dedup backstop
```

### 2.2 Idempotency via Deterministic Keys ([source](https://github.com/earendil-works/absurd/blob/main/docs/concepts.md))

Two patterns emerge from production systems:

**Pattern A — Spawn-time deduplication**:
```python
# If same idempotency_key already exists, return existing
scheduler.add_schedule(
    consolidate_memories,
    CronTrigger(hour=3, timezone="Asia/Bangkok"),
    id="daily_consolidation",  # Acts as idempotency key
)
```

**Pattern B — Execution deduplication**:
```python
async def consolidate_memories():
    """Idempotent via watermark — safe to re-run."""
    last_run = await get_last_consolidation_watermark()
    # Process only memories with created_at > last_run
    # UPSERT semantic memories: ON CONFLICT (content_hash) DO UPDATE
```

### 2.3 Async DB Session Management ([source: SQLAlchemy asyncio docs](http://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html))

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def consolidate_memories():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # All reads and writes in one transaction
            ...
```

**Key rules**:
- One `AsyncSession` per consolidation run
- Use `async with session.begin()` for atomic transaction boundaries
- Separate `AsyncSession` for job status tracking vs. memory data

### 2.4 Job Error Handling Pattern ([source](https://github.com/agronholm/apscheduler/discussions/1016))

```python
import functools

def handle_job_errors(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            # Custom alerting/metrics here
            raise  # Let APScheduler see the failure → EVENT_JOB_ERROR
    return wrapper

@handle_job_errors
async def consolidate_memories():
    ...
```

---

## 3. Daily Cron Scheduling & Timezone Handling

### 3.1 Asia/Bangkok Timezone — DST Analysis

**Asia/Bangkok (ICT, UTC+7) does NOT observe Daylight Saving Time.** This is a significant advantage:

- No DST transitions → no spring-forward/fall-back issues
- `Asia/Bangkok` is stable year-round at UTC+7
- No risk of the CronTrigger infinite-loop bug at DST boundaries (see [issue #1021](https://github.com/agronholm/apscheduler/issues/1021))

### 3.2 Recommended CronTrigger Configuration

```python
from zoneinfo import ZoneInfo
from apscheduler.triggers.cron import CronTrigger

# Asia/Bangkok — no DST, safe for CronTrigger
TZ_BANGKOK = ZoneInfo("Asia/Bangkok")

trigger = CronTrigger(
    hour=3,        # 03:00 ICT = 20:00 UTC previous day
    minute=0,
    second=0,
    timezone=TZ_BANGKOK,
)

# Alternative: UTC-based with offset
# 03:00 ICT = 20:00 UTC
trigger_utc = CronTrigger(
    hour=20,
    minute=0,
    timezone="UTC",
)
```

### 3.3 DST Safety Notes (for future portability)

If the timezone ever changes to one with DST:

- **APScheduler 3.x CronTrigger has known DST bugs** — infinite loops at transitions (issues [#1021](https://github.com/agronholm/apscheduler/issues/1021), [#1036](https://github.com/agronholm/apscheduler/issues/1036))
- **APScheduler 4.x master has fixes** using `ZoneInfo` instead of `pytz`, but DST-aware scheduling is still "wall clock" based
- **Mitigation**: Use UTC internally, convert display to local time. Or stick with `Asia/Bangkok` (no DST).

### 3.4 Jitter for Production ([source](https://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html))

```python
# Add random delay ±300s to avoid thundering herd
trigger = CronTrigger(
    hour=3, minute=0, timezone=TZ_BANGKOK,
    jitter=300,  # Random delay up to 5 minutes
)
```

---

## 4. Idempotent Episodic-to-Semantic Consolidation

### 4.1 Theoretical Foundation

Multiple OSS memory architectures implement consolidation:

| System | Consolidation Trigger | Mechanism |
|--------|----------------------|-----------|
| **MIND** ([source](https://github.com/StuckInTheNet/mind-memory)) | Tier router | Exponential decay `exp(-lambda * delta_t)`, Laplace-smoothed frequency activation |
| **CraniMem** ([arXiv 2603.15642](https://www.arxiv.org/pdf/2603.15642)) | Every N turns or idle | Replay score = intrinsic utility + frequency bonus; low-utility traces discarded |
| **AutoMem** ([automem.ai](https://automem.ai/docs/core-concepts/consolidation/)) | Scheduled background | 7-factor exponential decay: age, access, relationships, importance, confidence, floor clamp |
| **ZenBrain** ([github](https://github.com/zensation-ai/zenbrain)) | Sleep consolidation | FSRS spaced repetition, Hebbian strengthening, emotional modulation (up to 3x half-life) |
| **YourMemory** ([github](https://github.com/sachitrafa/YourMemory)) | On recall + batch | `strength = importance * e^(-effective_λ * days) * (1 + recall_count * 0.2)` |

### 4.2 Recommended Consolidation Algorithm

Based on best-practice synthesis:

```python
async def consolidate_memories():
    """
    Episodic → semantic consolidation with idempotent watermark.

    Safe to re-run: uses last_consolidation_at watermark.
    All writes use UPSERT (ON CONFLICT DO UPDATE).
    """
    async with AsyncSessionLocal() as session:
        # Step 1: Read watermark (idempotency anchor)
        last_run = await get_consolidation_watermark(session)

        # Step 2: Fetch new episodic memories since last run
        episodes = await get_new_episodes(session, since=last_run)

        if not episodes:
            return {"consolidated": 0, "skipped": 0}

        # Step 3: Score and filter episodes
        candidates = []
        for ep in episodes:
            score = calculate_importance(ep)
            if score >= IMPORTANCE_THRESHOLD:
                candidates.append((ep, score))

        # Step 4: Convert to semantic memories (UPSERT)
        for episode, score in candidates:
            semantic = extract_semantic_fact(episode)
            await upsert_semantic_memory(
                session,
                content_hash=hash_content(semantic),
                content=semantic,
                importance=score,
                source_episode_id=episode.id,
            )

        # Step 5: Update watermark
        await update_consolidation_watermark(session, datetime.now(UTC))

        await session.commit()
        return {"consolidated": len(candidates), "skipped": len(episodes) - len(candidates)}
```

### 4.3 Idempotency Guarantees

| Mechanism | How It Ensures Idempotency |
|-----------|---------------------------|
| **Watermark** | `last_consolidation_at` prevents re-processing old episodes |
| **Content hash** | `UNIQUE(content_hash)` on semantic memory table — duplicate facts merged |
| **UPSERT** | `INSERT ... ON CONFLICT (content_hash) DO UPDATE SET importance = GREATEST(existing.importance, excluded.importance), last_seen_at = NOW()` |
| **Transaction** | All writes in one `session.begin()` — atomic commit or rollback |

---

## 5. Importance Scoring & Forgetting Curves

### 5.1 Ebbinghaus Forgetting Curve Formula

The canonical exponential forgetting curve ([source: MPI-SWS](https://learning.mpi-sws.org/memorize/)):

```
R(t) = e^(-λ * t)
```

Where:
- **R(t)** = retention probability at time t
- **λ** = decay constant (forgetting rate)
- **t** = time elapsed since last review/consolidation

### 5.2 Multi-Factor Importance Scoring (synthesized from AutoMem + ZenBrain + YourMemory)

```python
DECAY_RATES = {
    "fact": 0.16,        # ~24 days half-life
    "strategy": 0.10,    # ~38 days half-life
    "preference": 0.12,  # ~30 days half-life
    "assumption": 0.20,  # ~19 days half-life
    "ephemeral": 0.35,   # ~11 days half-life
}

IMPORTANCE_FLOOR = 0.3   # High-importance memory never decays below 30% of its importance

def calculate_retention_score(
    memory: Memory,
    now: datetime,
) -> float:
    """
    Compute retention score using multi-factor exponential decay.

    Factors:
    1. Age-based: exp(-λ * days_since_creation)
    2. Access boost: 1 + 0.2 * log(1 + recall_count)
    3. Importance scaling: 0.5 + importance (scales 0.5 to 1.5)
    4. Relationship preservation: 1 + 0.3 * log(1 + relationship_count)
    5. Importance floor: score >= importance * IMPORTANCE_FLOOR
    """
    days = max((now - memory.created_at).days, 0)
    base_lambda = DECAY_RATES.get(memory.category, 0.16)

    # Importance modulates decay rate
    effective_lambda = base_lambda * (1 - memory.importance * 0.8)
    effective_lambda = max(effective_lambda, 0.01)

    # Core exponential decay
    age_factor = math.exp(-effective_lambda * days)

    # Access reinforcement
    access_factor = 1 + 0.2 * math.log(1 + memory.recall_count)

    # Importance scaling
    importance_factor = 0.5 + memory.importance

    # Relationship preservation (connected memories decay slower)
    relationship_factor = 1 + 0.3 * math.log(1 + len(memory.related_ids))

    # Combined score (capped at 1.0)
    score = min(age_factor * access_factor * importance_factor * relationship_factor, 1.0)

    # Importance floor — high-importance memories never decay into oblivion
    floor = memory.importance * IMPORTANCE_FLOOR
    return max(score, floor)
```

### 5.3 Recommended Importance Sources

| Signal | Source | Weight |
|--------|--------|--------|
| **Recency** | Last accessed timestamp | Higher for recent |
| **Frequency** | `recall_count` counter | `1 + 0.2 * log(1 + count)` |
| **User feedback** | Explicit rating (1-5) | Linear multiplier |
| **Emotional valence** | Sentiment analysis | ±30% modulation |
| **Relationship count** | Graph edge count | Logarithmic boost |
| **Cross-session mention** | Session dedup counter | +0.1 per cross-session hit |

---

## 6. Stale Pruning & Retention Configuration

### 6.1 Configurable Retention Policy

From best practices across OSS memory systems, a **configurable retention model** is essential.

```python
from pydantic import BaseModel
from typing import Literal

class RetentionConfig(BaseModel):
    """Configurable retention policy for memory pruning."""

    # Minimum retention score threshold (0.0 to 1.0)
    min_retention_score: float = 0.05

    # Maximum age in days before eligible for pruning
    max_age_days: int = 365

    # Maximum semantic memories before pruning triggers
    max_semantic_count: int = 10_000

    # Pruning mode
    mode: Literal["soft_delete", "archive", "delete"] = "archive"

    # Categories to protect from pruning
    protected_categories: list[str] = ["strategy", "preference"]

    # Importance floor — never prune memories above this importance
    protected_importance_floor: float = 0.7

    # Dry-run mode — log what would be pruned but do nothing
    dry_run: bool = False
```

### 6.2 Pruning Algorithm

```python
async def prune_stale_memories(config: RetentionConfig):
    """
    Prune stale memories based on configurable policy.

    Safe to re-run: uses idempotent soft-delete pattern.
    """
    async with AsyncSessionLocal() as session:
        # Find candidates: low score + old + not protected
        candidates = await get_prune_candidates(
            session,
            max_score=config.min_retention_score,
            max_age_days=config.max_age_days,
            max_count=config.max_semantic_count,
            protected_categories=config.protected_categories,
            protected_importance_floor=config.protected_importance_floor,
        )

        if config.dry_run:
            logger.info(f"DRY RUN: would prune {len(candidates)} memories")
            return {"pruned": 0, "dry_run": len(candidates)}

        if config.mode == "soft_delete":
            await soft_delete_memories(session, candidates)
        elif config.mode == "archive":
            await archive_memories(session, candidates)
        elif config.mode == "delete":
            await hard_delete_memories(session, candidates)

        await session.commit()
        logger.info(f"Pruned {len(candidates)} memories (mode={config.mode})")
        return {"pruned": len(candidates), "mode": config.mode}
```

### 6.3 Protection Rules

| Rule | Condition | Action |
|------|-----------|--------|
| High importance | `importance >= 0.7` | Never prune |
| Protected category | `category in ["strategy", "preference"]` | Skip unless user-confirmed |
| Recently accessed | `last_accessed_at < 30 days ago` | Skip |
| Relationship anchor | `relationship_count >= 3` | Keep (hub node) |

---

## 7. Job Registration Verification

### 7.1 Check Schedule Exists and Is Active

From APScheduler's own test suite ([source](https://github.com/agronholm/apscheduler/blob/master/tests/test_schedulers.py)):

```python
async def verify_schedule_registered(scheduler: AsyncScheduler, schedule_id: str) -> dict:
    """Verify a schedule is registered and active."""
    schedules = await scheduler.get_schedules()
    for s in schedules:
        if s.id == schedule_id:
            return {
                "registered": True,
                "id": s.id,
                "task_id": s.task_id,
                "next_run_time": s.next_run_time,
                "trigger": str(s.trigger),
            }
    return {"registered": False, "id": schedule_id}
```

### 7.2 Subscription-Based Verification

```python
from apscheduler.events import ScheduleAdded, ScheduleRemoved

async def verify_schedule_added(scheduler: AsyncScheduler, schedule_id: str) -> bool:
    """Subscribe to ScheduleAdded event to verify registration."""
    event_received = asyncio.Event()

    def listener(event):
        if isinstance(event, ScheduleAdded) and event.schedule_id == schedule_id:
            event_received.set()

    unsubscribe = scheduler.subscribe(listener)
    try:
        await asyncio.wait_for(event_received.wait(), timeout=5.0)
        return True
    except asyncio.TimeoutError:
        return False
    finally:
        unsubscribe()
```

### 7.3 Test Assertion Pattern ([source](https://github.com/agronholm/apscheduler/blob/master/tests/test_schedulers.py))

```python
async def test_consolidation_schedule_registered():
    async with AsyncScheduler() as scheduler:
        await scheduler.start_in_background()
        await scheduler.add_schedule(
            consolidate_memories,
            CronTrigger(hour=3, timezone="Asia/Bangkok"),
            id="daily_consolidation",
        )

        schedules = await scheduler.get_schedules()
        assert any(s.id == "daily_consolidation" for s in schedules)

        schedule = next(s for s in schedules if s.id == "daily_consolidation")
        assert schedule.task_id.endswith("consolidate_memories")
        assert schedule.next_run_time is not None
```

---

## 8. Deterministic Testing Without systemd

### 8.1 Why Not systemd Timer

The checklist mentions `systemctl status guinevere-scheduler`, but:

- **systemd timers are OS-level**, require root or lingering, and are not portable (Windows/macOS)
- **APScheduler is in-process**, runs with the application, needs no external daemon
- **Testing**: systemd timers can't be tested in unit tests; APScheduler schedules can
- **Separation**: Job logic (code) should be testable independently from job triggering (infrastructure)

### 8.2 Testing AsyncScheduler Without Real Time ([source](https://github.com/agronholm/apscheduler/issues/293))

APScheduler maintainer advice: **Triggers are pure functions** — input datetime → output datetime. Test them in isolation:

```python
from zoneinfo import ZoneInfo
from apscheduler.triggers.cron import CronTrigger

def test_cron_trigger_next_fire():
    """CronTrigger is a pure function — no scheduler needed."""
    tz = ZoneInfo("Asia/Bangkok")
    trigger = CronTrigger(hour=3, minute=0, timezone=tz)

    now = datetime(2026, 6, 2, 10, 0, tzinfo=tz)  # 10:00 ICT
    next_time = trigger.next()

    assert next_time is not None
    assert next_time.hour == 3
    assert next_time.minute == 0
    # Next 03:00 ICT after June 2 10:00 = June 3 03:00 ICT
    assert next_time.day == 3
```

### 8.3 Integration Testing with Background Scheduler ([source](https://github.com/agronholm/apscheduler/blob/master/tests/test_schedulers.py))

Using `pytest-asyncio` or `anyio` as the test plugin:

```python
import pytest
from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

@pytest.fixture
async def scheduler():
    async with AsyncScheduler() as s:
        await s.start_in_background()
        yield s

@pytest.mark.asyncio
async def test_consolidation_job_runs(scheduler):
    """Test that the consolidation job actually executes via the scheduler."""
    results = []

    async def track_result():
        results.append("executed")

    await scheduler.add_schedule(
        track_result,
        IntervalTrigger(seconds=0.1),  # Fast for testing
        id="test_consolidation",
    )

    await asyncio.sleep(0.3)
    assert "executed" in results
```

### 8.4 Using `freezegun` for Time Control ([source](https://github.com/agronholm/apscheduler/issues/293))

```python
from freezegun import freeze_time

@pytest.mark.asyncio
async def test_consolidation_watermark(scheduler):
    """Test watermark-based idempotency with frozen time."""
    # Set time to 2026-06-02 03:00 ICT (scheduled run time)
    with freeze_time("2026-06-02 03:00:00", tz_offset=7):
        result = await consolidate_memories()
        assert result["consolidated"] > 0

    # Re-run at same time — should be idempotent
    with freeze_time("2026-06-02 03:05:00", tz_offset=7):
        result = await consolidate_memories()
        assert result["consolidated"] == 0  # Already processed
```

### 8.5 Using `async-solipsism` for Fully Isolated Event Loop ([source](https://github.com/bmerry/async-solipsism))

```python
@pytest.fixture
def event_loop_policy():
    """No real I/O — fully deterministic event loop."""
    import async_solipsism
    return async_solipsism.EventLoopPolicy()
```

### 8.6 Test Matrix

| Test Type | What It Verifies | Tool | systemd Required? |
|-----------|-----------------|------|-------------------|
| Unit: trigger | `CronTrigger.next()` | pytest | No |
| Unit: consolidation fn | Idempotent watermark | pytest-asyncio | No |
| Unit: scoring | `calculate_retention_score()` | pytest + freezegun | No |
| Integration: scheduler | Schedule registered + job runs | AsyncScheduler in test | No |
| Integration: pruning | Dry-run vs real | pytest + DB fixture | No |
| E2E: full pipeline | Consolidation + prune cycle | AsyncScheduler + test DB | No |
| Smoke: systemd | OS-level timer active | `systemctl status` | **Yes** — optional |

**Conclusion**: systemd is only needed for the smoke test. All code-level verification can (and should) be done deterministically with pytest.

---

## 9. Recommended Job Design

### 9.1 Consolidated Daily Job

```python
"""
P3-015 Memory Consolidation — Daily Job Design
===============================================
Scheduled via APScheduler AsyncScheduler with CronTrigger.
Runs daily at 03:00 ICT (Asia/Bangkok, no DST).
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone
from typing import Any

from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.core.config import settings  # hypothetical config
from app.memory.models import Memory, RetentionConfig

UTC = timezone.utc
TZ_BANGKOK = "Asia/Bangkok"
logger = logging.getLogger(__name__)


async def build_scheduler() -> AsyncScheduler:
    """Build the APScheduler with PostgreSQL persistence."""
    engine = create_async_engine(settings.database.url)
    data_store = SQLAlchemyDataStore(engine)
    return AsyncScheduler(
        data_store,
        max_concurrent_jobs=1,  # Only one consolidation at a time
    )


async def register_jobs(scheduler: AsyncScheduler) -> None:
    """Register all daily jobs."""

    # Job 1: Episodic → Semantic Consolidation
    await scheduler.add_schedule(
        consolidate_memories,
        CronTrigger(hour=3, minute=0, timezone=TZ_BANGKOK, jitter=300),
        id="daily_consolidation",
    )

    # Job 2: Stale Pruning (runs after consolidation)
    await scheduler.add_schedule(
        prune_stale_memories,
        CronTrigger(hour=4, minute=0, timezone=TZ_BANGKOK, jitter=300),
        id="daily_pruning",
    )

    logger.info("Registered daily jobs: consolidation (03:00 ICT), pruning (04:00 ICT)")


async def consolidate_memories() -> dict[str, Any]:
    """
    Idempotent episodic-to-semantic consolidation.

    - Reads watermark to find unprocessed episodes
    - Scores each episode for importance
    - UPSERTs high-importance episodes as semantic facts
    - Updates watermark on success
    """
    # (Implementation as described in Section 4.2)
    ...


async def prune_stale_memories() -> dict[str, Any]:
    """
    Configurable stale pruning with safety protections.

    - Uses RetentionConfig for thresholds (default: min_score=0.05, max_age=365d)
    - Respects protected categories and importance floors
    - Archive mode by default; dry-run available
    """
    config = RetentionConfig(**settings.retention.model_dump())
    # (Implementation as described in Section 6.2)
    ...
```

### 9.2 Separation of Concerns

```
┌──────────────────────────────────────────────────┐
│                  AsyncScheduler                   │
│  ┌──────────────────────┐  ┌───────────────────┐  │
│  │ daily_consolidation  │  │  daily_pruning    │  │
│  │ (03:00 ICT)          │  │  (04:00 ICT)      │  │
│  └──────────┬───────────┘  └─────────┬─────────┘  │
│             │                        │             │
│  ┌──────────▼────────────────────────▼─────────┐  │
│  │          SQLAlchemyDataStore                 │  │
│  │         (PostgreSQL persistence)             │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐      ┌──────────────────────┐
│  Episodic Store   │      │  Semantic Store      │
│  (raw sessions)   │ ───► │  (consolidated facts) │
└──────────────────┘      └──────────────────────┘
```

### 9.3 Configuration

```python
# app/config/retention.py
class RetentionSettings(BaseModel):
    min_retention_score: float = 0.05
    max_age_days: int = 365
    max_semantic_count: int = 10_000
    mode: Literal["soft_delete", "archive", "delete"] = "archive"
    protected_categories: list[str] = ["strategy", "preference"]
    protected_importance_floor: float = 0.7
    dry_run: bool = False  # Safety: log-only until explicitly enabled

    # Consolidation thresholds
    importance_threshold: float = 0.3   # Minimum importance to promote
    min_episode_length: int = 10        # Minimum tokens/words to consider
    max_consolidation_batch: int = 500  # Max episodes per run

# app/config/scheduler.py
class SchedulerSettings(BaseModel):
    timezone: str = "Asia/Bangkok"
    consolidation_hour: int = 3
    consolidation_minute: int = 0
    pruning_hour: int = 4
    pruning_minute: int = 0
    jitter_seconds: int = 300
    max_concurrent_jobs: int = 1
    database_url: str = "postgresql+asyncpg://..."
```

---

## 10. Rollback Strategy

### 10.1 Consolidation Rollback

```python
async def rollback_consolidation(target_date: str) -> dict:
    """
    Rollback consolidation for a specific date.

    - Deletes semantic memories created during that run
    - Resets watermark to before that run
    - Preserves episodes (raw data never deleted)
    """
    async with AsyncSessionLocal() as session:
        # Find consolidation run
        run = await get_consolidation_run(session, target_date)

        # Delete semantic facts created in this run
        await session.execute(
            delete(SemanticMemory).where(
                SemanticMemory.source_run_id == run.id
            )
        )

        # Reset watermark
        await update_consolidation_watermark(session, run.watermark_before)

        await session.commit()
        return {
            "rolled_back": True,
            "date": target_date,
            "facts_removed": run.facts_created,
        }
```

### 10.2 Pruning Rollback

```python
async def rollback_pruning(target_date: str) -> dict:
    """
    Rollback pruning for a specific date.

    - Works only if mode was 'archive' (soft_delete or archive have undo)
    - 'delete' mode is NOT rollback-safe → requires DB restore
    """
    async with AsyncSessionLocal() as session:
        # Find pruned memories that were archived
        archived = await session.execute(
            select(ArchivedMemory).where(
                ArchivedMemory.pruned_at >= target_date
            )
        )

        # Restore from archive
        for mem in archived.scalars():
            await session.execute(
                insert(Memory).values(**mem.to_memory_dict())
            )
            await session.delete(mem)

        await session.commit()
        return {
            "restored": archived.rowcount,
            "from_archive": True,
        }
```

### 10.3 Rollback Decision Matrix

| Scenario | Rollback Possible? | Method | Risk |
|----------|-------------------|--------|------|
| Wrong consolidation threshold | Yes | Delete semantic facts, reset watermark | Low (episodes preserved) |
| Incorrect importance scoring | Yes | Same as above, re-run with corrected scoring | Low |
| Over-pruning (archive mode) | Yes | Restore from archive table | Low |
| Over-pruning (soft-delete) | Yes | UPDATE is_active=True | Low |
| Over-pruning (hard-delete) | **No** | Requires DB restore from backup | High |
| Scheduler misconfiguration | Yes | Remove/add schedule via API | None |
| Timezone error | Yes | Update CronTrigger timezone | None (Asia/Bangkok has no DST) |

### 10.4 Safety Guarantees

```python
# NEVER hard-delete by default — always archive first
# Require explicit config change to enable hard-delete
RETENTION_DEFAULT_MODE = "archive"

# High importance memories are NEVER pruned automatically
PROTECTED_IMPORTANCE_FLOOR = 0.7

# Config validation before pruning
def validate_retention_config(config: RetentionConfig) -> None:
    if config.mode == "delete" and not config.protected_categories:
        raise ValueError("Cannot enable hard-delete without protected categories")
    if config.min_retention_score > 0.3:
        raise ValueError(f"min_retention_score too aggressive: {config.min_retention_score}")
```

---

## Key Findings Summary

| Area | Finding | Source |
|------|---------|--------|
| **AsyncScheduler** | Use v4.x `AsyncScheduler` as context manager; `run_until_stopped()` or `start_in_background()` | [APScheduler userguide](https://apscheduler.readthedocs.io/en/master/userguide.html) |
| **Timezone** | Asia/Bangkok has no DST → safe with CronTrigger; prefer `ZoneInfo("Asia/Bangkok")` over pytz | [CronTrigger docs](https://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html) |
| **Persistence** | `SQLAlchemyDataStore` with `asyncpg` engine for PostgreSQL | [async_postgres.py](https://github.com/agronholm/apscheduler/blob/master/examples/standalone/async_postgres.py) |
| **Idempotency** | Watermark + content hash → UPSERT pattern; `max_concurrent_jobs=1` | [absurd/idempotency](https://github.com/earendil-works/absurd/blob/main/docs/concepts.md) |
| **Importance** | Multi-factor: age decay + access reinforcement + relationship boost + importance floor | [AutoMem consolidation](https://automem.ai/docs/core-concepts/consolidation/), [YourMemory](https://github.com/sachitrafa/YourMemory) |
| **Pruning** | Archive-first, configurable thresholds, protected categories, dry-run mode | [MIND memory](https://github.com/StuckInTheNet/mind-memory), [CraniMem](https://www.arxiv.org/pdf/2603.15642) |
| **Testing** | Pure function trigger tests + integration with `freezegun`/`async-solipsism`; systemd optional | [APScheduler test suite](https://github.com/agronholm/apscheduler/blob/master/tests/test_schedulers.py) |
| **Rollback** | Archive mode enables undo; hard-delete requires DB backup | Synthesized from job pipeline patterns |
| **systemd** | Not required for code verification; only for smoke testing OS-level timer | [Issue #293](https://github.com/agronholm/apscheduler/issues/293) |

---

## References

1. APScheduler Documentation: https://apscheduler.readthedocs.io/en/master/
2. APScheduler GitHub (test suite): https://github.com/agronholm/apscheduler
3. MIND Memory Architecture: https://github.com/StuckInTheNet/mind-memory
4. AutoMem Consolidation: https://automem.ai/docs/core-concepts/consolidation/
5. CraniMem (arXiv): https://www.arxiv.org/pdf/2603.15642
6. ZenBrain: https://github.com/zensation-ai/zenbrain
7. YourMemory: https://github.com/sachitrafa/YourMemory
8. Deterministic Job Pipeline: https://github.com/imgeaslikok/deterministic-job-pipeline
9. Absurd Workflow (idempotency): https://github.com/earendil-works/absurd
10. async-solipsism (testing): https://github.com/bmerry/async-solipsism
11. Ebbinghaus Forgetting Curve (MPI-SWS): https://learning.mpi-sws.org/memorize/
12. FSRS Spaced Repetition: https://www.mindomax.com/spaced-repetition-algorithms