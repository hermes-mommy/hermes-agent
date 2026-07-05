# P26.1 Research Synthesis

Date: 2026-06-28

## Verdict

Implement the write buffer with **Redis Streams** and keep **SQLite** as the final durable sink for 9Router accounting.

This is the smallest safe change that reduces SQLite lock pressure on the request path without moving the whole product off its current storage model.

## Exact Write Path Today

The hot write path is:

`open-sse/handlers/chatCore/requestDetail.js -> saveUsageStats(...) -> src/lib/db/repos/usageRepo.js:saveRequestUsage(...) -> SQLite transaction`

The request path currently does all of the following on usage completion:

- normalizes token counts
- calculates cost
- writes `usageHistory`
- updates `usageDaily`
- increments `_meta.totalRequestsLifetime`
- pushes a recent ring entry for in-memory dashboard state

That is the write path we want to offload.

## Exact Tables Involved

- `usageHistory`
- `usageDaily`
- `_meta`
- `requestDetails` stays on the existing buffered SQLite path for now

`requestDetails` is already buffered in memory and is the large payload surface. It is not the first phase target for Redis stream offload because the payload is large and sensitive.

## Redis Stream Design

### Stream

- Stream key: `9router:usage_events:v1`
- Dead-letter stream: `9router:usage_events:deadletter:v1`
- Consumer group: `usage-writers`
- Consumer name: stable per writer process, for example `usage-writer-${hostname}-${pid}`

### Event schema

Required fields:

- `request_id`
- `timestamp`
- `worker_id`
- `model`
- `provider`
- `combo`
- `input_tokens`
- `output_tokens`
- `cost`
- `latency_ms`
- `status`
- `error_class`

Recommended additional safe fields:

- `endpoint`
- `connection_id`
- `schema_version`
- `api_key_fp` instead of raw apiKey

### Security handling

- Raw API keys never enter Redis.
- If the app has an apiKey value, convert it to a one-way fingerprint before enqueue.
- Raw request bodies, response bodies, prompts, and provider payloads stay out of the stream.

### Semantics

- Producers call `XADD` only.
- The dedicated writer uses `XREADGROUP`.
- The writer commits SQLite first, then `XACK`.
- `XAUTOCLAIM` handles recovery for pending entries.
- Duplicate delivery is safe because SQLite uses `request_id` idempotency.

## SQLite Schema Changes

Additive changes only:

- `usageHistory.requestId TEXT`
- `usageHistory.streamId TEXT`
- `usageHistory.workerId TEXT`
- `usageHistory.combo TEXT`
- `usageHistory.latencyMs INTEGER DEFAULT 0`
- `usageHistory.errorClass TEXT`

Add an index or unique index on `requestId` so replay does not double count.

## Redis vs Postgres

Keep SQLite.

Reasoning:

- the production runtime already uses SQLite
- the goal is lock reduction, not a storage migration
- Redis is a buffer, not the final business datastore
- switching the sink to Postgres would widen the blast radius and make rollback harder

## Recommended Implementation Path

1. Add a shared usage-buffer module with Redis producer helpers and SQLite batch-write helpers.
2. Change `saveRequestUsage(...)` into a buffered producer with a direct SQLite fallback only when Redis is unavailable.
3. Extend request completion code so error events are emitted too, with `status` and `error_class`.
4. Run a dedicated writer service on the 9Router VPS that drains `9router:usage_events:v1` into SQLite in batches.
5. Add a small health/backlog view to the usage dashboard so buffer state is visible.
6. Keep the existing `requestDetails` buffered path intact for this phase.

## Risk Matrix

| Risk | Impact | Mitigation |
|---|---|---|
| Redis unavailable | Producer cannot enqueue | Fail over to direct SQLite write and log degraded mode |
| Writer down | Backlog grows | Requests still succeed; writer resumes and drains backlog |
| Duplicate delivery | Double counting | `request_id` unique idempotency on SQLite insert |
| Pending entries stuck | Replay lag | `XAUTOCLAIM` with idle threshold and retry ceiling |
| Stream memory growth | Redis memory pressure | AOF plus bounded trimming after healthy batches |
| API key exposure | Secret leakage | Store only a fingerprint in Redis and SQLite |
| Dashboard stale | Confusing UI | Add buffer health and backlog fields to stats payload |
| Live schema drift | Runtime errors | Additive schema sync on startup and verification before canary |

## Rollback Plan

Rollback order:

1. Disable the buffer feature flag.
2. Stop the writer service.
3. Stop Redis.
4. Leave the existing SQLite fallback in place.
5. If schema changes cause trouble, keep the additive columns and rollback code only.

The rollback goal is to restore the prior direct SQLite behavior without disturbing PM2 worker count, firewall rules, or Tailscale.

## Acceptance Criteria

- PM2 still shows exactly 2 `9router` workers.
- Public IPv4 `:20128` remains blocked.
- Tailscale access still works.
- Redis is loopback-only.
- Usage events are visible in Redis and acknowledged by the writer.
- SQLite receives rows in batch from the writer.
- Writer crash does not break requests.
- Backlog drains after writer recovery.
- SQLite integrity remains `ok`.
- No secret material appears in Redis payloads or evidence.
- Dashboard shows buffer health or backlog state.

## Footer

This synthesis chooses the minimal safe offload: Redis Streams for usage events, SQLite as the sink, and `requestDetails` left on its existing buffered path for this phase.
