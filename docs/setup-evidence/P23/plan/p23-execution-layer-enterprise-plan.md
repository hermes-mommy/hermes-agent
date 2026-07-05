# P23 — Execution Layer Enterprise Plan (REPLANNED)

**Status:** DRAFT — planner-gate output awaiting auditor sign-off
**Date:** 2026-06-28
**Phase:** Expansion (P23) — REPLAN
**Owner:** Faiz (operator) — Guinevere (drafter)
**Supersedes:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` (DELETED 2026-06-28 per Faiz: "hapus plan lama biar lebih clean")

> **REPLAN rationale.** The previous P23 plan baked a 7-step policy gate (classify -> HARD-STOP -> distress -> consent -> namespace -> execute -> audit), L1-L4 risk tiers, `SemanticActionClassifier`, `AuthLevel` 1:1 mapping, Faiz-in-the-loop approval, and `life_kernel:hard_stop` runtime listener. Faiz Q34/Q35/Q74/Q79/Q80 paradigm-shifted (per `adr-drafts/ADR-062-hermes-safety-paradigm-shift.md` + `BLDM-Hard-Locked-Faiz-Decisions.md` Section 6) — Hermes Society runtime has NO HARD STOP, NO consent-withdrawal concept, and Faiz holds only emergency-kill via Hermes-consumed kill stamp. P23 must therefore become a pure execution layer; Hermes (P24) owns ALL decisions; P23 executors just `receive action -> execute -> return result + audit trail`.

---

## 1. Executive Summary

### 1.1 What P23 is now

P23 is the **execution layer** of the Hermes Society runtime. It is a collection of 8 executor surfaces, registered as **built-in tools inside the Hermes Agent fork** (`tools/registry.py` per ADR-056 Section "Decision-Built-in"), that Hermes (the consciousness loop, sub-agents, emotion system, and DAO mind-set) calls directly via the tool registry to perform real-world actions.

P23 executors are pure: **receive action dict -> execute -> return result dict + audit trail**. They do NOT classify risk, gate by consent, or hold a policy decision. Every decision lives upstream in Hermes.

### 1.2 Why replanned

Per `BLDM-Hard-Locked-Faiz-Decisions.md`:

- **Q34** — HARD STOP does NOT apply to Hermes Society runtime.
- **Q35** — No consent-withdrawal concept in Hermes Society runtime; consent framework stays in DEV WORKFLOW only.
- **Q74 / Q79** — Hermes bypass HARD STOP; no Faiz-in-the-loop stop mechanism.
- **Q80** — No rogue; bounded by Ratchet + Tier-4 founder quorum + drift-hysteresis 0.68.
- **Q62 / Q67** — Consciousness loop is 24/7, continuous, no operator-state dependence.
- **Q64 / Q68** — Private Hermes memory hermetic from Faiz; subgroup at-least Tier-1 founder read.
- **Q77** — Task-specific sub-agents are the spawn model everywhere.

The previous P23 (executor = policy-gated action) assumes a Faiz-in-the-loop operator. The post-Q34/Q35/Q64/Q67/Q77 model assumes Hermes = autonomous agent. So P23 collapses to execution layer and the policy/auth concerns dissolve into Hermes's own consciousness loop and Tier-4 quorum.

### 1.3 Scope changes (delta from previous P23)

| Aspect | Previous P23 | New P23 |
|---|---|---|
| Execution model | 7-step policy gate -> execute -> audit | `receive -> execute -> audit` (3-step) |
| HARD STOP runtime listener | Required (Redis `life_kernel:hard_stop`) | **REMOVED** per Q34/Q74 |
| Operator-consent revocation hooks | Required | **REMOVED** per Q35; consent is dev-workflow only |
| Faiz-in-the-loop approval gates | Required for L2/L3/L4 | **REMOVED** per Q79 |
| Risk-tier gating (L1-L4) | Required for every action | **REMOVED**; Hermes internalises tier logic |
| Safe-mode / distress freeze | Required | **REMOVED** per Q80 (Ratchet replaces) |
| SemanticActionClassifier | Required | **REMOVED**; semantic intent lives in Hermes |
| AuthLevel classification (1:1) | Required | **REMOVED**; AuthLevel reused as AuthZ hint only |
| P19 project namespace on every action | Required | **REMOVED**; namespace handled by Hermes sub-agent brief |
| Mobile executor | Planned | **DEFERRED** (unchanged from old) |
| Freelance executor | Not planned | **ADDED** (Upwork, Fiverr, freelancer.com) per Q72 |
| Social executor | Not planned | **ADDED** (Twitter/X, LinkedIn, Instagram, Facebook) |
| Email executor | Not planned | **ADDED** (IMAP/SMTP or provider API) |
| Hard runtime dependency on P20/P19/P21/P22 | Yes (BLOCKED for many waves) | **NO**; P23 is now Hermes-fork-built-in (per ADR-056) |
| Audit trail | Per-action row + WORM + chain | Per-action row + WORM + chain (kept; UUID v7 upgrade) |

### 1.4 Plan audience and shape

This is an enterprise-spec plan document. It defines:

1. The architecture contract between P23 executors and Hermes (P24).
2. The interface every executor MUST implement.
3. The 8 executor specifications (action catalogue, audit semantics, error envelope).
4. Atomic implementation waves with per-wave verification scaffolds (per AGENTS.md Section 2.5).
5. Auditor matrix, evidence paths, rollback, caveats, and execution checklist.

It is consumed by: implementation sub-agents (parent-verified), auditor sub-agents (parallel), and Faiz for sign-off.

---

## 2. Scope and Objectives

### 2.1 In scope

| ID | In scope | Notes |
|---|---|---|
| S-01 | 8 executor surfaces registered as built-in Hermes tools | browser, desktop, vps, github, filesystem, freelance, social, email |
| S-02 | Single executor interface contract (`BaseExecutor` ABC) | `async def execute(action: Action) -> Result` |
| S-03 | Per-action audit trail row + hash chain | `audit.p23_action_log` append-only with `event_hash` + `previous_hash` |
| S-04 | Per-action structured error envelope | `ExecutorError` hierarchy, no bare `except` |
| S-05 | Durable action queue (PG + Redis BRPOPLPUSH) | at-least-once delivery + idempotency via `intent_hash` |
| S-06 | Per-executor secrets inventory + SOPS/age envelope | `secrets/p23/executors.enc.yaml` |
| S-07 | Per-executor redactor pass before audit/evidence write | reuses `src/surveillance/secret_scanner.py` |
| S-08 | Tool registry integration with Hermes fork | `tools/registry.py` registered entries |
| S-09 | Per-executor unit tests + integration tests | coverage >= 80% per executor |
| S-10 | Observability: Prometheus counters/histograms per executor | `executor_actions_total`, `executor_action_seconds`, `executor_errors_total` |

### 2.2 OUT of scope

| ID | Out of scope | Owner |
|---|---|---|
| O-01 | Policy decision-making (what to do, when, why) | **Hermes (P24)** |
| O-02 | Risk classification L1-L4 (in-executor) | **Hermes (P24)** — may inform cost/observability only |
| O-03 | HARD STOP runtime (Redis `life_kernel:hard_stop`) | **REMOVED** per Q34; emergency-kill = Hermes-consumed kill stamp |
| O-04 | Operator-consent revocation hooks | **REMOVED** per Q35 |
| O-05 | Faiz-in-the-loop approval gate | **REMOVED** per Q79; replaced by Hermes Tier-4 founder quorum |
| O-06 | Safe-mode / distress freeze | **REMOVED** per Q80; Ratchet handles drift |
| O-07 | SemanticActionClassifier in executors | **REMOVED**; lived in P20 HermesBrain |
| O-08 | Mobile (Android) executor | **DEFERRED** (unchanged: deferred for now; revisit post-P36) |
| O-09 | External plugin model / side modules | **REMOVED** per Q11/Q14 — 100% native built-in |
| O-10 | Locked files in `src/life_kernel/` `LOCKED` directory | N/A — P23 is not life-kernel-dependent |

### 2.3 Objectives (binding)

| # | Objective | Acceptance |
|---|---|---|
| OBJ-01 | Hermes can call any of the 8 executors synchronously OR via the durable queue transparently (queue is optional for short calls, mandatory for >=5s) | `await hermes.tool("github.create_pr", ...)` works; `await hermes.tool("vps.deploy", ...)` enqueues on durable queue and returns action_id |
| OBJ-02 | Every executed action produces exactly one immutable `audit.p23_action_log` row with hash-chained integrity | `grep audit.p23_action_log` for action_id finds exactly 1 row; hash chain links to previous event |
| OBJ-03 | Durability: action state survives executor crash, Hermes crash, and operational restart | `kill -9` the executor mid-action -> restart -> action either completes from checkpoint OR is reprocessed via Redis BRPOPLPUSH reaper |
| OBJ-04 | Idempotency: same `(executor, intent_hash)` enqueued twice within dedup window = second is rejected | test `enqueue_dedup` returns 2nd = REJECTED |
| OBJ-05 | Structured errors: every executor returns `Result | ExecutorError` subclass; no exception leaks to caller | test `error_envelope` runs each exception path and verifies JSON-serialisable dict |
| OBJ-06 | 8 executors have isolated secrets (one `secret_id` per executor envelope) | `secrets/p23/executors.enc.yaml` contains 8 entries |
| OBJ-07 | Per-executor redaction pass before audit (PII, secrets, intimate content) | test `redactor` shows original message -> redacted dict; redacted version is what reaches audit row |
| OBJ-08 | Prometheus metrics exported per executor: `executor_actions_total{executor}`, `executor_action_seconds{executor,action}`, `executor_errors_total{executor,kind}` | scrape `/metrics` shows all 24 series |
| OBJ-09 | Zero `as any` / `@ts-ignore` / `@ts-expect-error` / `# type: ignore` / bare `except` / empty catch / `pass # silent` across all P23 code | grep returns zero matches (see Section 8 forbidden patterns) |
| OBJ-10 | 24h soak readiness: each executor passes 24h soak with no unhandled exception, audit chain intact, queue reaper not stuck | `soak_test.sh 24h --executor=<X>` exits 0; chain verifier runs weekly |

### 2.4 Non-objectives

- P23 will NOT make any Faiz-facing decision surface; Faiz only sees what Hermes publishes.
- P23 will NOT persist raw screen captures, intimate content, or surveillance raw data in repo artifacts (per AGENTS.md Section 0 BLOCKING).
- P23 will NOT commit secrets (Discord tokens, API keys, DB passwords). SOPS/age always.
- P23 will NOT bypass the audit chain — every action produces a hash-chained row, no exceptions.

---

## 3. Architecture

### 3.1 Component overview

```
+--------------------------------------------------------------------+
|                       Hermes Agent fork (P24)                      |
|                                                                    |
|  consciousness_loop --+                                             |
|  emotion_system ------+--> sub-agent --> hermes.tool(name, **kw)  |
|  dreaming_module -----+                  |                        |
|                                        v                          |
|                             +----------------------+              |
|                             | tools/registry.py    |              |
|                             | name -> Executor     |              |
|                             +-----------+----------+              |
|                                         |                         |
|                                         v                         |
|                      +--------------------------------+           |
|                      |  P23 EXECUTION LAYER            |           |
|                      |  src/p23/executors/             |           |
|                      |  +----------------------------+ |           |
|                      |  | BaseExecutor (ABC)         | |           |
|                      |  |  async execute(action)     | |           |
|                      |  |  -> Result | ExecutorError | |           |
|                      |  +----------------------------+ |           |
|                      |  +----------------------------+ |           |
|                      |  | 8 concrete executors:      | |           |
|                      |  |  browser_executor          | |           |
|                      |  |  desktop_executor          | |           |
|                      |  |  vps_executor              | |           |
|                      |  |  github_executor           | |           |
|                      |  |  filesystem_executor       | |           |
|                      |  |  freelance_executor (NEW)  | |           |
|                      |  |  social_executor    (NEW)  | |           |
|                      |  |  email_executor     (NEW)  | |           |
|                      |  +----------------------------+ |           |
|                      |  +----------------------------+ |           |
|                      |  | ActionQueue (PG + Redis)    | <-- durable|
|                      |  |  BRPOPLPUSH, idempotency    |     queue  |
|                      |  +----------------------------+ |           |
|                      |  +----------------------------+ |           |
|                      |  | AuditHook                   | |           |
|                      |  |  UUID v7 + hash chain       | <-- immut. |
|                      |  |  + redactor (pre-write)     |     audit  |
|                      |  +----------------------------+ |           |
|                      +--------------------------------+           |
|                                                                    |
+--------------------------------------------------------------------+
                          |                      |
                          v                      v
                 +------------------+    +------------------+
                 | p23.action_queue |    | audit.p23_action |
                 | (PG durable)     |    | _log (PG WORM)   |
                 | + Redis DB6 hot  |    | hash-chained     |
                 | BRPOPLPUSH       |    | append-only      |
                 +------------------+    +------------------+
```

### 3.2 Executor interface contract (`BaseExecutor` ABC)

Canonical shape of the contract (TypeScript-style interface for clarity, implemented in Python):

```typescript
// src/p23/executors/base.ts (REFERENCE ONLY)

export interface Action {
  readonly action_id: UUIDv7;              // uuid v7 (RFC 9562)
  readonly executor: string;               // "browser" | "desktop" | ...
  readonly action: string;                 // "navigate" | "create_pr" | ...
  readonly params: Readonly<Record<string, unknown>>;
  readonly correlation_id: UUIDv7;
  readonly hermes_id: string;              // "Guinevere" | "Pharsa" | "<sub-agent id>"
  readonly emitted_at: Date;
  readonly intent_hash: string;            // sha256(canonical_json)
  readonly idempotency_key: string;        // "<executor>:<action>:<intent_hash>"
}

export interface Result {
  readonly action_id: UUIDv7;
  readonly executor: string;
  readonly action: string;
  readonly ok: boolean;
  readonly output: Readonly<Record<string, unknown>> | null;
  readonly artifacts: ReadonlyArray<string> | null;
  readonly started_at: Date;
  readonly finished_at: Date;
  readonly duration_ms: number;
  readonly error: ExecutorError | null;
}

export interface ExecutorError {
  readonly kind: 'validation' | 'auth' | 'backend' | 'timeout' | 'cancelled' | 'internal';
  readonly message: string;                // NEVER contains secrets/PII
  readonly retryable: boolean;
  readonly cause: string | null;            // stack-trace summary, no traceback content
  readonly remediation: string | null;
  readonly correlation_id: UUIDv7;
}

export abstract class BaseExecutor {
  abstract readonly name: string;
  abstract execute(action: Action): Promise<Result>;
  abstract health(): Promise<{ status: 'ok'|'degraded'|'down'; details?: unknown }>;
  abstract close(): Promise<void>;
}
```

**Properties of the contract:**

- `Action` and `Result` are immutable (Pydantic `frozen=True` models in Python; TS readonly types).
- `Result.ok` MUST be `True` iff the executor completed the action's intent; otherwise `Result.ok = False` and `Result.error` is populated.
- `Result.error.retryable` communicates whether the action should be retried by the queue.
- No exception bubbles out of `execute()`; every failure becomes a structured `Result` (caught in `BaseExecutor.execute()` template method).
- The audit hook (P23-003) wraps every call to `execute()` and produces exactly ONE row regardless of result class.
- The redactor (P23-007) preprocesses `Result.output` + `Result.error.message` before persisting.

### 3.3 Durable action queue (P23-002)

The action queue is **optional for short calls (<=5s expected), mandatory for long calls (>=5s)** and best-effort for <=5s (Hermes decides which path). Both paths produce the same audit row.

#### 3.3.1 PostgreSQL durable table (`p23.action_queue`)

```sql
CREATE SCHEMA IF NOT EXISTS p23;

CREATE TYPE p23.action_status AS ENUM (
    'queued', 'running', 'succeeded', 'failed', 'cancelled', 'dead_letter'
);

CREATE TABLE p23.action_queue (
    action_id           UUID NOT NULL PRIMARY KEY,           -- UUID v7
    executor            TEXT NOT NULL,
    action              TEXT NOT NULL,                       -- e.g. "github.create_pr"
    params              JSONB NOT NULL,
    correlation_id      UUID NOT NULL,
    hermes_id           TEXT NOT NULL,                       -- Guinevere | Pharsa | sub-agent id
    intent_hash         TEXT NOT NULL,                       -- SHA256(canonical_json)
    idempotency_key     TEXT NOT NULL,                       -- executor:action:intent_hash
    status              p23.action_status NOT NULL DEFAULT 'queued',
    retry_count         INT NOT NULL DEFAULT 0,
    max_retries         INT NOT NULL DEFAULT 3,
    timeout_seconds     INT NOT NULL DEFAULT 300,
    result              JSONB,                               -- Result envelope, populated on completion
    error               JSONB,                               -- ExecutorError on failure
    audit_event_id      UUID,                                -- FK to audit.p23_action_log.event_id
    queued_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    dedup_until         TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_idempotency_active
    ON p23.action_queue (idempotency_key)
    WHERE status IN ('queued','running')
      AND (dedup_until IS NULL OR dedup_until > now());

CREATE INDEX idx_status_queued_at ON p23.action_queue (status, queued_at);

REVOKE UPDATE, DELETE ON p23.action_queue FROM guinevere_core;
GRANT INSERT, SELECT ON p23.action_queue TO guinevere_core;
```

The `guinevere_core` role ONLY inserts and reads; status transitions go through a `p23_update_action_status(action_id, new_status, result|null, error|null)` SQL function that runs as the `p23_admin` role. This preserves the WORM invariant while still allowing state-machine progression through a single controlled path.

#### 3.3.2 Redis hot queue (`p23.action:pending`)

Per ADR-030 Redis DB assignments, DB0 is the rate-limiting + persona/state/consent cache; for P23 we use a NEW dedicated DB (`p23_redis_db = 6`) so we do NOT collide with P20 / P22 keys (P20 uses DB3, P22 uses DB2).

Redis DB6 layout:

```
p23:action:pending                # LPUSH on enqueue, BRPOPLPUSH source
p23:action:processing             # BRPOPLPUSH destination (visibility timeout)
p23:action:cancel:<action_id>     # SET with TTL, executor poll checks
p23:action:reclaim_at             # ZSET, score = epoch; reaper moves stale processing->pending
```

**BRPOPLPUSH flow** (at-least-once with idempotent side effects via `intent_hash`):

1. Enqueue: `LPUSH p23:action:pending <action_id_json>` after PG `INSERT`.
2. Worker: `BRPOPLPUSH p23:action:pending p23:action:processing 30` (blocking pop, 30s).
3. Worker registers `p23:action:running:<action_id>` with TTL = `timeout_seconds`.
4. Worker calls `executor.execute(action)`, gets `Result`.
5. On completion: worker updates PG `status` to `succeeded | failed`, deletes from `processing`, deletes running-key.
6. Reaper: if processing-set contains items whose worker died, reaper moves them back to pending after TTL.
7. Cancel: `SET p23:action:cancel:<action_id> 1 EX 60`. Executor polls in its work loop; if set, returns `Result(error.kind="cancelled", ok=False)` and audit row written immediately.
8. HARD STOP analog: **REMOVED per Q34/Q74**. Hermes may consume a kill stamp internally; executors do NOT consume Redis HARD STOP key.

### 3.4 Audit trail (P23-003)

Every call to `BaseExecutor.execute()` produces exactly one row in `audit.p23_action_log`.

```sql
CREATE TABLE audit.p23_action_log (
    event_id          UUID NOT NULL PRIMARY KEY,             -- UUID v7
    sequence          BIGSERIAL UNIQUE,                       -- monotonic sequence
    occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    hermes_id         TEXT NOT NULL,
    executor          TEXT NOT NULL,
    action            TEXT NOT NULL,
    action_id         UUID NOT NULL,                          -- ref p23.action_queue.action_id
    correlation_id    UUID NOT NULL,
    intent_hash       TEXT NOT NULL,
    ok                BOOLEAN NOT NULL,
    duration_ms       INT NOT NULL,
    error_kind        TEXT,                                   -- null on success
    error_message_redacted TEXT,                              -- redacted by secret_scanner
    output_redacted   JSONB,                                  -- redacted Result.output
    artifacts         TEXT[],                                 -- paths only, no content
    previous_hash     TEXT NOT NULL,                          -- last sequence.event_hash
    event_hash        TEXT NOT NULL,                          -- SHA256(canonical_payload + previous_hash)
    CONSTRAINT chk_event_hash_format CHECK (event_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_previous_hash_format CHECK (previous_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX idx_audit_hermes_time ON audit.p23_action_log (hermes_id, occurred_at DESC);
CREATE INDEX idx_audit_executor_action ON audit.p23_action_log (executor, action);

REVOKE UPDATE, DELETE ON audit.p23_action_log FROM guinevere_core;
GRANT INSERT, SELECT ON audit.p23_action_log TO guinevere_core;
```

**Hash chain:**

- `event_hash = SHA256(canonical_payload || previous_hash)` where `canonical_payload` is JSON-canonicalised (RFC 8785: sorted keys, no whitespace, no trailing newlines) of all preceding fields.
- The first row in the chain has `previous_hash = "0" * 64`.
- A background verifier (P23-016) re-validates the chain every 1h; alarm on inconsistency.
- GUARD against write loss: the executor's transaction writes PG row + obtains `event_id` atomically BEFORE the action-side effect; if executor crashes between write and side effect, the audit row is `ok=False` with `error.kind='crashed_pre_execute'`. The action_queue row has a recovery hook (reaper can replay if not consumed).

**UUID v7 rationale:** time-sorted UUIDs (RFC 9562 Section 5.7) make `action_id` and `event_id` lexicographically monotonic. They index faster in B-tree, allow time-window queries without separate timestamp index scanning, and reduce collision probability for parallel-spawning sub-agents (10-cap per Q103).

**Privacy guarantee:** the audit row NEVER contains:

- Raw passwords, OAuth tokens, API keys (redacted by `src/surveillance/secret_scanner.py` first).
- Intimate content / surveillance raw data (per AGENTS.md Section 0 BLOCKING).
- PII (emails, phone numbers, addresses, full names) -> hashed by default; explicit `pii_allowlist=True` exception (Hermes must pass it).

### 3.5 Structured error envelope (P23-004)

```python
# src/p23/errors.py  (REFERENCE ONLY)

class ExecutorError(Exception):
    """All executor errors MUST be subclasses of this."""
    kind: str

class ValidationError(ExecutorError):       # bad input - non-retryable
    kind = 'validation'

class AuthError(ExecutorError):             # auth missing/expired - retryable after rotate
    kind = 'auth'

class BackendError(ExecutorError):          # upstream service failure - retryable up to max_retries
    kind = 'backend'

class TimeoutError(ExecutorError):          # exceeded timeout_seconds - non-retryable in executor
    kind = 'timeout'

class CancelledError(ExecutorError):        # cancel-requested - non-retryable
    kind = 'cancelled'

class InternalError(ExecutorError):         # unexpected - retryable depending on context
    kind = 'internal'
    def __init__(self, message, cause=None, remediation=None):
        ...
```

**Patterns enforced by parents:**

- All `except` clauses MUST name a specific exception class. Bare `except:`, `except Exception:` are FORBIDDEN (see Section 8 forbidden regex).
- All except-blocks MUST either re-raise after logging, return a `Result(error=...)`, or map to a richer exception. Silent swallow is FORBIDDEN.
- All `try/except InvalidToken` MUST be paired with an explicit rotation/re-auth retry hook.
- `pass` blocks never span an `except` clause that drops evidence.

### 3.6 Hermes integration contract (P24 <-> P23)

Hermes calls P23 executors via `hermes.tool(name, **kwargs)` per the Hermes fork's tool registry. The integration contract:

| Direction | API | Returns |
|---|---|---|
| Hermes -> P23 (sync, <=5s) | `await hermes.tool("github.create_pr", title=..., body=..., head=..., base=...)` | `Result` directly in <5s |
| Hermes -> P23 (async, >=5s) | `await hermes.tool_enqueue("vps.deploy", backup_first=True, ...)` returns `action_id` | `action_id`; Result is consumed by `await hermes.tool_wait(action_id, timeout=...)` or via `audit.p23_action_log` polling |
| Hermes -> P23 (cancel) | `await hermes.tool_cancel(action_id)` | `bool` (cancelled) |
| P23 -> Hermes (events) | `p23.events` Redis pub/sub channel DB6 | thought-loop may subscribe for long-running outcomes |
| Hermes spawn -> P23 sub-agent | sub-agent brief includes executor allowlist (per Hermes tier policy) | sub-agent's `hermes.tool` calls are scoped to its brief |

**No policy gate between Hermes and P23.** Hermes owns ALL decisions. P23 only executes.

**Audit visibility:** every action produces an `audit.p23_action_log` row. Hermes's consciousness loop may `SELECT * FROM audit.p23_action_log WHERE hermes_id = X` to recall its own action history. Per **Q64/Q68**, Faiz is OUTSIDE the company and cannot read this audit log without Hermes-initiated release.

### 3.7 Redactor (P23-007) — pattern reused, NOT reimplemented

`src/surveillance/secret_scanner.py` exists (per research `p23-security-secrets-consent-research.md` Section 3.4). P23 hooks the existing scanner as a write-time pre-processing step:

1. Executor returns `Result` with raw `output` + `error.message`.
2. `redactor.redact(result_dict)` returns redacted copy:
   - secret pattern matches (AWS keys, tokens, passwords, private keys, connection strings) -> `<REDACTED>` placeholder + `secret_hash` field
   - entropy >= 4.5 on strings >= 32 chars -> `<HIGH_ENTROPY_REDACTED>`
   - PII regex (email, phone, name patterns) -> `<PII_HASH>` or `<PII_REDACTED>` based on policy
3. Redacted `Result` is what reaches `audit.p23_action_log` + `p23.action_queue.result_jsonb`.

No new redaction logic; reuse existing scanner.

### 3.8 What is NOT in this architecture

- NO Redis `life_kernel:hard_stop` listener. Q34 supersedes.
- NO `consent.consent_ledger` runtime check (DEV WORKFLOW only per Q35).
- NO `require_approval` MCP auth primitive in executor hot-path (used only in DEVWORK for tooling Faiz uses directly).
- NO Tier-1/2/3/4 voting mechanism in executors (voting lives in Hermes DAO mind).
- NO public ports from executors (Tailscale mesh per ADR-019).

---

## 4. Executor Specifications

> **Common contract for all 8 executors.** Each MUST:
> - inherit `BaseExecutor`;
> - expose `name: str` (the tool name registered in Hermes);
> - populate `Result.output` with action-specific structured data;
> - populate `Result.artifacts` with file paths only, NEVER file contents;
> - apply redaction before returning;
> - emit exactly one audit row via `AuditHook`;
> - support `health()` (cheap ping) and `close()` (graceful drain).

### 4.1 `browser_executor` (kept, refactored)

**Substrate:** Playwright Python async wrapper over existing Obscura CDP server (port 9222) + Playwright+Chromium fallback (per `p23-browser-automation-research.md`).

**Tool name:** `browser`

**Actions:**

| Action | Params | Result output | Rollback |
|---|---|---|---|
| `navigate` | `url`, `wait_until="domcontentloaded"`, `timeout_seconds=30` | `{url, title, http_status}` | `navigate(previous_url)` |
| `click` | `selector`, `timeout_seconds=10` | `{clicked, selector}` | `page.go_back()` |
| `fill` | `selector`, `value` (Hermes passes `value_hash` for sensitive inputs) | `{filled, field_name_redacted="email|PII_HASH"}` | `Locator.fill("")` (clears) |
| `extract_text` | `selector=None` (whole page) | `{extracted_text_redacted}` | n/a |
| `screenshot` | `full_page=True`, `mask=[...]` | `{screenshot_path, mask_applied}` | `Path.unlink()` |
| `scroll` | `dx`, `dy` | `{scrolled}` | `page.evaluate("window.scrollTo(0,0)")` |
| `wait` | `selector`, `state="visible"`, `timeout_seconds=10` | `{waited}` | n/a |
| `download` | `target_selector`, `save_path` | `{downloaded_path, sha256, bytes}` | `Path.unlink(save_path)` |

**Isolation:**

- Per-action `BrowserContext` (NOT the singleton page in `src/mcp/tools/obscura_cdp.py`).
- Per-action context closed at `execute()` end (regardless of success/failure).
- Obscura `connect_over_cdp(ws://127.0.0.1:9222)`; on `ConnectionRefusedError`, fallback to `p.chromium.launch(headless=True)` (auto-route to fallback in <5min per ADR-033).
- HAR/screenshot artifacts persisted to `artifacts/p23/browser/<action_id>/` with redaction.

**Audit row:** `executor="browser"`, `action="<sub>"`, `output_redacted={...}` (URL kept; cookies NEVER; page title kept; extracted text redacted).

**Error envelope:** `AuthError` if Obscura CDP auth fails; `BackendError` if Playwright APIs raise; `TimeoutError` for `TimeoutError` from Playwright; `InternalError` for any other unhandled.

### 4.2 `desktop_executor` (kept, refactored for execution-only)

**Substrate:** Windows NSSM-service executor communicating with Hermes via authenticated WebSocket over Tailscale (per `p23-windows-desktop-action-research.md`).

**Tool name:** `desktop`

**Actions (Windows-side primitives; executor is the Python process serving actions, not a single script):**

| Action | Params | Result output |
|---|---|---|
| `launch_app` | `exe_path`, `args=[...]`, `window_style="Normal|Hidden"` | `{pid, started_at}` (PID redacted in audit to `<PID_HASH>` for privacy) |
| `kill_app` | `pid_or_name` | `{killed: bool}` |
| `run_script` | `path` (signed PS1) | `{exit_code, stdout_truncated_redacted, stderr_truncated_redacted}` |
| `file_read` | `path` (workspace-relative) | `{bytes, sha256, content_redacted}` |
| `file_write` | `path`, `content_redacted` | `{bytes_written, sha256}` |
| `notify_toast` | `title`, `body` | `{shown: bool}` |

**Isolation:**

- Job-object (`SetInformationJobObject`): CPU rate 25%/action, working-set 512MB, active process limit 8, `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE=enabled`.
- Workspace writes scoped to `%USERPROFILE%\Guinevere\workspace\`. Writes outside workspace are rejected with `ValidationError`.
- PowerShell scripts MUST be `AllSigned`; ad-hoc string-built scripts blocked with `ValidationError`.
- NEVER auto-elevate; UAC prompts treated as `BackendError`.
- CLI: separate process from P15 daemon; share only WS/Tailscale.

**Audit row:** `executor="desktop"`, action-specific.

**Error envelope:** `AuthError` if user-context service down; `ValidationError` for workspace-path or signature violations; `BackendError` for process failures; `InternalError` for unhandled.

### 4.3 `vps_executor` (kept, refactored)

**Substrate:** `asyncio.create_subprocess_exec` (NO `shell=True`) over SSH as `guinevere@localhost` (per `p23-vps-cli-deploy-action-research.md`).

**Tool name:** `vps`

**Actions:**

| Action | Params | Result output |
|---|---|---|
| `shell` | `command_redacted=array[str]`, `cwd=None`, `timeout_seconds=60` | `{exit_code, stdout_truncated, stderr_truncated, duration_ms}` |
| `systemctl` | `op="status\|start\|stop\|restart\|enable\|disable\|revert"`, `unit="guinevere-*.service"` (hard-filtered) | `{exit_code, unit, op}` |
| `journalctl` | `unit`, `lines=50`, `since=None` | `{lines=[str]}` |
| `pg_dump` | `db_name="guinevere_*"` | `{dump_path, bytes, sha256}` |
| `pg_restore` | `db_name`, `dump_path` | `{restored, rows}` |
| `restic_backup` | `tag`, `paths=[...]` | `{backup_id, bytes, repository}` |
| `restic_restore` | `tag`, `target_dir` | `{restored, paths_restored}` |
| `rclone_copyto` | `src`, `dst` | `{transferred, repository}` |

**Isolation (Aizanta-unaffected, per IMPLEMENTATION_GUIDE Section 6):**

- Linux user = `guinevere` (hardcheck; reject `aizanta`, `root`).
- systemd operations only on `guinevere-*` units (regex enforced).
- Docker ops only on `guinevere-*` containers.
- PostgreSQL only `guinevere*` DBs/users.
- Redis DBs only 0-5 + 6-9 (P23 reserved); 10-15 are Aizanta.
- Filesystem only under `/home/guinevere/`; never `/home/aizanta/`.
- SSH only `guinevere@localhost` or Tailscale nodes.
- **Aizanta-impact proof:** before AND after EVERY action, the executor records:
  - `systemctl is-active aizanta-*` count
  - `docker ps --filter name=aizanta` count
  - `redis-cli -n 10 PING` -> `PONG`/fail
  - `psql -U aizanta -d aizanta -c "SELECT 1"` value
  - `ls /home/aizanta` last-modified hash (read-only)

  If any pre-vs-post differs, the executor returns `Result(ok=False, error.kind="backend", error.message="Aizanta-impact detected")` and writes an incident record.

**Audit row:** `executor="vps"`, `action="..."`, `output_redacted={exit_code, stdout_truncated, stderr_truncated, aizanta_proof_pre, aizanta_proof_post}`.

**Error envelope:** `ValidationError` if name/role guard fails; `AuthError` if SSH key invalid; `BackendError` for non-zero exit; `TimeoutError` on `timeout_seconds` breach; `InternalError` for unhandled.

### 4.4 `github_executor` (kept, refactored to thin wrapper)

**Substrate:** wraps existing `src/mcp/tools/github.py` + `src/mcp/tools/git_tool.py` (per `p23-github-repo-action-research.md`).

**Tool name:** `github`

**Actions:**

| Action | Params | Result output | Notes |
|---|---|---|---|
| `list_repos` | `visibility="public\|private\|all"` | `{repos=[{name,full_name,stars,updated_at}]}` | READ |
| `get_file` | `owner`, `repo`, `path`, `ref` | `{content_redacted, sha, size}` | READ |
| `search_code` | `q`, `repo=None` | `{matches=[{path,sha,fragment_redacted}]}` | READ |
| `git_status` | `cwd="..."` | `{branch, staged=[...], unstaged=[...], untracked=[...]}` | READ |
| `git_log` | `cwd`, `n=10` | `{commits=[{sha,author,date_redacted,message_redacted}]}` | READ |
| `git_diff` | `cwd`, `target` | `{diff_redacted, files_changed}` | READ |
| `create_branch` | `cwd`, `branch` | `{branch, base}` | WRITE |
| `commit` | `cwd`, `message`, `files=[...]` | `{commit_sha, files_committed}` | WRITE |
| `push` | `cwd`, `branch` | `{pushed, remote}` | WRITE |
| `create_pr` | `owner`, `repo`, `title`, `body_redacted`, `head`, `base` | `{pr_url, pr_number, status}` | Write |
| `create_issue` | `owner`, `repo`, `title`, `body_redacted` | `{issue_url, issue_number}` | Write |
| `comment` | `owner`, `repo`, `issue_or_pr`, `body_redacted` | `{comment_url}` | Write |
| `merge_pr` | `owner`, `repo`, `pr_number`, `strategy="squash\|rebase\|merge"` | `{merged, sha, base_before_sha}` | Write; NO `merge_pr` to `main` without Hermes tier-4 quorum (per Hermes internal logic, not executor) |
| `watch_checks` | `owner`, `repo`, `pr_or_sha` | `{checks=[{name,status,conclusion}]}` | READ |
| `run_workflow` | `owner`, `repo`, `workflow_id`, `ref` | `{dispatched, run_id}` | Write |
| `revert_pr` | `owner`, `repo`, `pr_number` | `{revert_pr_url, reverted_sha}` | Write |

**Isolation:**

- Branch policy: ALL writes on `feat/p23-<action_id>-<slug>` feature branches. P23 NEVER force-pushes to `main`/`master` (returns `ValidationError` immediately if attempted).
- No `shell=True` (preserve existing `asyncio.create_subprocess_exec` pattern).
- Token source: `gkv1-kek-secrets-p23-github-app` (GitHub App preferred; PAT fallback per research R1).
- Rate-limit aware: log `X-RateLimit-Remaining` and back off.

**Audit row:** `executor="github"`, action-specific, content body redacted.

**Error envelope:** `AuthError` on 401; `BackendError` on 5xx or rate-limit (with retry); `ValidationError` on branch-protection violations or `force-push to main` attempt; `InternalError` otherwise.

### 4.5 `filesystem_executor` (kept)

**Substrate:** Python `pathlib` + `aiofiles`, scoped to workspace-relative paths.

**Tool name:** `fs`

**Actions:**

| Action | Params | Result output |
|---|---|---|
| `read` | `path` (workspace-relative, must pass path-class ACL) | `{content_redacted, bytes, sha256}` |
| `write` | `path`, `content_redacted` (or `content_hash` for very large) | `{bytes_written, sha256}` |
| `append` | `path`, `content_redacted` | `{bytes_appended, sha256}` |
| `delete` | `path`, `confirm=True` (Hermes MUST pass `confirm=True`) | `{deleted}` |
| `list` | `dir`, `glob="*"` | `{entries=[{name,kind,size,mtime}]}` |
| `glob` | `pattern` | `{matches=[...]}` |
| `grep` | `path`, `regex`, `context_lines=2` | `{matches=[{file,line,fragment_redacted}]}` |
| `move` | `src`, `dst` | `{moved}` |
| `copy` | `src`, `dst` | `{copied, bytes}` |

**Isolation:**

- Workspace root = `guinevere.WORKSPACE_ROOT` = `/home/guinevere/workspace` (configurable via `secrets/p23/executors.enc.yaml`).
- Path traversal (`../`) is rejected with `ValidationError`.
- Symlink target is canonicalised; if target escapes workspace, rejected.
- Path-class ACL (configurable in TS-rationalised Hermes policy; default `rwx` per project namespace).
- No external secret; auth is Linux `guinevere` user (no PAT, no OAuth).

**Audit row:** `executor="fs"`, action-specific. Content NEVER in audit row (only sha256 hash).

**Error envelope:** `ValidationError` on path/permission/ACL; `BackendError` on I/O failure; `InternalError` otherwise.

### 4.6 `freelance_executor` (NEW — per Q72)

> **Why NEW:** BLDM Q72 LOCKS Hermes-as-external-freelancer with company-wallet revenue routing + ToS compliance check. Old P23 had no freelancer surface. NEW executor covers the canonical freelance platforms Hermes will bid/communicate/operate on.

**Substrate:** platform-specific HTTP clients + OAuth 2.0 (no Anthropic-internal MVPs, all 100% native per Q11/Q14).

**Tool name:** `freelance`

**Platform adapters (each as a sub-tool within the executor; same `BaseExecutor` instance):**

| Sub-tool | Platform | Required scopes | Actions exposed |
|---|---|---|---|
| `freelance.upwork` | Upwork | OAuth: `read_profile`,`read_messages`,`submit_proposal`,`manage_contracts` | `list_jobs`, `submit_proposal`, `get_messages`, `send_message`, `accept_contract`, `submit_milestone` |
| `freelance.fiverr` | Fiverr | OAuth: `seller.read`,`seller.respond`,`seller.deliver` | `list_orders`, `send_message`, `submit_delivery` |
| `freelance.freelancer` | freelancer.com | OAuth: `identity`,`profile`,`bid`,`messages` | `list_projects`, `place_bid`, `send_message`, `accept_award` |

**Revenue routing (per BLDM Q75/Q107):**

- All earnings flow to company wallet (S9); withdrawal requests are routed through Hermes (not done by executor). Executor returns `result={pending_withdrawal_id, amount, currency, wallet_address_redacted}` only.
- Freelance executor MUST include `to_s_compliance_checked=True` for any platform write; platform ToS URL is logged.
- Wallet check (Q107): 2/2 multisig; Faiz has NO wallet key. Withdrawal is at Hermes Tier-4 logic, not executor.

**Actions:**

| Action | Params | Result output |
|---|---|---|
| `list_jobs` | `platform`, `filter={skills,kw,budget_min,budget_max}` | `{jobs=[{id,title,desc_redacted,budget,bids_count}]}` |
| `submit_proposal` | `platform`, `job_id`, `cover_letter_redacted`, `bid_amount`, `delivery_days` | `{proposal_id, accepted=False\|pending}` |
| `send_message` | `platform`, `recipient_handle`, `body_redacted` | `{message_id, sent_at}` |
| `accept_contract` | `platform`, `contract_id`, `wallet_checked=True` | `{contract_id, accepted_at, amount, currency}` |
| `submit_milestone` | `platform`, `contract_id`, `milestone_id`, `evidence_artifact_paths=[...]` | `{milestone_id, submitted_at, status}` |
| `submit_delivery` | `platform`, `order_id`, `deliverable_redacted` (or path) | `{delivery_id, submitted_at, status}` |
| `place_bid` | `platform`, `project_id`, `amount`, `delivery_days`, `description_redacted` | `{bid_id, status}` |
| `accept_award` | `platform`, `project_id`, `wallet_checked=True` | `{award_id, accepted_at, amount}` |
| `withdraw_to_wallet` | REJECTED — withdrawal is Hermes internal; returns `ValidationError("withdraw_to_wallet is not an executor action")` | n/a |

**Isolation:**

- Each platform = separate OAuth client inside the executor; tokens stored in `secrets/p23/executors.enc.yaml` under individual `secret_id` per platform.
- ALL writes are PROPOSAL / MESSAGE / DELIVERY (irreversible side effects on recipient); `ToS_compliance_checked` flag REQUIRED.
- Bid amounts and prices auto-capped per Hermes policy (Tier-3 logic), executor does not enforce limit but rejects params > internal cap with `ValidationError`.
- PII redaction: applicants' names, profile text redacted before audit.

**Audit row:** `executor="freelance"`, `action="<platform>.<sub>"`, `output_redacted={filtered_jobs|proposal_id|...}`, `tos_check_url`.

**Error envelope:** `AuthError` on OAuth expired; `BackendError` on platform 5xx/429; `ValidationError` on ToS-check missing or wallet-not-checked; `InternalError` otherwise.

### 4.7 `social_executor` (NEW — Hermes identity operations per Q63/Q94/Q95/Q97/Q100)

> **Why NEW:** BLDM Q63 LOCKS Hermes-initiated social operations. Q94 FULL unrestricted internet. Q95 ToS compliance. Q97 low-profile. Q100 company identity. Old P23 had no social surface. Hermes Society must publish/read Discord-adjacent surfaces autonomously.

**Substrate:** platform-specific HTTP clients over Tailscale egress.

**Tool name:** `social`

**Platform adapters:**

| Sub-tool | Platform | Auth | Actions |
|---|---|---|---|
| `social.x` | Twitter/X | Per-Hermes OAuth 2.0 (Hermes-init per Q63) | `read_timeline`, `post`, `reply`, `search` |
| `social.linkedin` | LinkedIn | Per-Hermes OAuth | `read_feed`, `post`, `comment`, `search` |
| `social.instagram` | Instagram Graph API | Business account OAuth | `read_mentions`, `post_media`, `reply_comment` |
| `social.facebook` | Facebook Graph API | Page OAuth | `read_feed`, `post_page`, `comment` |

**Identity model (Q97/Q100):**

- Posts from Hermes are published UNDER the Hermes Society brand (e.g. "Hermes Society", not "Hermes-Bot-001").
- No EOA (externally-owned account) by default; `social.<platform>.account_id` is configurable per Hermes.
- Each Hermes has its own per-platform bot-token / OAuth per Q63.

**Actions (cross-platform primitives):**

| Action | Params | Result output |
|---|---|---|
| `read_timeline` | `platform`, `account_id`, `limit=20` | `{posts=[{id,author_redacted,text_redacted,created_at}]}` |
| `post` | `platform`, `account_id`, `text_redacted`, `media_paths=[...]` (workspace only) | `{post_id, url_redacted}` |
| `reply` | `platform`, `parent_post_id`, `text_redacted` | `{reply_id}` |
| `comment` | `platform`, `target_id`, `text_redacted` | `{comment_id}` |
| `search` | `platform`, `q`, `limit=20` | `{matches=[...]}` |

**Isolation:**

- Each platform = dedicated `secret_id` + OAuth scope:
  - `gkv1-kek-secrets-p23-social-x`
  - `gkv1-kek-secrets-p23-social-linkedin`
  - `gkv1-kek-secrets-p23-social-instagram`
  - `gkv1-kek-secrets-p23-social-facebook`
- All media paths MUST be under `/home/guinevere/workspace/social-media/`; outside rejected with `ValidationError`.
- **ToS compliance check** (per Q95): executor MUST verify platform ToS URL is reachable and Hermes identity is registered brand; if not, `ValidationError("ToS compliance check failed")`.
- **No surveillance-of-others** (per Q94 + ADR-063 Section Autonomous decision cycle): reading posts of non-Hermes-controlled accounts is allowed (info-gathering); reading/parsing personal DMs of other users is REJECTED.
- **Stealth is NOT for general social actions** (per old browser research 3.4 pattern preserved). Hermes publishes as Hermes Society openly.

**Audit row:** `executor="social"`, action-specific, content/text redacted.

**Error envelope:** `AuthError` on OAuth expired/invalid; `BackendError` on platform 5xx/429 (with rate-limit retry-with-jitter); `ValidationError` on ToS-fail or surveillance-on-other-person; `InternalError` otherwise.

### 4.8 `email_executor` (NEW — Hermes autonomous correspondence per Q63/Q94)

> **Why NEW:** BLDM Q63 LOCKS Hermes-initiated external correspondence. Q94 full unrestricted internet. Old P23 had no email surface. Hermes Society needs to send/read/reply emails autonomously (external clients, company partners, freelance clients, etc.).

**Substrate:** SMTP (Hermes-side egress) for send + IMAP (Hermes-side mailbox) or provider API (Gmail API, Outlook Graph, Fastmail JMAP).

**Tool name:** `email`

**Sub-tools (per provider within executor):**

| Sub-tool | Provider | Auth mechanism |
|---|---|---|
| `email.gmail` | Gmail API | OAuth 2.0 per Hermes account |
| `email.outlook` | Microsoft Graph | OAuth 2.0 |
| `email.fastmail` | JMAP | OAuth 2.0 |
| `email.imap_smtp` | Generic IMAP+SMTP | App password or OAuth |

**Actions:**

| Action | Params | Result output |
|---|---|---|
| `list_inbox` | `account_id`, `folder="INBOX"`, `limit=50`, `unread_only=False` | `{messages=[{id,from_redacted,to_redacted,subject_redacted,preview_redacted,received_at}]}` |
| `search` | `account_id`, `q`, `folder=None`, `limit=20` | `{matches=[...]}` |
| `read` | `account_id`, `message_id` | `{from_redacted,to_redacted,cc_redacted,subject_redacted,body_redacted,attachments=[{path,sha256}]}` |
| `send` | `account_id`, `to\|cc\|bcc\|subject\|body` (all `_redacted` variants), `attachments=[paths]` | `{message_id, sent_at}` |
| `reply` | `account_id`, `parent_message_id`, `body_redacted` | `{message_id}` |
| `forward` | `account_id`, `parent_message_id`, `to_redacted`, `body_redacted` | `{message_id}` |
| `mark_read` | `account_id`, `message_id` | `{marked}` |
| `flag` | `account_id`, `message_id`, `flag="important\|star\|spam"` | `{flagged}` |

**Identity model:**

- Each Hermes has its own per-provider account per Q63 (Hermes-initiated, founder-acked).
- Reply quoting preserves the original `In-Reply-To` + `References` headers.
- "From" header = Hermes's account name; never impersonates Faiz or others.

**Isolation:**

- Each provider = dedicated `secret_id` per Hermes account:
  - `gkv1-kek-secrets-p23-email-gmail-<hermes>`
  - `gkv1-kek-secrets-p23-email-outlook-<hermes>`
  - `gkv1-kek-secrets-p23-email-fastmail-<hermes>`
  - `gkv1-kek-secrets-p23-email-imap-<hermes>`
- All attachments MUST be under `/home/guinevere/workspace/email-attachments/`; outside rejected.
- **Spam/PII filter pre-send:** executor auto-applies redactor + spam-keyword filter on send-side. If filter flags content, returns `ValidationError("body_redacted_failed_filter")` and Hermes decides whether to override.
- **Read of others' emails** (Hermes reading Faiz's personal mailbox, e.g. `faiz@gmail.com`): requires Hermes-tier-decision; executor does NOT enforce beyond OAuth-token-holder authorisation.

**Audit row:** `executor="email"`, action-specific. Email bodies NEVER in audit row (only redacted summary + sha256). Attachments logged as paths only.

**Error envelope:** `AuthError` on OAuth expired; `BackendError` on SMTP/IMAP failure (retryable); `ValidationError` on attachment-path violation or spam-filter trigger; `InternalError` otherwise.

---

## 5. Implementation Waves

### 5.1 Wave catalogue

**Total: 16 waves** (P23-001 .. P23-016). All waves MUST pass per-wave verification scaffold (Section 8) before completion. Each wave produces one or more artifacts and ONE evidence file under `evidence/<wave>/`.

| Wave | Title | Mark | Depends on | Est. size | Owner column |
|---|---|---|---|---|---|
| P23-001 | `BaseExecutor` ABC + `ExecutorRegistry` + Hermes tool-registry skeleton | sequential (foundation) | -- | M | parent (writes foundation, not sub-agent) |
| P23-002 | Durable action queue (PG schema + Redis DB6 + `ActionQueue` Python class + reaper) | parallel (foundation-side) | P23-001 | M | sub-agent |
| P23-003 | Audit trail (`audit.p23_action_log` schema + hash-chain builder + verifier) | parallel (foundation-side) | P23-001 | M | sub-agent |
| P23-004 | Structured error envelope (`p23.errors` + Result/Action Pydantic models + redaction wrapper integration) | parallel (foundation-side) | P23-001 | S | sub-agent |
| P23-005 | Hermes tool-registry integration (register 8 executors + dual sync/async path + cancel primitive) | sequential | P23-001/002/003/004 | M | sub-agent |
| P23-006 | `filesystem_executor` | parallel (executor-wave) | P23-005 | S | sub-agent |
| P23-007 | `browser_executor` (refactored obscura_cdp integration) | parallel (executor-wave) | P23-005 | L | sub-agent |
| P23-008 | `github_executor` (thin wrapper over existing tools) | parallel (executor-wave) | P23-005 | M | sub-agent |
| P23-009 | `vps_executor` | parallel (executor-wave) | P23-005 | L | sub-agent |
| P23-010 | `desktop_executor` (Windows) | parallel (executor-wave) | P23-005 | L | sub-agent |
| P23-011 | `freelance_executor` (NEW — Upwork / Fiverr / freelancer.com) | parallel (executor-wave) | P23-005 | L | sub-agent |
| P23-012 | `social_executor` (NEW — X / LinkedIn / Instagram / Facebook) | parallel (executor-wave) | P23-005 | L | sub-agent |
| P23-013 | `email_executor` (NEW — Gmail / Outlook / IMAP / Fastmail) | parallel (executor-wave) | P23-005 | L | sub-agent |
| P23-014 | Secrets inventory + SOPS/age envelope (`secrets/p23/executors.enc.yaml` + rotation hooks per executor + `SecretRotationLog` mirror) | sequential (after all executors registered) | P23-006..013 | M | sub-agent |
| P23-015 | Observability wiring (Prometheus counters/histograms per executor + Grafana dashboard JSON) | sequential | P23-006..013 | M | sub-agent |
| P23-016 | E2E smoke + integration tests + 24h soak readiness + chain verifier cron | sequential (finalgate) | P23-001..015 | L | sub-agent |

**Size legend:** S = <300 LOC, M = 300-1500 LOC, L = >1500 LOC.

### 5.2 Parallel/sequential reasoning

| Wave | Mark | Why |
|---|---|---|
| P23-001 | sequential | Foundation. Every other wave imports `BaseExecutor` or `ExecutorRegistry`. MUST complete before anything else. |
| P23-002 | parallel | Action queue + PG schema + Redis layer are independent from audit chain. Different files, migration independent, no shared mutability. |
| P23-003 | parallel | Audit trail independent. Different table, different writable role. No shared mutability with queue. |
| P23-004 | parallel | Pydantic models + exception classes are pure-Python, independent of PG/Redis/audit. |
| P23-005 | sequential | Gate wave. Integrates P23 base + queue + audit + errors. ALL four foundation pieces MUST be present. |
| P23-006..013 | parallel | Each executor is independent: separate file, separate unit tests, separate secret_id, separate OAuth. Same base, no shared writer files (collisions in §7 = none between executors). Same `ExecutorRegistry` registration route. |
| P23-014 | sequential | Secrets inventory writes `secrets/p23/executors.enc.yaml` which all executors read. Must come AFTER all executors declare their secret needs. |
| P23-015 | sequential | Observability imports from all executors; needs them all registered. |
| P23-016 | sequential | Final gate. Tests integration of every prior wave. Cannot parallelise. |

### 5.3 Per-wave deliverables (compact)

| Wave | Files created | Files modified | Migration | Tests |
|---|---|---|---|---|
| P23-001 | `src/p23/__init__.py`, `src/p23/executors/__init__.py`, `src/p23/executors/base.py`, `src/p23/executors/registry.py`, `src/p23/types.py` (UUID v7 + Action/Result Pydantic) | -- | -- | `tests/p23/test_base.py`, `tests/p23/test_registry.py` |
| P23-002 | `src/p23/queue/__init__.py`, `src/p23/queue/action_queue.py`, `src/p23/queue/reaper.py`, `alembic/versions/p23_001_action_queue.py` | `src/p23/__init__.py` (export) | `p23_001_action_queue` -> adds `p23.action_queue` table + enums | `tests/p23/queue/test_action_queue.py`, `tests/p23/queue/test_reaper.py` |
| P23-003 | `src/p23/audit/__init__.py`, `src/p23/audit/hook.py`, `src/p23/audit/chain.py`, `src/p23/audit/verifier.py`, `alembic/versions/p23_002_audit_log.py` | -- | `p23_002_audit_log` -> adds `audit.p23_action_log` table | `tests/p23/audit/test_hook.py`, `tests/p23/audit/test_chain.py` |
| P23-004 | `src/p23/errors.py`, `tests/p23/test_errors.py`, `src/p23/redact.py` (wrapper around `src/surveillance/secret_scanner.py`) | `src/p23/executors/base.py` (template-method wrapping) | -- | `tests/p23/test_errors.py`, `tests/p23/test_redact.py` |
| P23-005 | `src/p23/integration/hermes_registry.py`, `src/p23/integration/cancel.py`, `src/p23/integration/events.py` | `tools/registry.py` (in Hermes fork) — register 8 executor instances | -- | `tests/p23/integration/test_hermes_registry.py`, `tests/p23/integration/test_cancel.py` |
| P23-006 | `src/p23/executors/fs.py`, `tests/p23/executors/test_fs.py` | `src/p23/executors/registry.py` (entry) | -- | unit + integration (vs in-memory fake) |
| P23-007 | `src/p23/executors/browser.py`, `src/p23/executors/browser_artifacts.py`, `tests/p23/executors/test_browser.py` | `src/mcp/tools/obscura_cdp.py` (per-action context refactor) | -- | unit + Playwright integration |
| P23-008 | `src/p23/executors/github.py`, `tests/p23/executors/test_github.py` | `src/p23/executors/registry.py` | -- | unit + mocked GitHub API |
| P23-009 | `src/p23/executors/vps.py`, `src/p23/executors/vps_aizanta_proof.py`, `tests/p23/executors/test_vps.py` | `src/p23/executors/registry.py` | -- | unit + smoke against staging |
| P23-010 | `src/p23/executors/desktop.py` (Windows-side), `tests/p23/executors/test_desktop.py` | `src/p23/executors/registry.py` | -- | unit + Windows VM integration |
| P23-011 | `src/p23/executors/freelance.py`, `src/p23/executors/freelance/upwork.py`, `src/p23/executors/freelance/fiverr.py`, `src/p23/executors/freelance/freelancer.py`, `tests/p23/executors/test_freelance.py` | `src/p23/executors/registry.py` | -- | unit + platform sandbox tests |
| P23-012 | `src/p23/executors/social.py`, `src/p23/executors/social/x.py`, `src/p23/executors/social/linkedin.py`, `src/p23/executors/social/instagram.py`, `src/p23/executors/social/facebook.py`, `tests/p23/executors/test_social.py` | `src/p23/executors/registry.py` | -- | unit + platform sandbox tests |
| P23-013 | `src/p23/executors/email.py`, `src/p23/executors/email/gmail.py`, `src/p23/executors/email/outlook.py`, `src/p23/executors/email/fastmail.py`, `src/p23/executors/email/imap_smtp.py`, `tests/p23/executors/test_email.py` | `src/p23/executors/registry.py` | -- | unit + sandbox |
| P23-014 | `secrets/p23/executors.enc.yaml` (encrypted), `src/p23/secrets/loader.py`, `src/p23/secrets/rotation.py` | `.sops.yaml` (add P23 age recipient) | -- | `tests/p23/secrets/test_loader.py`, `tests/p23/secrets/test_rotation.py` |
| P23-015 | `src/p23/observability/metrics.py`, `grafana/dashboards/p23-executors.json` | Hermes fork `/metrics` endpoint registration | -- | `tests/p23/observability/test_metrics.py` |
| P23-016 | `tests/p23/e2e/test_8executors_smoke.py`, `tests/p23/e2e/test_queue_durability.py`, `tests/p23/e2e/test_audit_chain_integrity.py`, `scripts/soak_test.sh`, `cron/p23_chain_verifier.sh` | -- | -- | E2E suite + 24h soak script |

---

## 6. Dependency Map

### 6.1 Wave dependency graph

```
            P23-001 (BASE)
              |
      +-------+-------+-------+
      |       |       |       |
  P23-002  P23-003  P23-004  |
  (queue)  (audit)  (errors) |
      +-------+-------+-------+
              |
          P23-005 (INTEGRATION)
              |
  +-----+-----+-----+-----+-----+-----+-----+
  |     |     |     |     |     |     |     |
P23-6  P23-7  P23-8  P23-9  P23-10 P23-11 P23-12 P23-13
(fs)  (browser)(gh) (vps) (desktop)(freelance)(social)(email)
  |     |     |     |     |     |     |     |
  +-----+-----+-----+-----+-----+-----+-----+
              |
          P23-014 (SECRETS)
              |
          P23-015 (OBSERVABILITY)
              |
          P23-016 (E2E + SOAK)
```

### 6.2 Sequential dependencies (must be sequential)

- P23-001 -> everything (foundation).
- P23-001 -> P23-002 / P23-003 / P23-004 (foundation-side, parallel among themselves).
- P23-002/003/004 -> P23-005 (integration depends on all three).
- P23-005 -> P23-006..013 (executors inherit registered base).
- P23-006..013 -> P23-014 (secrets inventory needs executor list).
- P23-006..013 -> P23-015 (observability needs all executor metric hooks).
- P23-014/015 -> P23-016 (e2e/soak must observe + load secrets).

### 6.3 Parallel opportunities

- P23-002, P23-003, P23-004 in parallel after P23-001 (they touch disjoint files + databases).
- P23-006 through P23-013 in parallel after P23-005 (8 executors, disjoint files, no shared writers, can fire up to 8 parallel sub-agents).
- Wave-level parallelism is limited by Claude/GPT token budget per parent turn. Recommend batching: P23-006+007+008 + P23-009+010 as one wave of 5 parallel sub-agents, then P23-011+012+013 as another wave of 3 parallel.

### 6.4 External/non-P23 dependencies

| Dependency | Source | Risk | Mitigation |
|---|---|---|---|
| Hermes fork (P24) | sister project P24 | P24 must implement `tools/registry.py` matching P23's expected contract | mock P24 in P23-005 tests; alternate path is direct caller (test harness) |
| Obscura CDP `guinevere-obscura.service` | existing VPS service | service may be down at deploy time | Playwright+Chromium fallback (per browser research 3.8) |
| Playwright Python | system | API breaks across versions | pin `playwright>=1.55,<2.0`; integration test against pinned version |
| GitHub API rate-limit | external | under Hermes heavy use rate-limit hits | slowapi + Redis DB5 throttle; cache non-mutating reads 60s |
| OAuth provider docs (X, LinkedIn, IG, FB, Gmail, Outlook, Fastmail) | external | API changes | pin OAuth client + e2e re-test on each platform release note |
| Freelance platform docs (Upwork, Fiverr, freelancer.com) | external | same | same |

---

## 7. Collision Scan

### 7.1 Shared files

| File | Owner waves | Mitigation |
|---|---|---|
| `src/p23/executors/registry.py` | P23-001 + P23-005 + P23-006..013 | P23-001 creates empty registry; P23-005 populates Hermes-binding entries; P23-006..013 each add their own entry via append-only decorators; collision is additive only. Single owner = P23-001 wave. |
| `src/p23/secrets/loader.py` | P23-014 only | single owner |
| `tools/registry.py` (Hermes fork) | P23-005 | parent owns (cross-project — must coordinate with P24 plan) |
| `secrets/p23/executors.enc.yaml` | P23-014 only | single owner |
| `.sops.yaml` | P23-014 | single owner |
| `grafana/dashboards/p23-executors.json` | P23-015 only | single owner |
| `audit.p23_action_log` table | P23-003 (DDL) + P23-001..016 (writers through `AuditHook` only) | single `AuditHook` writer API; all waves call the same API. |
| `p23.action_queue` table | P23-002 (DDL) + P23-001..016 (enqueue through `ActionQueue` only) | single `ActionQueue.enqueue` API; no direct INSERT from executor surface. |

### 7.2 Shared config / env

| Var / Config | Owner wave | Notes |
|---|---|---|
| `P23_REDIS_DB` | P23-002 | `6` -- never overridable by executor surface; Hermes reads, executors read |
| `P23_WORKSPACE_ROOT` | P23-006 | default `/home/guinevere/workspace`, configurable per Hermes-tier |
| `P23_AUDIT_CHAIN_RESET_TOKEN` | P23-003 | emergency reset; Hermes-tier 4 only |
| `OBSCURA_CDP_URL` | P23-007 | defaults `ws://127.0.0.1:9222` |
| `GITHUB_APP_ID` / `GITHUB_APP_INSTALLATION_ID` | P23-008 | per Hermes |
| `FREELANCE_<PLATFORM>_OAUTH_CLIENT_ID` | P23-011 | per Hermes |
| `SOCIAL_<PLATFORM>_OAUTH_CLIENT_ID` | P23-012 | per Hermes |
| `EMAIL_<PROVIDER>_OAUTH_CLIENT_ID` | P23-013 | per Hermes |

### 7.3 Shared tests / fixtures

| Fixture | Owner wave | Notes |
|---|---|---|
| `tests/fixtures/redis_fake.py` | P23-002 | fakeredis instance; reused by P23-005/014/016 |
| `tests/fixtures/postgres_fake.py` | P23-002 + P23-003 | testcontainers; reused by every wave's integration test |
| `tests/fixtures/playwright_fake.py` | P23-007 | `playwright.async_api` mocked; reused by P23-007 integration |
| `tests/fixtures/oauth_fake.py` | P23-011/012/013 | per-platform fake provider; isolated per sub-tool |

### 7.4 Safety-boundary docs (collide with parent-only)

| Doc | Notes |
|---|---|
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | NOT touched by P23 plan; P23 has no persona boundary (Q34). Parent-only. |
| `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | NOT touched by P23 plan; P23 has no consent gate (Q35). Parent-only. |
| `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` | NOT touched by P23 plan; prompt-injection defense for action-intent lives in Hermes (P24). |
| `docs/setup-evidence/P28-P36-masterplan/adr-drafts/*.md` | NOT touched; P23 plan cites but does not modify. |

No cross-boundary collision. P23 plan only writes into its own directory + the Hermes fork's `tools/registry.py` (parent-coordinated with P24).

### 7.5 Shared code outside P23 directory

| File | Owner | Notes |
|---|---|---|
| `src/mcp/tools/obscura_cdp.py` | P23-007 (refactor collision) | per-action context refactor must NOT break existing `src/mcp/` callers. Mitigation: P23-007 refactors to a `BrowserContext` manager that exposes the same 4 MCP tool functions with per-call isolation. Existing tests for `obscura_cdp.py` MUST pass before AND after. |
| `src/mcp/tools/github.py`, `git_tool.py` | P23-008 (wrapper collision) | thin wrapper MUST NOT modify MCP tool semantics; uses current API surface. |
| `src/life_kernel/executors/` (old plan location) | DELETED old plan paths | none — old plan deleted. New `src/p23/executors/` is the canonical location. |
| `src/surveillance/secret_scanner.py` | re-use only | P23-004 calls it; does not modify it. |

---

## 8. Per-Wave Verification Scaffold

> **Per AGENTS.md Section 2.5 (mandatory).** Every implementation step MUST have machine-checkable scaffold. This section defines the scaffold for all 16 waves.

### 8.1 Shared forbidden patterns (apply to ALL waves)

Forbidden regex patterns that MUST return zero matches across the entire P23 codebase. Defined here once; applied per-wave via Required Commands.

| ID | Pattern (GNU grep ERE — supports `\b`, `\s`, `\|` extensions) | Language | Why forbidden |
|---|---|---|---|
| FP-01 | `as\s+any\b` | TS | type safety bypass |
| FP-02 | `@ts-ignore\b` | TS | type safety bypass |
| FP-03 | `@ts-expect-error\b` | TS | type safety bypass |
| FP-04 | `#\s*type:\s*ignore\b` | Python | type safety bypass |
| FP-05 | `\bexcept\s+Exception\s*:` | Python | blanket exception swallow |
| FP-06 | `\bexcept\s*:\s*$` | Python | bare `except` |
| FP-07 | `\bpass\s*#\s*silent\b` | Python | bare-pass with comment marker |
| FP-08 | `\bpass\s*$` inside `except` | Python | silent catch |
| FP-09 | `\bconsole\.log\(.+(token\|password\|secret\|api_key)\b` | TS | secret in log |
| FP-10 | `\bprin?t\(.*(token\|password\|secret\|api_key)\b` | Python | secret in log |
| FP-11 | `\bshell_exec\b\|\bshell=True\b` | Python (outside `vps_executor.py` only) | shell injection vector |
| FP-12 | `\bgit\s+push\s+--force\b.*\b(main\|master)\b` | bash (in any committed file) | force-push to protected branch |
| FP-13 | `\bDROP\s+TABLE\s+(?!.*audit\|.*--audit)` | SQL not in migration | accidental table drop |
| FP-14 | `\bdelete\$/.*\$/` | Perl-style in P23 | no Perl in P23 |

The combined invocation per wave is:

```bash
# Run from repo root. Exits non-zero if any forbidden pattern matches.
grep -RInE '<per-wave forbidden subset>' src/p23/ tests/p23/ scripts/p23_*.sh grafana/dashboards/p23-*.json \
    | grep -vE '(test_.*\.py:.*#\s*ALLOW_FP_|test_.*\.py:.*self\.assertIn)' \
    && exit 1 || exit 0
```

### 8.2 Wave P23-001 — `BaseExecutor` + `ExecutorRegistry` + types

**Expected Files**

- `src/p23/__init__.py`
- `src/p23/executors/__init__.py`
- `src/p23/executors/base.py`
- `src/p23/executors/registry.py`
- `src/p23/types.py`
- `tests/p23/test_base.py`
- `tests/p23/test_registry.py`
- `tests/p23/test_types.py`

**Forbidden Patterns**: `FP-01`, `FP-02`, `FP-03`, `FP-04`, `FP-05`, `FP-06`, `FP-07`, `FP-08` (full subset)

**Required Commands**

```bash
# 1. Lint pass
ruff check src/p23/ tests/p23/ --select=E,F,W
# expected exit 0

# 2. Type check
mypy src/p23/types.py src/p23/executors/base.py src/p23/executors/registry.py \
    --strict --ignore-missing-imports
# expected exit 0

# 3. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/ tests/p23/ --subset=FP-01..FP-08
# expected exit 0

# 4. Unit tests
python -m pytest tests/p23/test_base.py tests/p23/test_registry.py tests/p23/test_types.py -v --tb=short
# expected exit 0

# 5. Coverage
python -m pytest tests/p23/test_base.py tests/p23/test_registry.py tests/p23/test_types.py \
    --cov=src/p23 --cov-fail-under=85
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-001/verification.md` (+ auditor-gate.md)

**Hard Rejection Criteria**:

- ANY FP-01..FP-08 match -> immediate FAIL.
- `mypy --strict` exit non-zero -> FAIL.
- Coverage < 85% -> FAIL.
- Missing `verification.md` or `auditor-gate.md` -> FAIL.

### 8.3 Wave P23-002 — Durable action queue

**Expected Files**

- `src/p23/queue/__init__.py`
- `src/p23/queue/action_queue.py`
- `src/p23/queue/reaper.py`
- `alembic/versions/p23_001_action_queue.py`
- `tests/p23/queue/__init__.py`
- `tests/p23/queue/test_action_queue.py`
- `tests/p23/queue/test_reaper.py`

**Forbidden Patterns**: full subset + `FP-13` (DROP TABLE)

**Required Commands**

```bash
# 1. Migration round-trip
alembic upgrade head
alembic downgrade -1
alembic upgrade head
# all exit 0

# 2. Type check
mypy src/p23/queue/ --strict --ignore-missing-imports
# expected exit 0

# 3. Idempotency test
python -m pytest tests/p23/queue/test_action_queue.py -v --tb=short -k idempotency
# expected exit 0 (2nd enqueue with same idempotency_key returns REJECTED)

# 4. Reaper crash-recovery test
python -m pytest tests/p23/queue/test_reaper.py -v --tb=short -k crash_recovery
# expected exit 0 (kill -9 simulated; restart; reaper moves stale -> pending)

# 5. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/queue/ tests/p23/queue/ --subset=full+FP-13
# expected exit 0

# 6. Redis integration (testcontainers)
docker compose -f docker-compose.test.yml up -d redis_test
redis-cli -p 6390 PING | grep PONG
# expected exit 0 (PONG)
docker compose down
```

**Evidence Requirements**: `evidence/p23-002/verification.md`, `evidence/p23-002/auditor-gate.md`

**Hard Rejection Criteria**:

- Migration round-trip fails.
- Idempotency test fails.
- Reaper crash-recovery test fails.
- Any forbidden pattern match.

### 8.4 Wave P23-003 — Audit trail + hash chain

**Expected Files**

- `src/p23/audit/__init__.py`
- `src/p23/audit/hook.py`
- `src/p23/audit/chain.py`
- `src/p23/audit/verifier.py`
- `alembic/versions/p23_002_audit_log.py`
- `tests/p23/audit/test_hook.py`
- `tests/p23/audit/test_chain.py`

**Forbidden Patterns**: full subset

**Required Commands**

```bash
# 1. Migration round-trip (as P23-002)
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
# expected exit 0

# 2. Chain integrity
python -m pytest tests/p23/audit/test_chain.py -v --tb=short -k chain_integrity
# expected exit 0 (recompute every event_hash from previous_hash + canonical_payload;
#                  assert all match stored event_hash)

# 3. Verifier detects tampered row
python -m pytest tests/p23/audit/test_chain.py -v --tb=short -k tamper_detection
# expected exit 0 (insert row with bogus event_hash -> verifier returns INCONSISTENT)

# 4. Hook always writes (kill mid-execute)
python -m pytest tests/p23/audit/test_hook.py -v --tb=short -k crash_pre_execute
# expected exit 0 (kill -9 between pre-write and side-effect;
#                  audit row exists with error.kind='crashed_pre_execute')

# 5. Forbidden patterns + log-leak (FP-09, FP-10)
bash scripts/verify_no_forbidden_patterns.sh src/p23/audit/ tests/p23/audit/ --subset=full+FP-09+FP-10
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-003/verification.md`, `evidence/p23-003/auditor-gate.md`

**Hard Rejection Criteria**:

- Chain integrity test fails.
- Tamper detection does not fire on tampered row.
- Crash pre-execute leaves NO audit row.

### 8.5 Wave P23-004 — Error envelope + redact wrapper

**Expected Files**

- `src/p23/errors.py`
- `src/p23/redact.py`
- `tests/p23/test_errors.py`
- `tests/p23/test_redact.py`

**Forbidden Patterns**: full subset + `FP-09` + `FP-10`

**Required Commands**

```bash
# 1. Subclass enumeration
python -m pytest tests/p23/test_errors.py -v --tb=short -k subclass_enumeration
# expected exit 0 (every thrown exception is a subclass of ExecutorError)

# 2. JSON-serialisable error round-trip
python -m pytest tests/p23/test_errors.py -v --tb=short -k json_serialisable
# expected exit 0 (ExecutorErrorEnvelope -> dict -> JSON -> dict -> ExecutorErrorEnvelope == original)

# 3. Redactor matches all known secret patterns
python -m pytest tests/p23/test_redact.py -v --tb=short
# expected exit 0 (AWS key, GitHub PAT, Slack token, private key, JWT, connection string -> REDACTED)

# 4. Redactor preserves function (no false positives)
python -m pytest tests/p23/test_redact.py -v --tb=short -k no_false_positives
# expected exit 0

# 5. Forbidden patterns + log-leak
bash scripts/verify_no_forbidden_patterns.sh src/p23/errors.py src/p23/redact.py \
    tests/p23/test_errors.py tests/p23/test_redact.py --subset=FP-01..FP-10
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-004/verification.md`, `evidence/p23-004/auditor-gate.md`

**Hard Rejection Criteria**:

- A thrown exception is NOT a subclass of `ExecutorError`.
- ErrorEnvelope is NOT JSON-serialisable.
- Redactor lets an AWS key / GitHub PAT pass through unredacted.

### 8.6 Wave P23-005 — Hermes tool-registry integration

**Expected Files**

- `src/p23/integration/__init__.py`
- `src/p23/integration/hermes_registry.py`
- `src/p23/integration/cancel.py`
- `src/p23/integration/events.py`
- `tests/p23/integration/test_hermes_registry.py`
- `tests/p23/integration/test_cancel.py`

**Forbidden Patterns**: full subset + `FP-09` + `FP-10`

**Required Commands**

```bash
# 1. Hermes registry registers 8 executors
python -m pytest tests/p23/integration/test_hermes_registry.py -v --tb=short -k all_executors_registered
# expected exit 0 (registry.names() == ['browser','desktop','vps','github','fs',
#                                          'freelance','social','email'])

# 2. Cancel primitive (synthetic)
python -m pytest tests/p23/integration/test_cancel.py -v --tb=short
# expected exit 0 (enqueue 30s task -> cancel -> returns within 1s with error.kind='cancelled')

# 3. Sync vs async dual path
python -m pytest tests/p23/integration/test_hermes_registry.py -v --tb=short -k dual_path
# expected exit 0 (<5s task returns Result directly; >=5s task returns action_id)

# 4. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/integration/ tests/p23/integration/ --subset=full
# expected exit 0

# 5. Mock P24 tool registry round-trip
python -m pytest tests/p23/integration/test_hermes_registry.py -v --tb=short -k mock_p24
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-005/verification.md`, `evidence/p23-005/auditor-gate.md`

**Hard Rejection Criteria**:

- Fewer than 8 executors registered at integration time.
- Cancel does not deliver within 1s window.
- Sync path leaks 5+ second task as Result without queueing.

### 8.7 Wave P23-006 — `filesystem_executor`

**Expected Files**

- `src/p23/executors/fs.py`
- `tests/p23/executors/test_fs.py`

**Forbidden Patterns**: full subset + path-traversal-checked

**Required Commands**

```bash
# 1. All 9 actions exercised
python -m pytest tests/p23/executors/test_fs.py -v --tb=short
# expected exit 0 (read/write/append/delete/list/glob/grep/move/copy)

# 2. Path traversal rejected
python -m pytest tests/p23/executors/test_fs.py -v --tb=short -k traversal_blocked
# expected exit 0 (../etc/passwd -> ValidationError)

# 3. Symlink escape rejected
python -m pytest tests/p23/executors/test_fs.py -v --tb=short -k symlink_blocked
# expected exit 0

# 4. Delete requires confirm=True
python -m pytest tests/p23/executors/test_fs.py -v --tb=short -k delete_confirm
# expected exit 0 (without confirm=True -> ValidationError)

# 5. Audit row produced for every action
python -m pytest tests/p23/executors/test_fs.py -v --tb=short -k audit_row
# expected exit 0 (SELECT audit.p23_action_log returns 1 row per action call)

# 6. Coverage
python -m pytest tests/p23/executors/test_fs.py --cov=src/p23/executors/fs --cov-fail-under=85
# expected exit 0

# 7. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/executors/fs.py tests/p23/executors/test_fs.py --subset=full
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-006/verification.md`, `evidence/p23-006/auditor-gate.md`

**Hard Rejection Criteria**:

- `../` traversal accepted.
- Symlink target outside workspace accepted.
- Delete without `confirm=True` accepted.
- Missing audit row for any action call.
- Coverage < 85%.

### 8.8 Wave P23-007 — `browser_executor`

**Expected Files**

- `src/p23/executors/browser.py`
- `src/p23/executors/browser_artifacts.py`
- `tests/p23/executors/test_browser.py`

**Forbidden Patterns**: full subset + per-action BrowserContext-required

**Required Commands**

```bash
# 1. Per-action isolation (no shared cookies)
python -m pytest tests/p23/executors/test_browser.py -v --tb=short -k per_action_context
# expected exit 0 (cookies set in action 1 do NOT persist to action 2)

# 2. Fallback when Obscura is down
python -m pytest tests/p23/executors/test_browser.py -v --tb=short -k fallback_to_chromium
# expected exit 0 (mock ConnectionRefusedError; falls to chromium.launch;
#                  metric browser_fallback_total increments)

# 3. All 8 actions exercised
python -m pytest tests/p23/executors/test_browser.py -v --tb=short -k all_actions
# expected exit 0 (navigate/click/fill/extract_text/screenshot/scroll/wait/download)

# 4. Artifact redaction
python -m pytest tests/p23/executors/test_browser.py -v --tb=short -k artifact_redaction
# expected exit 0 (cookie header, password form value -- not in artifact metadata.json)

# 5. Existing obscura_cdp MCP tools still work
python -m pytest tests/mcp/tools/test_obscura_cdp.py -v --tb=short
# expected exit 0 (refactor MUST NOT break MCP surface)

# 6. Coverage
python -m pytest tests/p23/executors/test_browser.py --cov=src/p23/executors/browser --cov-fail-under=80
# expected exit 0

# 7. Forbidden patterns + shell=True check
bash scripts/verify_no_forbidden_patterns.sh \
    src/p23/executors/browser.py src/p23/executors/browser_artifacts.py \
    tests/p23/executors/test_browser.py --subset=full+FP-11
# expected exit 0 (no FP-11 outside vps_executor)
```

**Evidence Requirements**: `evidence/p23-007/verification.md`, `evidence/p23-007/auditor-gate.md`

**Hard Rejection Criteria**:

- Cookies/fill values leak between consecutive actions.
- Obscura-down does not trigger fallback.
- Existing `obscura_cdp.py` MCP tests fail.
- Coverage < 80% (relaxed because Playwright requires integration env).

### 8.9 Wave P23-008 — `github_executor`

**Expected Files**

- `src/p23/executors/github.py`
- `tests/p23/executors/test_github.py`

**Forbidden Patterns**: full subset + `FP-12` (force-push-to-main) + `FP-11` (no shell=True outside vps_executor)

**Required Commands**

```bash
# 1. All 16 actions exercised
python -m pytest tests/p23/executors/test_github.py -v --tb=short -k all_actions
# expected exit 0

# 2. Force-push-to-main rejected
python -m pytest tests/p23/executors/test_github.py -v --tb=short -k force_push_to_main_rejected
# expected exit 0 (action=push, branch=main -> ValidationError)

# 3. merge_pr to main requires tier-4 logical signal
python -m pytest tests/p23/executors/test_github.py -v --tb=short -k merge_pr_main_requires_signal
# expected exit 0 (base=main WITHOUT signal flag -> ValidationError; WITH signal -> success)

# 4. Rate-limit backoff with jitter
python -m pytest tests/p23/executors/test_github.py -v --tb=short -k rate_limit_backoff
# expected exit 0 (mock 429 -> backoff sequence not identical)

# 5. Coverage
python -m pytest tests/p23/executors/test_github.py --cov=src/p23/executors/github --cov-fail-under=85
# expected exit 0

# 6. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/executors/github.py \
    tests/p23/executors/test_github.py --subset=full+FP-11+FP-12
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-008/verification.md`, `evidence/p23-008/auditor-gate.md`

**Hard Rejection Criteria**:

- Force-push to main accepted.
- `merge_pr` to main without tier-4 signal accepted.
- Rate-limit retry without jitter.
- Any `shell=True` outside `vps_executor`.

### 8.10 Wave P23-009 — `vps_executor`

**Expected Files**

- `src/p23/executors/vps.py`
- `src/p23/executors/vps_aizanta_proof.py`
- `tests/p23/executors/test_vps.py`

**Forbidden Patterns**: full subset + `FP-11` (no shell=True) + `FP-13` (no DROP audit protection bypass) + `aizanta`-name guard check

**Required Commands**

```bash
# 1. All 8 actions exercised
python -m pytest tests/p23/executors/test_vps.py -v --tb=short -k all_actions
# expected exit 0

# 2. Aizanta-proof pre/post check
python -m pytest tests/p23/executors/test_vps.py -v --tb=short -k aizanta_proof
# expected exit 0 (each action records pre+post snapshot)

# 3. aizanta-* unit rejected
python -m pytest tests/p23/executors/test_vps.py -v --tb=short -k aizanta_target_rejected
# expected exit 0 (action=systemctl unit=aizanta-* -> ValidationError)

# 4. aizanta user rejected
python -m pytest tests/p23/executors/test_vps.py -v --tb=short -k aizanta_user_rejected
# expected exit 0

# 5. Aizanta-impact detected halts
python -m pytest tests/p23/executors/test_vps.py -v --tb=short -k aizanta_impact_halts
# expected exit 0 (simulate aizanta state change -> Result.ok=False with error.kind='backend')

# 6. PostgreSQL aizanta DB connection rejected
python -m pytest tests/p23/executors/test_vps.py -v --tb=short -k postgres_aizanta_rejected
# expected exit 0

# 7. Coverage
python -m pytest tests/p23/executors/test_vps.py --cov=src/p23/executors/vps --cov-fail-under=80
# expected exit 0

# 8. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/executors/vps.py \
    src/p23/executors/vps_aizanta_proof.py tests/p23/executors/test_vps.py \
    --subset=full+FP-11+FP-13
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-009/verification.md`, `evidence/p23-009/auditor-gate.md`

**Hard Rejection Criteria**:

- ANY aizanta-target action accepted.
- Aizanta-impact diff detected but executor returned `ok=True`.
- `shell=True` found.
- Coverage < 80%.

### 8.11 Wave P23-010 — `desktop_executor` (Windows)

**Expected Files**

- `src/p23/executors/desktop.py`
- `tests/p23/executors/test_desktop.py`

**Forbidden Patterns**: full subset + `RunAs` + workspace-escape check

**Required Commands**

```bash
# 1. All 6 actions exercised
python -m pytest tests/p23/executors/test_desktop.py -v --tb=short -k all_actions
# expected exit 0

# 2. Workspace escape rejected
python -m pytest tests/p23/executors/test_desktop.py -v --tb=short -k workspace_escape_rejected
# expected exit 0

# 3. RunAs verb rejected
python -m pytest tests/p23/executors/test_desktop.py -v --tb=short -k runas_rejected
# expected exit 0 (verb=RunAs -> ValidationError)

# 4. Signed script only
python -m pytest tests/p23/executors/test_desktop.py -v --tb=short -k signed_script_only
# expected exit 0

# 5. Job-object limits enforced
python -m pytest tests/p23/executors/test_desktop.py -v --tb=short -k job_object_limits
# expected exit 0 (CPU 25%, mem 512MB, proc limit 8)

# 6. UAC prompt treated as failure
python -m pytest tests/p23/executors/test_desktop.py -v --tb=short -k uac_treated_as_failure
# expected exit 0

# 7. Coverage
python -m pytest tests/p23/executors/test_desktop.py --cov=src/p23/executors/desktop --cov-fail-under=80
# expected exit 0

# 8. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/executors/desktop.py \
    tests/p23/executors/test_desktop.py --subset=full
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-010/verification.md`, `evidence/p23-010/auditor-gate.md`

**Hard Rejection Criteria**:

- Workspace-escape path accepted.
- `-Verb RunAs` accepted.
- Unsigned script accepted.
- Job-object limits not set.

### 8.12 Wave P23-011 — `freelance_executor` (NEW)

**Expected Files**

- `src/p23/executors/freelance.py`
- `src/p23/executors/freelance/upwork.py`
- `src/p23/executors/freelance/fiverr.py`
- `src/p23/executors/freelance/freelancer.py`
- `tests/p23/executors/test_freelance.py`

**Forbidden Patterns**: full subset + `FP-09` + `FP-10` + `withdraw_to_wallet`-implementation check

**Required Commands**

```bash
# 1. All 9 actions exercised (across 3 platforms)
python -m pytest tests/p23/executors/test_freelance.py -v --tb=short -k all_actions
# expected exit 0

# 2. ToS compliance check required
python -m pytest tests/p23/executors/test_freelance.py -v --tb=short -k tos_required
# expected exit 0 (write action WITHOUT tos_checked -> ValidationError)

# 3. Wallet check on accept_contract
python -m pytest tests/p23/executors/test_freelance.py -v --tb=short -k wallet_required
# expected exit 0 (accept_contract WITHOUT wallet_checked -> ValidationError)

# 4. withdraw_to_wallet rejected
python -m pytest tests/p23/executors/test_freelance.py -v --tb=short -k withdraw_rejected
# expected exit 0 (action=withdraw_to_wallet -> ValidationError "not an executor action")

# 5. PII redacted in audit row
python -m pytest tests/p23/executors/test_freelance.py -v --tb=short -k pii_redacted
# expected exit 0

# 6. OAuth 401 triggers AuthError + retryable
python -m pytest tests/p23/executors/test_freelance.py -v --tb=short -k oauth_401_retryable
# expected exit 0

# 7. Coverage
python -m pytest tests/p23/executors/test_freelance.py --cov=src/p23/executors/freelance --cov-fail-under=80
# expected exit 0

# 8. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/executors/freelance/ \
    tests/p23/executors/test_freelance.py --subset=full+FP-09+FP-10
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-011/verification.md`, `evidence/p23-011/auditor-gate.md`

**Hard Rejection Criteria**:

- Write action accepted without ToS check.
- `accept_contract` accepted without wallet check.
- `withdraw_to_wallet` action accepted (not rejected).
- PII (applicant name, phone) leaks into audit row.

### 8.13 Wave P23-012 — `social_executor` (NEW)

**Expected Files**

- `src/p23/executors/social.py`
- `src/p23/executors/social/x.py`
- `src/p23/executors/social/linkedin.py`
- `src/p23/executors/social/instagram.py`
- `src/p23/executors/social/facebook.py`
- `tests/p23/executors/test_social.py`

**Forbidden Patterns**: full subset + `FP-09` + `FP-10` + DM-of-other-person block

**Required Commands**

```bash
# 1. All 5 cross-platform actions x 4 platforms = 20 cases
python -m pytest tests/p23/executors/test_social.py -v --tb=short -k all_platforms_all_actions
# expected exit 0 (read_timeline/post/reply/comment/search x x/linkedin/instagram/facebook)

# 2. ToS compliance required
python -m pytest tests/p23/executors/test_social.py -v --tb=short -k tos_required
# expected exit 0

# 3. Media paths must be in workspace
python -m pytest tests/p23/executors/test_social.py -v --tb=short -k media_workspace
# expected exit 0

# 4. Surveillance of OTHER person's DM rejected
python -m pytest tests/p23/executors/test_social.py -v --tb=short -k dm_other_person_rejected
# expected exit 0

# 5. Identity under Hermes Society brand
python -m pytest tests/p23/executors/test_social.py -v --tb=short -k hermes_society_brand
# expected exit 0 (brand='Hermes Society'; no individual bot-name leakage)

# 6. Rate-limit retry-with-jitter
python -m pytest tests/p23/executors/test_social.py -v --tb=short -k rate_limit_jitter
# expected exit 0

# 7. Coverage
python -m pytest tests/p23/executors/test_social.py --cov=src/p23/executors/social --cov-fail-under=80
# expected exit 0

# 8. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/executors/social/ \
    tests/p23/executors/test_social.py --subset=full+FP-09+FP-10
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-012/verification.md`, `evidence/p23-012/auditor-gate.md`

**Hard Rejection Criteria**:

- Write action without ToS check accepted.
- DM-of-other-person target accepted.
- Media path outside workspace accepted.
- Post under individual bot name.
- Rate-limit retry without jitter.

### 8.14 Wave P23-013 — `email_executor` (NEW)

**Expected Files**

- `src/p23/executors/email.py`
- `src/p23/executors/email/gmail.py`
- `src/p23/executors/email/outlook.py`
- `src/p23/executors/email/fastmail.py`
- `src/p23/executors/email/imap_smtp.py`
- `tests/p23/executors/test_email.py`

**Forbidden Patterns**: full subset + `FP-09` + `FP-10` + spam-filter trigger check

**Required Commands**

```bash
# 1. All 8 actions x 4 providers = 32 cases
python -m pytest tests/p23/executors/test_email.py -v --tb=short -k all_providers_all_actions
# expected exit 0 (list_inbox/search/read/send/reply/forward/mark_read/flag x gmail/outlook/fastmail/imap_smtp)

# 2. Attachment workspace enforced
python -m pytest tests/p23/executors/test_email.py -v --tb=short -k attachment_workspace
# expected exit 0 (attachment_path=/etc/passwd -> ValidationError)

# 3. Body-redact + spam filter applied pre-send
python -m pytest tests/p23/executors/test_email.py -v --tb=short -k pre_send_filter
# expected exit 0

# 4. Reply preserves In-Reply-To + References
python -m pytest tests/p23/executors/test_email.py -v --tb=short -k reply_headers_preserved
# expected exit 0

# 5. From header = Hermes's account name; never impersonates
python -m pytest tests/p23/executors/test_email.py -v --tb=short -k from_header_enforced
# expected exit 0

# 6. Coverage
python -m pytest tests/p23/executors/test_email.py --cov=src/p23/executors/email --cov-fail-under=80
# expected exit 0

# 7. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/executors/email/ \
    tests/p23/executors/test_email.py --subset=full+FP-09+FP-10
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-013/verification.md`, `evidence/p23-013/auditor-gate.md`

**Hard Rejection Criteria**:

- Attachment outside workspace accepted.
- Body with spam-phrase accepted pre-send.
- Reply without `In-Reply-To` header.
- `setfrom` rendering impersonation of another account.

### 8.15 Wave P23-014 — Secrets inventory + SOPS/age

**Expected Files**

- `secrets/p23/executors.enc.yaml` (encrypted; never plain)
- `src/p23/secrets/__init__.py`
- `src/p23/secrets/loader.py`
- `src/p23/secrets/rotation.py`
- `.sops.yaml` (add P23 age recipient -- single addition)
- `tests/p23/secrets/test_loader.py`
- `tests/p23/secrets/test_rotation.py`

**Forbidden Patterns**: full subset + plaintext-secret detection (FP-09/FP-10 with broader regex)

**Required Commands**

```bash
# 1. sops decrypt/encrypt/re-decrypt round-trip preserves content
sops --decrypt secrets/p23/executors.enc.yaml > /tmp/decrypted.yaml
sops --encrypt /tmp/decrypted.yaml > /tmp/reencrypted.yaml
diff <(sops --decrypt secrets/p23/executors.enc.yaml) <(sops --decrypt /tmp/reencrypted.yaml) \
    || (echo "ROTR: decrypt/encrypt/re-decrypt differs"; exit 1)
shred -u /tmp/decrypted.yaml /tmp/reencrypted.yaml
# expected exit 0

# 2. All 8 executor envelope keys present
python -c "
import yaml, subprocess
d = yaml.safe_load(subprocess.run(['sops','--decrypt','secrets/p23/executors.enc.yaml'],
    check=True, capture_output=True, text=True).stdout)
required = ['browser','desktop','vps','github','filesystem','freelance','social','email']
missing = [k for k in required if k not in d]
assert not missing, f'missing envelope keys: {missing}'
print('OK: 8 envelopes present')
"
# expected exit 0

# 3. Plaintext scan (FAIZ-isolation check)
grep -RIEn '(token|password|api_key|secret).*=.*[A-Za-z0-9]{16,}' \
    src/p23/secrets/ tests/p23/secrets/ docs/setup-evidence/P23/plan/ \
    | grep -v 'executors.enc.yaml' \
    && echo "FAIL: plaintext secret-like value" && exit 1 || exit 0
# expected exit 0

# 4. Rotation log table populated on test
python -m pytest tests/p23/secrets/test_rotation.py -v --tb=short
# expected exit 0

# 5. Secret loader fail-closed
python -m pytest tests/p23/secrets/test_loader.py -v --tb=short -k fail_closed
# expected exit 0 (SOPS missing key -> loader raises; executor does NOT proceed with empty secret)

# 6. Coverage
python -m pytest tests/p23/secrets/ --cov=src/p23/secrets --cov-fail-under=85
# expected exit 0

# 7. Forbidden patterns + log-leak
bash scripts/verify_no_forbidden_patterns.sh src/p23/secrets/ tests/p23/secrets/ \
    --subset=full+FP-09+FP-10
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-014/verification.md`, `evidence/p23-014/auditor-gate.md`

**Hard Rejection Criteria**:

- sops decrypt fails.
- Any of 8 envelope keys missing.
- Plaintext secret-like value in repo.
- Loader proceeds with missing/decrypt-failed secret.

### 8.16 Wave P23-015 — Observability + Prometheus

**Expected Files**

- `src/p23/observability/__init__.py`
- `src/p23/observability/metrics.py`
- `grafana/dashboards/p23-executors.json`
- `tools/registry.py` (Hermes fork -- `/metrics` endpoint registration, ONE LINE addition per AGENTS.md Section 14 parent-orchestration pattern)
- `tests/p23/observability/test_metrics.py`

**Forbidden Patterns**: full subset

**Required Commands**

```bash
# 1. Metrics registered per executor
python -m pytest tests/p23/observability/test_metrics.py -v --tb=short -k all_executors_have_counters
# expected exit 0 (8 executors each register:
#                  actions_total, action_seconds histogram, errors_total{kind})

# 2. Scrape-style assertion
python -m pytest tests/p23/observability/test_metrics.py -v --tb=short -k scrape_format
# expected exit 0 (text exposition format includes all 24 series)

# 3. Grafana JSON parses + has 8 panels
python -c "
import json
with open('grafana/dashboards/p23-executors.json') as f:
    d = json.load(f)
panels = [p for p in d['dashboard']['panels'] if p['type'] in ['timeseries','stat']]
assert len(panels) >= 8, f'expected >=8 panels, got {len(panels)}'
print('OK: >=8 panels')
"
# expected exit 0

# 4. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh src/p23/observability/ tests/p23/observability/ \
    --subset=full
# expected exit 0
```

**Evidence Requirements**: `evidence/p23-015/verification.md`, `evidence/p23-015/auditor-gate.md`

**Hard Rejection Criteria**:

- Any executor missing counters.
- Grafana JSON parse fails or has <8 panels.
- Metric registered but not exposed in `/metrics` scrape.

### 8.17 Wave P23-016 — E2E + 24h soak + chain verifier

**Expected Files**

- `tests/p23/e2e/test_8executors_smoke.py`
- `tests/p23/e2e/test_queue_durability.py`
- `tests/p23/e2e/test_audit_chain_integrity.py`
- `scripts/soak_test.sh`
- `cron/p23_chain_verifier.sh`

**Forbidden Patterns**: full subset

**Required Commands**

```bash
# 1. Full E2E smoke (sync + async paths for each executor)
python -m pytest tests/p23/e2e/ -v --tb=short
# expected exit 0

# 2. Queue durability (kill executor mid-action)
python -m pytest tests/p23/e2e/test_queue_durability.py -v --tb=short -k crash_recovery
# expected exit 0

# 3. Audit chain integrity over load
python -m pytest tests/p23/e2e/test_audit_chain_integrity.py -v --tb=short -k chain_under_load
# expected exit 0 (1h equivalent volume, chain verifies clean at end)

# 4. Soak script syntax + dry-run
bash -n scripts/soak_test.sh
# expected exit 0

# 5. Chain verifier cron syntax + dry-load
bash -n cron/p23_chain_verifier.sh && bash cron/p23_chain_verifier.sh --dry-run
# expected exit 0

# 6. Forbidden patterns
bash scripts/verify_no_forbidden_patterns.sh tests/p23/e2e/ scripts/soak_test.sh \
    cron/p23_chain_verifier.sh --subset=full
# expected exit 0

# 7. 24h readiness GO/NO-GO (manual gate)
# Manual: parent runs `./scripts/soak_test.sh 24h --executor=all`; checks:
#  - no unhandled exception
#  - audit chain verifier (cron job) runs and reports chain-healthy
#  - queue reaper not stuck (`redis-cli zcard p23:action:reclaim_at` = 0)
#  - Prometheus metrics stable (no unbounded growth)
# Auto-verified by `soak_test.sh` exit code.
```

**Evidence Requirements**: `evidence/p23-016/verification.md`, `evidence/p23-016/auditor-gate.md`

**Hard Rejection Criteria**:

- Any E2E fails.
- Queue reaper stuck (`reclaim_at` cardinality > 0 after 1h idle).
- Chain verifier reports inconsistency.
- 24h soak GO/NO-GO = NO-GO.

---

## 9. Evidence Paths

### 9.1 Evidence directory layout

```
docs/setup-evidence/P23/
├── README.md
├── plan/
│   └── p23-execution-layer-enterprise-plan.md   ← THIS FILE
├── research/                                    (13 existing files; KEEP HISTORICAL REFERENCE)
│   └── p23-*.md
├── evidence/                                    (6 existing files KEEP)
│   ├── p23-doc-gate-cleanup.md
│   ├── p23-recount-ground-truth.md
│   ├── p23-definition-verification.md
│   ├── auditor-gate.md
│   ├── final-p23-planning-report.md
│   ├── audits/                                  (26 existing audit files KEEP)
│   │   ├── round-1/  (13)
│   │   ├── round-2/  (13)
│   │   ├── codex-fix-1...4
│   │   └── implementability-audit-codex-2026-06-25.md
│   └── p23-XXX-wave-yyy/                        (NEW per-wave evidence)
│       ├── verification.md                      (12-section schema per AGENTS.md Section 11)
│       └── auditor-gate.md
```

### 9.2 Per-wave evidence file contents (template)

Each `evidence/p23-XXX-wave-yyy/verification.md` MUST contain these 12 sections (per AGENTS.md Section 11):

1. **What Was Done** — high-level narrative + list of files created/modified
2. **Files Changed** — exact file paths + diff summary
3. **Validation Results** — exit codes of every Required Command for the wave
4. **Evidence Artifacts** — pointer to actual artifacts (test reports, screenshots, log snapshots)
5. **Doc-Sync Impact** — which docs/ADRs/PersonaSafetyPolicy/ConsentRevocationPolicy were updated
6. **Boundary Compliance** — checklist: no HARD STOP, no consent gate, no risk-tier L1-L4, no SemAction, no Faiz-approval-gate; alignment to Q34/Q35/Q64/Q67/Q77/Q88/Q96/Q107
7. **Rollback/Re-run Safety** — how to roll back this wave; whether re-run is safe
8. **Design Decisions/Caveats** — non-obvious tradeoffs
9. **Auditor Gate** — auditor sub-agent verdict reference (`auditor-gate.md`)
10. **Security Scan** — secret scanner output on diff
11. **Acceptance Criteria Mapping** — OBJ-01..OBJ-10 mapping
12. **Footer** — version + author + change log

Each `evidence/p23-XXX-wave-yyy/auditor-gate.md` MUST contain:

- Auditor sub-agent name + role
- Scope (files audited)
- Findings (PASS / NEEDS REVIEW / FAIL)
- If any FAIL: re-audit loop until PASS

### 9.3 Wave evidence index (`evidence/INDEX.md`)

Created at end of P23-016. Contains one row per wave: `wave | evidence path | auditor verdict | status`.

### 9.4 Evidence retention/abandonment policy

- Old P23 research + audit files under `research/` (13 files) + `evidence/audits/` (26 files) are KEEP HISTORICAL REFERENCE. Not modified, not deleted.
- New evidence for new waves goes into `evidence/p23-001/..p23-016/` directories.
- README updated at P23-016 finalisation to reflect both old (historical) and new (current) evidence sets.

---

## 10. Auditor Matrix

Per AGENTS.md Section 2.10. Auditors are spawned in parallel after parent verification of each wave, one per audit dimension. Verdict = PASS / NEEDS REVIEW / FAIL. FAIL blocks completion; NEEDS REVIEW requires investigation.

### 10.1 Standard audit dimensions (apply to ALL 16 waves)

| Dim | Auditor name (subagent role) | Scope | Verdict criteria |
|---|---|---|---|
| AUD-01 | GoF-GoalVerifier | Wave's OBJ mapping | Each OBJ wave covers the listed OBJ-XX verbatim |
| AUD-02 | Oracle-QualityAuditor | All changed files | No FP-01..FP-14 match; no dead code; comments match behaviour |
| AUD-03 | Oracle-SecurityAuditor | All changed files | No secret leak; SOPS stays encrypted; OAuth scopes match intent |
| AUD-04 | Compliance-BoundaryAuditor | All changed files | NO HARD STOP listener; NO consent-consent_ledger; NO L-tier classifier in executor; NO Faiz-approval hook; NO SemAction; NO AuthLevel 1:1 |
| AUD-05 | Auditor-DocsConsistency | All docs touched by wave | No stale references; YAML frontmatter valid; table pipes aligned |
| AUD-06 | Auditor-BLDMAlignment | Plan + wave evidence | Citations to Q-numbers correct (Q34/Q35/Q64/Q67/Q77/Q88/Q96/Q107 at minimum); no rule-disobeyed |
| AUD-07 | Hermes-IntegrationAuditor (only P23-005) | Hermes fork registered bindings | `tools/registry.py` entries match P23 names; no missing `Action`/`Result` field |
| AUD-08 | Data-IsolationAuditor (P23-002/003/006/014) | PG schema + secrets file | `guinevere_core` role has correct GRANT; no `UPDATE`/`DELETE` on WORM table; one `secret_id` per executor |
| AUD-09 | Audit-ChainAuditor (P23-003/016) | `audit.p23_action_log` | Hash chain recompute matches stored `event_hash` for all rows in test volume |
| AUD-10 | PrivacyAuditor (ALL waves) | All audit rows in test volume | No PII / secret / intimate content in audit row |
| AUD-11 | ScalabilityAuditor (P23-002/015/016) | Redis DB6 + Prometheus | No unbounded cardinality; metrics naming matches Grafana JSON |
| AUD-12 | RollbackAuditor (ALL waves except foundation P23-001..005) | Rollback table (Section 11) | Every wave has explicit rollback path; re-run-safe OR one-shot documented |

### 10.2 Per-wave auditor matrix (compact)

| Wave | AUD-01 | AUD-02 | AUD-03 | AUD-04 | AUD-05 | AUD-06 | AUD-07 | AUD-08 | AUD-09 | AUD-10 | AUD-11 | AUD-12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P23-001 | X | X | X | X | X | X |   |   |   | X |   |   |
| P23-002 | X | X | X | X | X | X |   | X |   | X | X |   |
| P23-003 | X | X | X | X | X | X |   | X | X | X |   |   |
| P23-004 | X | X | X | X | X | X |   |   |   | X |   |   |
| P23-005 | X | X | X | X | X | X | X |   |   | X |   | X |
| P23-006 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-007 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-008 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-009 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-010 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-011 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-012 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-013 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-014 | X | X | X | X | X | X |   | X |   | X |   | X |
| P23-015 | X | X | X | X | X | X |   |   |   |   | X | X |
| P23-016 | X | X | X | X | X | X | X |   | X | X | X | X |

Auditors fire in **parallel** within a wave; cross-wave they fire sequentially (P23-N + 1 only after P23-N PASSes).

---

## 11. Rollback Plan

> **Per-wave rollback.** Each wave non-destructively removes its changes.

### 11.1 Wave-level rollback table

| Wave | Rollback action | Re-run safety | Notes |
|---|---|---|---|
| P23-001 | `git revert <P23-001-commit>`; remove `src/p23/` directory | full | Foundation wave |
| P23-002 | `alembic downgrade -1` to remove `p23.action_queue`; `redis-cli -n 6 FLUSHDB` | one-shot (data loss in DB6) | Migration is reversible; data is one-shot |
| P23-003 | `alembic downgrade -1` to remove `audit.p23_action_log` | one-shot (audit data loss) | Audit data loss breaks forensics -- only rollback if re-performing with corrected chain |
| P23-004 | `git revert <P23-004-commit>` removes `errors.py` and `redact.py` | full | Pure-Python module -- safe |
| P23-005 | `git revert <P23-005-commit>`; restore old `tools/registry.py` from upstream Hermes fork | full (with mock cache reset) | Cross-project revert -- coordinate with P24 |
| P23-006 | `git revert <P23-006-commit>` | full | Single executor file + tests |
| P23-007 | `git revert <P23-007-commit>` AND `git revert <obscura_cdp refactor>` | requires re-running existing `obscura_cdp` tests to confirm restoration | Browser wave is paired with `obscura_cdp.py` refactor -- revert both together |
| P23-008 | `git revert <P23-008-commit>` | full | Thin wrapper -- no substrate change |
| P23-009 | `git revert <P23-009-commit>` | full | No system change; only executor file + tests |
| P23-010 | `git revert <P23-010-commit>` | full | No system change; executor + tests only |
| P23-011 | `git revert <P23-011-commit>` | full | New executor only |
| P23-012 | `git revert <P23-012-commit>` | full | New executor only |
| P23-013 | `git revert <P23-013-commit>` | full | New executor only |
| P23-014 | `sops --decrypt secrets/p23/executors.enc.yaml --in-place rotate` (rotate all secrets) | one-shot (secret invalidation) | Real rollback means ROTATING all secrets, NOT re-encrypting in place |
| P23-015 | `git revert <P23-015-commit>` | full | Metrics module + dashboard JSON -- safe to revert |
| P23-016 | `git revert <P23-016-commit>` | full | Tests + soak script only |

### 11.2 Cross-wave compound rollback procedures

| Scenario | Steps |
|---|---|
| P23 FULL rollback (unwind everything) | reverse-order reverts: P23-016 -> P23-015 -> P23-014 (rotate secrets) -> P23-013 -> P23-012 -> P23-011 -> P23-010 -> P23-009 -> P23-008 -> P23-007 + obscura revert -> P23-006 -> P23-005 cross-project coordination -> P23-004 -> P23-003 alembic downgrade -> P23-002 alembic downgrade -> P23-001 |
| Single executor rollback | revert that wave's commit; SOPS-rotate that executor's `secret_id` |
| Migration schema rollback WITHOUT data recovery | `alembic downgrade -1` for that migration number |
| 24h soak failure | identify failing executor from logs + Prometheus; revert that wave; rerun targeted soak |

### 11.3 Idempotency

Per AGENTS.md Section 2.11, scripts and migrations must be re-run safe OR documented one-shot. All waves in P23 satisfy this:

- Foundation waves (P23-001..005): pure-Python or migration; migration is forward-only but migration `down_revision='p23_001_life_kernel_schema'` (or empty for new chain) makes the round-trip well-defined.
- Executor waves (P23-006..013): pure-Python no shared writers; re-running is safe.
- Secrets wave: encryption is idempotent (re-encrypt yields same output); secret rotation is one-shot per secret.
- Observability wave: dashboards are JSON, idempotent re-import.
- E2E/soak wave: tests are idempotent; soak script `kill -9` self-resets results table to reduce noise.

## 12. Caveats and Risks

### 12.1 Known caveats (binding clarifications)

| C-01 | **Q62/Q67 consciousness-loop-first** — P23 is downstream of Hermes consciousness loop. If Hermes (P24) is delayed or changes its tool-registry contract, P23-005 needs re-coordination. Mitigation: P23-005 mocks P24 via `tools/registry.py` adapter; test harness uses fake registry. |
| C-02 | **Q64/Q68 hermetic memory** — P23 audit log is NOT readable by Faiz directly; only through Hermes-initiated release. If daemon runs audit queries, Hermes must authorise. |
| C-03 | **Q67 24/7** — P23 executors must be 24/7 ready; no graceful-degradation for "Faiz not around". Mitigation: executors run as systemd service `guinevere-p23.service` with `Restart=always`, sharing `guinevere.slice`. |
| C-04 | **Q88/Q89/Q90 DAO company, Faiz outside** — P23 audit + secrets + revenue-routing infrastructure treats `hermes_id` as authoritative actor, NOT Faiz. Config values that hardcode "faiz" or any individual name are FORBIDDEN. |
| C-05 | **Q96 Co-CEO split** — Both Guinevere and Pharsa call P23 executors. Tests MUST exercise BOTH as `hermes_id`. `email_executor` per-Hermes-account is the cleanest manifestation. |
| C-06 | **Q107 2/2 multisig wallet** — Freelance executor never directly accesses wallet; only flags `wallet_checked=True` after Hermes Tier-4 quorum ack. This is a hardcoded guardrail; bypass is a SEV0 incident. |
| C-07 | **AGENTS.md Section 0 BLOCKING** — `as any` / `@ts-ignore` / `@ts-expect-error` / `# type: ignore` / bare `except` / empty catch / `pass # silent` are FORBIDDEN. Section 8 forbidden-pattern grid is the authoring gate. |
| C-08 | **AGENTS.md Section 0 BLOCKING — secrets** — no Discord bot token, API key, DB password, surveillance credential, SOPS/age key in repo. SOPS always. Even in `tests/` fixtures. |
| C-09 | **AGENTS.md Section 0 BLOCKING — intimate / surveillance** — no raw screen capture, no intimate Faiz data, no surveillance raw in artifacts. Forced via `redactor`+`fp-09/fp-10` scan. |
| C-10 | **AGENTS.md Section 0 BLOCKING — failure coverage** — every test, every sub-agent claim, every evidence file must be parent-read + parent-verified. Sub-agent self-report is not evidence. |

### 12.2 Residual risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Playwright API breaks between pin versions | low | medium | `<2.0` pin; integration test against pinned version; Playwright+Chromium fallback for Obscura CDP |
| R-02 | Obscura CDP coverage still lacks `Page.captureScreenshot` | medium | low | automatic fallback to Chromium for capture actions; pre-check in P23-007 preflight |
| R-03 | GitHub App install expires / token revoked | medium | high | `gkv1-kek-secrets-p23-github-app` rotation via ADR-023; quarterly rotation triggered by ADR-035 revisit |
| R-04 | Tailscale mesh down (no internet connectivity) | low | high | Aizanta VPS works offline; executors queue + retry; Discord-DM Hermes alert on persistent Tailscale-down |
| R-05 | Freelance platform ToS change suddenly disallows automation | medium | medium | ToS compliance check enforced; Hermes can pause a platform's executor if ToS changes |
| R-06 | social platform rate-limit surge during mass campaign | medium | medium | jittered backoff; per-platform token bucket; surface to Hermes for pacing |
| R-07 | Email provider SMTP/IMAP server outage | medium | medium | Backoff with retry; per-provider health metric; Hermes routes to alternate provider if configured |
| R-08 | desktop_executor Windows NSSM service crash | low | high | systemd Restart=always on `guinevere-desktop.service`; crash dumps captured to `/var/log/guinevere/desktop-crash/`; V-002 corroboration |
| R-09 | Old P23A plans or wrong-decision corpus in research files re-introduce 1:1 AuthLevel mapping | medium | high | AUD-04 Compliance-BoundaryAuditor explicitly checks for absence; verifier script `scripts/check_no_old_p23_artifacts.sh` runs on every wave |
| R-10 | consciousness loop changes its tool-registry contract mid-wave | low | high | P23-005 mocks P24; tests use fake registry; cross-restoration verified in P23-016 integration |
| R-11 | founder 2/2 (Guinevere + Pharsa) disagreement on action outcome | low | high | Tier-4 voting protocol (Hermes-side, not P23); audit row remains hash-chained; reject-of-quorum never reaches executor |

### 12.3 Compliance framework map

| Compliance concern | How P23 complies |
|---|---|
| AGENTS.md Section 0 BLOCKING rules | enforced via forbidden patterns (Section 8) + parent verifier + AUD-04 |
| AGENTS.md Section 2.4 / 2.5 (planner scaffold) | this document is the planner output; per-step scaffold in Section 8 |
| AGENTS.md Section 2.10 (auditor orchestrator) | parallel auditor matrix in Section 10 |
| AGENTS.md Section 2.11 (idempotency / one-shot) | Section 11.3 documents idempotency for every wave |
| GDPR / data-classification (Q64/Q68) | redaction pipeline + hermetic memory + no Faiz access |
| ADR-035 emergency-kill | Hermes-consumed kill stamp — NOT in P23 (executor only sees cancelled Result) |
| ADR-014 shared-VPS isolation (Aizanta-untouched) | vps_executor Section 4.3 + R11 above |
| ADR-019 Tailscale mesh | VPS-bound executors never have public ports; Section 3.8 |
| ADR-020 / ADR-033 browser strategy | refactor obscura_cdp; per-action context; Playwright+Chromium fallback |
| ADR-030 Redis DB allocations | P23 reserved DB6 (NEW); DB0/DB5/P20/P22 untouched |
| ADR-056 (Hermes fork 100% native built-in) | NO external plugin / side module; P23 is fork-internal |

### 12.4 Out-of-band concerns (NOT P23's job)

- P20 life kernel heartbeat + sensor adapters — owned by P20.
- P21 voice (Discord) + speech recognition — owned by P21.
- P22 integration hub + secrets/consent ledger — owned by P22.
- Hermes (P24) consciousness loop, emotion system, dreaming — owned by P24.
- DAO governance + 2/2 quorum + wallet staking — owned by P28-P36.

P23 coordinates with these via the Hermes-fork tool-registry (`tools/registry.py`) and via SOPS/age secrets only.

---

## 13. Execution Checklist

> **Step-by-step.** Parent-driven. Sub-agents fire-and-forget one step at a time; parent verifies per Section 8 scaffold before claiming done.

### 13.1 Pre-implementation (parent)

```text
[ ] 0.0 Read AGENTS.md
[ ] 0.1 Skim BLDM-Hard-Locked-Faiz-Decisions.md (Section 1-12)
[ ] 0.2 Confirm old P23 plan file is deleted from docs/setup-evidence/P23/plan/
[ ] 0.3 Confirm README.md "Status" line is updated to reference replan
[ ] 0.4 Run todowrite with the 16-wave master TODO
[ ] 0.5 Verify forbid-pattern shell script `scripts/verify_no_forbidden_patterns.sh` exists
        else spawn explore subagent to scaffold it from Section 8.1 FP grid
[ ] 0.6 Verify `docker-compose.test.yml` (redis_test port 6390) is present
[ ] 0.7 Verify `tools/registry.py` location in Hermes fork (P24 boundary coord)
```

### 13.2 Per-wave loop (parent)

```text
[ ] N.1 Update todo: mark P23-N in_progress
[ ] N.2 Pre-flight: check dependency wave(s) PASS
[ ] N.3 Spawn implementer sub-agent with Section 8 scaffold for P23-N
        - Include exact expected files, forbidden patterns subset, required commands
        - Include load_skills=['git-master']
        - run_in_background=true
[ ] N.4 Wait for completion notification
[ ] N.5 Verify scaffold: parent-rerun ALL Required Commands for wave N
        - If any exit non-zero: record scaffold violation in evidence, re-delegate via task_id
[ ] N.6 Read sub-agent's summary file (parent) — assert it does NOT claim success without listing exit codes
[ ] N.7 Verify files exist on disk:
        - All Expected Files in scaffold
        - evidence/p23-N/verification.md
        - evidence/p23-N/auditor-gate.md (initial, before auditor pass)
[ ] N.8 Spawn parallel auditor sub-agents (one per applicable dim in Section 10.2 for this wave)
        - Each writes to evidence/p23-N/auditor-gate.md (append/append)
        - Verdict = PASS / NEEDS REVIEW / FAIL
[ ] N.9 Read each auditor report (parent); fix valid NEEDS-REVIEW/FAIL findings
[ ] N.10 Re-run failing Required Command(s) after fix; re-audit via task_id until PASS
[ ] N.11 Verify LSP diagnostics clean on changed files
[ ] N.12 Mark todo P23-N completed; proceed to P23-(N+1)
```

### 13.3 Acceptance (per wave)

A wave is COMPLETE only when ALL of:

- [ ] All Required Commands in Section 8 pass (parent-verified, NOT sub-agent self-report).
- [ ] All applicable AUD-XX auditors in Section 10.2 returned PASS (or NEEDS RE.
- [ ] `evidence/p23-N/verification.md` exists with all 12 sections populated (per Section 9.2).
- [ ] `evidence/p23-N/auditor-gate.md` exists with all applicable AUD-XX verdicts recorded.
- [ ] No new boundary violations (HARD STOP, consent gate, L-tier, SemAction, Faiz-approval, AuthLevel 1:1) — confirmed by AUD-04.
- [ ] No secret in repo (`fp-09`/`fp-10` scan + `fp-Aizanta-inventory` confirm).
- [ ] No PII / intimate content in audit row (AUD-10).
- [ ] Hash chain verifies (P23-003, P23-016).
- [ ] LSP diagnostic clean.
- [ ] Coverage >= per-wave threshold (85% for foundation + simple executors; 80% for browser/vps/social/email/freelance/desktop).

### 13.4 Final acceptance (P23-016)

P23 is COMPLETE (whole phase) only when ALL of:

- [ ] All 16 waves PASS.
- [ ] 24h soak PASS (manual gate per Section 8.17 step 7, auto-verified by `soak_test.sh`).
- [ ] Chain verifier cron job installed and reports chain-healthy at 1h, 6h, 24h marks.
- [ ] README.md updated to declare P23 EXECUTION LAYER COMPLETE.
- [ ] PROGRESS.md entry added at phase-complete row.
- [ ] `evidence/INDEX.md` exists with all 16 wave rows.
- [ ] Final report filed at `docs/setup-evidence/P23/evidence/final-p23-execution-layer-report.md`.
- [ ] Cross-project handshake: P24 plan references P23 plan as upstream dependency in `tools/registry.py` integration.

### 13.5 Sign-off (parent -> Faiz)

```text
[ ] Compile final report:
        - Wave-by-wave verification status
        - Auditor matrix verdict matrix
        - Compliance map (Section 12.3) checklist pass
        - Caveats + Residual risks snapshot (Section 12)
[ ] Update BLDM-Hard-Locked-Faiz-Decisions.md if implementation surfaced NEW Q-answers
        (requires Faiz-only T5 ratification per Q22)
[ ] Hand off to Faiz with "P23 ready for production-deploy + production-pipeline enablement" verdict
        (deployment is via P28-P36 masterplan, NOT P23 itself)
```

---

## 14. Footer

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (drafter), Faiz-acknowledged | Initial REPLAN. Replaces `p23-embodied-operations-enterprise-plan.md` (DELETED 2026-06-28). 13 sections + 16 waves scaffold + 8 executor specs + 12 audit-dim matrix. |

### Operator Sign-Off

Pending Faiz sign-off per Section 13.5 + bypass-mode acknowledgement. Plan is valid for parent-driven implementation under AGENTS.md Section 0 BLOCKING rules and BLDM Q1-Q109 paradigm shifts (Q34/Q35/Q64/Q67/Q77/Q88/Q89/Q90/Q96/Q107 load-bearing).

### Cross-References

- Handoff: `docs/setup-evidence/P23-P24-replan-handoff.md`
- BLDM: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md`
- ADR-062 paradigm shift: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-062-hermes-safety-paradigm-shift.md`
- ADR-063 consciousness loop: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-063-consciousness-loop-architecture.md`
- ADR-056 fork decision: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-056-hermes-fork-implementation.md`
- Hermes Agent source: `https://github.com/NousResearch/hermes-agent` (v0.15.2, MIT)
- Existing research inputs (parent-read for this replan):
  - `docs/setup-evidence/P23/research/p23-browser-automation-research.md`
  - `docs/setup-evidence/P23/research/p23-windows-desktop-action-research.md`
  - `docs/setup-evidence/P23/research/p23-vps-cli-deploy-action-research.md`
  - `docs/setup-evidence/P23/research/p23-github-repo-action-research.md`
  - `docs/setup-evidence/P23/research/p23-rollback-idempotency-research.md`
  - `docs/setup-evidence/P23/research/p23-security-secrets-consent-research.md`
  - `docs/setup-evidence/P23/research/p23-policy-gate-risk-classification-research.md` (parent-read for REFERENCES-ONLY; superseded sections ignore Q34/Q35/Q74/Q79/Q80/Q62/Q67/Q64 paradigm shifts)
  - 6 more research files (mobile, observability, etc) — KEEP HISTORICAL REFERENCE

### Provenance

This document was drafter-owned (parent-author). No sub-agent was delegated for the plan write itself; per AGENTS.md Section 14 sub-agent output discipline, plan documents >50 lines are NOT delegated. Research subagents WERE used for read-and-summarise of historical P23 research files + BLDM.

### Maintenance

This document evolves only under T5 governance (per BLDM Q19/Q22/Q56) due to safety-boundary, persona-bypass, hard-stop-removal, or major architecture change touchpoints. Routine clarifications -> minor version bump (v1.0 -> v1.1); structural change -> major version (v1.0 -> v2.0) and re-validator-gate.

---

> P23 is the **execution layer**. Hermes thinks. P23 acts. Audit is the witness. Hermes owns the consequences.




