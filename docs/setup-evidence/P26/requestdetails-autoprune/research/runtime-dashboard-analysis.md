# P26 requestDetails Autoprune Runtime Dashboard Analysis

| Field | Value |
|---|---|
| Date | 2026-06-27 |
| Workspace | `C:\Users\faizz\guinevere` |
| SSH target | `root@49.12.82.34 -p 39999` |
| Runtime host | `ninerouter-vps` |
| Runtime timezone evidence | `2026-06-27T19:22:19+07:00` |
| Scope | Read-only runtime research for 9Router requestDetails autoprune |
| Output path | `docs/setup-evidence/P26/requestdetails-autoprune/research/runtime-dashboard-analysis.md` |
| Safety | No mutation, no restart, no env dump, no endpoint payload/body printed |

## 1. Executive Verdict

PASS for read-only runtime research.

The current 9Router runtime is online with exactly two PM2 cluster workers. The canonical app health endpoint is healthy and fast at `/api/health`. Dashboard and usage UI routes are reachable but redirect to `/login` without session auth; usage API routes return `401 Unauthorized` without printing payloads. The live SQLite database is large (`920M`) and `requestDetails` is capped at `1000` rows in current runtime state, with `498` streaming placeholder rows and `746` zero-token rows in the retained window.

Pruning `requestDetails` should not affect routing, model/provider selection, or API request forwarding if it only deletes from the `requestDetails` observability table. Routing depends on provider/key/combo/config tables and runtime provider selection, while `requestDetails` is a dashboard/observability table read by `/api/usage/request-details`. The main operational risk is dashboard detail/history loss and possible SQLite write-lock or WAL/freelist behavior during prune, not routing behavior.

## 2. Read-Only Runtime Commands Used

All commands were read-only and avoided printing secrets, raw request payloads, response bodies, environment values, tokens, provider account data, or API keys.

```bash
ssh -p 39999 -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@49.12.82.34 'hostname; date -Is; pm2 status --no-color; pm2 pid 9router'
```

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'ss -ltnp 2>/dev/null | awk "NR==1 || /:20128|node|PM2/"'
```

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'curl -sS -o /dev/null -w "%{http_code} %{time_total}s %{size_download}B %{url_effective}\n" --max-time 20 http://127.0.0.1:20128/api/health'
```

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'sqlite3 -readonly /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM requestDetails;"'
```

## 3. PM2 Runtime State

`pm2 status --no-color` showed exactly two online `9router` application rows:

| PM2 id | Name | Version | Mode | PID | Uptime | Restarts | Status | CPU | Memory |
|---|---|---:|---|---:|---|---:|---|---:|---:|
| 0 | `9router` | `0.5.8` | cluster | `43086` | `58m` | 5 | online | 0% | 281.2 MB |
| 1 | `9router` | `0.5.8` | cluster | `43093` | `58m` | 5 | online | 0% | 234.8 MB |

`pm2 pid 9router` returned:

```text
43086
43093
```

Listener evidence:

| Port | Listener |
|---:|---|
| 20128 | `0.0.0.0:20128`, owned by PM2 god process |

Interpretation: The runtime currently satisfies the requested "PM2 2 workers" condition. Both workers are online, clustered, and using modest memory at the time of probe.

## 4. Endpoint Health and Route Timing

No endpoint bodies were printed. Timings are from `curl -o /dev/null -w`.

### 4.1 Public/Internal Health and Core APIs

| Route | HTTP | Time | Download Size | Interpretation |
|---|---:|---:|---:|---|
| `/api/health` | 200 | 0.008076s | 11 B | Canonical app health endpoint healthy |
| `/api/auth/status` | 200 | 0.007584s | 228 B | Auth status endpoint reachable |
| `/api/version` | 200 | 0.072175s | 68 B | Version endpoint reachable |
| `/api/v1/models` | 200 | 0.030654s | 3041 B | OpenAI-compatible model listing reachable |

### 4.2 Dashboard and Usage Routes Without Auth Session

| Route | HTTP | Time | Download Size | Interpretation |
|---|---:|---:|---:|---|
| `/` | 307 | 0.003674s | 10 B | Redirects to dashboard/login flow |
| `/health` | 404 | 0.007959s | 9706 B | Not the canonical health route |
| `/dashboard` | 307 | 0.003705s | 6 B | Redirects to `/login` |
| `/dashboard/usage` | 307 | 0.003495s | 6 B | Redirects to `/login` |
| `/dashboard/usage?tab=details` | 307 | 0.003035s | 6 B | Redirects to `/login` |
| `/api/usage/stats` | 401 | 0.003616s | 24 B | Auth-gated |
| `/api/usage/history` | 401 | 0.005878s | 24 B | Auth-gated |
| `/api/usage/request-details?page=1&pageSize=10` | 401 | 0.003405s | 24 B | Auth-gated |

Header-only checks confirmed:

| Route | Header Evidence |
|---|---|
| `/dashboard` | `HTTP/1.1 307 Temporary Redirect`, `location: /login` |
| `/dashboard/usage` | `HTTP/1.1 307 Temporary Redirect`, `location: /login` |
| `/api/usage/request-details?page=1&pageSize=10` | `HTTP/1.1 401 Unauthorized`, `content-type: application/json` |

Interpretation: Dashboard and usage route machinery is responsive. The observed non-200 statuses are expected auth behavior, not a route timing or runtime availability failure. Authenticated UI timing was not measured because the task prohibited secret/payload printing and did not provide a safe auth session/cookie.

## 5. Route Inventory

Read-only build inventory found these relevant routes:

| Route File | Meaning |
|---|---|
| `/api/health/route.js` | Canonical health route |
| `/api/auth/status/route.js` | Auth status route |
| `/api/usage/stats/route.js` | Usage stats API |
| `/api/usage/history/route.js` | Usage history API |
| `/api/usage/request-details/route.js` | requestDetails API |
| `/api/usage/request-logs/route.js` | request log API |
| `/api/usage/stream/route.js` | usage stream API |
| `/(dashboard)/dashboard/usage/page.js` | Usage dashboard page |
| `/(dashboard)/dashboard/page.js` | Dashboard page |
| `/login/page.js` | Login page |

## 6. Live SQLite State

SQLite candidate files:

| File | Size |
|---|---:|
| `/var/lib/9router/db/data.sqlite` | 963,706,880 bytes (`920M`) |
| `/var/lib/9router/db/backups/upgrade-0.5.4-to-0.5.8-0.5.8-20260626-172853/data.sqlite` | 274,432 bytes |

Live DB selected for read-only analysis:

```text
/var/lib/9router/db/data.sqlite
```

Schema inventory confirmed these tables:

```text
requestDetails
usageDaily
usageHistory
```

Table counts and time window:

| Metric | Value |
|---|---:|
| `requestDetails_count` | 1000 |
| `usageHistory_count` | 5957 |
| `usageDaily_count` | 2 |
| `oldest_requestDetails` | `2026-06-27T10:15:35.459Z` |
| `newest_requestDetails` | `2026-06-27T12:22:47.941Z` |
| `zero_token_requestDetails` | 746 |
| `placeholder_rows` | 498 |
| `status=success` rows in requestDetails | 1000 |
| `recent_hour_requestDetails` | 1000 |
| `recent_hour_usageHistory` | 4775 |

Database page stats:

| PRAGMA | Value |
|---|---:|
| `page_count` | 235280 |
| `page_size` | 4096 |
| `freelist_count` | 79862 |

Interpretation:

- The retained `requestDetails` window is full at `1000` rows.
- The DB file is much larger than the logical requestDetails cap implies, likely because historical writes and SQLite page freelist/WAL behavior leave file size high until vacuum/compaction. Vacuum would be a mutation and was not performed.
- `498` placeholder rows indicate the streaming placeholder pattern is materially present in the live retained window.
- `746` zero-token rows means the details table has a high share of observability rows that are low diagnostic value for token accounting.

## 7. requestDetails Schema and Indexes

`PRAGMA table_info(requestDetails)`:

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT | Primary key |
| `timestamp` | TEXT | Required |
| `provider` | TEXT | Indexed |
| `model` | TEXT | Indexed |
| `connectionId` | TEXT | Indexed |
| `status` | TEXT | Status field |
| `data` | TEXT | Full JSON detail blob |

`PRAGMA index_list(requestDetails)`:

| Index | Type |
|---|---|
| `idx_rd_conn` | connectionId |
| `idx_rd_model` | model |
| `idx_rd_provider` | provider |
| `idx_rd_ts` | timestamp DESC |
| `sqlite_autoindex_requestDetails_1` | primary key |

`usageHistory` has separate normalized token columns: `promptTokens`, `completionTokens`, `cost`, `tokens`, and `meta`.

Interpretation: `requestDetails` is structurally isolated from `usageHistory` and `usageDaily`. Pruning details rows should remove dashboard detail records only; it should not remove normalized usage totals/history unless the prune also touches other tables.

## 8. Current Build and Config Hints

Runtime package version:

```text
standalone_package_version=0.5.8
```

Local ecosystem config in this workspace matches the observed two-worker deployment pattern:

```text
name: 9router
script: custom-server.js
cwd: /root/9router/.next/standalone
exec_mode: cluster
instances: 2
PORT: 20128
HOSTNAME: 0.0.0.0
```

Build string search confirmed the current schema has `requestDetails`, `usageHistory`, and `usageDaily` as separate SQLite tables. The route inventory confirms `/api/usage/request-details` exists as a dedicated usage-detail API.

## 9. Should requestDetails Pruning Affect Routing?

Verdict: It should not affect routing if implemented as a narrow prune of only `requestDetails`.

Reasoning:

1. Routing/forwarding lives on the OpenAI-compatible API routes such as `/api/v1/chat/completions`, `/api/v1/models`, `/api/v1/responses`, and provider/combo/model configuration.
2. `requestDetails` is an observability/dashboard detail table with a full JSON blob per request.
3. `usageHistory` and `usageDaily` are separate accounting surfaces for normalized usage history and aggregates.
4. Dashboard usage detail API reads `requestDetails`; model/provider routing should not read it for provider selection.
5. The live `/api/v1/models` endpoint returned 200 while usage detail API remained auth-gated, supporting separation between runtime API routing and dashboard usage details.

Routing impact would become possible only if a prune implementation:

- Locks the SQLite database long enough to stall writes/readers under load.
- Accidentally deletes from `usageHistory`, `usageDaily`, `providerConnections`, `providerNodes`, `combos`, `apiKeys`, `settings`, or `kv`.
- Runs `VACUUM` or schema changes during live high-traffic windows without a maintenance gate.
- Performs broad file replacement or DB restore instead of targeted SQL deletes.

## 10. Autoprune Implications

Current state already shows `requestDetails_count=1000`, so 9Router 0.5.8 appears to have a higher cap than older research that cited `200` max records. However, the database file remains `920M`, and the freelist count is high. Therefore:

- Lowering the retained row count may reduce future query scan/render payload size for `/api/usage/request-details`.
- Deleting rows alone may not immediately shrink `data.sqlite`; SQLite file compaction requires `VACUUM` or equivalent, which is a mutation and should be separately approved/gated.
- Pruning placeholder rows specifically would improve dashboard signal because placeholders are nearly half of the retained window.
- If the dashboard relies on newest `requestDetails` rows for the details tab, pruning oldest rows by timestamp should be safe for current UI behavior.
- A high-frequency autoprune loop must avoid competing with the app's normal write path.

## 11. Risks

| Risk | Severity | Notes | Mitigation |
|---|---|---|---|
| SQLite write lock during prune | Medium | Live app writes usage and request details under traffic | Use small batches, indexed `timestamp` predicates, short transactions |
| Accidental cross-table deletion | High | Would affect usage history, aggregates, or routing config | Hard-code table allowlist to `requestDetails`; dry-run count first |
| File size not shrinking after delete | Medium | Operators may expect disk to drop immediately | Document SQLite freelist behavior; defer `VACUUM` to approved maintenance |
| Dashboard detail loss | Low/Medium | Old request payload/response debug records disappear | Retain enough latest rows; optionally export redacted aggregate counts only |
| Placeholder-only prune hides stream diagnostics | Low | Placeholder rows reveal stream starts/aborts | Prefer age/count-based prune first; placeholder pruning can be optional |
| Authenticated dashboard timing unmeasured | Low | Routes were only probed unauthenticated | Use browser/session-safe auth probe later without printing cookies or payloads |

## 12. Recommended Verification Commands

These commands are read-only unless explicitly marked otherwise.

### 12.1 Before Any Prune

```bash
ssh -p 39999 root@49.12.82.34 'pm2 status --no-color; pm2 pid 9router'
```

```bash
ssh -p 39999 root@49.12.82.34 'curl -sS -o /dev/null -w "%{http_code} %{time_total}s %{size_download}B\n" --max-time 20 http://127.0.0.1:20128/api/health'
```

```bash
ssh -p 39999 root@49.12.82.34 'sqlite3 -readonly /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM requestDetails; SELECT COUNT(*) FROM usageHistory; SELECT COUNT(*) FROM usageDaily;"'
```

```bash
ssh -p 39999 root@49.12.82.34 'sqlite3 -readonly /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM requestDetails WHERE COALESCE(json_extract(data,''$.tokens.prompt_tokens''),0)=0 AND COALESCE(json_extract(data,''$.tokens.completion_tokens''),0)=0;"'
```

### 12.2 Dashboard/API Timing Smoke

```bash
ssh -p 39999 root@49.12.82.34 'for u in /api/health /api/auth/status /api/version /api/v1/models /dashboard /dashboard/usage /api/usage/request-details?page=1\\&pageSize=10; do curl -sS -o /dev/null -w "%{http_code} %{time_total}s %{size_download}B $u\n" --max-time 20 "http://127.0.0.1:20128$u"; done'
```

Expected unauthenticated statuses from current runtime:

| Route | Expected |
|---|---:|
| `/api/health` | 200 |
| `/api/auth/status` | 200 |
| `/api/version` | 200 |
| `/api/v1/models` | 200 |
| `/dashboard` | 307 |
| `/dashboard/usage` | 307 |
| `/api/usage/request-details?page=1&pageSize=10` | 401 |

### 12.3 After a Future Prune

```bash
ssh -p 39999 root@49.12.82.34 'sqlite3 -readonly /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM requestDetails; SELECT MIN(timestamp), MAX(timestamp) FROM requestDetails; SELECT COUNT(*) FROM usageHistory; SELECT COUNT(*) FROM usageDaily;"'
```

```bash
ssh -p 39999 root@49.12.82.34 'du -h /var/lib/9router/db/data.sqlite; sqlite3 -readonly /var/lib/9router/db/data.sqlite "PRAGMA page_count; PRAGMA page_size; PRAGMA freelist_count;"'
```

```bash
ssh -p 39999 root@49.12.82.34 'pm2 status --no-color; curl -sS -o /dev/null -w "%{http_code} %{time_total}s\n" --max-time 20 http://127.0.0.1:20128/api/health; curl -sS -o /dev/null -w "%{http_code} %{time_total}s\n" --max-time 20 http://127.0.0.1:20128/api/v1/models'
```

## 13. Evidence Summary

| Check | Result |
|---|---|
| `AGENTS.md` read first | PASS |
| SSH target used read-only | PASS |
| PM2 has exactly two 9Router workers | PASS |
| No restart/mutation performed | PASS |
| `/api/health` healthy | PASS |
| Dashboard route timing checked | PASS, auth redirect |
| Usage route timing checked | PASS, auth redirect/API 401 |
| DB/table state checked read-only | PASS |
| Secrets/payloads avoided | PASS |
| requestDetails pruning routing impact assessed | PASS |

## 14. Caveats

Authenticated dashboard render timing was not measured because no safe authenticated browser/session context was supplied, and the research avoided printing cookies, tokens, payloads, or response bodies. The unauthenticated redirect/API timings still prove route responsiveness and auth-gating behavior.

No prune, vacuum, checkpoint, restart, deploy, config edit, or database mutation was performed.

## 15. Footer

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-06-27 | Guinevere runtime research | Initial read-only runtime analysis for P26 requestDetails autoprune. |
