# P26.1 SQLite Schema Usage Inventory

| Field | Value |
|---|---|
| Task | P26.1 SQLite schema researcher |
| Output path | `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\research\sqlite-schema-usage-inventory.md` |
| Repo cwd | `C:\Users\faizz\guinevere` |
| Production target | `root@49.12.82.34 -p 39999` |
| Captured at | 2026-06-28T00:17:53+07:00 |
| Remote hostname | `ninerouter-vps` |
| Mode | Read-only local + production metadata inventory |
| Production mutation | None |
| Secret/payload handling | No env dump, no row payload/body dump, no request/response JSON content printed |

## Verdict

PASS for read-only schema and usage inventory.

9Router uses a live SQLite database for usage/request/cost persistence. The canonical production DB path is `/var/lib/9router/db/data.sqlite`; the app-facing path `/root/.9router/db/data.sqlite` resolves to the same target. Usage/cost tables are `usageHistory`, `usageDaily`, and `requestDetails`. `usageHistory` stores normalized per-request token/cost fields; `usageDaily` stores daily aggregate JSON; `requestDetails` stores large full-detail JSON blobs for dashboard request details and is the dominant disk surface.

## Read-Only Commands Used

Local repository search:

```powershell
Get-Content -LiteralPath AGENTS.md
rg -n "sqlite|aiosqlite|sqlite3|SQLITE|\.db|DB_PATH|DATABASE_URL|project_costs|api_cost|token_usage|request_log|usage_log|llm.*usage|cost_total|9router|NINE_ROUTER" -S src tests alembic pyproject.toml .env.example docs/setup-evidence docs/40-operations docs/70-finops
rg --files -g "*.py" -g "*.sql" -g "*.yml" -g "*.yaml" -g "*.json" -g "*.md" | rg "(9router|router|usage|cost|token|metrics|dashboard|grafana|prometheus|sqlite|db|database|llm)" -i
```

Production metadata checks:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'hostname; date -Is'
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'ls -lh /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite-wal /var/lib/9router/db/data.sqlite-shm; stat -c "%n size=%s mode=%a owner=%U:%G mtime=%y" /var/lib/9router/db/data.sqlite /root/.9router/db/data.sqlite; readlink -f /root/.9router/db/data.sqlite /var/lib/9router/db/data.sqlite'
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'sqlite3 "file:/var/lib/9router/db/data.sqlite?mode=ro" "PRAGMA database_list; PRAGMA journal_mode; PRAGMA wal_autocheckpoint; PRAGMA page_size; PRAGMA page_count; PRAGMA freelist_count; PRAGMA auto_vacuum; PRAGMA integrity_check;"'
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'sqlite3 "file:/var/lib/9router/db/data.sqlite?mode=ro" "SELECT name, type FROM sqlite_master WHERE type IN (''table'',''index'',''trigger'',''view'') ORDER BY type,name;"'
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'sqlite3 "file:/var/lib/9router/db/data.sqlite?mode=ro" "SELECT sql FROM sqlite_master WHERE name IN (''usageHistory'',''usageDaily'',''requestDetails'',''idx_uh_ts'',''idx_uh_provider'',''idx_uh_model'',''idx_uh_conn'',''idx_rd_ts'',''idx_rd_provider'',''idx_rd_model'',''idx_rd_conn'') ORDER BY type,name;"'
```

Production aggregate checks, with no payload content:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'sqlite3 -header -column "file:/var/lib/9router/db/data.sqlite?mode=ro" "SELECT ''requestDetails'' table_name, COUNT(*) rows, MIN(timestamp) min_ts, MAX(timestamp) max_ts FROM requestDetails UNION ALL SELECT ''usageHistory'', COUNT(*), MIN(timestamp), MAX(timestamp) FROM usageHistory UNION ALL SELECT ''usageDaily'', COUNT(*), MIN(dateKey), MAX(dateKey) FROM usageDaily;"'
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'sqlite3 -header -column "file:/var/lib/9router/db/data.sqlite?mode=ro" "SELECT ''requestDetails_15m'' metric, COUNT(*) value FROM requestDetails WHERE timestamp >= strftime(''%Y-%m-%dT%H:%M:%fZ'',''now'',''-15 minutes'') UNION ALL SELECT ''usageHistory_15m'', COUNT(*) FROM usageHistory WHERE timestamp >= strftime(''%Y-%m-%dT%H:%M:%fZ'',''now'',''-15 minutes'') UNION ALL SELECT ''requestDetails_1h'', COUNT(*) FROM requestDetails WHERE timestamp >= strftime(''%Y-%m-%dT%H:%M:%fZ'',''now'',''-1 hour'') UNION ALL SELECT ''usageHistory_1h'', COUNT(*) FROM usageHistory WHERE timestamp >= strftime(''%Y-%m-%dT%H:%M:%fZ'',''now'',''-1 hour'') UNION ALL SELECT ''usageHistory_24h'', COUNT(*) FROM usageHistory WHERE timestamp >= strftime(''%Y-%m-%dT%H:%M:%fZ'',''now'',''-24 hours'');"'
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'sqlite3 -header -column "file:/var/lib/9router/db/data.sqlite?mode=ro" "SELECT name, COUNT(*) pages, ROUND(SUM(pgsize)/1048576.0,2) mib FROM dbstat WHERE name IN (''requestDetails'',''usageHistory'',''usageDaily'',''idx_rd_ts'',''idx_rd_provider'',''idx_rd_model'',''idx_rd_conn'') GROUP BY name ORDER BY SUM(pgsize) DESC;"'
```

Production source inventory:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'find /root/9router/.next/standalone -path "*api*usage*route.js" -o -path "*/dashboard/usage/page.js" 2>/dev/null | sort'
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'grep -nE "saveRequestUsage|saveRequestDetail|getRequestDetails|getUsageHistory|getUsageStats|getChartData|appendRequestLog|usageHistory|usageDaily|requestDetails|INSERT|DELETE|SELECT|ORDER BY|LIMIT|pageSize|MAX_|prune|cleanup|timestamp|emit|statsEmitter" /root/9router/src/lib/db/repos/usageRepo.js /root/9router/src/lib/db/repos/requestDetailsRepo.js'
```

## DB Path Discovery

Production DB files:

```text
/var/lib/9router/db/data.sqlite      920M
/var/lib/9router/db/data.sqlite-wal   44M
/var/lib/9router/db/data.sqlite-shm   96K
```

Stat evidence:

```text
/var/lib/9router/db/data.sqlite size=963706880 mode=644 owner=root:root mtime=2026-06-28 00:17:17.941909060 +0700
/root/.9router/db/data.sqlite size=31 mode=777 owner=root:root mtime=2026-06-27 10:04:08.503471541 +0700
readlink -f /root/.9router/db/data.sqlite -> /var/lib/9router/db/data.sqlite
readlink -f /var/lib/9router/db/data.sqlite -> /var/lib/9router/db/data.sqlite
```

Conclusion: SQLite is present and active. Canonical DB path for operations is `/var/lib/9router/db/data.sqlite`; application-facing symlink path is `/root/.9router/db/data.sqlite`.

## SQLite PRAGMA State

Read-only PRAGMA output:

```text
database_list: 0|main|/var/lib/9router/db/data.sqlite
journal_mode: wal
wal_autocheckpoint: 1000
page_size: 4096
page_count: 235280
freelist_count: 44213
auto_vacuum: 0
integrity_check: ok
```

Interpretation:

- WAL mode is enabled.
- `auto_vacuum=0`; deletes will not automatically shrink the main DB file.
- `freelist_count=44213` indicates about 172.7 MiB reusable pages at 4 KiB/page.
- Integrity check passed.

## SQLite Object Inventory

Observed tables:

```text
_meta
apiKeys
combos
kv
providerConnections
providerNodes
proxyPools
requestDetails
settings
sqlite_sequence
usageDaily
usageHistory
```

Observed usage/request/cost-related indexes:

```text
idx_rd_conn
idx_rd_model
idx_rd_provider
idx_rd_ts
idx_uh_conn
idx_uh_model
idx_uh_provider
idx_uh_ts
sqlite_autoindex_requestDetails_1
sqlite_autoindex_usageDaily_1
```

Other routing/config indexes present:

```text
idx_ak_key
idx_combo_name
idx_kv_scope
idx_pc_priority
idx_pc_provider
idx_pc_provider_active
idx_pn_type
idx_pp_active
idx_pp_status
```

## Usage Schema

```sql
CREATE TABLE usageHistory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  provider TEXT,
  model TEXT,
  connectionId TEXT,
  apiKey TEXT,
  endpoint TEXT,
  promptTokens INTEGER DEFAULT 0,
  completionTokens INTEGER DEFAULT 0,
  cost REAL DEFAULT 0,
  status TEXT,
  tokens TEXT,
  meta TEXT
);
CREATE INDEX idx_uh_conn ON usageHistory(connectionId);
CREATE INDEX idx_uh_model ON usageHistory(model);
CREATE INDEX idx_uh_provider ON usageHistory(provider);
CREATE INDEX idx_uh_ts ON usageHistory(timestamp DESC);
```

Purpose: normalized per-request usage accounting. This is the primary visible table for request count, token totals, model/provider breakdown, endpoints, status, and cost.

Security note: `apiKey` is a column name. This research did not select, print, or sample values from that column.

## Daily Aggregate Schema

```sql
CREATE TABLE usageDaily (
  dateKey TEXT PRIMARY KEY,
  data TEXT NOT NULL
);
```

Purpose: per-day aggregate JSON. Prior local evidence states this JSON contains rollups by provider/model/account/API-key/endpoint. This research did not print JSON contents.

## Request Details Schema

```sql
CREATE TABLE requestDetails (
  id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  provider TEXT,
  model TEXT,
  connectionId TEXT,
  status TEXT,
  data TEXT NOT NULL
);
CREATE INDEX idx_rd_conn ON requestDetails(connectionId);
CREATE INDEX idx_rd_model ON requestDetails(model);
CREATE INDEX idx_rd_provider ON requestDetails(provider);
CREATE INDEX idx_rd_ts ON requestDetails(timestamp DESC);
```

Purpose: dashboard request detail records. `data` is full JSON detail blob and can be very large/sensitive. This research only counted rows and storage size; it did not print payload content.

## Counts, Ranges, and Write Frequency Indicators

Production aggregate snapshot:

```text
table_name      rows  min_ts                    max_ts
--------------  ----  ------------------------  ------------------------
requestDetails  1000  2026-06-27T16:31:54.106Z  2026-06-27T17:17:48.287Z
usageHistory    8567  2026-06-26T10:37:57.081Z  2026-06-27T17:17:48.288Z
usageDaily      3     2026-06-26                2026-06-28
```

Recent write-rate proxy, using timestamp comparisons only:

```text
metric              value
------------------  -----
requestDetails_15m  373
usageHistory_15m    376
requestDetails_1h   1000
usageHistory_1h     1426
usageHistory_24h    7399
```

Interpretation:

- Usage/request persistence is actively written.
- `requestDetails` is at its configured cap of 1000 rows and turns over quickly under current traffic.
- `usageHistory` had 7399 rows in the last 24 hours at capture time, so it is the broader accounting history surface.
- `usageDaily` has 3 daily aggregate rows.

## Storage Footprint

`dbstat` aggregate:

```text
name             pages   mib
---------------  ------  ------
requestDetails   189826  741.51
usageHistory     636     2.48
usageDaily       33      0.13
idx_rd_provider  20      0.08
idx_rd_conn      14      0.05
idx_rd_ts        13      0.05
idx_rd_model     9       0.04
```

Interpretation:

- `requestDetails` dominates SQLite disk usage because it stores large detail JSON blobs.
- `usageHistory` is much smaller despite more rows, because it stores normalized columns and smaller JSON fields.
- The relevant indexes are tiny relative to `requestDetails.data`.

## Application Write Path

Source shims:

```text
/root/9router/src/lib/usageDb.js -> re-export from "@/lib/db/index.js"
/root/9router/src/lib/requestDetailsDb.js -> re-export from "@/lib/db/index.js"
```

DB barrel exports:

```text
saveRequestUsage, getUsageHistory, getUsageStats, getChartData,
appendRequestLog, getRecentLogs
saveRequestDetail, getRequestDetails, getRequestDetailById
```

`usageRepo.js` write/read evidence:

```text
saveRequestUsage(entry)
INSERT INTO usageHistory(timestamp, provider, model, connectionId, apiKey, endpoint, promptTokens, completionTokens, cost, status, tokens, meta) VALUES(...)
SELECT data FROM usageDaily WHERE dateKey = ?
INSERT INTO usageDaily(dateKey, data) VALUES(?, ?) ON CONFLICT(dateKey) DO UPDATE SET data = excluded.data
INSERT INTO _meta(key, value) VALUES('totalRequestsLifetime', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value
statsEmitter.emit("update")
getUsageHistory(filter)
SELECT timestamp, provider, model, connectionId, apiKey, endpoint, cost, status, tokens FROM usageHistory ... ORDER BY id ASC
getUsageStats(period)
SELECT timestamp, provider, model, tokens, status FROM usageHistory ORDER BY id DESC LIMIT 100
getChartData(period)
SELECT timestamp, promptTokens, completionTokens, cost FROM usageHistory WHERE timestamp >= ?
appendRequestLog() is no-op; request log is derived from usageHistory table on read.
```

`requestDetailsRepo.js` write/read evidence:

```text
DEFAULT_MAX_RECORDS = 200
maxRecords: settings.observabilityMaxRecords || parseInt(process.env.OBSERVABILITY_MAX_RECORDS || String(DEFAULT_MAX_RECORDS), 10)
DEFAULT_MAX_JSON_SIZE = 5 * 1024
saveRequestDetail(detail)
INSERT INTO requestDetails(id, timestamp, provider, model, connectionId, status, data) VALUES(...) ON CONFLICT(id) DO UPDATE SET ...
SELECT COUNT(*) as c FROM requestDetails
DELETE FROM requestDetails WHERE id IN (SELECT id FROM requestDetails ORDER BY timestamp ASC LIMIT ?)
getRequestDetails(filter)
SELECT COUNT(*) as c FROM requestDetails ...
SELECT data FROM requestDetails ... ORDER BY timestamp DESC LIMIT ? OFFSET ?
getRequestDetailById(id)
SELECT data FROM requestDetails WHERE id = ?
```

Interpretation:

- `saveRequestUsage` writes `usageHistory`, updates `usageDaily`, and increments `_meta.totalRequestsLifetime`.
- `saveRequestDetail` batches writes to `requestDetails`, then deletes oldest rows beyond configured `maxRecords`.
- Runtime has `requestDetails` capped at 1000 rows, so settings/env override appears to be higher than the source default of 200.
- `requestDetails` is used for dashboard details, not routing.

## Dashboard and Endpoint Inventory

Usage/dashboard routes visible in the production build:

```text
/root/9router/.next/standalone/.next/server/app/(dashboard)/dashboard/usage/page.js
/root/9router/.next/standalone/.next/server/app/api/usage/[connectionId]/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/[connectionId]/codex-reset-credits/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/chart/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/history/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/logs/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/providers/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/request-details/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/request-logs/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/stats/route.js
/root/9router/.next/standalone/.next/server/app/api/usage/stream/route.js
```

Source-level route evidence:

```text
/root/9router/src/app/api/usage/request-details/route.js imports getRequestDetails from "@/lib/usageDb"
/root/9router/src/app/api/usage/providers/route.js imports getRequestDetails from "@/lib/requestDetailsDb"
/root/9router/src/app/(dashboard)/dashboard/usage/components/RequestDetailsTab.js fetches "/api/usage/providers"
/root/9router/src/app/(dashboard)/dashboard/usage/components/RequestDetailsTab.js fetches "/api/usage/request-details?..."
/root/9router/src/app/(dashboard)/dashboard/usage/components/UsageChart.js fetches "/api/usage/chart?period=..."
/root/9router/src/app/(dashboard)/dashboard/usage/components/ProviderLimits/index.js fetches "/api/usage/${connectionId}"
```

Previous P26 route timing evidence, read-only and unauthenticated:

```text
/dashboard/usage -> 307 redirect to /login
/api/usage/stats -> 401 without auth
/api/usage/history -> 401 without auth
/api/usage/request-details?page=1&pageSize=10 -> 401 without auth
```

Interpretation:

- Dashboard details tab reads `requestDetails`.
- Usage overview/chart/history reads `usageHistory`/`usageDaily`.
- Provider usage routes use usage/request detail repositories.
- API routes are auth-gated; this research did not use cookies or print response bodies.

## Local Repository Cross-Checks

Local docs and evidence align with production:

- `docs/setup-evidence/P26/requestdetails-autoprune/research/current-dashboard-db-ground-truth.md` previously found `/var/lib/9router/db/data.sqlite`, `requestDetails` schema, 1000 detail rows, and `usageHistory`/`usageDaily` counts.
- `docs/setup-evidence/P26/requestdetails-autoprune/research/db-audit.md` previously found `requestDetails` as the dominant disk surface and confirmed `usageHistory`/`usageDaily` are smaller.
- `docs/setup-evidence/P26/highend-2worker-tuning/research/sqlite-lock-analysis.md` discovered `/root/.9router/db/data.sqlite -> /var/lib/9router/db/data.sqlite`, WAL mode, and SQLite lock contention under PM2 two-worker topology.
- `docs/setup-evidence/fixes/evidence-cost-tracker-9router-sqlite.md` documents the cost tracker moving from partial Redis data to 9Router SQLite `usageHistory`/`usageDaily` as primary data source.

Canonical Guinevere app memory remains PostgreSQL + Redis per ADRs; this SQLite inventory is specific to the 9Router runtime's internal persistence.

## Implications for Redis Write Buffer Work

Candidate high-write surfaces:

| Surface | Write pattern | Risk/Notes |
|---|---|---|
| `requestDetails` | Frequent batched insert/update plus oldest-row delete after count cap | Largest disk surface; writes can contend under PM2 workers; payload column must never be logged. |
| `usageHistory` | One insert per completed request usage | Primary token/cost accounting history; much smaller row footprint but high row volume. |
| `usageDaily` | One upsert per usage save by date key | Aggregate JSON; small table but write-amplified by every usage event. |
| `_meta.totalRequestsLifetime` | Upsert/increment per usage save | Tiny table, still part of write transaction. |

Potential Redis buffer target: buffer request/usage writes before SQLite flush, but preserve ordering, idempotency, and crash recovery semantics. A buffer must not lose `usageHistory` rows, must not duplicate cost totals, and must not expose `requestDetails.data`.

## Boundary Compliance

| Boundary | Result |
|---|---|
| Read `AGENTS.md` first | PASS |
| Production actions read-only | PASS |
| No service restart | PASS |
| No DB write/delete/update/insert/vacuum/checkpoint | PASS |
| No env dump | PASS |
| No row payload/body dump | PASS |
| No secrets printed | PASS |
| Output markdown written at requested path | PASS |

## Caveats

- Source snippets were read from the live 9Router source tree and built route files. Minified built files were only used for route existence; source repo files were used for function-level evidence.
- Recent write indicators are timestamp-count proxies, not direct SQLite write tracing.
- Authenticated dashboard response timing was not re-run in this task because safe auth material was not provided and the task prohibited secret exposure.

## Footer

P26.1 SQLite schema usage inventory generated 2026-06-28. This report is research-only and authorizes no production mutation.
