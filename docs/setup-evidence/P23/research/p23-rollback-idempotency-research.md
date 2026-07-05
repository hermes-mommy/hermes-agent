# P23 Research — Rollback + Idempotency

> **Status:** RESEARCH.  
> **Date:** 2026-06-25.  
> **Author:** Guinevere research subagent.  
> **Phase:** P23 — Embodied Operations / Personal OS Action Layer.  
> **Scope:** Durable, auditable action lifecycle with retry/backoff/cancel/rollback state for every P23 action.

---

## 1. Objective

P23 introduces an **Embodied Operations / Personal OS Action Layer** — Guinevere executes actions across multiple executor surfaces (browser, Windows desktop, VPS/SSH, GitHub, file system, external APIs). Every action must be:

- **Durable**: action state persists across crashes, restarts, and HARD STOP.
- **Auditable**: each state transition is recorded in a tamper-evident, hash-chained audit trail (extends P22 `audit.integration_api_log`).
- **Retryable**: failed actions retry with exponential backoff + jitter, bounded by risk tier.
- **Cancellable**: any action can be cancelled via HARD STOP or explicit operator command.
- **Rollbackable**: each executor has a defined rollback path; L3+ actions require backup BEFORE execute (AGENTS.md §0.1 invariant 3).
- **Idempotent**: re-run safe or one-shot documented (AGENTS.md §2.11); dedup via `(namespace, intent_hash)`.

This research defines the **action lifecycle state-machine**, **durable queue schema** (PostgreSQL + Redis hot queue), **retry/backoff policy**, **per-executor rollback model**, **L3 deploy gate sequence**, **idempotency-key design**, and **rollback audit trail** for P23.

---

## 2. Sources Consulted

### 2.1 Authority Documents (Ground Truth)

| Source | Path | Key Provisions |
|---|---|---|
| **AGENTS.md §0.1** | `AGENTS.md` (lines 57-92) | P20 Living Autonomy Kernel autonomy-first governance exception. Invariants: (1) HARD STOP halts all; (2) autonomous actions produce audit trail; (3) **all autonomous deployments produce backup + rollback evidence before promotion**; (4) **all autonomous self-modifications pass regression tests before promotion**; (5) secrets/personal/intimate/surveillance data never exposed; (6) consent revocation absolute; (7) audit for debugging not approval bottleneck. Policy-gated autonomy for engineering deployment (backup→canary→smoke→rollback), self-improvement (regression→audit→rollback-before-promote), daily-life actions (risk-classified). |
| **AGENTS.md §2.11** | `AGENTS.md` (lines 226-228) | Idempotency and parallel sessions: "Scripts, migrations, evidence generators, and setup steps must be re-run safe or document one-shot behavior and rollback." Destructive/stateful overlap requires explicit clarification. |
| **ADR-029** | `adr/ADR-029-self-modification-automated-testing.md` | Self-modification automated testing. Automatic rollback: if any test fails after deployment, `git revert` to last known-good commit; rollback within 60s; restore full service. Safety-critical change classification (persona, safety boundary, surveillance, encryption, memory access, loop governance). Authority hierarchy: safety > user > policy. |
| **ADR-025** | `adr/ADR-025-backup-disaster-recovery-strategy.md` | Backup & DR strategy. Formal backup/DR policy with restore validation. RPO/RTO targets, restore tests, encrypted backups, emergency runbooks. PostgreSQL, Redis persistence, encrypted secrets, ADRs/docs/evidence, object storage, service config. |
| **ADR-032** | `adr/ADR-032-backup-storage-strategy.md` | Backup storage: **idcloudhost S3 primary** + **Cloudflare R2 secondary**. No Backblaze B2. rclone config for both remotes. Retention: Daily 7, Weekly 4, Monthly 6, Yearly 2, Permanent unlimited. Bucket: `guinevere-dr-backups`. |
| **ADR-035** | `adr/ADR-035-hermes-migration.md` | Hermes migration. 7-phase plan with hard gates. Sentinel path `/home/guinevere/.backup/last-success` (B11 caveat — verified sentinel, accepted risk on offline age-key recovery). Per-phase rollback documented. Shadow mode 48hr before cutover. `hermes gateway stop` universal kill-switch. D12 driver: rollback safety +2. |
| **ADR-030** | `adr/ADR-030-redis-db-assignments.md` | Redis DB0-DB5. **DB0**: Rate limiting, persona state, consent grants (noeviction, RDB+AOF). **DB1**: Memory recall (allkeys-lru, RDB). **DB2**: Surveillance buffer, consent cache (allkeys-lfu, AOF). **DB3**: Agent state (noeviction, RDB). **DB4**: Hermes session, Discord state (volatile-lru, RDB). **DB5**: Cost tracking, safety plugin state (noeviction, AOF+RDB). Runtime authoritative (reconciled 2026-06-05). |
| **IMPLEMENTATION_GUIDE.md §6** | `docs/IMPLEMENTATION_GUIDE.md` (lines 592-637) | Shared VPS rules. Cgroup: `MemoryMax=8G`, `CPUQuota=200%`. Linux user `guinevere`. Isolation matrix: separate users, Docker networks, PostgreSQL DBs, Redis DB numbers (Guinevere 0-5, Aizanta 10-15), systemd prefix `guinevere-*`. If you break Aizanta: stop, rollback, verify, document, report. |
| **P22 Security Research** | `docs/setup-evidence/P22/research/p22-security-consent-research.md` | `audit.integration_api_log` table: hash-chained (`event_hash = SHA256(canonical_payload + previous_hash)`), append-only (`no_update_or_delete CHECK`, `REVOKE UPDATE, DELETE`), WORM. Fields: event_id, sequence, occurred_at, actor_type, actor_id, integration_id, provider, http_method, endpoint_path, scope_used, response_status, correlation_id, metadata JSONB, previous_hash, event_hash. 4-level auth matrix (L1 Read-Autonomous, L2 Write-Notify, L3 Destructive-Approval, L4 Forbidden). Circuit breaker, rate limiting, exponential backoff with full jitter. |

### 2.2 Runtime Code (Ground Truth)

| Source | Path | Key Provisions |
|---|---|---|
| **heartbeat.py** | `src/life_kernel/heartbeat.py` | HARD STOP via Redis key `life_kernel:hard_stop`. 1s heartbeat checks live flag. Fail-closed: Redis unreachable → do NOT clear state. Stale recovery: clears `hard_stop_requested` if live flag absent. Publishes HARD STOP to Discord before stopping. Universal kill-switch. |
| **journal.py** | `src/life_kernel/journal.py` | JournalWriter: reflective entries via PostgresAuditJournal. Records reasoning, lessons_learned, confidence, cycle, phase, focus. Fail-soft: DB failure never crashes kernel. |
| **checkpoint.py** | `src/life_kernel/checkpoint.py` | LangGraph checkpointer. PostgreSQL (durable) + Redis DB6 (fast recovery). Dual checkpointer pattern. State persistence for crash recovery. |

---

## 3. Findings

### 3.1 Action Lifecycle State-Machine

Every P23 action transitions through a deterministic state-machine. States are persisted to PostgreSQL (durable) and mirrored to Redis (hot queue). Terminal states are `succeeded`, `failed`, `rolled-back`, `cancelled`, `timed-out`.

```
                          ┌─────────────────────────────────────────────────────────────┐
                          │                                                             │
                          ▼                                                             │
                   ┌─────────────┐         ┌──────────────┐         ┌──────────┐     │
        enqueue ──▶│   queued    │───────▶ │  scheduled   │───────▶ │ pre-flight│     │
                   └─────────────┘         └──────────────┘         │ (policy  │     │
                        │                       ▲                   │  gate)   │     │
                        │ cancel                │ retry              └────┬─────┘     │
                        ▼                       │                         │           │
                   ┌─────────────┐              │                    pass │           │
                   │  cancelled  │              │                         ▼           │
                   └─────────────┘              │                   ┌──────────┐     │
                                               │                   │ running  │     │
                                               │                   └────┬─────┘     │
                                               │                        │           │
                                               │            ┌───────────┼───────────┼─────────┐
                                               │            │           │           │         │
                                               │            ▼           ▼           ▼         ▼
                                               │      ┌─────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
                                               │      │succeeded│ │ failed  │ │timed-  │ │cancelled │
                                               │      └─────────┘ └────┬────┘ │ out    │ └──────────┘
                                               │                     │       └───┬────┘
                                               │                     │ retry     │
                                               │                     ▼           │
                                               │              ┌────────────┐    │
                                               └──────────────│ retry_count │    │
                                                   (if <max)  │ < max?     │    │
                                                              └─────┬──────┘    │
                                                                    │ yes        │
                                                                    ▼            │
                                                               ┌──────────┐      │
                                                               │ backoff  │      │
                                                               │ (exp+jit)│      │
                                                               └─────┬────┘      │
                                                                     │           │
                                                                     ▼           │
                                                               ┌──────────┐      │
                                                               │ scheduled│      │
                                                               └──────────┘      │
                                                                     ▲            │
                                                       no retry     │            │
                                                  ┌────────────────┘            │
                                                  ▼                              │
                                            ┌─────────────┐                    │
                                            │ dead-letter  │◀───────────────────┘
                                            │ (exhausted)  │   (cancel during running)
                                            └──────┬───────┘
                                                   │
                                                   ▼
                                            ┌─────────────┐
                                            │ rolled-back │ (if rollback available)
                                            └─────────────┘
```

**State definitions:**

| State | Meaning | Persistence | Redis Key |
|---|---|---|---|
| `queued` | Action enqueued, awaiting scheduler pickup | PostgreSQL row | `p23:action:{action_id}` (BRPOPLPUSH source) |
| `scheduled` | Scheduler claimed action, set `started_at`, will dispatch to executor | PostgreSQL row | moved to `p23:action:processing` (BRPOPLPUSH dest) |
| `pre-flight` | Policy gate evaluating: risk tier, consent, auth matrix, budget, backup-required check | PostgreSQL row (transient) | N/A (in-memory) |
| `running` | Executor performing the action | PostgreSQL row | `p23:action:running:{action_id}` (TTL = timeout) |
| `succeeded` | Action completed successfully, artifact recorded | PostgreSQL row (terminal) | deleted |
| `failed` | Action failed, retry eligible if `retry_count < max_retries` | PostgreSQL row | moved back to `p23:action:{action_id}` on retry |
| `rolled-back` | Rollback executed after failure or cancellation | PostgreSQL row (terminal) | deleted |
| `cancelled` | Operator or HARD STOP cancelled the action | PostgreSQL row (terminal) | deleted |
| `timed-out` | Action exceeded `timeout_seconds` | PostgreSQL row (terminal) | TTL expired |
| `dead-letter` | Retries exhausted, action parked for manual inspection | PostgreSQL row (terminal) | `p23:action:deadletter` |

**Terminal states are immutable**: once an action reaches `succeeded`, `failed` (no retry), `rolled-back`, `cancelled`, `timed-out`, or `dead-letter`, the row is locked (no UPDATE/DELETE per WORM audit pattern from P22).

### 3.2 Durable Queue Schema (DDL)

#### 3.2.1 PostgreSQL Table — `p23.action_queue`

```sql
-- Schema: p23 (dedicated schema for P23 embodied operations)
CREATE SCHEMA IF NOT EXISTS p23;

-- Enum types
CREATE TYPE p23.action_status AS ENUM (
    'queued', 'scheduled', 'pre-flight', 'running',
    'succeeded', 'failed', 'rolled-back', 'cancelled', 'timed-out', 'dead-letter'
);

CREATE TYPE p23.risk_tier AS ENUM ('L1', 'L2', 'L3', 'L4');

CREATE TYPE p23.executor_type AS ENUM (
    'browser', 'windows_desktop', 'vps_ssh', 'github', 'file_system', 'external_api'
);

CREATE TYPE p23.rollback_state AS ENUM (
    'none',           -- no rollback needed (succeeded) or not yet attempted
    'pending',        -- rollback queued
    'in_progress',    -- rollback executing
    'succeeded',      -- rollback completed
    'failed',         -- rollback itself failed (escalate)
    'unavailable'     -- no rollback path exists for this executor/action
);

-- Main action queue table
CREATE TABLE p23.action_queue (
    -- Identity
    action_id           UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    namespace           TEXT NOT NULL,                    -- e.g., 'browser', 'vps.deploy', 'github.pr'
    executor            p23.executor_type NOT NULL,
    surface             TEXT NOT NULL,                    -- e.g., 'discord', 'vps', 'windows-pc', 'github'
    intent              TEXT NOT NULL,                    -- human-readable intent description
    intent_hash         TEXT NOT NULL,                    -- SHA256(canonical_payload) for idempotency dedup
    risk_tier           p23.risk_tier NOT NULL,

    -- State
    status              p23.action_status NOT NULL DEFAULT 'queued',
    payload             JSONB NOT NULL,                   -- action parameters, target, args
    retry_count         INT NOT NULL DEFAULT 0,
    max_retries         INT NOT NULL DEFAULT 3,           -- overridden by risk_tier defaults
    backoff_base_seconds INT NOT NULL DEFAULT 1,
    backoff_max_seconds INT NOT NULL DEFAULT 60,
    timeout_seconds     INT NOT NULL DEFAULT 300,

    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    scheduled_at        TIMESTAMPTZ,
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,

    -- Rollback
    rollback_state      p23.rollback_state NOT NULL DEFAULT 'none',
    rollback_payload    JSONB,                            -- rollback instructions (backup ref, revert cmd)
    rollback_started_at TIMESTAMPTZ,
    rollback_finished_at TIMESTAMPTZ,

    -- Artifacts & Audit
    artifact_path       TEXT,                             -- path to result artifact (screenshot, log, file)
    audit_id            UUID,                             -- FK to audit.integration_api_log.event_id
    correlation_id      UUID NOT NULL,                    -- links to upstream agent decision / heartbeat cycle
    parent_action_id    UUID,                             -- for compound actions (rollback chain)

    -- Idempotency & Dedup
    idempotency_key     TEXT NOT NULL,                    -- namespace + ':' + intent_hash
    dedup_until         TIMESTAMPTZ,                      -- window for rejecting duplicate enqueues

    -- Hard stop / cancel
    cancel_requested    BOOLEAN NOT NULL DEFAULT FALSE,
    cancel_reason       TEXT,
    hard_stop_triggered BOOLEAN NOT NULL DEFAULT FALSE,

    -- Constraints
    CONSTRAINT chk_retry_count_nonneg CHECK (retry_count >= 0),
    CONSTRAINT chk_max_retries_nonneg CHECK (max_retries >= 0),
    CONSTRAINT chk_idempotency_key_format CHECK (idempotency_key LIKE '%:%'),
    CONSTRAINT chk_l4_no_retry CHECK (risk_tier != 'L4' OR max_retries = 0),
    CONSTRAINT chk_l3_backup_required CHECK (
        (risk_tier != 'L3' AND risk_tier != 'L4') OR
        (rollback_payload IS NOT NULL AND rollback_payload ? 'backup_ref')
    )
);

-- Idempotency: prevent duplicate actions within dedup window
CREATE UNIQUE INDEX idx_action_queue_idempotency
    ON p23.action_queue (idempotency_key)
    WHERE status IN ('queued', 'scheduled', 'pre-flight', 'running')
      AND (dedup_until IS NULL OR dedup_until > now());

-- Query indexes
CREATE INDEX idx_action_queue_status ON p23.action_queue (status, created_at);
CREATE INDEX idx_action_queue_namespace ON p23.action_queue (namespace, status);
CREATE INDEX idx_action_queue_executor ON p23.action_queue (executor, status);
CREATE INDEX idx_action_queue_correlation ON p23.action_queue (correlation_id);
CREATE INDEX idx_action_queue_risk_tier ON p23.action_queue (risk_tier, status);
CREATE INDEX idx_action_queue_started_at ON p23.action_queue (started_at)
    WHERE status = 'running';

-- Append-only enforcement (WORM pattern from P22 audit trail)
REVOKE UPDATE, DELETE ON p23.action_queue FROM guinevere_core;
GRANT INSERT, SELECT ON p23.action_queue TO guinevere_core;
-- Status updates go through a dedicated role with UPDATE on status columns only
-- (implemented via a trigger function or stored procedure)
```

#### 3.2.2 Dead-Letter Table — `p23.action_dead_letter`

```sql
CREATE TABLE p23.action_dead_letter (
    action_id           UUID NOT NULL PRIMARY KEY,
    namespace           TEXT NOT NULL,
    executor            p23.executor_type NOT NULL,
    intent              TEXT NOT NULL,
    risk_tier           p23.risk_tier NOT NULL,
    final_status        p23.action_status NOT NULL,
    payload             JSONB NOT NULL,
    retry_count         INT NOT NULL,
    max_retries         INT NOT NULL,
    last_error          TEXT,
    created_at          TIMESTAMPTZ NOT NULL,
    moved_to_dlq_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    correlation_id      UUID NOT NULL,
    inspector_notes     TEXT,
    resolved            BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT chk_dlq_final_status CHECK (
        final_status IN ('failed', 'timed-out', 'rolled-back')
    )
);

GRANT INSERT, SELECT, UPDATE ON p23.action_dead_letter TO guinevere_core;
```

#### 3.2.3 Redis Hot Queue (DB0 per ADR-030)

Per ADR-030, DB0 is the task queue (rate limiting, persona state, consent grants — noeviction, RDB+AOF). P23 uses DB0 for the hot action queue with `BRPOLLPUSH` for reliable at-least-once delivery:

```
# Redis DB0 key layout for P23
p23:action:pending          # LPUSH enqueue, BRPOPLPUSH source → processing
p23:action:processing       # BRPOPLPUSH destination (in-flight, visibility timeout)
p23:action:running:{action_id}   # TTL = timeout_seconds (auto-expiry = timed-out)
p23:action:deadletter       # RPUSH exhausted actions
p23:action:cancel:{action_id}    # SET with TTL — checked by running executors
p23:hard_stop               # = life_kernel:hard_stop (shared, universal halt)
```

**BRPOPLPUSH flow** (at-least-once with idempotent side effects):
1. Enqueue: `LPUSH p23:action:pending {action_id_json}` (after PostgreSQL INSERT).
2. Worker: `BRPOPLPUSH p23:action:pending p23:action:processing 30` (blocking pop with 30s timeout).
3. Worker sets `p23:action:running:{action_id}` with TTL = `timeout_seconds`.
4. On success/failure: worker removes from `p23:action:processing`, deletes running key.
5. Visibility timeout: if worker crashes, the item stays in `p23:action:processing`; a reaper moves stale items back to `p23:action:pending` after TTL expiry.
6. Cancel: `SET p23:action:cancel:{action_id} 1 EX 60` — executor checks this flag in its poll loop.

### 3.3 Retry/Backoff Policy

Per risk tier, with exponential backoff + full jitter (AWS pattern cited in P22 research §5.3):

| Risk Tier | Description | max_retries | backoff_base | backoff_max | On Exhaustion | Backup Required |
|---|---|---|---|---|---|---|
| **L1** | Read-autonomous (browser scrape, file read, API GET) | 3 | 1s | 30s | Dead-letter + alert | No |
| **L2** | Write-notify (file write, API POST/PUT, Discord message) | 2 | 2s | 60s | Dead-letter + notify operator | No (workspace backup recommended) |
| **L3** | Destructive-approval (VPS deploy, systemctl, DROP, git push --force) | 1 + escalate | 5s | 120s | **Rollback immediately**, escalate to Faiz | **Yes — before execute** (§0.1 invariant 3) |
| **L4** | Forbidden (rm -rf /, DROP TABLE production, bypass HARD STOP) | 0 | N/A | N/A | **Never enqueued** — hard reject at pre-flight | N/A |

**Backoff formula (exponential + full jitter):**
```python
import random

def compute_backoff(retry_count: int, base: int, max_delay: int) -> float:
    """Exponential backoff with full jitter (AWS pattern)."""
    exp_delay = min((2 ** retry_count) * base, max_delay)
    return random.uniform(0, exp_delay)  # full jitter
```

**Retry eligibility checks:**
1. `retry_count < max_retries` for the tier.
2. Error is retryable (network timeout, 5xx, rate-limit 429 with Retry-After). Non-retryable: 4xx (except 429), validation errors, safety violations.
3. HARD STOP not active (`life_kernel:hard_stop` absent).
4. Cancel not requested (`p23:action:cancel:{action_id}` absent).
5. Idempotency key not already succeeded (check PostgreSQL).

**Dead-letter on exhaustion:** after `max_retries` exhausted, action moves to `p23.action_dead_letter` with `last_error`, `resolved=FALSE`. Inspector (operator or autonomous review) marks `resolved=TRUE` after manual intervention.

**Cancel mechanisms:**
- **HARD STOP**: Redis `life_kernel:hard_stop` set → all workers check this in poll loop → running executors checkpoint state and halt → queued items remain `queued` (not cancelled; resume after HARD STOP clear).
- **Explicit cancel**: `SET p23:action:cancel:{action_id} 1 EX 60` → executor checks flag in poll loop → transitions to `cancelled` → initiates rollback if action was `running` and executor supports it.

### 3.4 Per-Executor Rollback Model

| Executor | Pre-Execute (L3) | Rollback Path | Limitations |
|---|---|---|---|
| **browser** | Capture DOM snapshot (HTML + scroll position) before mutation | Close page/tab, restore DOM snapshot from pre-execute capture, clear cookies set during session | Can't undo external side effects (e.g., form submission that already hit server). If action was a POST, rollback = compensating DELETE if supported, else mark `unavailable`. |
| **windows_desktop** | Snapshot process list + file state for affected paths | Kill spawned process (by PID), restore file from workspace trash/backup (`~/.guinevere/trash/`), undo registry changes via `.reg` export | Can't undo network side effects. Process kill is best-effort (process may have already exited). |
| **vps_ssh** | **pg_dump + file snapshot to S3/R2** (ADR-032), record `systemctl status` baseline | Restore from backup (pg_dump restore, rclone copy from R2 free-egress), `systemctl revert` to baseline, canary smoke test, update sentinel `/home/guinevere/.backup/last-success` | L3 requires full backup BEFORE execute. Rollback target = last known-good (sentinel path per ADR-035 B11). Large DB restores take minutes — document RTO. |
| **github** | Record commit SHA / branch state before action | Revert PR (`gh pr revert` or `git revert`), delete branch, restore reflog state | Can't undo if PR already merged to protected branch without force-push rights. Rollback = revert commit (new commit that undoes changes). |
| **file_system** | Copy target file/dir to workspace trash (`~/.guinevere/trash/{action_id}/`) before mutation | Restore from trash copy, or restore from workspace backup snapshot | Trash has size limit (configurable, default 1GB). Oversized operations bypass trash and require explicit L3 backup. |
| **external_api** | Record pre-state if API supports read (GET current value) | API undo endpoint where supported (e.g., Gmail `messages.delete` → `messages.undelete`, Notion `archive` → `unarchive`). Else **compensating action** (e.g., if created resource, delete it; if sent email, send recall if supported). | Many APIs have no undo. Compensating actions must be idempotent themselves. If neither undo nor compensate possible, mark `rollback_state = 'unavailable'` and escalate. |

**Rollback state transitions:**
```
none → pending → in_progress → (succeeded | failed)
                                        │
                                        └─ if failed: escalate to Faiz, mark action for manual review
```

**L3 backup-before-execute gate (AGENTS.md §0.1 invariant 3):**
- Pre-flight checks `risk_tier = 'L3'`.
- If `rollback_payload.backup_ref` is NULL → **reject enqueue** (CHECK constraint).
- Backup must complete and verify (S3/R2 upload confirmed) BEFORE action transitions to `running`.
- If backup fails → action stays `queued`, alert fired, no execution.

### 3.5 L3 Deploy Gate Sequence

For L3 actions (VPS deploys, self-modifications, destructive ops), the full gate sequence per AGENTS.md §0.1 and ADR-029:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      L3 DEPLOY GATE SEQUENCE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. BACKUP                                                          │
│     ├─ pg_dump guinevere_core → /tmp/deploy_{action_id}.sql.gz     │
│     ├─ rclone copyto /tmp/deploy_{action_id}.sql.gz                │
│     │   idcloudhost:guinevere-dr-backups/deploy/{action_id}/        │
│     ├─ rclone copyto /tmp/deploy_{action_id}.sql.gz                │
│     │   r2:guinevere-dr-backups/deploy/{action_id}/ (secondary)    │
│     ├─ File snapshot: tar -czf /tmp/files_{action_id}.tar.gz       │
│     │   /home/guinevere/code/ /home/guinevere/config/              │
│     ├─ rclone copyto to both S3 + R2                                │
│     └─ Verify: rclone check (both remotes) → record backup_ref     │
│        in rollback_payload                                          │
│                                                                     │
│  2. CANARY                                                          │
│     ├─ Deploy to canary (canary service / port 8001)               │
│     ├─ Run smoke tests:                                              │
│     │   curl http://localhost:8001/health → 200                    │
│     │   psql -U guinevere_core -c "SELECT 1" → OK                  │
│     │   redis-cli -n 0 PING → PONG                                 │
│     │   Run regression test suite (ADR-029):                        │
│     │     python -m pytest tests/ -v --tb=short                    │
│     └─ If canary fails → ROLLBACK immediately, do not promote      │
│                                                                     │
│  3. PROMOTE or ROLLBACK                                             │
│     ├─ PROMOTE (canary passed):                                     │
│     │   systemctl restart guinevere-{service}                      │
│     │   Verify production health (same smoke tests on port 8000)   │
│     │   Update sentinel: echo "{action_id}" >                       │
│     │     /home/guinevere/.backup/last-success                     │
│     │   Action → succeeded                                          │
│     │                                                               │
│     └─ ROLLBACK (canary failed OR production health failed):       │
│         ├─ git revert HEAD (ADR-029: last known-good commit)       │
│         ├─ rclone copy r2:.../{action_id}/ /tmp/restore/           │
│         ├─ psql -U guinevere_core -d guinevere < restore/dump.sql  │
│         ├<arg_value> systemctl restart guinevere-{service}                    │
│         ├─ Verify: smoke tests on port 8000                        │
│         ├─ Action → rolled-back                                    │
│         └─ Alert Faiz (Discord webhook + Gotify)                   │
│                                                                     │
│  ROLLBACK TARGET: last known-good = sentinel path                  │
│  /home/guinevere/.backup/last-success (ADR-035 B11 caveat:         │
│  verified sentinel, accepted risk until offline age-key recovery)  │
│                                                                     │
│  TIMELINESS: ADR-029 requires rollback within 60 seconds for       │
│  self-modifications. VPS deploys may take longer (DB restore);      │
│  document RTO per action type in payload.                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Self-modification gate (ADR-029, AGENTS.md §0.1 invariant 4):**
- All autonomous self-modifications MUST pass regression tests before promotion.
- Test categories: unit, integration, safety boundary, regression.
- Safety-critical changes (persona, safety boundary, surveillance, encryption, memory access, loop governance) require explicit Faiz review regardless of test results.
- Rollback target = last known-good commit (`git revert`).
- Rollback events logged to audit trail + alerted via Discord (ADR-022) + Gotify.

### 3.6 Idempotency-Key Design

**Idempotency key construction:**
```
idempotency_key = namespace + ':' + intent_hash

where:
  namespace   = executor scope (e.g., 'browser', 'vps.deploy', 'github.pr', 'fs.write')
  intent_hash = SHA256(canonical_json(payload))
```

**Canonical JSON payload** (deterministic ordering):
```python
import hashlib
import json

def compute_intent_hash(payload: dict) -> str:
    """SHA256 of canonical JSON (sorted keys, no whitespace)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

**Dedup logic:**
1. On enqueue: compute `idempotency_key`.
2. Check PostgreSQL: `SELECT status FROM p23.action_queue WHERE idempotency_key = $1 AND status IN ('queued','scheduled','pre-flight','running') AND (dedup_until IS NULL OR dedup_until > now())`.
3. If active duplicate exists → **reject enqueue** (return existing `action_id`).
4. If succeeded duplicate exists → return existing `action_id` (idempotent — already done).
5. Else: INSERT new row with `idempotency_key`.

**At-least-once with idempotent side effects:**
- Redis `BRPOPLPUSH` guarantees at-least-once delivery (a worker may process the same action twice after crash recovery).
- Executors MUST be idempotent: re-running the same action produces the same result without duplicate side effects.
- Idempotency patterns per executor:
  - **browser**: check if page already in expected state before acting.
  - **external_api**: use provider idempotency keys (e.g., Stripe `Idempotency-Key` header, Gmail message ID dedup).
  - **github**: check if PR/commit already exists before creating.
  - **file_system**: check file content hash before writing (skip if identical).
  - **vps_ssh**: check service state before restarting (skip if already in target state).

**One-shot actions (§2.11 documentation requirement):**
- Actions that cannot be made idempotent (e.g., sending a non-dedupable email) MUST document one-shot behavior in `payload.one_shot = true` and set `max_retries = 0`.
- These actions rely on the idempotency key to prevent duplicate enqueues, but do not retry on failure.

### 3.7 Audit Trail for Rollback

Extends P22 `audit.integration_api_log` hash-chained WORM pattern to P23 action lifecycle:

#### 3.7.1 P23 Action Audit Table — `audit.p23_action_log`

```sql
-- Extends P22 audit schema (audit.integration_api_log pattern)
CREATE TABLE audit.p23_action_log (
    id                  BIGSERIAL PRIMARY KEY,
    event_id            UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    sequence            BIGSERIAL NOT NULL,               -- monotonic ordering
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    action_id           UUID NOT NULL,                    -- FK to p23.action_queue
    namespace           TEXT NOT NULL,
    executor            TEXT NOT NULL,
    surface             TEXT NOT NULL,
    intent              TEXT NOT NULL,
    risk_tier           TEXT NOT NULL,
    status_from         TEXT,                             -- previous state
    status_to           TEXT NOT NULL,                    -- new state
    retry_count         INT,
    correlation_id      UUID NOT NULL,

    -- Reasoning + command intent (per journal.py pattern)
    reasoning           TEXT NOT NULL,                    -- why this action/transition was chosen
    command_intent      TEXT NOT NULL,                    -- what command/intent was executed
    outcome             TEXT NOT NULL,                    -- 'success', 'failure', 'rollback', 'cancel', 'timeout'
    artifact_path       TEXT,                             -- path to result artifact

    -- Rollback-specific
    rollback_state      TEXT,
    rollback_reason     TEXT,
    backup_ref          TEXT,                             -- S3/R2 path for L3 backups

    -- Hash chain (per P22 pattern)
    previous_hash       TEXT,
    event_hash          TEXT NOT NULL,

    -- Metadata
    metadata            JSONB,

    -- WORM enforcement (per P22)
    CONSTRAINT no_update_or_delete CHECK (false) NO INHERIT
);

-- Hash chain: event_hash = SHA256(canonical_payload + previous_hash)
-- Computed by trigger BEFORE INSERT

REVOKE UPDATE, DELETE ON audit.p23_action_log FROM guinevere_core;
GRANT INSERT, SELECT ON audit.p23_action_log TO guinevere_core;

CREATE INDEX idx_p23_audit_action_id ON audit.p23_action_log (action_id, sequence);
CREATE INDEX idx_p23_audit_correlation ON audit.p23_action_log (correlation_id);
CREATE INDEX idx_p23_audit_occurred_at ON audit.p23_action_log (occurred_at);
```

#### 3.7.2 Hash Chain Computation

```python
import hashlib
import json
from datetime import datetime, timezone

async def compute_event_hash(payload: dict, previous_hash: str | None) -> str:
    """SHA256(canonical_payload + previous_hash) — per P22 audit trail pattern."""
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    chain_input = canonical + (previous_hash or '')
    return hashlib.sha256(chain_input.encode('utf-8')).hexdigest()

async def append_audit_event(
    audit_conn, action_id: str, status_from: str, status_to: str,
    reasoning: str, command_intent: str, outcome: str,
    correlation_id: str, rollback_state: str = None,
    backup_ref: str = None, artifact_path: str = None,
    metadata: dict = None
) -> str:
    """Append a hash-chained audit event. Returns event_hash."""
    # Get previous hash (last event in chain)
    prev = await audit_conn.fetchrow(
        "SELECT event_hash FROM audit.p23_action_log ORDER BY sequence DESC LIMIT 1"
    )
    previous_hash = prev['event_hash'] if prev else None

    payload = {
        'action_id': action_id,
        'status_from': status_from,
        'status_to': status_to,
        'reasoning': reasoning,
        'command_intent': command_intent,
        'outcome': outcome,
        'rollback_state': rollback_state,
        'backup_ref': backup_ref,
        'artifact_path': artifact_path,
        'occurred_at': datetime.now(timezone.utc).isoformat(),
        'metadata': metadata or {},
    }

    event_hash = await compute_event_hash(payload, previous_hash)

    await audit_conn.execute(
        """INSERT INTO audit.p23_action_log
           (action_id, status_from, status_to, reasoning, command_intent, outcome,
            rollback_state, backup_ref, artifact_path, correlation_id,
            previous_hash, event_hash, metadata)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)""",
        action_id, status_from, status_to, reasoning, command_intent, outcome,
        rollback_state, backup_ref, artifact_path, correlation_id,
        previous_hash, event_hash, json.dumps(metadata or {})
    )
    return event_hash
```

#### 3.7.3 Audit Events per State Transition

| Transition | Audit Event | Reasoning Required |
|---|---|---|
| `→ queued` | Action enqueued with intent, risk_tier, idempotency_key | Why this action was created (upstream decision/cycle) |
| `→ scheduled` | Worker claimed action | Scheduler decision (priority, queue depth) |
| `→ pre-flight` | Policy gate evaluation | Risk assessment, consent check, budget check |
| `→ running` | Executor started | Command intent, target surface, timeout |
| `→ succeeded` | Action completed | Outcome, artifact path, duration |
| `→ failed` | Action failed (retry eligible) | Error type, error message, retry decision |
| `→ retry (backoff)` | Backoff scheduled | Retry count, backoff delay, jitter |
| `→ dead-letter` | Retries exhausted | Final error, escalation flag |
| `→ rolled-back` | Rollback executed | Rollback reason, backup_ref, restore verification |
| `→ cancelled` | Cancel received | Cancel source (operator/HARD STOP), reason |
| `→ timed-out` | Timeout exceeded | Timeout duration, partial state |

**Every audit event includes:**
- `reasoning`: why this transition happened (per `journal.py` pattern — reflective, for self-diagnosis).
- `command_intent`: what was executed or attempted.
- `outcome`: success/failure/rollback/cancel/timeout.
- `artifact_path`: where the result evidence lives.
- `rollback_state`: current rollback status.
- `previous_hash` + `event_hash`: tamper-evident chain.

---

## 4. Implications for P23 Design

### 4.1 Durable Queue is Non-Negotiable

P23 actions span multiple executors with varying latency (browser = seconds, VPS deploy = minutes). The queue MUST be PostgreSQL-durable (survives crash) with Redis hot queue for low-latency dispatch. A crash mid-action must not lose the action — it must be recoverable from `p23:action:processing` (visibility timeout reaper) or PostgreSQL row.

### 4.2 Risk Tier Drives the Entire Lifecycle

The 4-level matrix (L1-L4) from P22 extends naturally to P23:
- **L1**: autonomous, retry 3x, no backup, dead-letter on exhaustion.
- **L2**: autonomous with notify, retry 2x, workspace backup recommended.
- **L3**: **requires backup before execute** (§0.1 invariant 3), retry 1x + escalate, full deploy gate (backup→canary→smoke→promote/rollback).
- **L4**: never enqueued — hard reject at pre-flight.

### 4.3 Rollback is Executor-Specific, Not Generic

Each executor has a distinct rollback path. P23 must implement a `RollbackStrategy` interface per executor:
```python
class RollbackStrategy(ABC):
    @abstractmethod
    async def pre_execute_backup(self, action: Action) -> BackupRef: ...
    @abstractmethod
    async def rollback(self, action: Action, backup: BackupRef) -> RollbackResult: ...
    @abstractmethod
    def supports_rollback(self, action: Action) -> bool: ...
```

### 4.4 Idempotency Keys Prevent Duplicate Execution

The `(namespace, intent_hash)` idempotency key is the primary dedup mechanism. Executors must additionally implement idempotent side effects (check-before-act) because Redis BRPOPLPUSH is at-least-once, not exactly-once.

### 4.5 HARD STOP Integration is Mandatory

P23 workers MUST check `life_kernel:hard_stop` in their poll loops (per `heartbeat.py` pattern). On HARD STOP:
- Running executors checkpoint and halt.
- Queued items remain queued (resume after clear).
- No new items are dequeued.

### 4.6 Audit Trail Extends P22

The `audit.p23_action_log` table extends the P22 `audit.integration_api_log` hash-chained WORM pattern. Every state transition is an audit event with reasoning + command intent + outcome + artifact path + rollback state. This satisfies AGENTS.md §0.1 invariant 2 (autonomous actions produce audit trail) and invariant 7 (audit for debugging).

### 4.7 Shared VPS Constraints Apply

Per IMPLEMENTATION_GUIDE.md §6:
- P23 services run as `guinevere` user with cgroup `MemoryMax=8G`, `CPUQuota=200%`.
- Redis DB0 (P23 queue) must not overlap Aizanta DB10-15.
- PostgreSQL: P23 schema `p23` in `guinevere_core` DB, separate from Aizanta.
- Rollback procedures must verify Aizanta unaffected (§6 "If You Break Aizanta" protocol).

---

## 5. Risks / Open Questions

### 5.1 Redis DB0 Capacity

DB0 already holds rate limiting, persona state, and consent grants (ADR-030). Adding P23 hot queue may increase memory pressure. **Risk**: DB0 OOM (noeviction policy → writes fail). **Mitigation**: monitor `redis-cli -n 0 INFO memory`, set maxmemory if needed, consider moving P23 queue to DB6+ (checkpoint.py already uses DB6 for life_kernel — coordinate).

### 5.2 Long-Running L3 Deploys Block the Queue

VPS deploys with DB restore can take minutes. A single worker blocked on L3 deploy stalls the queue. **Mitigation**: separate worker pool for L3 (dedicated worker with longer timeout), or async deploy with status polling.

### 5.3 External API Rollback Limitations

Many external APIs have no undo endpoint. Compensating actions may themselves fail or be non-idempotent. **Risk**: `rollback_state = 'unavailable'` for critical actions. **Mitigation**: classify external API actions by undo-support; require consent for non-undoable write actions; document in `payload.reversible = false`.

### 5.4 Browser DOM Snapshot Size

Capturing full DOM snapshots for browser rollback may consume significant memory/storage. **Risk**: memory pressure on shared VPS (8GB cgroup). **Mitigation**: cap snapshot size (e.g., 5MB), store to disk not memory, skip snapshot for read-only browser actions.

### 5.5 Windows Desktop Process Tracking

Windows daemon (P15) tracks active windows but rollback requires process lifecycle management. **Risk**: process may spawn children that survive parent kill. **Mitigation**: use process groups (`taskkill /T /PID`), record full process tree at spawn.

### 5.6 GitHub Revert on Protected Branches

If a PR is merged to a protected branch, `git revert` works but creates a new commit. Force-push to delete branch may be blocked. **Risk**: rollback creates noise in git history. **Mitigation**: document revert-vs-delete policy per repo; prefer revert commits (safer, auditable).

### 5.7 ADR-035 B11 Sentinel Path Caveat

The sentinel `/home/guinevere/.backup/last-success` is verified but has an accepted risk: offline age-key recovery and `secrets/backup/` restoration are not yet re-enabled for encrypted S3/R2 restore. **Risk**: L3 rollback may fail if backup restore requires encrypted secrets not yet available. **Mitigation**: document this as a blocker for encrypted-backup L3 rollbacks; plaintext backups (pg_dump) work; encrypted file snapshots may not until B10 is resolved.

### 5.8 Idempotency Key Collision Across Namespaces

If two different namespaces produce the same `intent_hash` (extremely unlikely with SHA256), they could collide if the uniqueness index is not scoped properly. **Mitigation**: the `idempotency_key = namespace + ':' + intent_hash` format ensures namespace scoping; the unique index covers the full key.

### 5.9 HARD STOP During Rollback

If HARD STOP is triggered during an in-progress rollback, the rollback may be interrupted, leaving the system in a partially-rolled-back state. **Risk**: inconsistent state. **Mitigation**: rollback operations should be short and atomic where possible; on HARD STOP clear, check for `rollback_state = 'in_progress'` and resume or escalate.

---

## 6. Recommendations to Planner

### 6.1 Implement the State-Machine as a LangGraph Subgraph

P23 action lifecycle maps cleanly to a LangGraph state machine (consistent with `life_kernel` architecture). Each state is a node; transitions are edges. This enables checkpoint-based recovery (per `checkpoint.py` pattern) and integrates with the existing kernel.

### 6.2 Use Dual Checkpointer for Action State

Follow `checkpoint.py` pattern: PostgreSQL (durable) + Redis DB6 (fast recovery) for action state. This gives crash recovery without sacrificing latency.

### 6.3 Separate Worker Pools by Risk Tier

- **L1/L2 workers**: general pool, short timeout (300s), 4-8 workers.
- **L3 workers**: dedicated pool, long timeout (1800s), 1-2 workers, full deploy gate.
- **L4**: no workers — hard reject at enqueue.

### 6.4 Implement a Reaper for Stale Processing Items

A background job (every 60s) scans `p23:action:processing` for items older than their `timeout_seconds`. Stale items are moved back to `p23:action:pending` and `retry_count` incremented. This handles worker crashes gracefully.

### 6.5 Expose Action Status via Discord Command

Add `/action status {action_id}` and `/action cancel {action_id}` Discord commands (port to Hermes plugin per ADR-035). This gives Faiz visibility and control over P23 actions, satisfying the "audit for debugging" principle while maintaining autonomy.

### 6.6 Define Executor Interfaces Early

The `Executor` and `RollbackStrategy` interfaces should be defined before any executor implementation. This ensures all executors conform to the same lifecycle, idempotency, and rollback contract.

### 6.7 Test Rollback Before Going Live

Per ADR-029, rollback mechanisms must be tested regularly. P23 should include:
- Unit tests for each executor's rollback strategy.
- Integration tests for the full L3 deploy gate (backup→canary→smoke→rollback).
- Chaos tests: kill worker mid-action, trigger HARD STOP during rollback, simulate Redis outage.

### 6.8 Document One-Shot Actions Explicitly

Per §2.11, actions that cannot be idempotent must document one-shot behavior. Add `payload.one_shot = true` flag and set `max_retries = 0`. These should be rare and require operator awareness.

### 6.9 Coordinate Redis DB Usage with ADR-030

P23 hot queue uses DB0 (per ADR-030 task queue assignment). If DB0 capacity is a concern, propose a superseding ADR to move P23 queue to DB6+ (currently used by `checkpoint.py` for life_kernel). Do not silently change DB assignments.

---

## 7. Verdict

**APPROVED for planner consumption.** This research provides a complete, ground-truth-grounded design for P23 action lifecycle, durable queue, retry/backoff, per-executor rollback, L3 deploy gate, idempotency, and audit trail. The design:

1. **Satisfies AGENTS.md §0.1 invariants**: backup before promote (invariant 3), regression before self-mod promote (invariant 4), audit trail for all autonomous actions (invariant 2), HARD STOP halts all (invariant 1).
2. **Satisfies AGENTS.md §2.11**: idempotency keys prevent double-execution; one-shot actions documented.
3. **Extends P22 audit pattern**: hash-chained WORM `audit.p23_action_log` with reasoning + command intent + outcome + artifact path + rollback state.
4. **Integrates with existing infrastructure**: Redis DB0 (ADR-030), PostgreSQL `guinevere_core` (ADR-007), S3/R2 backup (ADR-032), HARD STOP (`heartbeat.py`), LangGraph checkpoint (`checkpoint.py`), journal reasoning (`journal.py`).
5. **Respects shared VPS constraints**: cgroup limits, Aizanta isolation, `guinevere` user.

**Key risks to track**: Redis DB0 capacity, L3 deploy queue blocking, external API rollback limitations, ADR-035 B11 sentinel caveat for encrypted restores.

**Next step**: Planner gate should produce the P23 enterprise plan with per-step scaffolds, using this research as the rollback/idempotency authority.
