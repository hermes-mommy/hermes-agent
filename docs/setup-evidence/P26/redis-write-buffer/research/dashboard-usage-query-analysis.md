# P26.1 Dashboard Usage Query Analysis

| Field | Value |
|---|---|
| Task | P26.1 dashboard performance researcher |
| Repository | `C:\Users\faizz\guinevere` |
| Production target | `root@49.12.82.34 -p 39999` |
| Runtime app | 9Router on port `20128` |
| Runtime package evidence | `9router` PM2 app, compiled standalone build under `/root/9router/.next/standalone` |
| Scope | Read-only dashboard endpoint/file/query research |
| Output | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\research\dashboard-usage-query-analysis.md` |
| Secret handling | No environment dumps, DB payload bodies, cookies, auth headers, provider secrets, or request/response bodies printed |

## 1. Executive Verdict

PASS for read-only dashboard usage query research.

The 9Router dashboard usage surfaces are backed by three SQLite observability/accounting tables:

- `usageHistory`: per-request normalized token/cost rows.
- `usageDaily`: daily JSON rollups used for multi-day summaries.
- `requestDetails`: capped full request/response detail JSON used by the details dashboard.

Current live evidence shows `usageHistory_count=8583`, `usageDaily_count=3`, and `requestDetails_count=1000`. `requestDetails` is already capped by app settings/defaults, but the DB file remains large (`920M`, WAL `44M`) because historical large detail rows and SQLite freelist/WAL behavior persist after deletes. Usage dashboard API routes are auth-gated and fast when probed unauthenticated; dashboard page redirects to login as expected.

## 2. Summary/Cache Decision

### Needed now

No new Redis summary/cache is required immediately for the dashboard usage overview.

Reasons:

1. Multi-day overview already uses `usageDaily`, which is the built-in summary table.
2. The current live usage cardinality is small for indexed SQLite reads (`8583` `usageHistory` rows, `3` daily rows).
3. Request details are capped at `1000` rows, and details pagination uses indexed `timestamp DESC`.
4. Unauthenticated route timing is fast, so there is no current route-level symptom proving dashboard query latency needs a cache.

### Needed later

Add a Redis or SQLite materialized summary later if any of these become true:

- `usageHistory` grows into hundreds of thousands or millions of rows due to retention expansion.
- Authenticated `/api/usage/stats`, `/api/usage/chart`, or `/api/usage/providers` exceeds an agreed SLO under real dashboard load.
- Dashboard is polled frequently by multiple clients and repeats the same time-window scans.
- `usageDaily` is no longer enough because the UI needs high-cardinality provider/account/model breakdowns across long windows.

### More urgent than summary/cache

The more immediate performance concern is not summary computation. It is heavy `requestDetails.data` payload storage and SQLite file/WAL growth:

- `requestDetails` stores large JSON detail blobs.
- Current retained `requestDetails` is capped at `1000`, but the DB file is still `920M`.
- Continue/complete `requestDetails` prune/compaction planning separately; do not solve that with usage-summary caching.

## 3. Dashboard Endpoint Inventory

Remote route inventory command:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "cd /root/9router/.next/standalone && find .next/server/app -path '*usage*' -o -path '*health*' -o -path '*dashboard*' | sed 's#^#/#' | head -200"
```

Relevant route files found:

| Route/File | Purpose |
|---|---|
| `/api/health/route.js` | Canonical health endpoint |
| `/api/usage/stats/route.js` | Usage overview stats API |
| `/api/usage/chart/route.js` | Usage chart API |
| `/api/usage/providers/route.js` | Provider usage breakdown API |
| `/api/usage/history/route.js` | Recent usage history API |
| `/api/usage/logs/route.js` | Usage log API |
| `/api/usage/request-logs/route.js` | Text-style request log API |
| `/api/usage/request-details/route.js` | Paginated full request details API |
| `/api/usage/stream/route.js` | Server-sent usage update stream |
| `/api/usage/[connectionId]/route.js` | Per-connection usage API |
| `/api/usage/[connectionId]/codex-reset-credits/route.js` | Per-connection Codex credit reset API |
| `/dashboard/usage/page.js` | Dashboard usage UI page |
| `/dashboard/page.js` | Main dashboard page |
| `/dashboard/providers/page.js` | Provider dashboard page |
| `/dashboard/providers/[id]/page.js` | Provider detail page |

## 4. Runtime Timing Evidence

Commands used:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "curl -sS -o /dev/null -w '/api/health %{http_code} %{time_total}s %{size_download}B\n' --max-time 15 http://127.0.0.1:20128/api/health"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "curl -sS -o /dev/null -w '/api/usage/stats %{http_code} %{time_total}s %{size_download}B\n' --max-time 15 http://127.0.0.1:20128/api/usage/stats"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "curl -sS -o /dev/null -w '/api/usage/chart %{http_code} %{time_total}s %{size_download}B\n' --max-time 15 http://127.0.0.1:20128/api/usage/chart"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "curl -sS -o /dev/null -w '/api/usage/providers %{http_code} %{time_total}s %{size_download}B\n' --max-time 15 http://127.0.0.1:20128/api/usage/providers"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "curl -sS -o /dev/null -w '/api/usage/request-details %{http_code} %{time_total}s %{size_download}B\n' --max-time 15 'http://127.0.0.1:20128/api/usage/request-details?page=1&pageSize=10'"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "curl -sS -o /dev/null -w '/dashboard/usage %{http_code} %{time_total}s %{size_download}B\n' --max-time 15 http://127.0.0.1:20128/dashboard/usage"
```

Evidence:

```text
/api/health 200 0.005479s 11B
/api/usage/stats 401 0.004074s 24B
/api/usage/chart 401 0.004614s 24B
/api/usage/providers 401 0.003192s 24B
/api/usage/request-details 401 0.003582s 24B
/dashboard/usage 307 0.003609s 6B
```

Interpretation:

- `/api/health` is healthy.
- Usage APIs are auth-gated and respond quickly with 401 when unauthenticated.
- `/dashboard/usage` redirects quickly to login without a session.
- Authenticated dashboard query timing was not measured because no safe browser/session cookie was supplied and the task prohibited secret exposure.

## 5. SQLite Schema Evidence

Commands used:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "sqlite3 -readonly /var/lib/9router/db/data.sqlite '.schema usageHistory'"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "sqlite3 -readonly /var/lib/9router/db/data.sqlite '.schema usageDaily'"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "sqlite3 -readonly /var/lib/9router/db/data.sqlite '.schema requestDetails'"
```

Schema evidence:

```sql
CREATE TABLE usageHistory (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, provider TEXT, model TEXT, connectionId TEXT, apiKey TEXT, endpoint TEXT, promptTokens INTEGER DEFAULT 0, completionTokens INTEGER DEFAULT 0, cost REAL DEFAULT 0, status TEXT, tokens TEXT, meta TEXT);
CREATE INDEX idx_uh_ts ON usageHistory(timestamp DESC);
CREATE INDEX idx_uh_provider ON usageHistory(provider);
CREATE INDEX idx_uh_model ON usageHistory(model);
CREATE INDEX idx_uh_conn ON usageHistory(connectionId);
```

```sql
CREATE TABLE usageDaily (dateKey TEXT PRIMARY KEY, data TEXT NOT NULL);
```

```sql
CREATE TABLE requestDetails (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, provider TEXT, model TEXT, connectionId TEXT, status TEXT, data TEXT NOT NULL);
CREATE INDEX idx_rd_ts ON requestDetails(timestamp DESC);
CREATE INDEX idx_rd_provider ON requestDetails(provider);
CREATE INDEX idx_rd_model ON requestDetails(model);
CREATE INDEX idx_rd_conn ON requestDetails(connectionId);
```

## 6. Current DB Volume Evidence

Commands used:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "sqlite3 -readonly -cmd '.timer on' /var/lib/9router/db/data.sqlite 'SELECT COUNT(*) AS usageHistory_count FROM usageHistory; SELECT COUNT(*) AS usageDaily_count FROM usageDaily; SELECT COUNT(*) AS requestDetails_count FROM requestDetails; SELECT MIN(timestamp), MAX(timestamp) FROM usageHistory; SELECT MIN(timestamp), MAX(timestamp) FROM requestDetails;'"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "du -h /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite-wal /var/lib/9router/db/data.sqlite-shm 2>/dev/null"
```

Evidence:

```text
8583
3
1000
2026-06-26T10:37:57.081Z|2026-06-27T17:18:24.866Z
2026-06-27T16:32:35.638Z|2026-06-27T17:18:24.866Z
```

```text
920M /var/lib/9router/db/data.sqlite
44M  /var/lib/9router/db/data.sqlite-wal
96K  /var/lib/9router/db/data.sqlite-shm
```

Interpretation:

- `usageHistory` has a modest live row count.
- `usageDaily` already stores aggregated summary rows.
- `requestDetails` is at the configured/default cap of `1000`.
- Large DB size is disproportionate to current row counts, consistent with earlier P26 evidence that large historical `requestDetails.data` pages/freelist/WAL dominate storage.

## 7. Compiled Query Path Evidence

Command used:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "cd /root/9router/.next/standalone && grep -RIn --include='*.js' 'FROM usageHistory' .next/server/chunks .next/server/app/api/usage 2>/dev/null | head -80"
```

Important sanitized snippets from `.next/server/chunks/4884.js`:

```text
SELECT timestamp, provider, model, connectionId, apiKey, endpoint, cost, status, tokens
FROM usageHistory ORDER BY id DESC LIMIT ?
```

```text
SELECT timestamp, provider, model, tokens, status
FROM usageHistory ORDER BY id DESC LIMIT 100
```

```text
SELECT timestamp, promptTokens, completionTokens, cost
FROM usageHistory WHERE timestamp >= ? AND timestamp <= ?
```

```text
SELECT timestamp, provider, model, connectionId, apiKey, endpoint
FROM usageHistory WHERE timestamp >= ?
```

```text
SELECT timestamp, provider, model, connectionId, apiKey, endpoint, promptTokens, completionTokens, cost, tokens
FROM usageHistory WHERE timestamp >= ?
```

```text
SELECT timestamp, provider, model, connectionId, promptTokens, completionTokens, status, tokens
FROM usageHistory ORDER BY id DESC LIMIT ?
```

Request details query evidence:

```text
SELECT COUNT(*) as c FROM requestDetails ...
SELECT data FROM requestDetails ... ORDER BY timestamp DESC LIMIT ? OFFSET ?
```

Request details write/cap evidence:

```text
INSERT INTO requestDetails(...) VALUES(...) ON CONFLICT(id) DO UPDATE SET ...
SELECT COUNT(*) as c FROM requestDetails
DELETE FROM requestDetails WHERE id IN (SELECT id FROM requestDetails ORDER BY timestamp ASC LIMIT ?)
```

Daily summary query evidence:

```text
SELECT data FROM usageDaily WHERE dateKey = ?
INSERT INTO usageDaily(dateKey, data) VALUES(?, ?) ON CONFLICT(dateKey) DO UPDATE SET data = excluded.data
SELECT dateKey, data FROM usageDaily
SELECT dateKey, data FROM usageDaily WHERE dateKey >= ?
```

Provider/account metadata joins:

```text
getProviderConnections()
getProviderNodes()
getApiKeys()
```

The compiled stats path maps connection IDs, provider node IDs, and API keys to display labels. Secret values were not queried or printed.

## 8. Usage Stats Surface

Primary files:

| File | Role |
|---|---|
| `/root/9router/.next/standalone/.next/server/app/api/usage/stats/route.js` | Route entry for usage stats |
| `/root/9router/.next/standalone/.next/server/app/api/usage/chart/route.js` | Route entry for chart data |
| `/root/9router/.next/standalone/.next/server/app/api/usage/providers/route.js` | Route entry for provider breakdown |
| `/root/9router/.next/standalone/.next/server/chunks/4884.js` | Compiled usage repository and dashboard aggregation logic |
| `/root/9router/.next/standalone/.next/server/app/(dashboard)/dashboard/usage/page.js` | Usage dashboard page |

Main query behavior:

- Recent requests: `usageHistory ORDER BY id DESC LIMIT 100`, filtered to hide rows with both prompt and completion tokens equal to zero.
- Last 10 minutes: `usageHistory WHERE timestamp >= ? AND timestamp <= ?`, grouped in app memory by minute.
- Today/24h: direct scan of `usageHistory WHERE timestamp >= ?`.
- 7d/30d/60d/all: mostly `usageDaily`, plus some `usageHistory WHERE timestamp >= ?` passes to refresh `lastUsed` values for model/account/API-key/endpoint groups.
- Provider metrics: built from `usageDaily.byProvider` for multi-day windows or direct `usageHistory` rows for today/24h.

Performance read:

- Current `usageHistory` volume does not justify a new cache by itself.
- If retention grows, the `lastUsed` refresh scans over `usageHistory WHERE timestamp >= ?` are the first overview path likely to benefit from materialization.

## 9. Request Logs and Details Surface

Primary files:

| File | Role |
|---|---|
| `/root/9router/.next/standalone/.next/server/app/api/usage/request-details/route.js` | Paginated detail API |
| `/root/9router/.next/standalone/.next/server/app/api/usage/request-logs/route.js` | Text request log API |
| `/root/9router/.next/standalone/.next/server/app/api/usage/logs/route.js` | Usage logs API |
| `/root/9router/.next/standalone/.next/server/chunks/4884.js` | `getRequestDetails`, `getRecentLogs`, detail write buffer/cap |

Main query behavior:

- Details: count filtered `requestDetails`, then fetch `data` blobs ordered by newest timestamp.
- Filters supported by compiled query: provider, model, connectionId, status, startDate, endDate.
- Recent text logs: reads recent `usageHistory` rows, maps connection IDs to provider names, formats lines.

Performance read:

- `requestDetails` is capped at `1000`, but rows can be very large because `data` stores request/response/provider blobs.
- Pagination that fetches `data` can still be expensive because each selected row may contain a large JSON blob.
- For dashboard details, pruning/retention and payload truncation matter more than summary caching.

## 10. Provider Metrics Surface

Primary files:

| File | Role |
|---|---|
| `/root/9router/.next/standalone/.next/server/app/api/usage/providers/route.js` | Provider breakdown route |
| `/root/9router/.next/standalone/.next/server/app/dashboard/providers/page.js` | Provider dashboard UI |
| `/root/9router/.next/standalone/.next/server/chunks/4884.js` | Provider/account aggregation from usage data |

Relevant DB/config surfaces:

| Table/Source | Purpose |
|---|---|
| `usageHistory.provider` | Per-request provider label |
| `usageDaily.data.byProvider` | Pre-aggregated provider usage |
| `usageDaily.data.byModel` | Pre-aggregated model/provider breakdown |
| `usageDaily.data.byAccount` | Connection/account breakdown |
| `usageDaily.data.byApiKey` | API-key grouped usage display |
| `usageDaily.data.byEndpoint` | Endpoint grouped usage display |
| `providerConnections` | Maps connection ID to display name/email/id |
| `providerNodes` | Maps provider node ID to display name |
| `apiKeys` | Maps API-key identifiers to display labels |

Secret note: compiled code can read `apiKeys` and provider connection data for label mapping, but this research did not print those rows or values.

## 11. Backlog and Health Surfaces

### Health

Primary files:

| File | Role |
|---|---|
| `/root/9router/.next/standalone/.next/server/app/api/health/route.js` | Canonical app health |
| `/root/9router/.next/standalone/.next/server/app/dashboard/page.js` | Main dashboard page |

Evidence:

```text
/api/health 200 0.005479s 11B
```

### Backlog / active requests

No separate durable backlog table was identified for 9Router dashboard usage.

Compiled usage logic maintains in-process globals:

```text
global._pendingRequests
global._pendingTimers
global._recentRing
global._statsEmitter
```

Dashboard stats include:

- `pending`
- `activeRequests`
- `recentRequests`
- `errorProvider`

These are process-memory metrics, not durable SQLite backlog records. With PM2 cluster mode, each worker may hold its own in-memory pending state unless app-level aggregation exists elsewhere; no separate cross-worker backlog table was found in this research.

## 12. Cache/Buffer Implications for P26 Redis Write Buffer

This research supports a narrow Redis write-buffer plan for ingestion/write pressure, not a broad dashboard cache as the next move.

Recommended priority:

1. Keep `usageDaily` as the dashboard summary source for overview windows.
2. Use Redis buffering, if implemented, for write smoothing and flush safety around high request volume, not as a first dashboard read cache.
3. Keep `requestDetails` out of Redis unless storing only small metadata. Full detail payloads are too large and sensitive for casual cache replication.
4. If later adding a read cache, cache only sanitized aggregate objects: totals, byProvider, byModel, byEndpoint, last10Minutes. Avoid request payloads, provider responses, API keys, auth labels, or raw `requestDetails.data`.

Potential future cache keys:

```text
usage:summary:{window}
usage:chart:{window}
usage:providers:{window}
usage:last10m
```

Do not cache:

```text
requestDetails.data
providerConnections.data
apiKeys.key
auth cookies/tokens
raw request/response/provider payloads
```

## 13. Risks and Caveats

| Risk | Severity | Notes |
|---|---|---|
| Authenticated query latency unknown | Low/Medium | Current timing only proves route/auth responsiveness, not logged-in dashboard render cost |
| Large detail payloads | Medium | `requestDetails.data` can be large even with only 1000 rows retained |
| SQLite file size misconception | Medium | Deletes may not reduce `data.sqlite` without a gated compaction operation |
| Cross-worker pending state | Medium | PM2 cluster in-memory pending metrics may be per-worker unless externally aggregated |
| Secret exposure through careless debugging | High | Provider/API-key tables exist; future probes must avoid row payload dumps |

## 14. Commands Run

Local:

```powershell
Get-Content -Path AGENTS.md -Raw
rg --files
rg -n "dashboard|usage|request_logs|request log|provider|backlog|health|metrics" src tests docs\setup-evidence\P26 docs\setup-evidence\P25 docs\setup-evidence\P24 -g "*.py" -g "*.md" -g "*.sql" -g "*.yml" -g "*.yaml" -g "*.json"
rg --files | rg "(?i)(dashboard|9router|router|usage|metrics|health|backlog|provider|request)"
Get-Content -Path research-reports\9router-dashboard-details-trace.md -Raw
Get-Content -Path research-reports\9router-usage-persistence-audit.md -Raw
Get-Content -Path docs\setup-evidence\P26\requestdetails-autoprune\research\current-dashboard-db-ground-truth.md -Raw
Get-Content -Path docs\setup-evidence\P26\requestdetails-autoprune\research\runtime-dashboard-analysis.md -Raw
```

Remote read-only:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "cd /root/9router/.next/standalone && find .next/server/app -path '*usage*' -o -path '*health*' -o -path '*dashboard*' | sed 's#^#/#' | head -200"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "cd /root/9router/.next/standalone && grep -RIl --include='*.js' -E 'usageHistory|usageDaily|requestDetails|providerConnections|providerNodes|request-logs|request-details|api/health|queue|backlog|metrics' .next/server/app .next/server/chunks 2>/dev/null | sed 's#^#/#' | head -200"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "sqlite3 -readonly /var/lib/9router/db/data.sqlite '.schema usageHistory'"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "sqlite3 -readonly /var/lib/9router/db/data.sqlite '.schema usageDaily'"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "sqlite3 -readonly /var/lib/9router/db/data.sqlite '.schema requestDetails'"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "cd /root/9router/.next/standalone && grep -RIn --include='*.js' 'FROM usageHistory' .next/server/chunks .next/server/app/api/usage 2>/dev/null | head -80"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "cd /root/9router/.next/standalone && grep -RIn --include='*.js' 'FROM requestDetails' .next/server/chunks .next/server/app/api/usage 2>/dev/null | head -80"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "cd /root/9router/.next/standalone && grep -RIn --include='*.js' 'usageDaily' .next/server/chunks .next/server/app/api/usage 2>/dev/null | head -80"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "cd /root/9router/.next/standalone && grep -RIn --include='*.js' 'providerConnections' .next/server/chunks .next/server/app/api/usage .next/server/app/api/health 2>/dev/null | head -80"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "sqlite3 -readonly -cmd '.timer on' /var/lib/9router/db/data.sqlite 'SELECT COUNT(*) AS usageHistory_count FROM usageHistory; SELECT COUNT(*) AS usageDaily_count FROM usageDaily; SELECT COUNT(*) AS requestDetails_count FROM requestDetails; SELECT MIN(timestamp), MAX(timestamp) FROM usageHistory; SELECT MIN(timestamp), MAX(timestamp) FROM requestDetails;'"
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "du -h /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite-wal /var/lib/9router/db/data.sqlite-shm 2>/dev/null"
```

Failed/non-material commands:

- Some nested PowerShell/SSH/SQLite quote attempts failed before producing useful output.
- No mutation occurred from those failures.
- The final evidence above uses successful read-only commands.

## 15. Boundary Compliance

- No modifications except this markdown output.
- No service restarts.
- No environment dumps.
- No raw request/response payloads.
- No API keys, cookies, tokens, or provider credentials printed.
- No DB mutation, checkpoint, vacuum, prune, or deploy performed.

## 16. Footer

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere / Codex | Initial P26.1 dashboard usage query analysis; read-only local and production evidence. |
