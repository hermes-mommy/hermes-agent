# P26.1 Redis Stream Architecture Research

## Verdict

Use **Redis Streams**, not Redis Lists, for the 9Router usage write buffer.

Recommended path:

```text
9Router workers -> Redis Stream -> usage-writer consumer group -> SQLite batch transaction -> XACK
```

Streams are the better fit because this workload needs durable-ish append-only events, fan-in from many workers, consumer-group ownership, pending-entry visibility, replay/retry semantics, and explicit acknowledgement after the SQLite commit. Redis Lists can provide a simple queue with `LPUSH`/`BRPOP`, but they do not natively provide consumer-group pending state, per-message acknowledgement, idle retry claiming, or backlog introspection. Lists are only preferable if the system intentionally accepts at-most-once or manually reimplemented retry semantics.

## Sources

- Redis Streams data type: <https://redis.io/docs/latest/develop/data-types/streams/>
- `XREADGROUP`: <https://redis.io/docs/latest/commands/xreadgroup/>
- `XACK`: <https://redis.io/docs/latest/commands/xack/>
- `XPENDING`: <https://redis.io/docs/latest/commands/xpending/>
- `XAUTOCLAIM`: <https://redis.io/docs/latest/commands/xautoclaim/>
- Redis persistence: <https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/>
- Redis Node.js probabilistic streaming guide: <https://redis.io/docs/latest/develop/clients/nodejs/probs/>

## Architecture

### Stream

- Stream key: `usage:events:v1`
- Consumer group: `usage-writers`
- Consumer name: stable per writer process, for example `usage-writer-${hostname}-${pid}`
- Producer role: each 9Router worker appends one usage event per completed request
- Consumer role: dedicated usage-writer reads batches from the group, writes all valid events in one SQLite transaction, then acknowledges only the committed event IDs

The stream should be created during startup or migration with a group start ID that matches the desired behavior:

- `$`: consume only events appended after group creation. Best for new deployments.
- `0`: consume existing stream history. Best when enabling the writer after producers may already be writing.

For P26.1, use `$` only if startup ordering guarantees the group exists before workers append. Otherwise use `0` during initial rollout to avoid dropping pre-existing buffered events.

### Event Schema

Every Redis Stream entry must include these required fields:

| Field | Type | Required | Notes |
|---|---:|---:|---|
| `request_id` | string | yes | Stable unique request identifier. Use as SQLite idempotency key. |
| `timestamp` | string | yes | ISO-8601 UTC timestamp from completion time. |
| `worker_id` | string | yes | 9Router worker identity. |
| `model` | string | yes | Resolved model name. |
| `provider` | string | yes | Provider used for the request. |
| `combo` | string | yes | Routing combo/config label. |
| `input_tokens` | integer string | yes | Non-negative integer encoded as Redis field string. |
| `output_tokens` | integer string | yes | Non-negative integer encoded as Redis field string. |
| `cost` | decimal string | yes | Exact decimal string, not binary float text where avoidable. |
| `latency_ms` | integer string | yes | Non-negative integer. |
| `status` | string | yes | Recommended enum: `success`, `error`, `cancelled`, `timeout`. |
| `error_class` | string | yes | Empty string or `none` for success; stable class for errors. |

Recommended additional fields:

| Field | Type | Why |
|---|---:|---|
| `schema_version` | string | Allows future migration; start with `1`. |
| `route_id` | string | Helps debug routing behavior. |
| `attempt` | integer string | Producer-side attempt count if retries happen before usage logging. |
| `metadata_hash` | string | Optional non-sensitive correlation without storing raw private data. |

Do not include secrets, prompts, responses, raw surveillance data, API keys, or intimate/personal content in the stream. Usage accounting should stay metadata-only.

## Producer Semantics

Each 9Router worker appends to `usage:events:v1` after request completion, even for failed requests when usage or latency accounting is meaningful.

Recommended producer behavior:

- Use Redis `XADD usage:events:v1 * field value ...`.
- Treat failed append as an observable accounting failure, not as success.
- Log a structured error with non-sensitive identifiers.
- Optionally use a bounded local emergency spool only if the system already has encrypted local durability and replay controls. Do not silently drop events.
- Use approximate stream trimming only after the consumer group is proven healthy and backlog retention is sized. Prefer retention by policy, not aggressive fixed length during initial rollout.

## Consumer Group Semantics

### Normal Read Path

The usage-writer reads new messages from the group with `XREADGROUP GROUP usage-writers <consumer> COUNT <batch_size> BLOCK <ms> STREAMS usage:events:v1 >`.

Recommended defaults:

- `COUNT`: 100 to 1000, tuned by SQLite write latency.
- `BLOCK`: 1000 to 5000 ms for steady service with low idle CPU.
- SQLite transaction size: match `COUNT`, with a max transaction duration target.

The `>` ID means the consumer asks for messages never delivered to any consumer in the group. Redis tracks delivered-but-unacknowledged messages in the group's pending entries list.

### ACK After DB Commit

Acknowledgement must happen **after** SQLite commit.

Required sequence:

1. Read a batch from the consumer group.
2. Validate and normalize fields.
3. Start SQLite transaction.
4. Upsert/insert events using `request_id` as an idempotency key.
5. Commit SQLite transaction.
6. `XACK usage:events:v1 usage-writers <ids...>` for only the committed messages.

Never acknowledge before commit. If the process dies after commit but before `XACK`, the event remains pending and may be retried. The SQLite write path must therefore be idempotent on `request_id`.

### Retry and Pending Semantics

Redis consumer groups maintain pending entries until `XACK`.

Required recovery loop:

- Monitor `XPENDING usage:events:v1 usage-writers` for total pending count, oldest pending ID, and consumers with pending work.
- Periodically use `XAUTOCLAIM usage:events:v1 usage-writers <consumer> <min-idle-ms> 0 COUNT <n>` to claim messages idle longer than the retry threshold.
- Reprocess claimed messages through the same SQLite idempotent transaction path.
- Acknowledge only after commit.

Suggested thresholds:

- `min-idle-ms`: 30,000 to 120,000 ms, depending on worst-case SQLite batch latency and restart behavior.
- `COUNT`: 100 to 500 for reclaim loops.
- Alert if pending count grows continuously, oldest idle age exceeds SLO, or one consumer owns most pending messages while inactive.

Poison event behavior:

- Add retry accounting outside Redis stream fields if possible, or track delivery count from pending metadata.
- After a configured retry ceiling, write the event to a SQLite dead-letter table or a separate Redis Stream such as `usage:events:deadletter:v1`.
- ACK poison messages only after the dead-letter write commits.
- Dead-letter entries must exclude secrets and raw payloads; include the original stream ID, request_id, validation error, and safe event fields.

## Backlog and Backpressure

The system needs explicit thresholds for stream length, pending count, consumer lag, and SQLite write latency.

Recommended behavior:

| Condition | Signal | Action |
|---|---|---|
| Normal | Stream length and pending count stable | Continue batch writes. |
| Writer slow | Pending count and oldest idle age rising | Increase writer concurrency only if SQLite can safely support it; otherwise reduce producer pressure. |
| SQLite locked/slow | Transaction latency exceeds SLO | Back off writer reads, preserve pending entries, alert. |
| Redis backlog high | Stream length above warning threshold | Emit degraded health and reduce 9Router request concurrency if accounting is mandatory. |
| Redis near memory cap | Memory/backlog critical | Stop accepting new high-cost work or fail closed for accounting-critical paths. |

Backpressure recommendation:

- For usage accounting, prefer **fail-degraded with visible health** over silently losing usage events.
- If exact accounting is required for billing/cost control, fail closed when Redis cannot accept events after bounded retry.
- If accounting is best-effort for observability only, fail open but emit a durable audit/error metric for dropped events.

## Persistence Choice

Use Redis persistence because this stream buffers usage accounting events before SQLite durability.

Recommended Redis persistence:

- Enable AOF.
- Prefer `appendfsync everysec` for a practical balance: at most about one second of Redis write loss under abrupt host failure, with much better throughput than fsync-always.
- Optionally combine AOF with RDB snapshots for faster restarts/backups.
- Do not rely on RDB-only persistence for this write buffer if losing recent usage events is unacceptable, because snapshot intervals can lose more recent writes.

If usage accounting is billing-critical, consider stronger durability:

- `appendfsync always` only if load testing proves the latency cost is acceptable.
- Redis replica or managed Redis with persistence guarantees.
- Producer-side idempotency and reconciliation against provider request logs.

## SQLite Batch Transaction Design

SQLite should be treated as the final durable store for the usage event.

Required properties:

- Unique constraint on `request_id`.
- Insert or idempotent upsert so duplicate stream delivery cannot double-count.
- Store original Redis stream ID for audit/replay correlation.
- Single transaction per batch.
- Commit before `XACK`.
- Roll back the full transaction on validation or write failure unless the writer explicitly splits valid and invalid records into committed safe subsets.

Recommended table-level concepts:

- `request_id` unique primary/idempotency key.
- `stream_id` for Redis entry correlation.
- usage fields from the schema.
- `ingested_at` writer timestamp.
- `writer_id` consumer name.

## Node.js Client Implications

If the 9Router source or writer is Node.js:

- Use the official Redis Node client (`redis` / node-redis) and its command methods for `XADD`, `XGROUP CREATE`, `XREADGROUP`, `XACK`, `XPENDING`, and `XAUTOCLAIM`.
- Redis command replies for stream reads are nested arrays/objects depending on client options; normalize them behind a small parser before validation.
- Redis field values are strings. Parse integer and decimal fields explicitly and reject invalid values before SQLite commit.
- Use one long-lived Redis client per process role; avoid opening a client per request.
- Use blocking reads in the dedicated writer, not in request-path workers.
- Handle reconnects explicitly. After reconnect, resume group reads and pending recovery; do not assume in-flight unacked messages were lost.
- Avoid JavaScript floating point for exact `cost` math when precision matters. Store cost as a decimal string or integer micros/nanos.
- For graceful shutdown, stop reading new batches, finish or roll back the active SQLite transaction, `XACK` committed IDs, then close Redis and SQLite handles.

## Operational Metrics

Minimum metrics:

- Producer `XADD` success/failure count.
- Stream length.
- Consumer group lag/backlog.
- Pending count and oldest pending idle age.
- Batch size, transaction latency, commit failures.
- `XACK` success/failure count.
- Reclaimed message count.
- Dead-letter count.
- Duplicate/idempotent replay count.

Minimum alerts:

- Redis unavailable to producers.
- Usage-writer down.
- Pending oldest idle age above threshold.
- Backlog growth sustained over threshold.
- SQLite commit failures.
- Dead-letter count above zero for sustained period.
- AOF disabled or persistence misconfigured in environments where loss is unacceptable.

## Final Recommendation

Implement P26.1 with Redis Streams and a single dedicated `usage-writer` consumer group. The correctness hinge is simple and strict: **commit SQLite first, then `XACK`**. Make SQLite idempotent on `request_id`, reclaim idle pending entries with `XAUTOCLAIM`, monitor backlog aggressively, and enable AOF persistence so Redis behaves like a bounded durable write buffer rather than a best-effort queue.

